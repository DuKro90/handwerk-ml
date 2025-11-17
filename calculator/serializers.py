"""
Serializers for Handwerk ML Calculator API
"""
from rest_framework import serializers
from .models import (
    Project, Material, MaterialPrice, ProjectMaterial,
    PricePrediction, AccountingAudit, Settings, Document
)


class MaterialSerializer(serializers.ModelSerializer):
    """Serializer für Material"""
    class Meta:
        model = Material
        fields = [
            'id', 'name', 'category', 'unit', 'datanorm_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MaterialPriceSerializer(serializers.ModelSerializer):
    """Serializer für Material-Preise"""
    class Meta:
        model = MaterialPrice
        fields = [
            'id', 'material', 'price', 'region',
            'valid_from', 'valid_to', 'recorded_at'
        ]
        read_only_fields = ['id', 'recorded_at']


class ProjectMaterialSerializer(serializers.ModelSerializer):
    """Serializer für Projekt-Material Verknüpfung"""
    material_name = serializers.CharField(source='material.name', read_only=True)

    class Meta:
        model = ProjectMaterial
        fields = [
            'id', 'project', 'material', 'material_name',
            'quantity', 'unit_price', 'total_cost', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProjectListSerializer(serializers.ModelSerializer):
    """Serializer für Projekt-Liste (einfache Ansicht)"""
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'project_type', 'final_price',
            'project_date', 'created_at', 'is_finalized'
        ]
        read_only_fields = ['id', 'created_at']


class ProjectDetailSerializer(serializers.ModelSerializer):
    """Serializer für Projekt-Details (vollständige Ansicht)"""
    materials = ProjectMaterialSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'project_type',
            'region', 'total_area_sqm', 'wood_type', 'complexity',
            'final_price', 'created_at', 'project_date',
            'is_finalized', 'finalized_at', 'materials'
        ]
        read_only_fields = ['id', 'created_at', 'finalized_at']


class PricePredictionSerializer(serializers.ModelSerializer):
    """Serializer für Preis-Vorhersagen"""
    class Meta:
        model = PricePrediction
        fields = [
            'id', 'timestamp', 'project_features', 'predicted_price',
            'confidence_score', 'similar_projects_count', 'model_version',
            'actual_price', 'was_accepted', 'user_modified_price',
            'prediction_error'
        ]
        read_only_fields = [
            'id', 'timestamp', 'predicted_price', 'confidence_score',
            'similar_projects_count'
        ]


class PricePredictionCreateSerializer(serializers.ModelSerializer):
    """Serializer für Preis-Vorhersagen erstellen"""
    class Meta:
        model = PricePrediction
        fields = ['project_features']


class AccountingAuditSerializer(serializers.ModelSerializer):
    """Serializer für Audit-Trail"""
    class Meta:
        model = AccountingAudit
        fields = [
            'id', 'table_name', 'record_id', 'action_type',
            'user_id', 'timestamp', 'old_values', 'new_values'
        ]
        read_only_fields = ['id', 'timestamp']


class SettingsSerializer(serializers.ModelSerializer):
    """Serializer für Globale Einstellungen"""
    class Meta:
        model = Settings
        fields = [
            'id',
            'labor_rate_per_hour',
            'material_markup_percentage',
            'overhead_percentage',
            'profit_margin_percentage',
            'polster_fabric_base_price',
            'polster_labor_rate',
            'foam_types',
            'seam_extras',
            'antirutsch_price',
            'zipper_price',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer für Dokumente"""
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'filename', 'file_type', 'file_size_bytes',
            'file_path', 'text_content', 'text_preview',
            'processing_status', 'processing_error',
            'last_processed', 'is_processed', 'has_text',
            'page_count', 'image_width', 'image_height', 'image_format',
            'embedding', 'extracted_features', 'similar_projects',
            'project', 'project_name', 'searchable_text',
            'created_at', 'updated_at', 'uploaded_by'
        ]
        read_only_fields = [
            'id', 'embedding', 'extracted_features', 'similar_projects',
            'text_content', 'text_preview', 'searchable_text',
            'processing_status', 'last_processed',
            'page_count', 'image_width', 'image_height', 'image_format',
            'created_at', 'updated_at', 'is_processed', 'has_text'
        ]
