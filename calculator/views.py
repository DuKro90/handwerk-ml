"""
REST API views for Handwerk ML
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.management import call_command
from io import StringIO
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import models
from django.db.models import Count
from datetime import datetime, timedelta
import statistics

from .models import (
    Project, Material, MaterialPrice, ProjectMaterial,
    PricePrediction, AccountingAudit, Settings, Document
)
from .document_processor import DocumentProcessor
from .serializers import (
    ProjectListSerializer, ProjectDetailSerializer,
    MaterialSerializer, MaterialPriceSerializer, ProjectMaterialSerializer,
    PricePredictionSerializer, PricePredictionCreateSerializer,
    AccountingAuditSerializer, SettingsSerializer
)


class ProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing construction projects
    """
    queryset = Project.objects.all()
    permission_classes = []  # Customize as needed

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProjectDetailSerializer
        return ProjectListSerializer

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent projects (last 30 days)"""
        from datetime import timedelta
        from django.utils import timezone

        thirty_days_ago = timezone.now() - timedelta(days=30)
        projects = Project.objects.filter(project_date__gte=thirty_days_ago)
        serializer = self.get_serializer(projects, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get projects filtered by type"""
        project_type = request.query_params.get('type')
        if not project_type:
            return Response(
                {'error': 'type parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        projects = Project.objects.filter(project_type=project_type)
        serializer = self.get_serializer(projects, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        """Finalize a project (makes it immutable)"""
        project = self.get_object()
        if project.is_finalized:
            return Response(
                {'error': 'Project is already finalized'},
                status=status.HTTP_400_BAD_REQUEST
            )
        project.is_finalized = True
        project.finalized_at = timezone.now()
        project.save()

        # Log audit trail
        AccountingAudit.objects.create(
            table_name='calculator_project',
            record_id=project.id,
            action_type='UPDATE',
            user_id=request.user.id if request.user.is_authenticated else 0,
            old_values={'is_finalized': False},
            new_values={'is_finalized': True, 'finalized_at': project.finalized_at.isoformat()}
        )

        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=['post'])
    def add_material(self, request, pk=None):
        """Add material to project"""
        project = self.get_object()

        if project.is_finalized:
            return Response(
                {'error': 'Cannot modify finalized project'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ProjectMaterialSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(project=project)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get project statistics"""
        total_projects = Project.objects.count()
        finalized_projects = Project.objects.filter(is_finalized=True).count()
        avg_price = Project.objects.values_list('final_price', flat=True)

        if avg_price:
            avg_price_value = sum(avg_price) / len(avg_price)
        else:
            avg_price_value = 0

        return Response({
            'total_projects': total_projects,
            'finalized_projects': finalized_projects,
            'average_price': float(avg_price_value),
            'projects_by_type': dict(
                Project.objects.values_list('project_type').annotate(
                    count=models.Count('id')
                ).values_list('project_type', 'count')
            ) if total_projects > 0 else {},
        })


class MaterialViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing materials
    """
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get materials filtered by category"""
        category = request.query_params.get('category')
        if not category:
            return Response(
                {'error': 'category parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        materials = Material.objects.filter(category=category)
        serializer = self.get_serializer(materials, many=True)
        return Response(serializer.data)


class MaterialPriceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing material prices
    """
    queryset = MaterialPrice.objects.all()
    serializer_class = MaterialPriceSerializer

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current prices for all materials"""
        from datetime import date
        today = date.today()

        prices = MaterialPrice.objects.filter(
            valid_from__lte=today
        ).filter(
            models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=today)
        )
        serializer = self.get_serializer(prices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_material(self, request):
        """Get price history for specific material"""
        material_id = request.query_params.get('material_id')
        if not material_id:
            return Response(
                {'error': 'material_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        prices = MaterialPrice.objects.filter(material_id=material_id).order_by('-recorded_at')
        serializer = self.get_serializer(prices, many=True)
        return Response(serializer.data)


class PricePredictionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing price predictions
    """
    queryset = PricePrediction.objects.all()
    serializer_class = PricePredictionSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return PricePredictionCreateSerializer
        return PricePredictionSerializer

    @action(detail=False, methods=['post'])
    def predict(self, request):
        """
        Create a price prediction for a new project
        """
        serializer = PricePredictionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # TODO: Implement actual ML prediction logic
        # For now, return a mock prediction
        predicted_price = 5000.00  # Mock prediction
        confidence_score = 0.75  # Mock confidence

        prediction = PricePrediction.objects.create(
            project_features=serializer.validated_data,
            predicted_price=predicted_price,
            confidence_score=confidence_score,
            similar_projects_count=0,
            model_version='v1.0.0'
        )

        response_serializer = PricePredictionSerializer(prediction)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def feedback(self, request, pk=None):
        """
        Submit feedback for a prediction
        """
        prediction = self.get_object()

        actual_price = request.data.get('actual_price')
        was_accepted = request.data.get('was_accepted')
        user_modified_price = request.data.get('user_modified_price')

        if actual_price:
            prediction.actual_price = actual_price
            prediction.prediction_error = abs(
                float(prediction.predicted_price) - float(actual_price)
            ) / float(actual_price) * 100  # MAPE

        if was_accepted is not None:
            prediction.was_accepted = was_accepted

        if user_modified_price:
            prediction.user_modified_price = user_modified_price

        prediction.save()

        return Response(PricePredictionSerializer(prediction).data)

    @action(detail=False, methods=['get'])
    def accuracy_metrics(self, request):
        """
        Get model accuracy metrics
        """
        predictions_with_feedback = PricePrediction.objects.filter(
            actual_price__isnull=False
        )

        if not predictions_with_feedback.exists():
            return Response({
                'error': 'No predictions with feedback yet',
                'sample_size': 0
            })

        errors = [
            float(p.prediction_error) for p in predictions_with_feedback
            if p.prediction_error is not None
        ]

        if not errors:
            return Response({
                'error': 'No valid errors calculated',
                'sample_size': 0
            })

        import statistics
        avg_error = statistics.mean(errors)
        median_error = statistics.median(errors)
        std_dev = statistics.stdev(errors) if len(errors) > 1 else 0

        return Response({
            'sample_size': len(errors),
            'mean_mape': round(avg_error, 2),
            'median_mape': round(median_error, 2),
            'std_dev': round(std_dev, 2),
            'min_error': round(min(errors), 2),
            'max_error': round(max(errors), 2),
        })


class AccountingAuditViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing accounting audit trail (read-only)
    GoBD Compliance: Audit logs are immutable
    """
    queryset = AccountingAudit.objects.all()
    serializer_class = AccountingAuditSerializer

    @action(detail=False, methods=['get'])
    def by_record(self, request):
        """Get audit trail for a specific record"""
        record_id = request.query_params.get('record_id')
        table_name = request.query_params.get('table_name')

        if not record_id or not table_name:
            return Response(
                {'error': 'record_id and table_name parameters required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        audits = AccountingAudit.objects.filter(
            record_id=record_id,
            table_name=table_name
        ).order_by('timestamp')

        serializer = self.get_serializer(audits, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent audit trail entries"""
        from datetime import timedelta
        from django.utils import timezone

        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)

        audits = AccountingAudit.objects.filter(
            timestamp__gte=start_date
        ).order_by('-timestamp')[:100]

        serializer = self.get_serializer(audits, many=True)
        return Response(serializer.data)


class SettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet für globale Einstellungen
    Verwaltet Preise, Stundensätze, Markup etc.
    """
    queryset = Settings.objects.all()
    serializer_class = SettingsSerializer

    @action(detail=False, methods=['get', 'post', 'put', 'patch'])
    def current(self, request):
        """Get or update current settings"""
        if request.method == 'GET':
            settings = Settings.objects.first()
            if not settings:
                # Erstelle Standard-Einstellungen wenn keine existieren
                settings = Settings.objects.create()
            serializer = self.get_serializer(settings)
            return Response(serializer.data)

        elif request.method in ['POST', 'PUT', 'PATCH']:
            settings = Settings.objects.first()
            if not settings:
                settings = Settings.objects.create()

            serializer = self.get_serializer(settings, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# PDF Parser View
from rest_framework.views import APIView
from django.http import JsonResponse
import json

class PDFParserView(APIView):
    """
    Parse PDF documents and extract project information for automatic price calculation
    """

    def post(self, request):
        """
        Upload and parse a PDF file

        Returns extracted data:
        - name: Project name
        - project_type: Type of project
        - estimated_hours: Estimated working hours
        - material_cost: Estimated material costs
        - description: Description from PDF
        - confidence: Confidence score (0-100)
        """

        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES['file']

        # TODO: Implement actual PDF parsing with pdfplumber or PyPDF2
        # For now, we return simulated data
        # In production: extract text from PDF and use NLP/regex to parse

        # Simulated extracted data
        # In real implementation:
        # 1. Use pdfplumber to read PDF
        # 2. Extract text content
        # 3. Use regex/NLP to find:
        #    - Project name
        #    - Project type
        #    - Material listings
        #    - Time estimates
        # 4. Calculate confidence based on how much data was found

        parsed_data = {
            'name': f'Projekt aus {file.name[:-4]}',
            'project_type': 'Allgemeines Projekt',
            'estimated_hours': 8.5,
            'material_cost': 450.00,
            'description': 'Automatisch aus PDF analysiert.\n\nTipp: Für präzisere Ergebnisse:\n- Verwende aussagekräftige Dateinamen\n- Enthalte Material-Listen\n- Gib Stunden-Schätzungen an',
            'confidence': 65,  # 0-100, depends on how much was extracted
        }

        return Response(parsed_data, status=status.HTTP_200_OK)


class PolstereiBerechnungViewSet(viewsets.ModelViewSet):
    """
    ViewSet für Polstererei-Kissen-Berechnungen
    Speichert Kalkulationen als Projekte
    """
    queryset = Project.objects.filter(project_type='Polstererei-Kissen')
    serializer_class = ProjectDetailSerializer

    @action(detail=False, methods=['post'])
    def calculate_and_save(self, request):
        """
        Kissen-Kalkulation durchführen und als Projekt speichern

        Expected POST data:
        {
            "width_cm": 60,
            "height_cm": 60,
            "thickness_cm": 10,
            "foam_type": "GR 5560",
            "seam_type": "Normal",
            "fabric_price": 100.0,
            "has_antirutsch": false
        }
        """
        from .polsterei_config import calculate_full_cushion_price
        from datetime import date

        width = request.data.get('width_cm')
        height = request.data.get('height_cm')
        thickness = request.data.get('thickness_cm')
        foam_type = request.data.get('foam_type', 'GR 5560')
        seam_type = request.data.get('seam_type', 'Normal')
        fabric_price = request.data.get('fabric_price', 100.0)
        has_antirutsch = request.data.get('has_antirutsch', False)

        # Validierung
        if not all([width, height, thickness]):
            return Response(
                {'error': 'width_cm, height_cm, und thickness_cm sind erforderlich'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            width = int(width)
            height = int(height)
            thickness = int(thickness)
            fabric_price = float(fabric_price)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Ungültige Werte - Zahlen erwartet'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Berechnung durchführen mit polsterei_config
        calculation = calculate_full_cushion_price(
            width_cm=width,
            height_cm=height,
            thickness_cm=thickness,
            foam_type=foam_type,
            seam_type=seam_type,
            fabric_price=fabric_price,
            has_antirutsch=has_antirutsch
        )

        # Projekt erstellen
        project_name = f'Kissen {width}×{height} cm mit {seam_type}'

        # Komplexität basierend auf Größe
        area = width * height
        if area < 2000:
            complexity = 1  # Einfach
        elif area < 5000:
            complexity = 2  # Mittel
        else:
            complexity = 3  # Komplex

        project = Project.objects.create(
            name=project_name,
            description=json.dumps({
                'dimensions': {
                    'width': width,
                    'height': height,
                    'thickness': thickness,
                    'area_cm2': area,
                    'area_m2': area / 10000,
                    'perimeter_m': 2 * (width + height) / 100,
                },
                'material': {
                    'foam_type': foam_type,
                    'seam_type': seam_type,
                    'fabric_price': fabric_price,
                    'has_antirutsch': has_antirutsch,
                },
                'calculation': calculation,
            }, indent=2, default=str),
            project_type='Polstererei-Kissen',
            total_area_sqm=area / 10000,
            wood_type=foam_type,
            complexity=complexity,
            final_price=calculation['total_cost'],
            project_date=date.today(),
            is_finalized=False,
        )

        # Audit-Trail
        AccountingAudit.objects.create(
            table_name='calculator_project',
            record_id=project.id,
            action_type='INSERT',
            user_id=request.user.id if request.user.is_authenticated else 0,
            new_values={
                'name': project.name,
                'project_type': project.project_type,
                'final_price': str(project.final_price),
            }
        )

        serializer = ProjectDetailSerializer(project)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ============================================================================
# ML ViewSets - Embeddings und Confidence Scoring
# ============================================================================

from calculator.ml.embeddings import EmbeddingGenerator
from calculator.ml.confidence import ConfidenceCalculator
import logging

logger = logging.getLogger(__name__)

# Initialisiere ML-Komponenten
embedding_generator = EmbeddingGenerator()
confidence_calculator = ConfidenceCalculator()


class SimilarProjectsViewSet(viewsets.ViewSet):
    """
    Findet ähnliche Projekte basierend auf Beschreibung

    POST /api/v1/similar-projects/find/
    Body: {
        "description": "Eichentreppe, 14 Stufen, gedreht",
        "top_k": 10
    }
    """

    @action(detail=False, methods=['post'])
    def find(self, request):
        """Findet ähnliche Projekte"""

        description = request.data.get('description', '')
        top_k = request.data.get('top_k', 10)

        if not description:
            return Response(
                {'error': 'description ist erforderlich'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generiere Embedding für die neue Beschreibung
        embedding = embedding_generator.generate_embedding(description)

        if not embedding:
            return Response(
                {'error': 'Konnte Embedding nicht generieren'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Finde ähnliche Projekte
        projects = Project.objects.filter(
            is_finalized=True
        ).exclude(
            description_embedding__isnull=True
        )

        similar = embedding_generator.find_similar_projects(
            embedding,
            projects,
            top_k=top_k
        )

        return Response({
            'input_embedding_dimension': len(embedding),
            'similar_projects': [
                {
                    'id': str(s['project'].id),
                    'name': s['project'].name,
                    'description': s['project'].description[:100] if s['project'].description else '',
                    'final_price': float(s['project'].final_price) if s['project'].final_price else 0,
                    'wood_type': s['project'].wood_type or '',
                    'project_type': s['project'].project_type or '',
                    'complexity': s['project'].complexity or 0,
                    'similarity': round(s['similarity'], 3)
                }
                for s in similar
            ],
            'count': len(similar)
        })


class ConfidenceScoreViewSet(viewsets.ViewSet):
    """
    Berechnet Confidence Score für Preis-Vorhersagen

    POST /api/v1/confidence/calculate/
    Body: {
        "similar_projects_count": 5,
        "price_variance": 5000,
        "predicted_price": 15000,
        "data_quality_score": 0.8,
        "avg_months_old": 6
    }
    """

    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """Berechnet Confidence Score"""

        try:
            similar_count = request.data.get('similar_projects_count', 0)
            price_variance = request.data.get('price_variance', 0)
            predicted_price = request.data.get('predicted_price', 0)
            data_quality = request.data.get('data_quality_score', 0.5)
            avg_months_old = request.data.get('avg_months_old', 12)

            confidence = confidence_calculator.calculate_confidence(
                similar_projects_count=similar_count,
                price_variance=price_variance,
                predicted_price=predicted_price,
                data_quality_score=data_quality,
                avg_months_old=avg_months_old
            )

            return Response(confidence)

        except Exception as e:
            logger.error(f"Confidence-Fehler: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# Price Prediction ViewSets - XGBoost Model
# ============================================================================

from calculator.ml.price_predictor import PricePredictor
from calculator.ml.feature_engineer import FeatureEngineer
from pathlib import Path
from django.conf import settings
import pandas as pd


class XGBoostPricePredictionViewSet(viewsets.ViewSet):
    """
    XGBoost-based price prediction endpoint

    POST /api/v1/price-prediction/predict/
    Body: {
        "total_area_sqm": 25.5,
        "complexity": 3,
        "wood_type": "Eiche",
        "project_type": "Treppenbau",
        "region": "NRW",
        "project_date": "2025-11-17"
    }
    """

    @action(detail=False, methods=['post'])
    def predict(self, request):
        """Predict price for project"""

        try:
            # Load trained model
            model_file = Path(settings.BASE_DIR) / 'models' / 'xgboost_model.pkl'

            if not model_file.exists():
                return Response(
                    {'error': 'Model not trained yet. Run: python manage.py train_model'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            predictor = PricePredictor()
            predictor.load_model(str(model_file))

            # Extract features from request
            feature_engineer = FeatureEngineer()
            features_dict = feature_engineer.extract_features(request.data)

            # Create DataFrame for prediction
            features_df = pd.DataFrame([features_dict])

            # Make prediction
            predicted_price = float(predictor.predict(features_df)[0])

            # Get confidence interval
            predictions, lower, upper = predictor.predict_with_confidence(
                features_df,
                confidence_percentile=0.95
            )

            # Get feature importance if available
            feature_importance = predictor.get_feature_importance(top_k=5)

            return Response({
                'predicted_price': round(predicted_price, 2),
                'confidence_interval': {
                    'lower_bound': round(float(lower[0]), 2),
                    'upper_bound': round(float(upper[0]), 2),
                },
                'confidence': 'high' if abs(upper[0] - lower[0]) < predicted_price * 0.2 else 'medium',
                'model_info': predictor.get_model_info(),
                'top_features': feature_importance,
            })

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def model_info(self, request):
        """Get information about trained model"""

        try:
            model_file = Path(settings.BASE_DIR) / 'models' / 'xgboost_model.pkl'

            if not model_file.exists():
                return Response({
                    'status': 'not_trained',
                    'message': 'Model not trained yet. Run: python manage.py train_model'
                })

            predictor = PricePredictor()
            predictor.load_model(str(model_file))

            return Response(predictor.get_model_info())

        except Exception as e:
            logger.error(f"Model info error: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# Phase 3: Advanced ML Endpoints
# ============================================================================

class BatchPredictionViewSet(viewsets.ViewSet):
    """
    Batch price predictions for multiple projects

    POST /api/v1/batch-prediction/predict/
    Body: {
        "projects": [
            {"total_area_sqm": 25, "complexity": 3, ...},
            {"total_area_sqm": 50, "complexity": 4, ...}
        ]
    }
    """

    @action(detail=False, methods=['post'])
    def predict(self, request):
        """Batch predict prices"""

        try:
            projects_data = request.data.get('projects', [])

            if not projects_data:
                return Response(
                    {'error': 'projects list is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Load model
            model_file = Path(settings.BASE_DIR) / 'models' / 'xgboost_model.pkl'
            if not model_file.exists():
                return Response(
                    {'error': 'Model not trained'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            predictor = PricePredictor()
            predictor.load_model(str(model_file))
            feature_engineer = FeatureEngineer()

            predictions = []

            for project_data in projects_data:
                try:
                    features_dict = feature_engineer.extract_features(project_data)
                    features_df = pd.DataFrame([features_dict])
                    predicted_price = float(predictor.predict(features_df)[0])

                    # Log prediction
                    PricePrediction.objects.create(
                        project_features=project_data,
                        predicted_price=predicted_price,
                        confidence_score=0.75,
                        similar_projects_count=0,
                        model_version='phase2-xgboost'
                    )

                    predictions.append({
                        'predicted_price': round(predicted_price, 2),
                        'status': 'success'
                    })
                except Exception as e:
                    predictions.append({
                        'error': str(e),
                        'status': 'error'
                    })

            return Response({
                'total': len(predictions),
                'successful': sum(1 for p in predictions if p['status'] == 'success'),
                'predictions': predictions
            })

        except Exception as e:
            logger.error(f"Batch prediction error: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ModelMetricsViewSet(viewsets.ViewSet):
    """
    Model performance metrics and statistics

    GET /api/v1/model-metrics/summary/
    GET /api/v1/model-metrics/history/
    """

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get model performance summary"""

        try:
            # Get all predictions
            predictions = PricePrediction.objects.filter(
                model_version='phase2-xgboost'
            ).order_by('-timestamp')

            if not predictions.exists():
                return Response({
                    'status': 'no_predictions',
                    'message': 'No predictions recorded yet'
                })

            # Calculate metrics
            total_predictions = predictions.count()
            predictions_with_outcome = predictions.exclude(actual_price__isnull=True)
            accurate_predictions = predictions.filter(prediction_error__lt=0.15)  # MAPE < 15%

            accuracy_rate = (
                len(accurate_predictions) / len(predictions_with_outcome) * 100
                if predictions_with_outcome.exists() else 0
            )

            avg_error = (
                predictions_with_outcome.aggregate(
                    avg=models.Avg('prediction_error')
                )['avg'] or 0
            )

            return Response({
                'status': 'success',
                'total_predictions': total_predictions,
                'predictions_with_outcome': len(predictions_with_outcome),
                'accuracy_rate': round(accuracy_rate, 2),
                'average_error_mape': round(avg_error * 100, 2),
                'last_prediction': predictions.first().timestamp,
                'model_version': 'phase2-xgboost'
            })

        except Exception as e:
            logger.error(f"Metrics error: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get prediction history"""

        try:
            limit = int(request.query_params.get('limit', 50))
            predictions = PricePrediction.objects.filter(
                model_version='phase2-xgboost'
            ).order_by('-timestamp')[:limit]

            data = [
                {
                    'id': str(p.id),
                    'timestamp': p.timestamp.isoformat(),
                    'predicted_price': float(p.predicted_price),
                    'confidence_score': p.confidence_score,
                    'actual_price': float(p.actual_price) if p.actual_price else None,
                    'prediction_error': p.prediction_error,
                    'features': p.project_features
                }
                for p in predictions
            ]

            return Response({
                'count': len(data),
                'predictions': data
            })

        except Exception as e:
            logger.error(f"History error: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BatchSimilarityViewSet(viewsets.ViewSet):
    """
    Batch similarity search for multiple projects

    POST /api/v1/batch-similarity/find/
    """

    @action(detail=False, methods=['post'])
    def find(self, request):
        """Find similar projects for multiple inputs"""

        try:
            descriptions = request.data.get('descriptions', [])
            top_k = request.data.get('top_k', 5)

            if not descriptions:
                return Response(
                    {'error': 'descriptions list is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            embedding_gen = EmbeddingGenerator()
            results = []

            for desc in descriptions:
                embedding = embedding_gen.generate_embedding(desc)

                if not embedding:
                    results.append({'error': 'Could not generate embedding'})
                    continue

                projects = Project.objects.filter(
                    is_finalized=True
                ).exclude(description_embedding__isnull=True)

                similar = embedding_gen.find_similar_projects(
                    embedding, projects, top_k=top_k
                )

                results.append({
                    'description': desc[:50],
                    'similar_count': len(similar),
                    'top_match_similarity': round(similar[0]['similarity'], 3) if similar else 0
                })

            return Response({
                'total': len(results),
                'results': results
            })

        except Exception as e:
            logger.error(f"Batch similarity error: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DocumentViewSet(viewsets.ModelViewSet):
    """
    Document management ViewSet
    Upload, search, and manage documents for ML system

    GET    /api/v1/documents/ - List documents
    POST   /api/v1/documents/ - Upload document
    GET    /api/v1/documents/{id}/ - Get document
    DELETE /api/v1/documents/{id}/ - Delete document
    POST   /api/v1/documents/search/ - Search documents
    GET    /api/v1/documents/{id}/similar-projects/ - Find similar projects
    """

    queryset = Document.objects.all()
    permission_classes = []  # Customize as needed

    def list(self, request, *args, **kwargs):
        """List documents with filtering and search"""
        queryset = self.get_queryset()

        # Filter by file type
        file_type = request.query_params.get('file_type')
        if file_type:
            queryset = queryset.filter(file_type=file_type)

        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(processing_status=status_filter)

        # Filter by project
        project_id = request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        # Full-text search
        search_query = request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                models.Q(filename__icontains=search_query) |
                models.Q(searchable_text__icontains=search_query) |
                models.Q(text_preview__icontains=search_query)
            )

        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Upload a single document"""
        if 'file' not in request.FILES:
            return Response(
                {'error': 'file field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        uploaded_file = request.FILES['file']
        project_id = request.data.get('project_id')

        try:
            # Save file
            rel_path = DocumentProcessor.save_uploaded_file(
                uploaded_file,
                uploaded_file.name
            )

            # Create Document record
            file_type = self._get_file_type(uploaded_file.name)
            if not file_type:
                return Response(
                    {'error': 'Unsupported file type'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            document = Document.objects.create(
                filename=uploaded_file.name,
                file_type=file_type,
                file_path=rel_path,
                file_size_bytes=uploaded_file.size,
                project_id=project_id if project_id else None,
                processing_status='pending'
            )

            serializer = self.get_serializer(document)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def search(self, request):
        """Full-text search documents"""
        query = request.data.get('query')
        if not query:
            return Response(
                {'error': 'query is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Simple text search
        documents = Document.objects.filter(
            models.Q(filename__icontains=query) |
            models.Q(searchable_text__icontains=query) |
            models.Q(text_preview__icontains=query)
        )[:100]

        serializer = self.get_serializer(documents, many=True)
        return Response({
            'query': query,
            'results_count': len(documents),
            'results': serializer.data
        })

    @action(detail=True, methods=['get'])
    def similar_projects(self, request, pk=None):
        """Find projects similar to document content"""
        document = self.get_object()

        if not document.embedding:
            return Response(
                {'error': 'Document not processed or no embedding available'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from calculator.ml.embeddings import EmbeddingGenerator
            import numpy as np

            embedding_gen = EmbeddingGenerator()
            doc_embedding = np.array(document.embedding)

            # Find similar projects
            projects = Project.objects.filter(is_finalized=True).exclude(
                description_embedding__isnull=True
            )

            similar_projects = []
            for project in projects:
                try:
                    proj_embedding = np.array(project.description_embedding)
                    similarity = embedding_gen.calculate_similarity(
                        doc_embedding, proj_embedding
                    )
                    if similarity > 0.5:
                        similar_projects.append({
                            'id': str(project.id),
                            'name': project.name,
                            'type': project.project_type,
                            'similarity_score': round(float(similarity), 3),
                            'price': float(project.final_price)
                        })
                except:
                    continue

            similar_projects.sort(key=lambda x: x['similarity_score'], reverse=True)

            return Response({
                'document_id': str(document.id),
                'similar_projects_count': len(similar_projects),
                'projects': similar_projects[:10]
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Manually process a document"""
        document = self.get_object()

        try:
            document.processing_status = 'processing'
            document.save()

            full_path = DocumentProcessor.get_file_path(document.file_path)

            # Process document
            result = DocumentProcessor.process_document(full_path, document.file_type)

            if result['success']:
                document.text_content = result['text_content']
                document.text_preview = DocumentProcessor.create_text_preview(
                    result['text_content']
                )

                # Add metadata
                for key, value in result['metadata'].items():
                    if hasattr(document, key):
                        setattr(document, key, value)

                # Create searchable text
                from calculator.document_processor import DocumentSearcher
                document.searchable_text = DocumentSearcher.prepare_search_text(
                    result['text_content']
                )

                # Extract features
                from calculator.document_processor import DocumentFeatureExtractor
                features = DocumentFeatureExtractor.extract_features(
                    result['text_content'],
                    document.file_type,
                    result['metadata']
                )
                document.extracted_features = features

                # Create embedding
                try:
                    from calculator.document_processor import DocumentEmbedder
                    embedder = DocumentEmbedder()
                    embedding = embedder.embed_text(result['text_content'])
                    if embedding:
                        document.embedding = embedding
                except:
                    pass

                document.processing_status = 'completed'
                document.last_processed = timezone.now()

            else:
                document.processing_status = 'failed'
                document.processing_error = result['error']

            document.save()
            serializer = self.get_serializer(document)
            return Response(serializer.data)

        except Exception as e:
            document.processing_status = 'failed'
            document.processing_error = str(e)
            document.save()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Get document preview"""
        document = self.get_object()

        return Response({
            'id': str(document.id),
            'filename': document.filename,
            'type': document.file_type,
            'preview': document.text_preview or 'No preview available',
            'full_text': document.text_content or None,
            'features': document.extracted_features,
            'processed': document.is_processed
        })

    @staticmethod
    def _get_file_type(filename: str) -> str:
        """Determine file type from filename"""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''

        type_map = {
            'pdf': 'pdf',
            'docx': 'docx',
            'doc': 'docx',
            'jpg': 'image',
            'jpeg': 'image',
            'png': 'image',
            'bmp': 'image',
            'gif': 'image',
            'txt': 'txt',
        }

        return type_map.get(ext)

    def get_serializer_class(self):
        """Return appropriate serializer"""
        return DocumentSerializer

    def get_serializer(self, *args, **kwargs):
        """Override to handle file uploads"""
        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())
        return serializer_class(*args, **kwargs)


class DatabaseSyncViewSet(viewsets.ViewSet):
    """
    Database synchronization ViewSet
    Sync data from ML_Datafeed directory

    POST /api/v1/database-sync/sync/ - Start synchronization
    GET  /api/v1/database-sync/status/ - Get sync status
    """

    @action(detail=False, methods=['post'])
    def sync(self, request):
        """Synchronize database with ML_Datafeed"""
        try:
            datafeed_path = request.data.get('datafeed_path', 'C:\\ML_Datafeed')
            import_docs = request.data.get('import_docs', True)
            sync_projects = request.data.get('sync_projects', True)

            # Capture output from management command
            out = StringIO()

            try:
                call_command(
                    'sync_datafeed',
                    '--datafeed-path', datafeed_path,
                    '--full-sync' if (import_docs and sync_projects) else '',
                    stdout=out,
                    stderr=out
                )
            except TypeError:
                # Fallback for different Django versions
                call_command(
                    'sync_datafeed',
                    '--datafeed-path', datafeed_path,
                    stdout=out
                )

            output = out.getvalue()

            return Response({
                'status': 'success',
                'message': 'Database synchronization completed',
                'timestamp': timezone.now().isoformat(),
                'output': output,
                'datafeed_path': datafeed_path
            })

        except Exception as e:
            return Response(
                {
                    'status': 'error',
                    'message': str(e),
                    'timestamp': timezone.now().isoformat()
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get database synchronization status"""
        try:
            from pathlib import Path

            datafeed_path = Path(request.query_params.get('path', 'C:\\ML_Datafeed'))

            # Check if path exists
            if not datafeed_path.exists():
                return Response({
                    'ready': False,
                    'message': f'Datafeed path not found: {datafeed_path}',
                    'documents_count': 0,
                    'projects_count': 0,
                    'last_sync': None
                })

            # Count documents and projects in datafeed
            docs_dir = datafeed_path / 'documents'
            docs_count = 0
            if docs_dir.exists():
                docs_count = sum(1 for _ in docs_dir.rglob('*') if _.is_file())

            projects_file = datafeed_path / 'projects.json'
            projects_count = 0
            if projects_file.exists():
                try:
                    import json
                    with open(projects_file) as f:
                        data = json.load(f)
                        projects_count = len(data) if isinstance(data, list) else 1
                except:
                    projects_count = 0

            return Response({
                'ready': datafeed_path.exists(),
                'message': 'Datafeed ready for synchronization',
                'datafeed_path': str(datafeed_path),
                'documents_count': docs_count,
                'projects_count': projects_count,
                'last_sync': None
            })

        except Exception as e:
            return Response(
                {
                    'ready': False,
                    'message': str(e),
                    'error': True
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def info(self, request):
        """Get datafeed information"""
        try:
            from pathlib import Path

            default_path = 'C:\\ML_Datafeed'

            return Response({
                'default_path': default_path,
                'expected_structure': {
                    'documents': 'C:\\ML_Datafeed\\documents\\',
                    'projects': 'C:\\ML_Datafeed\\projects.json'
                },
                'supported_formats': {
                    'documents': ['pdf', 'docx', 'jpg', 'png', 'bmp', 'gif', 'txt'],
                    'projects': ['json']
                },
                'description': 'Synchronize data from ML_Datafeed directory into database'
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
