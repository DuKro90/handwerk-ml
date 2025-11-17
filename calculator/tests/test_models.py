"""
Tests for calculator models
"""
import pytest
from decimal import Decimal
from datetime import date
from calculator.models import Project, Material, ProjectMaterial


@pytest.mark.django_db
class TestProject:
    """Test Project model"""

    def test_create_project(self):
        """Test creating a project"""
        project = Project.objects.create(
            name="Treppenbau Test",
            description="Eine Testrenovierung",
            project_type="Treppenbau",
            region="Süd",
            total_area_sqm=Decimal("25.50"),
            wood_type="Eiche",
            complexity=2,
            final_price=Decimal("5000.00"),
            project_date=date.today()
        )

        assert project.id is not None
        assert project.name == "Treppenbau Test"
        assert not project.is_finalized

    def test_finalize_project(self):
        """Test finalizing a project"""
        project = Project.objects.create(
            name="Finalize Test",
            description="Test",
            project_type="Möbelbau",
            region="Nord",
            total_area_sqm=Decimal("10.00"),
            wood_type="Kiefer",
            complexity=1,
            final_price=Decimal("2000.00"),
            project_date=date.today()
        )

        project.is_finalized = True
        project.save()

        assert project.is_finalized
        assert project.finalized_at is not None

    def test_cannot_modify_finalized_project(self):
        """Test that finalized projects cannot be modified"""
        project = Project.objects.create(
            name="Immutable Test",
            description="Test",
            project_type="Dachstuhl",
            region="Mitte",
            total_area_sqm=Decimal("100.00"),
            wood_type="Buche",
            complexity=3,
            final_price=Decimal("15000.00"),
            project_date=date.today(),
            is_finalized=True
        )

        # Attempting to modify should raise ValueError
        project.name = "Modified Name"
        with pytest.raises(ValueError, match="Finalisierte Projekte"):
            project.save()


@pytest.mark.django_db
class TestMaterial:
    """Test Material model"""

    def test_create_material(self):
        """Test creating a material"""
        material = Material.objects.create(
            name="Eichenholz",
            category="Holz",
            unit="m³",
            datanorm_id="DN-1234"
        )

        assert material.id is not None
        assert material.name == "Eichenholz"
        assert material.category == "Holz"


@pytest.mark.django_db
class TestProjectMaterial:
    """Test ProjectMaterial model"""

    def test_add_material_to_project(self):
        """Test adding materials to a project"""
        project = Project.objects.create(
            name="Material Test",
            description="Test",
            project_type="Möbelbau",
            region="Süd",
            total_area_sqm=Decimal("20.00"),
            wood_type="Ahorn",
            complexity=2,
            final_price=Decimal("3000.00"),
            project_date=date.today()
        )

        material = Material.objects.create(
            name="Ahorn",
            category="Holz",
            unit="m³"
        )

        pm = ProjectMaterial.objects.create(
            project=project,
            material=material,
            quantity=Decimal("5.00"),
            unit_price=Decimal("100.00"),
            total_cost=Decimal("500.00")
        )

        assert pm.project == project
        assert pm.material == material
        assert pm.total_cost == Decimal("500.00")
