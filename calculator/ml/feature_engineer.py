"""
Feature Engineering Module
Extracts and transforms features from project data for ML models
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Feature engineering for construction project data
    Transforms raw project data into ML-ready features
    """

    def __init__(self):
        self.feature_names = None
        self.feature_config = None
        self.categorical_features = ['wood_type', 'project_type', 'region']
        self.numerical_features = ['total_area_sqm', 'complexity']

    def extract_features(self, project_dict: Dict) -> Dict[str, float]:
        """
        Extract features from single project

        Args:
            project_dict: Dictionary with project data

        Returns:
            dict: Extracted features
        """
        features = {}

        # Numerical features
        features['total_area_sqm'] = float(project_dict.get('total_area_sqm', 0))
        features['complexity'] = int(project_dict.get('complexity', 1))

        # Categorical features (store as-is for label encoding)
        features['wood_type'] = str(project_dict.get('wood_type', 'Unbekannt'))
        features['project_type'] = str(project_dict.get('project_type', 'Sonstiges'))
        features['region'] = str(project_dict.get('region', 'Deutschland'))

        # Derived features
        features['area_per_complexity'] = features['total_area_sqm'] / max(features['complexity'], 1)

        # Temporal features
        if 'project_date' in project_dict:
            try:
                project_date = pd.to_datetime(project_dict['project_date'])
                days_old = (datetime.now() - project_date).days
                features['months_old'] = max(0, days_old / 30)
                features['is_recent'] = 1 if days_old < 180 else 0  # Less than 6 months
            except:
                features['months_old'] = 0
                features['is_recent'] = 0
        else:
            features['months_old'] = 0
            features['is_recent'] = 0

        return features

    def extract_batch_features(self, projects_list: List[Dict]) -> pd.DataFrame:
        """
        Extract features from multiple projects

        Args:
            projects_list: List of project dictionaries

        Returns:
            pd.DataFrame: Features DataFrame
        """
        features_list = []

        for project in projects_list:
            try:
                features = self.extract_features(project)
                features_list.append(features)
            except Exception as e:
                logger.warning(f"Error extracting features for project: {e}")
                continue

        df = pd.DataFrame(features_list)
        self.feature_names = df.columns.tolist()

        return df

    def extract_from_queryset(self, queryset) -> Tuple[pd.DataFrame, List[float]]:
        """
        Extract features from Django QuerySet

        Args:
            queryset: Django QuerySet of Project objects

        Returns:
            tuple: (Features DataFrame, Prices list)
        """
        projects_data = []
        prices = []

        for project in queryset:
            data = {
                'total_area_sqm': project.total_area_sqm or 0,
                'complexity': project.complexity or 1,
                'wood_type': project.wood_type or 'Unbekannt',
                'project_type': project.project_type or 'Sonstiges',
                'region': project.region or 'Deutschland',
                'project_date': project.project_date,
                'final_price': project.final_price or 0,
            }

            features = self.extract_features(data)
            projects_data.append(features)
            prices.append(float(project.final_price or 0))

        df = pd.DataFrame(projects_data)
        self.feature_names = df.columns.tolist()

        return df, prices

    def compute_statistics(self, features_df: pd.DataFrame) -> Dict:
        """
        Compute statistics about features

        Args:
            features_df: Features DataFrame

        Returns:
            dict: Feature statistics
        """
        stats = {}

        for col in features_df.columns:
            if features_df[col].dtype in ['int64', 'float64']:
                stats[col] = {
                    'mean': float(features_df[col].mean()),
                    'std': float(features_df[col].std()),
                    'min': float(features_df[col].min()),
                    'max': float(features_df[col].max()),
                    'count': int(features_df[col].count()),
                }
            else:
                stats[col] = {
                    'unique_values': int(features_df[col].nunique()),
                    'count': int(features_df[col].count()),
                }

        return stats

    def create_interaction_features(
        self,
        features_df: pd.DataFrame,
        feature_pairs: Optional[List[Tuple[str, str]]] = None
    ) -> pd.DataFrame:
        """
        Create interaction features

        Args:
            features_df: Features DataFrame
            feature_pairs: Pairs of features to create interactions for

        Returns:
            pd.DataFrame: DataFrame with interaction features
        """
        df = features_df.copy()

        if feature_pairs is None:
            feature_pairs = [
                ('total_area_sqm', 'complexity'),
                ('total_area_sqm', 'months_old'),
            ]

        for feat1, feat2 in feature_pairs:
            if feat1 in df.columns and feat2 in df.columns:
                interaction_name = f'{feat1}_x_{feat2}'
                df[interaction_name] = df[feat1] * df[feat2]

        return df

    def get_feature_info(self) -> Dict:
        """
        Get information about extracted features

        Returns:
            dict: Feature information
        """
        return {
            'feature_names': self.feature_names,
            'n_features': len(self.feature_names) if self.feature_names else 0,
            'categorical_features': self.categorical_features,
            'numerical_features': self.numerical_features,
        }

    @staticmethod
    def normalize_features(features_df: pd.DataFrame, config: Optional[Dict] = None) -> pd.DataFrame:
        """
        Normalize numerical features

        Args:
            features_df: Features DataFrame
            config: Normalization configuration (min/max values)

        Returns:
            pd.DataFrame: Normalized DataFrame
        """
        df = features_df.copy()

        numerical_cols = df.select_dtypes(include=[np.number]).columns

        for col in numerical_cols:
            if config and col in config:
                min_val = config[col]['min']
                max_val = config[col]['max']
            else:
                min_val = df[col].min()
                max_val = df[col].max()

            if max_val > min_val:
                df[col] = (df[col] - min_val) / (max_val - min_val)
            else:
                df[col] = 0

        return df

    @staticmethod
    def handle_missing_values(
        features_df: pd.DataFrame,
        strategy: str = 'mean'
    ) -> pd.DataFrame:
        """
        Handle missing values in features

        Args:
            features_df: Features DataFrame
            strategy: 'mean', 'median', 'drop'

        Returns:
            pd.DataFrame: DataFrame with missing values handled
        """
        df = features_df.copy()

        if strategy == 'drop':
            df = df.dropna()
        elif strategy in ['mean', 'median']:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if df[col].isnull().sum() > 0:
                    if strategy == 'mean':
                        df[col].fillna(df[col].mean(), inplace=True)
                    elif strategy == 'median':
                        df[col].fillna(df[col].median(), inplace=True)

            # Fill categorical with mode
            categorical_cols = df.select_dtypes(include=['object']).columns
            for col in categorical_cols:
                if df[col].isnull().sum() > 0:
                    df[col].fillna(df[col].mode()[0], inplace=True)

        return df

    @staticmethod
    def detect_outliers(
        features_df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        threshold: float = 3.0
    ) -> pd.DataFrame:
        """
        Detect outliers using z-score method

        Args:
            features_df: Features DataFrame
            columns: Columns to check for outliers
            threshold: Z-score threshold (default 3.0 = 99.7% of data)

        Returns:
            pd.DataFrame: Boolean DataFrame indicating outliers
        """
        from scipy import stats

        df = features_df.copy()

        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns

        outliers = pd.DataFrame(False, index=df.index, columns=df.columns)

        for col in columns:
            if col in df.columns:
                z_scores = np.abs(stats.zscore(df[col].dropna()))
                outlier_indices = z_scores > threshold
                outliers.loc[df.index[outlier_indices.index], col] = True

        return outliers
