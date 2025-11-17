"""
Management command to generate synthetic training data for ML model
Usage: python manage.py generate_training_data --count 100
"""
from django.core.management.base import BaseCommand
from calculator.models import Project, Material, MaterialPrice, ProjectMaterial
from faker import Faker
from datetime import datetime, timedelta
import random
from decimal import Decimal


class Command(BaseCommand):
    help = 'Generate synthetic training data for ML model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=100,
            help='Number of projects to generate (default: 100)'
        )

    def handle(self, *args, **options):
        fake = Faker('de_DE')
        count = options['count']

        self.stdout.write(f"Generating {count} synthetic projects...")

        # Define categories and types
        project_types = ['Treppenbau', 'Dachstuhl', 'Möbelbau', 'Türen', 'Fenster']
        wood_types = ['Eiche', 'Kiefer', 'Buche', 'Ahorn', 'Erle']
        regions = ['Nord', 'Süd', 'Ost', 'West', 'Mitte']
        material_categories = ['Holz', 'Beschläge', 'Oberflächenbehandlung']

        # Create or get materials
        materials = []
        for category in material_categories:
            for i in range(3):
                material, created = Material.objects.get_or_create(
                    name=f'{category} Material {i+1}',
                    defaults={
                        'category': category,
                        'unit': 'm²' if category == 'Holz' else 'Stk',
                        'datanorm_id': f'DN-{category}-{i+1}'
                    }
                )
                materials.append(material)

        # Generate projects
        start_date = datetime.now() - timedelta(days=365)

        for i in range(count):
            project = Project.objects.create(
                name=f"Projekt {i+1}: {fake.catch_phrase()}",
                description=fake.paragraph(nb_sentences=3),
                project_type=random.choice(project_types),
                region=random.choice(regions),
                total_area_sqm=Decimal(str(random.uniform(10, 500))),
                wood_type=random.choice(wood_types),
                complexity=random.choice([1, 2, 3]),
                final_price=Decimal(str(random.uniform(1000, 50000))),
                project_date=(start_date + timedelta(days=random.randint(0, 365))).date(),
                is_finalized=random.choice([True, True, False]),  # 2/3 chance of finalized
            )

            # Add materials to project
            for _ in range(random.randint(2, 5)):
                material = random.choice(materials)
                quantity = Decimal(str(random.uniform(1, 100)))
                unit_price = Decimal(str(random.uniform(10, 500)))

                ProjectMaterial.objects.create(
                    project=project,
                    material=material,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_cost=quantity * unit_price
                )

            if (i + 1) % 10 == 0:
                self.stdout.write(f"  Created {i+1}/{count} projects...")

        self.stdout.write(self.style.SUCCESS(f'✓ Successfully generated {count} projects'))
