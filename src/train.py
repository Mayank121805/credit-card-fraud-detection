import os
import json
import time
import threading
from datetime import datetime
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

from src.preprocessing import DataPreprocessor, FEATURE_COLUMNS
from src.evaluation import compute_all_metrics, get_feature_importance

# Module-level training status dictionary
training_status = {
    'status': 'idle',  # 'idle', 'training', 'completed', 'error'
    'progress': 0,
    'message': 'Ready for training',
    'started_at': None,
    'completed_at': None,
    'error': None
}


class ModelTrainer:
    def __init__(self, config=None):
        self.config = config
        self.preprocessor = DataPreprocessor()
        self.model_folder = getattr(config, 'MODEL_FOLDER', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models'))
        os.makedirs(self.model_folder, exist_ok=True)

    def train_all(self, X_train, y_train, X_test, y_test, db_session=None) -> dict:
        """
        Train Logistic Regression and Random Forest models with balanced class weights.
        Saves artifacts and returns metrics dict.
        """
        results = {}

        # 1. Train Logistic Regression
        t_start_lr = time.time()
        lr_model = LogisticRegression(
            class_weight='balanced',
            max_iter=1000,
            random_state=42,
            C=0.1,
            solver='lbfgs'
        )
        lr_model.fit(X_train, y_train)
        lr_duration = time.time() - t_start_lr

        lr_metrics = compute_all_metrics(lr_model, X_test, y_test, 'Logistic Regression', threshold=0.5)
        lr_metrics['training_time_seconds'] = round(float(lr_duration), 2)

        # 2. Train Random Forest
        t_start_rf = time.time()
        rf_model = RandomForestClassifier(
            n_estimators=100,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1,
            max_depth=10
        )
        rf_model.fit(X_train, y_train)
        rf_duration = time.time() - t_start_rf

        rf_metrics = compute_all_metrics(rf_model, X_test, y_test, 'Random Forest', threshold=0.5)
        rf_metrics['training_time_seconds'] = round(float(rf_duration), 2)

        # 3. Feature Importance from Random Forest
        feature_importance = get_feature_importance(rf_model, FEATURE_COLUMNS)

        # 4. Save models with joblib
        os.makedirs(self.model_folder, exist_ok=True)
        lr_path = os.path.join(self.model_folder, 'logistic_regression.pkl')
        rf_path = os.path.join(self.model_folder, 'random_forest.pkl')

        joblib.dump(lr_model, lr_path)
        joblib.dump(rf_model, rf_path)

        # 5. Compile comprehensive metrics
        all_metrics = {
            'trained_at': datetime.utcnow().isoformat(),
            'training_rows': int(len(X_train)),
            'test_rows': int(len(X_test)),
            'logistic_regression': lr_metrics,
            'random_forest': rf_metrics,
            'feature_importance': feature_importance
        }

        metrics_path = os.path.join(self.model_folder, 'metrics.json')
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump(all_metrics, f, indent=2)

        # 6. Save to Database ModelRegistry if db_session is provided
        if db_session is not None:
            try:
                from database.models import ModelRegistry

                # Deactivate old active models
                db_session.query(ModelRegistry).update({'is_active': False})

                # Register LR
                reg_lr = ModelRegistry(
                    model_name='Logistic Regression',
                    version='1.0.0',
                    trained_at=datetime.utcnow(),
                    training_rows=len(X_train),
                    test_rows=len(X_test),
                    accuracy=lr_metrics['accuracy'],
                    precision_score=lr_metrics['precision'],
                    recall_score=lr_metrics['recall'],
                    f1_score=lr_metrics['f1'],
                    roc_auc=lr_metrics['roc_auc'],
                    pr_auc=lr_metrics['pr_auc'],
                    training_time_seconds=lr_duration,
                    is_active=False
                )
                db_session.add(reg_lr)

                # Register RF (active model)
                reg_rf = ModelRegistry(
                    model_name='Random Forest',
                    version='1.0.0',
                    trained_at=datetime.utcnow(),
                    training_rows=len(X_train),
                    test_rows=len(X_test),
                    accuracy=rf_metrics['accuracy'],
                    precision_score=rf_metrics['precision'],
                    recall_score=rf_metrics['recall'],
                    f1_score=rf_metrics['f1'],
                    roc_auc=rf_metrics['roc_auc'],
                    pr_auc=rf_metrics['pr_auc'],
                    training_time_seconds=rf_duration,
                    is_active=True
                )
                db_session.add(reg_rf)
                db_session.commit()
            except Exception as e:
                db_session.rollback()
                print(f"[ModelTrainer] Warning: Failed to save to ModelRegistry: {e}")

        return all_metrics

    def _async_worker(self, filepath: str, app=None):
        """Worker thread executing training pipeline stages."""
        global training_status

        try:
            # Stage 1: Initializing
            training_status.update({
                'status': 'training',
                'progress': 5,
                'message': 'Starting training workflow...',
                'started_at': datetime.utcnow().isoformat(),
                'completed_at': None,
                'error': None
            })

            # Stage 2: Load and validate dataset
            training_status.update({
                'progress': 15,
                'message': 'Loading and validating dataset...'
            })
            df, _ = self.preprocessor.load_and_validate(filepath)

            # Stage 3: Clean data
            training_status.update({
                'progress': 25,
                'message': 'Cleaning dataset and handling nulls/duplicates...'
            })
            cleaned_df = self.preprocessor.clean_data(df)

            # Stage 4: Preprocessing & Scaling
            training_status.update({
                'progress': 40,
                'message': 'Splitting dataset and fitting feature scalers...'
            })
            X_train, X_test, y_train, y_test, _ = self.preprocessor.preprocess_for_training(
                cleaned_df, model_folder=self.model_folder
            )

            # Stage 5 & 6: Train models
            training_status.update({
                'progress': 60,
                'message': 'Training Logistic Regression model...'
            })

            # We execute training and database saving with app context if provided
            def _execute(session):
                # 60% -> Train LR
                # 80% -> Train RF
                training_status.update({
                    'progress': 75,
                    'message': 'Training Random Forest model (balanced weights)...'
                })
                self.train_all(X_train, y_train, X_test, y_test, db_session=session)

            if app is not None:
                with app.app_context():
                    from extensions import db
                    _execute(db.session)
            else:
                _execute(None)

            # Stage 7 & 8: Metrics saved and DB recorded
            training_status.update({
                'progress': 95,
                'message': 'Metrics computed and model registry updated...'
            })

            # Stage 9: Complete
            training_status.update({
                'status': 'completed',
                'progress': 100,
                'message': 'Training completed successfully. All models and artifacts ready.',
                'completed_at': datetime.utcnow().isoformat(),
                'error': None
            })

        except Exception as e:
            # Stage 10: Handle error
            training_status.update({
                'status': 'error',
                'progress': 0,
                'message': f'Training failed: {str(e)}',
                'completed_at': datetime.utcnow().isoformat(),
                'error': str(e)
            })

    def start_training_async(self, filepath: str, app=None):
        """Start async model training in a background thread."""
        thread = threading.Thread(
            target=self._async_worker,
            args=(filepath, app),
            daemon=True
        )
        thread.start()
        return thread
