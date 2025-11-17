"""
Confidence scoring for ML predictions with error handling
"""
import logging
import numpy as np
from typing import List, Dict, Optional
from calculator.models import Project
from calculator.ml.embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


class ConfidenceCalculator:
    """Berechnet Confidence-Scores für ML-Predictions"""

    def __init__(self):
        self.embedding_gen = EmbeddingGenerator()

    def calculate_confidence(
        self,
        similar_projects_count: int,
        price_variance: float,
        predicted_price: float,
        data_quality_score: float,
        avg_months_old: float
    ) -> float:
        """
        Multi-Faktor Confidence Score Berechnung

        Formula:
          Confidence =
            0.35 × log(1+similar_count)/log(100) +
            0.30 × (1/(1+variance/price)) +
            0.20 × data_quality +
            0.15 × exp(-0.1×months_old)

        Returns: Score 0.0-1.0
        """

        # Component 1: Anzahl ähnlicher Projekte (0-1, logarithmisch)
        similarity_score = min(
            np.log(1 + similar_projects_count) / np.log(100),
            1.0
        )

        # Component 2: Preisvarianz (niedrige Varianz = höhere Confidence)
        if predicted_price > 0 and price_variance >= 0:
            variance_score = 1 / (1 + price_variance / predicted_price)
        else:
            variance_score = 0.5

        # Component 3: Datenqualität (0-1, vorberechnet)
        quality_score = max(0.0, min(1.0, data_quality_score))

        # Component 4: Zeitliche Nähe (neuere Projekte = relevanter)
        temporal_score = np.exp(-0.1 * avg_months_old)

        # Gewichtete Summe
        confidence = (
            0.35 * similarity_score +
            0.30 * variance_score +
            0.20 * quality_score +
            0.15 * temporal_score
        )

        return round(float(confidence), 3)

    def find_similar_projects(
        self,
        new_project_description: str,
        top_k: int = 20
    ) -> List[Dict]:
        """
        Findet die ähnlichsten Projekte via Cosine Similarity
        Returns: Liste von Dicts mit {project, similarity}
        """

        # Embedding für neue Beschreibung
        new_embedding = self.embedding_gen.generate_embedding(new_project_description)

        # Alle Projekte mit Embeddings holen
        projects = Project.objects.exclude(
            description_embedding__isnull=True
        ).filter(
            is_finalized=True  # Nur finalisierte Projekte
        )

        similarities = []
        for project in projects:
            similarity = self.embedding_gen.calculate_similarity(
                new_embedding,
                project.description_embedding
            )
            similarities.append({
                'project': project,
                'similarity': similarity
            })

        # Sortieren nach Similarity (höchste zuerst)
        similarities.sort(key=lambda x: x['similarity'], reverse=True)

        return similarities[:top_k]

    def calculate_data_quality(self, project_data: Dict) -> float:
        """
        Prüft Vollständigkeit und Qualität der Input-Features
        Returns: Score 0.0-1.0
        """
        required_fields = [
            'wood_type',
            'total_area_sqm',
            'project_type',
            'complexity',
            'region',
            'description'
        ]

        filled_fields = 0
        for field in required_fields:
            value = project_data.get(field)
            if value is not None and str(value).strip():
                filled_fields += 1

        # Basis-Score (Vollständigkeit)
        base_score = filled_fields / len(required_fields)

        # Bonus für gute Beschreibung (>20 Zeichen)
        description = str(project_data.get('description', ''))
        description_bonus = min(len(description) / 100, 0.2)

        # Bonus für realistische Werte
        area = project_data.get('total_area_sqm', 0)
        area_bonus = 0.1 if 5 <= area <= 500 else 0

        total_score = min(1.0, base_score + description_bonus + area_bonus)

        return round(total_score, 3)

    def classify_confidence_level(self, confidence: float) -> Dict[str, str]:
        """
        Klassifiziert Confidence-Score in menschenlesbare Kategorie
        Returns: {'level': str, 'color': str, 'recommendation': str}
        """
        if confidence >= 0.8:
            return {
                'level': 'Sehr hoch',
                'color': 'green',
                'recommendation': 'Vorhersage kann direkt verwendet werden.'
            }
        elif confidence >= 0.6:
            return {
                'level': 'Hoch',
                'color': 'lightgreen',
                'recommendation': 'Vorhersage ist verlässlich, manuelle Überprüfung empfohlen.'
            }
        elif confidence >= 0.4:
            return {
                'level': 'Mittel',
                'color': 'yellow',
                'recommendation': 'Vorhersage mit Vorsicht verwenden, sorgfältige Prüfung notwendig.'
            }
        elif confidence >= 0.2:
            return {
                'level': 'Niedrig',
                'color': 'orange',
                'recommendation': 'Vorhersage unsicher, manuelle Kalkulation empfohlen.'
            }
        else:
            return {
                'level': 'Sehr niedrig',
                'color': 'red',
                'recommendation': 'Vorhersage nicht verlässlich - manuelle Kalkulation erforderlich.'
            }
