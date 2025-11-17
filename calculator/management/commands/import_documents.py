"""
Management command to import documents from directory structure
Supports nested project folders with multiple file types
"""

import os
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from calculator.models import Document, Project
from calculator.document_processor import (
    DocumentProcessor, DocumentEmbedder, DocumentFeatureExtractor, DocumentSearcher
)


class Command(BaseCommand):
    help = 'Import documents from directory structure and process them for ML'

    def add_arguments(self, parser):
        parser.add_argument(
            'source_directory',
            type=str,
            help='Source directory with documents/projects'
        )
        parser.add_argument(
            '--create-projects',
            action='store_true',
            help='Create projects from folder names'
        )
        parser.add_argument(
            '--project-type',
            type=str,
            default='Verschiedenes',
            help='Project type to assign (default: Verschiedenes)'
        )
        parser.add_argument(
            '--region',
            type=str,
            default='Unbekannt',
            help='Region to assign (default: Unbekannt)'
        )
        parser.add_argument(
            '--embed',
            action='store_true',
            help='Create embeddings for documents'
        )
        parser.add_argument(
            '--recursive',
            action='store_true',
            default=True,
            help='Scan subdirectories recursively (default: True)'
        )

    def handle(self, *args, **options):
        source_dir = Path(options['source_directory'])

        if not source_dir.exists():
            raise CommandError(f'Directory does not exist: {source_dir}')

        self.stdout.write(self.style.SUCCESS('📁 Starting document import...'))
        self.stdout.write(f'Source: {source_dir}')

        # Ensure storage directory exists
        DocumentProcessor.ensure_storage_dir()

        stats = {
            'imported': 0,
            'skipped': 0,
            'errors': 0,
            'projects_created': 0,
        }

        # Import documents
        self.import_directory(
            source_dir,
            options,
            stats
        )

        # Process documents if requested
        if options['embed']:
            self.process_documents(stats)

        # Print summary
        self.print_summary(stats)

    def import_directory(self, directory: Path, options: dict, stats: dict, parent_project=None):
        """Recursively import documents from directory"""

        # List all items in directory
        try:
            items = sorted(directory.iterdir())
        except PermissionError:
            self.stdout.write(self.style.WARNING(f'⚠️ Permission denied: {directory}'))
            return

        # Separate folders and files
        folders = [item for item in items if item.is_dir()]
        files = [item for item in items if item.is_file()]

        # Process subdirectories first (if recursive)
        for folder in folders:
            # Skip hidden and system folders
            if folder.name.startswith('.'):
                continue

            self.stdout.write(f'\n📂 Processing folder: {folder.name}')

            # Create project for this folder if requested
            project = None
            if options['create_projects']:
                project = self.get_or_create_project(
                    folder.name,
                    options['project_type'],
                    options['region']
                )
                if project:
                    stats['projects_created'] += 1
                    self.stdout.write(f'  ✓ Created/Found project: {project.name}')

            # Recursively process subfolder
            self.import_directory(folder, options, stats, project)

        # Process files in current directory
        for file_path in files:
            result = self.process_file(file_path, options, parent_project)
            if result == 'imported':
                stats['imported'] += 1
                self.stdout.write(f'  ✓ Imported: {file_path.name}')
            elif result == 'skipped':
                stats['skipped'] += 1
            elif result == 'error':
                stats['errors'] += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error processing: {file_path.name}')
                )

    def process_file(self, file_path: Path, options: dict, project=None) -> str:
        """Process a single file"""

        # Determine file type
        suffix = file_path.suffix.lower()
        file_type = self.get_file_type(suffix)

        if not file_type:
            return 'skipped'

        # Check if already imported
        if Document.objects.filter(filename=file_path.name).exists():
            return 'skipped'

        try:
            # Save file to documents_storage
            file_rel_path = DocumentProcessor.save_uploaded_file(
                FileWrapper(file_path),
                file_path.name
            )

            full_path = DocumentProcessor.get_file_path(file_rel_path)
            file_size = DocumentProcessor.get_file_size(full_path)

            # Create Document record
            document = Document.objects.create(
                filename=file_path.name,
                file_type=file_type,
                file_path=file_rel_path,
                file_size_bytes=file_size,
                project=project,
                processing_status='pending',
                uploaded_by='import_script'
            )

            return 'imported'

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            return 'error'

    def get_or_create_project(self, folder_name: str, project_type: str, region: str):
        """Get or create project from folder name"""
        try:
            project, created = Project.objects.get_or_create(
                name=folder_name,
                defaults={
                    'description': f'Automatisch erstellt aus Ordner: {folder_name}',
                    'project_type': project_type,
                    'region': region,
                    'complexity': 2,
                    'project_date': timezone.now().date(),
                    'final_price': 0,
                }
            )
            return project
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating project: {str(e)}'))
            return None

    def process_documents(self, stats: dict):
        """Process pending documents"""
        self.stdout.write(self.style.SUCCESS('\n🔄 Processing documents...'))

        pending_docs = Document.objects.filter(processing_status='pending')

        try:
            embedder = DocumentEmbedder()
            has_embedder = True
        except ImportError:
            self.stdout.write(
                self.style.WARNING('⚠️ sentence-transformers not available, skipping embeddings')
            )
            has_embedder = False

        for doc in pending_docs:
            try:
                full_path = DocumentProcessor.get_file_path(doc.file_path)

                if not os.path.exists(full_path):
                    doc.processing_status = 'failed'
                    doc.processing_error = 'File not found'
                    doc.save()
                    continue

                # Process document
                result = DocumentProcessor.process_document(full_path, doc.file_type)

                if result['success']:
                    # Update document with extracted content
                    doc.text_content = result['text_content']
                    doc.text_preview = DocumentProcessor.create_text_preview(
                        result['text_content']
                    )

                    # Add metadata
                    for key, value in result['metadata'].items():
                        setattr(doc, key, value)

                    # Create searchable text
                    doc.searchable_text = DocumentSearcher.prepare_search_text(
                        result['text_content']
                    )

                    # Extract features
                    features = DocumentFeatureExtractor.extract_features(
                        result['text_content'],
                        doc.file_type,
                        result['metadata']
                    )
                    doc.extracted_features = features

                    # Create embedding if available
                    if has_embedder and result['text_content']:
                        embedding = embedder.embed_text(result['text_content'])
                        if embedding:
                            doc.embedding = embedding

                    doc.processing_status = 'completed'
                    doc.last_processed = timezone.now()
                    self.stdout.write(f'  ✓ Processed: {doc.filename}')

                else:
                    doc.processing_status = 'failed'
                    doc.processing_error = result['error']

                doc.save()

            except Exception as e:
                doc.processing_status = 'failed'
                doc.processing_error = str(e)
                doc.save()
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error processing {doc.filename}: {str(e)}')
                )

    def get_file_type(self, suffix: str) -> str:
        """Determine file type from suffix"""
        suffix = suffix.lower()

        if suffix == '.pdf':
            return 'pdf'
        elif suffix == '.docx':
            return 'docx'
        elif suffix in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
            return 'image'
        elif suffix == '.txt':
            return 'txt'
        else:
            return None

    def print_summary(self, stats: dict):
        """Print import summary"""
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('📊 Import Summary'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'✓ Imported:        {stats["imported"]}')
        self.stdout.write(f'⊘ Skipped:         {stats["skipped"]}')
        self.stdout.write(f'✗ Errors:          {stats["errors"]}')
        self.stdout.write(f'📁 Projects:       {stats["projects_created"]}')
        self.stdout.write(self.style.SUCCESS('='*50))


class FileWrapper:
    """Wrapper to read file in chunks like Django UploadedFile"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.file = None

    def chunks(self, chunk_size=2621440):  # 2.5 MB
        with open(self.file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
