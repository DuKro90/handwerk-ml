"""
Pytest configuration and fixtures for calculator app
"""
import pytest
from decimal import Decimal
from datetime import date
from django.contrib.auth.models import User

from calculator.models import Project, Material, MaterialPrice, ProjectMaterial


@pytest.fixture
def user():
    """Create a test user"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpassword123'
    )


@pytest.fixture
def admin_user():
    """Create a test admin user"""
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpassword123'
    )


@pytest.fixture
def material():
    """Create a test material"""
    return Material.objects.create(
        name='Eichenholz',
        category='Holz',
        unit='m³',
        datanorm_id='DN-001'
    )


@pytest.fixture
def material_price(material):
    """Create a test material price"""
    return MaterialPrice.objects.create(
        material=material,
        price=Decimal('100.00'),
        region='Nord',
        valid_from=date.today()
    )


@pytest.fixture
def project():
    """Create a test project"""
    return Project.objects.create(
        name='Test Project',
        description='A test project for Treppenbau',
        project_type='Treppenbau',
        region='Süd',
        total_area_sqm=Decimal('25.50'),
        wood_type='Eiche',
        complexity=2,
        final_price=Decimal('5000.00'),
        project_date=date.today(),
        is_finalized=False
    )


@pytest.fixture
def finalized_project():
    """Create a finalized test project"""
    return Project.objects.create(
        name='Finalized Project',
        description='A finalized project',
        project_type='Möbelbau',
        region='Nord',
        total_area_sqm=Decimal('50.00'),
        wood_type='Kiefer',
        complexity=1,
        final_price=Decimal('3000.00'),
        project_date=date.today(),
        is_finalized=True
    )


@pytest.fixture
def project_with_materials(project, material):
    """Create a project with materials"""
    ProjectMaterial.objects.create(
        project=project,
        material=material,
        quantity=Decimal('10.00'),
        unit_price=Decimal('100.00'),
        total_cost=Decimal('1000.00')
    )
    return project


@pytest.fixture
def sample_projects():
    """Create multiple sample projects for testing"""
    projects = []
    project_types = ['Treppenbau', 'Dachstuhl', 'Möbelbau']
    wood_types = ['Eiche', 'Kiefer', 'Buche']
    regions = ['Nord', 'Süd', 'Ost']

    for i in range(10):
        project = Project.objects.create(
            name=f'Sample Project {i+1}',
            description=f'Sample project number {i+1} for testing ML training',
            project_type=project_types[i % len(project_types)],
            region=regions[i % len(regions)],
            total_area_sqm=Decimal(str(20 + i * 5)),
            wood_type=wood_types[i % len(wood_types)],
            complexity=(i % 3) + 1,
            final_price=Decimal(str(2000 + i * 500)),
            project_date=date.today(),
            is_finalized=True
        )
        projects.append(project)

    return projects


@pytest.fixture
def api_client():
    """Create an API client for testing"""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_api_client(api_client, user):
    """Create an authenticated API client"""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_api_client(api_client, admin_user):
    """Create an admin API client"""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def prediction_data():
    """Create sample prediction data"""
    return {
        'name': 'Test Prediction',
        'description': 'A test prediction for a woodworking project',
        'project_type': 'Treppenbau',
        'wood_type': 'Eiche',
        'total_area_sqm': 25.5,
        'complexity': 2,
        'region': 'Nord'
    }
