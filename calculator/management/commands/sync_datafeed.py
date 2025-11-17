"""
Management command to sync data from ML_Datafeed directory
Imports documents and updates project data
"""

import os
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction

from calculator.models import Document, Project
from calculator.document_processor import DocumentProcessor


class Command(BaseCommand):
    help = 'Synchronize database with ML_Datafeed directory'

    def add_arguments(self, parser):
        parser.add_argument(
            '--datafeed-path',
            type=str,
            default='C:\\ML_Datafeed',
            help='Path to ML_Datafeed directory'
        )
        parser.add_argument(
            '--import-docs',
            action='store_true',
            help='Import documents from datafeed'
        )
        parser.add_argument(
            '--sync-projects',
            action='store_true',
            help='Sync project data'
        )
        parser.add_argument(
            '--full-sync',
            action='store_true',
            help='Full synchronization (docs + projects)'
        )

    def handle(self, *args, **options):
        datafeed_path = Path(options['datafeed_path'])

        if not datafeed_path.exists():
            raise CommandError(f'Datafeed directory not found: {datafeed_path}')

        self.stdout.write(self.style.SUCCESS('🔄 Starting database synchronization...'))
        self.stdout.write(f'Datafeed: {datafeed_path}')

        stats = {
            'documents_imported': 0,
            'documents_updated': 0,
            'documents_failed': 0,
            'projects_synced': 0,
            'projects_updated': 0,
            'errors': []
        }

        # Determine what to sync
        if options['full_sync']:
            do_docs = True
            do_projects = True
        else:
            do_docs = options['import_docs']
            do_projects = options['sync_projects']

        # If nothing specified, do everything
        if not do_docs and not do_projects:
            do_docs = True
            do_projects = True

        # Sync documents
        if do_docs:
            self.sync_documents(datafeed_path, stats)

        # Sync projects
        if do_projects:
            self.sync_projects(datafeed_path, stats)

        # Print summary
        self.print_summary(stats)

    def sync_documents(self, datafeed_path: Path, stats: dict):
        """Sync documents from datafeed"""
        self.stdout.write('\n📄 Syncing documents...')

        docs_dir = datafeed_path / 'documents'
        if not docs_dir.exists():
            self.stdout.write(self.style.WARNING(f'  ⚠️ Documents folder not found: {docs_dir}'))
            return

        try:
            # Get all files in documents folder
            files = list(docs_dir.rglob('*'))
            files = [f for f in files if f.is_file()]

            self.stdout.write(f'  Found {len(files)} files to process')

            for file_path in files:
                try:
                    # Check if already imported
                    if Document.objects.filter(filename=file_path.name).exists():
                        stats['documents_updated'] += 1
                        self.stdout.write(f'  ↻ Already exists: {file_path.name}')
                        continue

                    # Determine file type
                    file_type = self._get_file_type(file_path)
                    if not file_type:
                        self.stdout.write(f'  ⊘ Skipped (unsupported): {file_path.name}')
                        continue

                    # Copy file to documents_storage
                    rel_path = self._copy_file_to_storage(file_path)
                    full_path = DocumentProcessor.get_file_path(rel_path)

                    # Create document record
                    document = Document.objects.create(
                        filename=file_path.name,
                        file_type=file_type,
                        file_path=rel_path,
                        file_size_bytes=file_path.stat().st_size,
                        processing_status='pending',
                        uploaded_by='datafeed_sync'
                    )

                    stats['documents_imported'] += 1
                    self.stdout.write(f'  ✓ Imported: {file_path.name}')

                except Exception as e:
                    stats['documents_failed'] += 1
                    stats['errors'].append(f'Document error {file_path.name}: {str(e)}')
                    self.stdout.write(self.style.ERROR(f'  ✗ Error: {file_path.name}'))

        except Exception as e:
            stats['errors'].append(f'Documents sync error: {str(e)}')
            self.stdout.write(self.style.ERROR(f'Error syncing documents: {str(e)}'))

    def sync_projects(self, datafeed_path: Path, stats: dict):
        """Sync projects from datafeed"""
        self.stdout.write('\n🏗️ Syncing projects...')

        projects_file = datafeed_path / 'projects.json'
        if not projects_file.exists():
            self.stdout.write(self.style.WARNING(f'  ⚠️ Projects file not found: {projects_file}'))
            return

        try:
            with open(projects_file, 'r', encoding='utf-8') as f:
                projects_data = json.load(f)

            if not isinstance(projects_data, list):
                projects_data = [projects_data]

            self.stdout.write(f'  Found {len(projects_data)} projects to sync')

            with transaction.atomic():
                for proj_data in projects_data:
                    try:
                        # Get or create project
                        project, created = Project.objects.get_or_create(
                            name=proj_data.get('name'),
                            defaults={
                                'description': proj_data.get('description', ''),
                                'project_type': proj_data.get('project_type', 'Verschiedenes'),
                                'region': proj_data.get('region', 'Unbekannt'),
                                'total_area_sqm': proj_data.get('total_area_sqm'),
                                'wood_type': proj_data.get('wood_type', 'Gemischt'),
                                'complexity': proj_data.get('complexity', 2),
                                'project_date': proj_data.get('project_date', timezone.now().date()),
                                'final_price': proj_data.get('final_price', 0),
                            }
                        )

                        if created:
                            stats['projects_synced'] += 1
                            self.stdout.write(f'  ✓ Created: {project.name}')
                        else:
                            # Update existing project
                            for key, value in proj_data.items():
                                if key != 'name' and hasattr(project, key):
                                    setattr(project, key, value)
                            project.save()
                            stats['projects_updated'] += 1
                            self.stdout.write(f'  ↻ Updated: {project.name}')

                    except Exception as e:
                        stats['errors'].append(f'Project error {proj_data.get("name")}: {str(e)}')
                        self.stdout.write(self.style.ERROR(f'  ✗ Error: {proj_data.get("name")}'))

        except json.JSONDecodeError as e:
            stats['errors'].append(f'Invalid JSON in projects.json: {str(e)}')
            self.stdout.write(self.style.ERROR(f'Invalid JSON: {str(e)}'))
        except Exception as e:
            stats['errors'].append(f'Projects sync error: {str(e)}')
            self.stdout.write(self.style.ERROR(f'Error syncing projects: {str(e)}'))

    def _get_file_type(self, file_path: Path) -> str:
        """Determine file type from path"""
        ext = file_path.suffix.lower()

        type_map = {
            '.pdf': 'pdf',
            '.docx': 'docx',
            '.doc': 'docx',
            '.jpg': 'image',
            '.jpeg': 'image',
            '.png': 'image',
            '.bmp': 'image',
            '.gif': 'image',
            '.txt': 'txt',
        }

        return type_map.get(ext)

    def _copy_file_to_storage(self, source_path: Path) -> str:
        """Copy file to documents_storage and return relative path"""
        import uuid
        import shutil

        DocumentProcessor.ensure_storage_dir()

        # Generate unique filename
        file_ext = source_path.suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        rel_path = unique_filename
        dest_path = DocumentProcessor.DOCUMENTS_DIR / unique_filename

        # Copy file
        shutil.copy2(source_path, dest_path)

        return rel_path

    def print_summary(self, stats: dict):
        """Print synchronization summary"""
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('📊 Synchronization Summary'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'📄 Documents Imported:  {stats["documents_imported"]}')
        self.stdout.write(f'↻  Documents Updated:   {stats["documents_updated"]}')
        self.stdout.write(f'✗  Documents Failed:    {stats["documents_failed"]}')
        self.stdout.write(f'🏗️  Projects Synced:     {stats["projects_synced"]}')
        self.stdout.write(f'↻  Projects Updated:    {stats["projects_updated"]}')

        if stats['errors']:
            self.stdout.write(self.style.WARNING(f'\n⚠️ Errors ({len(stats["errors"])}):'))
            for error in stats['errors'][:5]:
                self.stdout.write(self.style.WARNING(f'  - {error}'))

        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(self.style.SUCCESS('✓ Synchronization complete!'))
