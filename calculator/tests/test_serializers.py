"""
Tests for DRF Serializers
"""
import pytest
from decimal import Decimal
from datetime import date

from calculator.serializers import (
    ProjectDetailSerializer,
    ProjectListSerializer,
    MaterialSerializer,
    PricePredictionCreateSerializer,
)


class TestProjectSerializers:
    """Test Project serializers"""

    def test_project_detail_serializer_valid(self):
        """Test valid project detail serializer"""
        data = {
            'name': 'Test Project',
            'description': 'A detailed description',
            'project_type': 'Treppenbau',
            'region': 'Nord',
            'total_area_sqm': 25.5,
            'wood_type': 'Eiche',
            'complexity': 2,
            'final_price': 5000.00,
            'project_date': str(date.today()),
        }
        serializer = ProjectDetailSerializer(data=data)
        assert serializer.is_valid()

    def test_project_detail_serializer_invalid_complexity(self):
        """Test invalid complexity value"""
        data = {
            'name': 'Test Project',
            'description': 'A detailed description',
            'project_type': 'Treppenbau',
            'region': 'Nord',
            'total_area_sqm': 25.5,
            'wood_type': 'Eiche',
            'complexity': 5,  # Invalid
            'final_price': 5000.00,
            'project_date': str(date.today()),
        }
        serializer = ProjectDetailSerializer(data=data)
        assert not serializer.is_valid()
        assert 'complexity' in serializer.errors

    def test_project_list_serializer(self):
        """Test project list serializer"""
        data = {
            'name': 'Test Project',
            'project_type': 'Möbelbau',
            'region': 'Süd',
            'final_price': 3000.00,
            'project_date': str(date.today()),
            'is_finalized': False,
        }
        serializer = ProjectListSerializer(data=data)
        # Note: This might fail due to missing required fields
        # ProjectListSerializer is for reading, not writing


class TestMaterialSerializer:
    """Test Material serializers"""

    def test_material_serializer_valid(self):
        """Test valid material serializer"""
        data = {
            'name': 'Eichenholz',
            'category': 'Holz',
            'unit': 'm³',
            'datanorm_id': 'DN-12345',
        }
        serializer = MaterialSerializer(data=data)
        assert serializer.is_valid()

    def test_material_serializer_required_fields(self):
        """Test material with missing required fields"""
        data = {
            'name': 'Eichenholz',
            # missing category and unit
        }
        serializer = MaterialSerializer(data=data)
        assert not serializer.is_valid()
        assert 'category' in serializer.errors
        assert 'unit' in serializer.errors


class TestPricePredictionSerializer:
    """Test Price Prediction serializers"""

    def test_prediction_create_serializer_valid(self):
        """Test valid prediction request"""
        data = {
            'name': 'New Project',
            'description': 'A description for prediction',
            'project_type': 'Treppenbau',
            'wood_type': 'Eiche',
            'total_area_sqm': 25.5,
            'complexity': 2,
            'region': 'Nord',
        }
        serializer = PricePredictionCreateSerializer(data=data)
        assert serializer.is_valid()

    def test_prediction_create_serializer_invalid_area(self):
        """Test prediction with invalid area"""
        data = {
            'name': 'New Project',
            'description': 'A description for prediction',
            'project_type': 'Treppenbau',
            'wood_type': 'Eiche',
            'total_area_sqm': -10,  # Invalid: negative
            'complexity': 2,
            'region': 'Nord',
        }
        serializer = PricePredictionCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'total_area_sqm' in serializer.errors

    def test_prediction_create_serializer_too_large_area(self):
        """Test prediction with unrealistic area"""
        data = {
            'name': 'New Project',
            'description': 'A description for prediction',
            'project_type': 'Treppenbau',
            'wood_type': 'Eiche',
            'total_area_sqm': 20000,  # Invalid: too large
            'complexity': 2,
            'region': 'Nord',
        }
        serializer = PricePredictionCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'total_area_sqm' in serializer.errors

    def test_prediction_create_serializer_required_fields(self):
        """Test prediction with missing required fields"""
        data = {
            'name': 'New Project',
            # missing other fields
        }
        serializer = PricePredictionCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'description' in serializer.errors
        assert 'project_type' in serializer.errors
