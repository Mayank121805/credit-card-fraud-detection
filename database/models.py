from datetime import datetime
from extensions import db


class PredictionLog(db.Model):
    __tablename__ = 'prediction_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    transaction_amount = db.Column(db.Float, nullable=False)
    prediction = db.Column(db.Integer, nullable=False)  # 0: Legit, 1: Fraud
    label = db.Column(db.String(20), nullable=False)    # 'Legitimate' or 'Fraudulent'
    probability_fraud = db.Column(db.Float, nullable=False)
    probability_legit = db.Column(db.Float, nullable=False)
    model_used = db.Column(db.String(50), nullable=False, default='RandomForest')
    source = db.Column(db.String(20), nullable=False, default='single')  # 'single' or 'batch'
    batch_id = db.Column(db.String(50), nullable=True, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'transaction_amount': float(self.transaction_amount) if self.transaction_amount is not None else 0.0,
            'prediction': int(self.prediction),
            'label': self.label,
            'probability_fraud': round(float(self.probability_fraud), 6) if self.probability_fraud is not None else 0.0,
            'probability_legit': round(float(self.probability_legit), 6) if self.probability_legit is not None else 0.0,
            'model_used': self.model_used,
            'source': self.source,
            'batch_id': self.batch_id
        }


class ModelRegistry(db.Model):
    __tablename__ = 'model_registry'

    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(100), nullable=False)
    version = db.Column(db.String(20), nullable=False, default='1.0.0')
    trained_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    training_rows = db.Column(db.Integer, nullable=False)
    test_rows = db.Column(db.Integer, nullable=False)
    accuracy = db.Column(db.Float, nullable=False)
    precision_score = db.Column(db.Float, nullable=False)
    recall_score = db.Column(db.Float, nullable=False)
    f1_score = db.Column(db.Float, nullable=False)
    roc_auc = db.Column(db.Float, nullable=False)
    pr_auc = db.Column(db.Float, nullable=False)
    training_time_seconds = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'model_name': self.model_name,
            'version': self.version,
            'trained_at': self.trained_at.isoformat() if self.trained_at else None,
            'training_rows': int(self.training_rows),
            'test_rows': int(self.test_rows),
            'accuracy': round(float(self.accuracy), 6) if self.accuracy is not None else 0.0,
            'precision_score': round(float(self.precision_score), 6) if self.precision_score is not None else 0.0,
            'recall_score': round(float(self.recall_score), 6) if self.recall_score is not None else 0.0,
            'f1_score': round(float(self.f1_score), 6) if self.f1_score is not None else 0.0,
            'roc_auc': round(float(self.roc_auc), 6) if self.roc_auc is not None else 0.0,
            'pr_auc': round(float(self.pr_auc), 6) if self.pr_auc is not None else 0.0,
            'training_time_seconds': round(float(self.training_time_seconds), 2) if self.training_time_seconds is not None else 0.0,
            'is_active': bool(self.is_active)
        }


class DatasetUpload(db.Model):
    __tablename__ = 'dataset_uploads'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    row_count = db.Column(db.Integer, nullable=False)
    fraud_count = db.Column(db.Integer, nullable=False)
    legit_count = db.Column(db.Integer, nullable=False)
    fraud_rate = db.Column(db.Float, nullable=False)
    file_size_mb = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'row_count': int(self.row_count),
            'fraud_count': int(self.fraud_count),
            'legit_count': int(self.legit_count),
            'fraud_rate': round(float(self.fraud_rate), 4) if self.fraud_rate is not None else 0.0,
            'file_size_mb': round(float(self.file_size_mb), 2) if self.file_size_mb is not None else 0.0
        }
