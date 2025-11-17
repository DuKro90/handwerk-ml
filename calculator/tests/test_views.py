"""
Tests for REST API views
"""
import pytest
from decimal import Decimal
from datetime import date
from rest_framework.test import APIClient, APITestCase
from rest_framework import status

from calculator.models import Project, Material, MaterialPrice, ProjectMaterial
from calculator.serializers import ProjectListSerializer


@pytest.mark.django_db
class ProjectAPITestCase(APITestCase):
    """Test Project API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.project = Project.objects.create(
            name="Test Project",
            description="Test Description",
            project_type="Treppenbau",
            region="Nord",
            total_area_sqm=Decimal("25.00"),
            wood_type="Eiche",
            complexity=2,
            final_price=Decimal("5000.00"),
            project_date=date.today()
        )

    def test_list_projects(self):
        """Test listing all projects"""
        response = self.client.get('/api/v1/projects/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_get_project_detail(self):
        """Test getting project details"""
        response = self.client.get(f'/api/v1/projects/{self.project.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == "Test Project"

    def test_create_project(self):
        """Test creating a project"""
        data = {
            'name': 'New Project',
            'description': 'New Description',
            'project_type': 'Möbelbau',
            'region': 'Süd',
            'total_area_sqm': 50.00,
            'wood_type': 'Kiefer',
            'complexity': 1,
            'final_price': 3000.00,
            'project_date': str(date.today())
        }
        response = self.client.post('/api/v1/projects/', data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Project'

    def test_update_project(self):
        """Test updating a project"""
        data = {'name': 'Updated Name'}
        response = self.client.patch(f'/api/v1/projects/{self.project.id}/', data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Name'

    def test_finalize_project(self):
        """Test finalizing a project"""
        response = self.client.post(f'/api/v1/projects/{self.project.id}/finalize/')
        assert response.status_code == status.HTTP_200_OK

        # Verify project is finalized
        self.project.refresh_from_db()
        assert self.project.is_finalized

    def test_cannot_modify_finalized_project(self):
        """Test that finalized projects cannot be modified"""
        self.project.is_finalized = True
        self.project.save()

        data = {'name': 'New Name'}
        response = self.client.patch(f'/api/v1/projects/{self.project.id}/', data)
        # Should raise error or return 400
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN]

    def test_delete_project(self):
        """Test deleting a project"""
        response = self.client.delete(f'/api/v1/projects/{self.project.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_get_recent_projects(self):
        """Test getting recent projects"""
        response = self.client.get('/api/v1/projects/recent/')
        assert response.status_code == status.HTTP_200_OK

    def test_get_projects_by_type(self):
        """Test filtering projects by type"""
        response = self.client.get('/api/v1/projects/by_type/?type=Treppenbau')
        assert response.status_code == status.HTTP_200_OK

    def test_get_project_statistics(self):
        """Test getting project statistics"""
        response = self.client.get('/api/v1/projects/statistics/')
        assert response.status_code == status.HTTP_200_OK
        assert 'total_projects' in response.data


@pytest.mark.django_db
class MaterialAPITestCase(APITestCase):
    """Test Material API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.material = Material.objects.create(
            name="Eichenholz",
            category="Holz",
            unit="m³"
        )

    def test_list_materials(self):
        """Test listing materials"""
        response = self.client.get('/api/v1/materials/')
        assert response.status_code == status.HTTP_200_OK

    def test_create_material(self):
        """Test creating a material"""
        data = {
            'name': 'Buchenholz',
            'category': 'Holz',
            'unit': 'm³'
        }
        response = self.client.post('/api/v1/materials/', data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_filter_by_category(self):
        """Test filtering materials by category"""
        response = self.client.get('/api/v1/materials/by_category/?category=Holz')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class PricePredictionAPITestCase(APITestCase):
    """Test Price Prediction API endpoints"""

    def setUp(self):
        self.client = APIClient()

    def test_create_prediction(self):
        """Test creating a price prediction"""
        data = {
            'name': 'Test Project',
            'description': 'Test description for prediction',
            'project_type': 'Treppenbau',
            'wood_type': 'Eiche',
            'total_area_sqm': 25.5,
            'complexity': 2,
            'region': 'Nord'
        }
        response = self.client.post('/api/v1/predictions/predict/', data)
        assert response.status_code == status.HTTP_201_CREATED
        assert 'predicted_price' in response.data

    def test_get_accuracy_metrics(self):
        """Test getting model accuracy metrics"""
        response = self.client.get('/api/v1/predictions/accuracy_metrics/')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class AuditAPITestCase(APITestCase):
    """Test Audit Trail API endpoints"""

    def setUp(self):
        self.client = APIClient()

    def test_list_audit_logs(self):
        """Test listing audit logs"""
        response = self.client.get('/api/v1/audit/recent/')
        assert response.status_code == status.HTTP_200_OK

    def test_get_audit_by_record(self):
        """Test getting audit logs for a specific record"""
        from uuid import uuid4
        record_id = uuid4()
        response = self.client.get(
            f'/api/v1/audit/by_record/?record_id={record_id}&table_name=calculator_project'
        )
        # Should return 200 even if no results
        assert response.status_code == status.HTTP_200_OK
