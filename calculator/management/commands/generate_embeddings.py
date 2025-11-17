"""
Management Command: Generiert Embeddings für alle Projekte
Lädt das SentenceTransformer-Modell und berechnet Embeddings für Descriptions
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache
from calculator.models import Project
from calculator.ml.embeddings import EmbeddingGenerator
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generiert Embeddings für alle Projekte ohne Embedding'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regeneriere Embeddings auch für bestehende'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('⏳ Starte Embedding-Generierung...'))

        # Filter Projekte
        if options['force']:
            projects = Project.objects.all()
            self.stdout.write(f"📝 Force-Modus: {projects.count()} Projekte")
        else:
            projects = Project.objects.filter(description_embedding__isnull=True)
            self.stdout.write(f"📝 {projects.count()} Projekte ohne Embedding")

        if projects.count() == 0:
            self.stdout.write(self.style.SUCCESS('✓ Alle Projekte haben schon Embeddings!'))
            return

        # Lade Embedding-Generator
        generator = EmbeddingGenerator()

        if not generator.model:
            self.stdout.write(self.style.ERROR('✗ Modell konnte nicht geladen werden!'))
            return

        # Generiere Embeddings
        success_count = 0
        for i, project in enumerate(projects, 1):
            if not project.description:
                self.stdout.write(f"⚠️  {i}/{projects.count()}: {project.name} hat keine Beschreibung")
                continue

            try:
                embedding = generator.generate_embedding(project.description)
                if embedding:
                    project.description_embedding = embedding
                    project.save(update_fields=['description_embedding'])
                    success_count += 1

                    if i % 10 == 0:
                        self.stdout.write(f"✓ {i}/{projects.count()} Embeddings generiert")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Fehler bei {project.name}: {e}"))

        # Summary
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Fertig! {success_count}/{projects.count()} Embeddings generiert'
        ))

        # Cache invalidieren
        cache.delete('embedding_model')
