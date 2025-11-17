"""
Django admin configuration for calculator app
"""
from django.contrib import admin
from .models import (
    Project, Material, MaterialPrice, ProjectMaterial,
    PricePrediction, AccountingAudit
)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'project_type', 'final_price', 'project_date', 'is_finalized']
    list_filter = ['project_type', 'is_finalized', 'project_date']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'finalized_at']
    fieldsets = (
        ('Basisdaten', {
            'fields': ('id', 'name', 'description', 'project_type')
        }),
        ('Projekteigenschaften', {
            'fields': ('wood_type', 'total_area_sqm', 'complexity', 'region')
        }),
        ('Finanzen', {
            'fields': ('final_price',)
        }),
        ('GoBD-Compliance', {
            'fields': ('is_finalized', 'finalized_at', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'unit']
    list_filter = ['category']
    search_fields = ['name', 'datanorm_id']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(MaterialPrice)
class MaterialPriceAdmin(admin.ModelAdmin):
    list_display = ['material', 'price', 'region', 'valid_from', 'valid_to']
    list_filter = ['region', 'valid_from']
    search_fields = ['material__name']
    readonly_fields = ['id', 'recorded_at']


@admin.register(ProjectMaterial)
class ProjectMaterialAdmin(admin.ModelAdmin):
    list_display = ['project', 'material', 'quantity', 'total_cost']
    list_filter = ['created_at']
    search_fields = ['project__name', 'material__name']
    readonly_fields = ['id', 'created_at']


@admin.register(PricePrediction)
class PricePredictionAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'predicted_price', 'confidence_score', 'model_version']
    list_filter = ['model_version', 'timestamp', 'was_accepted']
    search_fields = ['id']
    readonly_fields = ['id', 'timestamp']


@admin.register(AccountingAudit)
class AccountingAuditAdmin(admin.ModelAdmin):
    list_display = ['table_name', 'action_type', 'timestamp', 'user_id']
    list_filter = ['action_type', 'table_name', 'timestamp']
    search_fields = ['record_id']
    readonly_fields = ['id', 'timestamp', 'table_name', 'record_id', 'action_type', 'user_id', 'old_values', 'new_values']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
