"""
URL routing for calculator app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProjectViewSet, MaterialViewSet, MaterialPriceViewSet,
    PricePredictionViewSet, AccountingAuditViewSet, PDFParserView,
    PolstereiBerechnungViewSet, SettingsViewSet,
    SimilarProjectsViewSet, ConfidenceScoreViewSet,
    XGBoostPricePredictionViewSet, BatchPredictionViewSet,
    ModelMetricsViewSet, BatchSimilarityViewSet, DocumentViewSet,
    DatabaseSyncViewSet
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'materials', MaterialViewSet, basename='material')
router.register(r'material-prices', MaterialPriceViewSet, basename='material-price')
router.register(r'predictions', PricePredictionViewSet, basename='prediction')
router.register(r'audit', AccountingAuditViewSet, basename='audit')
router.register(r'polstererei', PolstereiBerechnungViewSet, basename='polstererei')
router.register(r'settings', SettingsViewSet, basename='settings')
router.register(r'similar-projects', SimilarProjectsViewSet, basename='similar-projects')
router.register(r'confidence', ConfidenceScoreViewSet, basename='confidence')
router.register(r'price-prediction', XGBoostPricePredictionViewSet, basename='price-prediction')

# Phase 3: Advanced ML Endpoints
router.register(r'batch-prediction', BatchPredictionViewSet, basename='batch-prediction')
router.register(r'model-metrics', ModelMetricsViewSet, basename='model-metrics')
router.register(r'batch-similarity', BatchSimilarityViewSet, basename='batch-similarity')

# Phase 5: Document Management System
router.register(r'documents', DocumentViewSet, basename='document')

# Phase 5: Database Synchronization
router.register(r'database-sync', DatabaseSyncViewSet, basename='database-sync')

urlpatterns = [
    path('', include(router.urls)),
    path('parse-pdf/', PDFParserView.as_view(), name='pdf-parser'),
]
