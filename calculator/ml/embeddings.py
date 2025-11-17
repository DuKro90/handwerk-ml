"""
Sentence transformer embeddings for semantic similarity search
"""
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Optional
import os


class EmbeddingGenerator:
    """Singleton für Embedding-Generierung mit Lazy Loading"""
    _instance: Optional['EmbeddingGenerator'] = None
    _model: Optional[SentenceTransformer] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def model(self) -> SentenceTransformer:
        """Lazy Loading des Sentence-Transformer-Modells"""
        if self._model is None:
            # Überprüfe ob externes Model-Directory existiert
            external_model_path = os.path.join(
                os.getenv('PROGRAMDATA', 'C:\\ProgramData'),
                'HandwerkML', 'Models', 'all-MiniLM-L6-v2'
            )

            if os.path.exists(external_model_path):
                print(f"Lade Modell von: {external_model_path}")
                self._model = SentenceTransformer(external_model_path)
            else:
                print("Lade Modell von HuggingFace (erster Start)")
                self._model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

        return self._model

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generiert 384-dim Embedding für Text
        Returns: List of floats (für JSON-Speicherung)
        """
        if not text or not text.strip():
            # Default-Embedding für leere Texte
            return [0.0] * 384

        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Batch-Generierung für Performance
        """
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
        return [emb.tolist() for emb in embeddings]

    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Cosine Similarity zwischen zwei Embeddings
        Returns: float 0.0-1.0
        """
        from sklearn.metrics.pairwise import cosine_similarity
        arr1 = np.array(embedding1).reshape(1, -1)
        arr2 = np.array(embedding2).reshape(1, -1)
        return float(cosine_similarity(arr1, arr2)[0][0])

    def find_similar_projects(self, query_embedding: List[float], projects, top_k: int = 5) -> List[dict]:
        """
        Finde ähnliche Projekte basierend auf Embeddings

        Args:
            query_embedding: Query-Embedding
            projects: QuerySet oder Liste von Projekten
            top_k: Anzahl top Ergebnisse

        Returns:
            Liste von ähnlichen Projekten mit Similarity Score
        """
        from sklearn.metrics.pairwise import cosine_similarity

        results = []

        for project in projects:
            # Skip projects without embeddings
            if not project.description_embedding:
                continue

            try:
                # Convert to numpy arrays
                query_arr = np.array(query_embedding).reshape(1, -1)
                project_arr = np.array(project.description_embedding).reshape(1, -1)

                # Calculate similarity
                similarity = float(cosine_similarity(query_arr, project_arr)[0][0])

                # Only include if similarity > threshold
                if similarity > 0.3:
                    results.append({
                        'id': str(project.id),
                        'name': project.name,
                        'type': project.project_type,
                        'similarity': similarity,
                        'price': float(project.final_price) if project.final_price else 0,
                    })
            except Exception as e:
                print(f"Error calculating similarity for {project.name}: {e}")
                continue

        # Sort by similarity (descending)
        results.sort(key=lambda x: x['similarity'], reverse=True)

        return results[:top_k]
