"""
XGBoost-based price prediction model
"""
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import pandas as pd
import numpy as np
import joblib
import os
from typing import Dict, Tuple, Optional


class PricePredictor:
    """XGBoost-basierter Preis-Prediktor mit Feature Engineering"""

    def __init__(self):
        self.model: Optional[xgb.XGBRegressor] = None
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.feature_names: list = []
        self.model_version = "v1.0.0"

    def prepare_features(self, projects_df: pd.DataFrame) -> pd.DataFrame:
        """
        Feature Engineering für Preis-Prediction
        """
        features = pd.DataFrame()

        # Numerische Features
        features['total_area_sqm'] = projects_df['total_area_sqm']
        features['complexity'] = projects_df['complexity']

        # Kategorische Features -> Label Encoding
        for col in ['wood_type', 'project_type', 'region']:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                self.label_encoders[col].fit(projects_df[col])

            features[f'{col}_encoded'] = self.label_encoders[col].transform(
                projects_df[col]
            )

        # Interaktions-Features
        features['wood_area_interaction'] = (
            features['total_area_sqm'] *
            (features['wood_type_encoded'] + 1)
        )

        features['complexity_area_interaction'] = (
            features['total_area_sqm'] *
            features['complexity']
        )

        # Temporale Features
        if 'project_date' in projects_df.columns:
            projects_df['months_old'] = (
                (pd.Timestamp.now() - pd.to_datetime(projects_df['project_date']))
                .dt.days / 30
            )
            features['months_old'] = projects_df['months_old']
            features['is_recent'] = (projects_df['months_old'] < 6).astype(int)

        self.feature_names = features.columns.tolist()
        return features

    def train(self, projects_queryset, test_size: float = 0.2) -> Dict:
        """
        Trainiert XGBoost-Modell
        Returns: Dict mit Training-Metriken
        """
        # QuerySet -> DataFrame
        df = pd.DataFrame(list(projects_queryset.values(
            'total_area_sqm', 'wood_type', 'project_type',
            'region', 'complexity', 'final_price', 'project_date'
        )))

        if len(df) < 30:
            raise ValueError(f"Mindestens 30 Projekte benötigt, nur {len(df)} vorhanden.")

        # Features vorbereiten
        X = self.prepare_features(df)
        y = df['final_price']

        # Train-Test-Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )

        # XGBoost trainieren
        self.model = xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            min_child_weight=3,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1
        )

        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            early_stopping_rounds=10,
            verbose=False
        )

        # Performance-Metriken
        train_predictions = self.model.predict(X_train)
        test_predictions = self.model.predict(X_test)

        train_mape = np.mean(np.abs((y_train - train_predictions) / y_train)) * 100
        test_mape = np.mean(np.abs((y_test - test_predictions) / y_test)) * 100

        train_rmse = np.sqrt(np.mean((y_train - train_predictions) ** 2))
        test_rmse = np.sqrt(np.mean((y_test - test_predictions) ** 2))

        metrics = {
            'train_mape': round(train_mape, 2),
            'test_mape': round(test_mape, 2),
            'train_rmse': round(train_rmse, 2),
            'test_rmse': round(test_rmse, 2),
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'model_version': self.model_version
        }

        print(f"✓ Modell trainiert | Test-MAPE: {test_mape:.2f}% | Test-RMSE: {test_rmse:.2f}€")

        return metrics

    def predict(self, project_data: Dict) -> float:
        """
        Vorhersage für neues Projekt
        project_data: dict mit keys wie 'wood_type', 'total_area_sqm', etc.
        """
        if self.model is None:
            raise ValueError("Modell muss erst trainiert oder geladen werden.")

        # DataFrame aus Input erstellen
        df = pd.DataFrame([project_data])

        # Features vorbereiten
        X = self.prepare_features(df)

        # Prediction
        predicted_price = float(self.model.predict(X)[0])

        return predicted_price

    def save_model(self, path: str = 'models/xgboost_model.pkl'):
        """Modell persistieren"""
        os.makedirs(os.path.dirname(path), exist_ok=True)

        model_data = {
            'model': self.model,
            'label_encoders': self.label_encoders,
            'feature_names': self.feature_names,
            'model_version': self.model_version
        }

        joblib.dump(model_data, path)
        print(f"✓ Modell gespeichert: {path}")

    def load_model(self, path: str = 'models/xgboost_model.pkl'):
        """Modell laden"""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Modell-Datei nicht gefunden: {path}")

        model_data = joblib.load(path)

        self.model = model_data['model']
        self.label_encoders = model_data['label_encoders']
        self.feature_names = model_data['feature_names']
        self.model_version = model_data.get('model_version', 'unknown')

        print(f"✓ Modell geladen: {path} (Version: {self.model_version})")
