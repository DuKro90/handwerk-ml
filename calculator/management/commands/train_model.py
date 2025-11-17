"""
Management Command: Train XGBoost Price Prediction Model
Trains model on historical project data
Usage: python manage.py train_model
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
import os

from calculator.models import Project
from calculator.ml.price_predictor import PricePredictor
from calculator.ml.feature_engineer import FeatureEngineer
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Train XGBoost price prediction model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-size',
            type=float,
            default=0.2,
            help='Portion of test data (0.0-1.0)'
        )
        parser.add_argument(
            '--min-samples',
            type=int,
            default=30,
            help='Minimum number of projects to train'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force training even if model exists'
        )
        parser.add_argument(
            '--model-dir',
            type=str,
            default='models',
            help='Directory to save model'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('⏳ Starting model training...'))

        # Get options
        test_size = options['test_size']
        min_samples = options['min_samples']
        force = options['force']
        model_dir = options['model_dir']

        # Create models directory
        model_path = Path(settings.BASE_DIR) / model_dir
        model_path.mkdir(exist_ok=True)

        model_file = model_path / 'xgboost_model.pkl'

        # Check if model already exists
        if model_file.exists() and not force:
            self.stdout.write(self.style.WARNING(
                f'⚠️  Model already exists at {model_file}\n'
                'Use --force to overwrite'
            ))
            return

        # Get finalized projects
        projects = Project.objects.filter(is_finalized=True).exclude(final_price__isnull=True)

        self.stdout.write(f'📊 Available finalized projects: {projects.count()}')

        # Check if we have enough data
        if projects.count() < min_samples:
            self.stdout.write(self.style.ERROR(
                f'✗ Need at least {min_samples} projects for training, '
                f'but only {projects.count()} available'
            ))
            return

        try:
            # Initialize feature engineer and predictor
            self.stdout.write('🔧 Initializing feature engineering...')
            feature_engineer = FeatureEngineer()

            # Extract features and prices
            self.stdout.write('📈 Extracting features...')
            features_df, prices = feature_engineer.extract_from_queryset(projects)

            # Handle missing values
            features_df = FeatureEngineer.handle_missing_values(features_df, strategy='mean')

            # Create interaction features
            self.stdout.write('🔗 Creating interaction features...')
            features_df = feature_engineer.create_interaction_features(features_df)

            # Compute statistics
            stats = feature_engineer.compute_statistics(features_df)
            self.stdout.write(f'📊 Extracted features: {len(stats)}')

            # Initialize predictor
            predictor = PricePredictor()

            # Train model
            self.stdout.write('🤖 Training XGBoost model...')
            import pandas as pd
            prices_series = pd.Series(prices, index=features_df.index)

            # Train/test split
            from sklearn.model_selection import train_test_split
            X_train, X_test, y_train, y_test = train_test_split(
                features_df, prices_series, test_size=test_size, random_state=42
            )

            # Train model
            metrics = predictor.train(
                X_train=X_train,
                y_train=y_train,
                X_val=X_test,
                y_val=y_test,
                max_depth=6,
                learning_rate=0.1,
                n_estimators=100,
            )

            if metrics.get('status') != 'success':
                self.stdout.write(self.style.ERROR(f'✗ Training failed: {metrics}'))
                return

            # Save model
            predictor.save_model(str(model_file))

            # Print results
            self.stdout.write(self.style.SUCCESS('\n✅ Training completed successfully!'))
            self.stdout.write(f'📁 Model saved to: {model_file}')

            self.stdout.write('\n📊 Training Metrics:')
            self.stdout.write(f"  Train MAPE: {metrics['train_mape']}%")
            self.stdout.write(f"  Test MAPE: {metrics['test_mape']}%")
            self.stdout.write(f"  Train RMSE: {metrics['train_rmse']}€")
            self.stdout.write(f"  Test RMSE: {metrics['test_rmse']}€")
            self.stdout.write(f"  Training Samples: {metrics['training_samples']}")
            self.stdout.write(f"  Test Samples: {metrics['test_samples']}")
            self.stdout.write(f"  Model Version: {metrics['model_version']}")
            self.stdout.write(f"  Saved to: {model_path}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Training failed: {str(e)}'))
