"""
GoBD-compliant data models for Handwerk ML
"""
from django.db import models
import uuid
from datetime import datetime


class Project(models.Model):
    """Historische Projekte für ML-Training"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()  # Freitext für Similarity Search
    project_type = models.CharField(max_length=100)  # "Treppenbau", "Dachstuhl", etc.

    # Anonymisierte Location
    region = models.CharField(max_length=50)  # "Süd", "Nord", etc.

    # Projekt-Details
    total_area_sqm = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    wood_type = models.CharField(max_length=50)  # "Eiche", "Kiefer", etc.
    complexity = models.IntegerField(choices=[(1, 'Einfach'), (2, 'Mittel'), (3, 'Komplex')])

    # Preis & Zeitdaten
    final_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    project_date = models.DateField()  # Wann wurde Projekt durchgeführt

    # ML-Embeddings (später berechnet)
    description_embedding = models.JSONField(null=True, blank=True)

    # GoBD: Immutable nach Finalisierung
    is_finalized = models.BooleanField(default=False)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-project_date']
        indexes = [
            models.Index(fields=['wood_type', 'project_type']),
            models.Index(fields=['project_date']),
            models.Index(fields=['is_finalized']),
        ]

    def save(self, *args, **kwargs):
        # GoBD: Nach Finalisierung keine Änderungen mehr
        if self.is_finalized and self.pk:
            old_instance = Project.objects.get(pk=self.pk)
            if old_instance.is_finalized:
                raise ValueError("Finalisierte Projekte können nicht geändert werden. Stornierung erforderlich.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.project_type})"


class Material(models.Model):
    """Material-Stammdaten"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)  # "Holz", "Beschläge", etc.
    unit = models.CharField(max_length=20)  # "m²", "m³", "Stk"
    datanorm_id = models.CharField(max_length=50, null=True, blank=True)  # Datanorm-Integration

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['datanorm_id']),
        ]

    def __str__(self):
        return f"{self.name} ({self.category})"


class MaterialPrice(models.Model):
    """Zeitreihen-Daten für Material-Preise"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='prices')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    region = models.CharField(max_length=50)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['material', 'recorded_at']),
            models.Index(fields=['valid_from', 'valid_to']),
        ]

    def __str__(self):
        return f"{self.material.name} - {self.region} ({self.valid_from})"


class ProjectMaterial(models.Model):
    """Verknüpfung Projekt <-> Material"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='materials')
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'material')

    def __str__(self):
        return f"{self.project.name} - {self.material.name}"


class PricePrediction(models.Model):
    """Log aller ML-Vorhersagen"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Input-Features
    project_features = models.JSONField()  # Alle Input-Features als JSON

    # Prediction
    predicted_price = models.DecimalField(max_digits=10, decimal_places=2)
    confidence_score = models.FloatField()  # 0.0 - 1.0
    similar_projects_count = models.IntegerField()
    model_version = models.CharField(max_length=50)

    # Outcome (später ausgefüllt)
    actual_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    was_accepted = models.BooleanField(null=True, blank=True)
    user_modified_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prediction_error = models.FloatField(null=True, blank=True)  # MAPE

    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['model_version']),
        ]

    def __str__(self):
        return f"Prediction {self.id} - {self.model_version}"


class AccountingAudit(models.Model):
    """GoBD-Compliance Audit-Trail - IMMUTABLE"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table_name = models.CharField(max_length=100)
    record_id = models.UUIDField()
    action_type = models.CharField(
        max_length=20,
        choices=[('INSERT', 'INSERT'), ('UPDATE', 'UPDATE'), ('DELETE', 'DELETE')]
    )
    user_id = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)  # IMMUTABLE
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)

    # GoBD: Audit-Trail selbst ist immutable
    class Meta:
        indexes = [
            models.Index(fields=['table_name', 'record_id']),
            models.Index(fields=['timestamp']),
        ]

    def save(self, *args, **kwargs):
        # Verhindert Updates nach Erstellung
        if self.pk:
            raise ValueError("Audit-Log-Einträge sind immutable und können nicht geändert werden.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Verhindert Löschungen
        raise ValueError("Audit-Log-Einträge können nicht gelöscht werden (GoBD-Compliance).")

    def __str__(self):
        return f"{self.action_type} {self.table_name} {self.record_id}"


class Settings(models.Model):
    """Zentrale Einstellungen für Preisberechnung"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Allgemeine Einstellungen
    labor_rate_per_hour = models.DecimalField(max_digits=6, decimal_places=2, default=50.00)
    material_markup_percentage = models.FloatField(default=30)
    overhead_percentage = models.FloatField(default=15)
    profit_margin_percentage = models.FloatField(default=25)

    # Polstererei-spezifische Einstellungen
    polster_fabric_base_price = models.DecimalField(max_digits=6, decimal_places=2, default=25.00)
    polster_labor_rate = models.DecimalField(max_digits=6, decimal_places=2, default=65.00)

    # Foam-Typen (gespeichert als JSON)
    foam_types = models.JSONField(default=dict, null=True, blank=True)

    # Seam-Typen (gespeichert als JSON)
    seam_extras = models.JSONField(default=dict, null=True, blank=True)

    # Material-Preise
    antirutsch_price = models.DecimalField(max_digits=6, decimal_places=2, default=15.00)
    zipper_price = models.DecimalField(max_digits=6, decimal_places=2, default=0.60)

    # Metadaten
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Settings"

    def __str__(self):
        return f"Settings (updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')})"


class Document(models.Model):
    """Verwaltung von Dokumenten für das ML-System"""
    DOCUMENT_TYPES = [
        ('pdf', 'PDF'),
        ('docx', 'Word Document'),
        ('image', 'Image (JPG/PNG)'),
        ('txt', 'Text File'),
    ]

    PROCESSING_STATUS = [
        ('pending', 'Ausstehend'),
        ('processing', 'Wird verarbeitet'),
        ('completed', 'Abgeschlossen'),
        ('failed', 'Fehler'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file_path = models.CharField(max_length=500)  # Relative path in documents_storage

    # Dokumentinhalt
    text_content = models.TextField(null=True, blank=True)  # Extrahierter Text
    text_preview = models.CharField(max_length=500, null=True, blank=True)  # Vorschau (erste 500 Zeichen)

    # ML-Integration
    embedding = models.JSONField(null=True, blank=True)  # Vector Embedding für Ähnlichkeitssuche
    extracted_features = models.JSONField(null=True, blank=True)  # Features für Preismodell
    similar_projects = models.JSONField(null=True, blank=True)  # Ähnliche Projekte (Cache)

    # Beziehungen
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')

    # Metadaten
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    page_count = models.IntegerField(null=True, blank=True)  # Für PDF
    image_width = models.IntegerField(null=True, blank=True)  # Für Bilder
    image_height = models.IntegerField(null=True, blank=True)
    image_format = models.CharField(max_length=20, null=True, blank=True)  # JPG, PNG, etc.

    # Verarbeitung
    processing_status = models.CharField(max_length=20, choices=PROCESSING_STATUS, default='pending')
    processing_error = models.TextField(null=True, blank=True)
    last_processed = models.DateTimeField(null=True, blank=True)

    # Suche
    searchable_text = models.TextField(null=True, blank=True)  # Volltext für Suche

    # Zeitstempel
    uploaded_by = models.CharField(max_length=100, default='system')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['file_type']),
            models.Index(fields=['processing_status']),
            models.Index(fields=['project']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.filename} ({self.file_type})"

    @property
    def is_processed(self):
        return self.processing_status == 'completed'

    @property
    def has_text(self):
        return bool(self.text_content)
