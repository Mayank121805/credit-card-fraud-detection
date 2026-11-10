import os
import io
import json
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, send_file
import pandas as pd

from extensions import db
from database.models import PredictionLog
from src.predict import (
    FEATURE_COLUMNS,
    load_model_and_scaler,
    load_lr_model,
    predict_single,
    predict_batch
)
from src.train import ModelTrainer, training_status

ml_bp = Blueprint('ml', __name__)


@ml_bp.route('/api/ml/train', methods=['POST'])
@ml_bp.route('/ml/train', methods=['POST'])
def train_models():
    """Start asynchronous model training."""
    # Check if already training
    if training_status.get('status') == 'training':
        return jsonify({
            'success': False,
            'message': 'Training is already in progress.',
            'training_status': training_status
        }), 409

    # Determine dataset filepath
    upload_folder = current_app.config.get(
        'UPLOAD_FOLDER',
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw')
    )

    dataset_path = None
    if os.path.exists(upload_folder):
        # Prefer creditcard.csv, then any csv
        priority_file = os.path.join(upload_folder, 'creditcard.csv')
        if os.path.exists(priority_file) and os.path.getsize(priority_file) > 0:
            dataset_path = priority_file
        else:
            csvs = [f for f in os.listdir(upload_folder) if f.lower().endswith('.csv')]
            if csvs:
                dataset_path = os.path.join(upload_folder, csvs[0])

    if not dataset_path or not os.path.exists(dataset_path):
        return jsonify({
            'success': False,
            'message': 'No dataset found. Please upload a dataset first.'
        }), 400

    # Start training in background thread
    trainer = ModelTrainer(config=current_app.config)
    trainer.start_training_async(dataset_path, app=current_app._get_current_object())

    return jsonify({
        'success': True,
        'message': 'Training started in background.'
    }), 200


@ml_bp.route('/api/ml/train/status', methods=['GET'])
@ml_bp.route('/ml/train/status', methods=['GET'])
def get_training_status():
    """Return the current async training status."""
    return jsonify(training_status), 200


@ml_bp.route('/api/ml/metrics', methods=['GET'])
@ml_bp.route('/ml/metrics', methods=['GET'])
def get_metrics():
    """Return saved metrics and evaluation curves from models/metrics.json."""
    model_folder = current_app.config.get(
        'MODEL_FOLDER',
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
    )
    metrics_path = os.path.join(model_folder, 'metrics.json')

    if not os.path.exists(metrics_path):
        return jsonify({
            'model_trained': False,
            'message': 'Models have not been trained yet.'
        }), 200

    try:
        with open(metrics_path, 'r', encoding='utf-8') as f:
            metrics_data = json.load(f)
        metrics_data['model_trained'] = True
        return jsonify(metrics_data), 200
    except Exception as e:
        return jsonify({
            'model_trained': False,
            'error': f'Failed to read metrics file: {str(e)}'
        }), 500


@ml_bp.route('/api/ml/predict', methods=['POST'])
@ml_bp.route('/ml/predict', methods=['POST'])
def predict_transaction():
    """
    Accept single transaction JSON payload and return fraud probability and classification.
    Payload must contain Time, V1-V28, Amount.
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid request: JSON body required'}), 400

    # Validate feature columns
    missing_cols = [col for col in FEATURE_COLUMNS if col not in data]
    if missing_cols:
        return jsonify({
            'error': f'Missing required features ({len(missing_cols)}): {", ".join(missing_cols[:5])}'
        }), 400

    model_folder = current_app.config.get(
        'MODEL_FOLDER',
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
    )
    model, scaler = load_model_and_scaler(model_folder)
    if model is None or scaler is None:
        return jsonify({
            'error': 'Models not trained yet. Please train the models before making predictions.'
        }), 400

    try:
        threshold = float(data.get('threshold', 0.5))
    except (ValueError, TypeError):
        threshold = 0.5

    try:
        result = predict_single(data, model, scaler, threshold=threshold)
        amount = float(data.get('Amount', 0.0))

        # Record in database
        try:
            log = PredictionLog(
                timestamp=datetime.utcnow(),
                transaction_amount=amount,
                prediction=result['prediction'],
                label=result['label'],
                probability_fraud=result['probability_fraud'],
                probability_legit=result['probability_legit'],
                model_used=result['model_used'],
                source='single',
                batch_id=None
            )
            db.session.add(log)
            db.session.commit()
            result['id'] = log.id
            result['timestamp'] = log.timestamp.isoformat()
        except Exception as db_err:
            db.session.rollback()
            print(f"[ml] Failed to log prediction: {db_err}")

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': f'Prediction failed: {str(e)}'}), 500


@ml_bp.route('/api/ml/predict/batch', methods=['POST'])
@ml_bp.route('/ml/predict/batch', methods=['POST'])
def predict_batch_transactions():
    """
    Accept CSV file, predict fraud for all rows, log to DB,
    and return result CSV as downloadable attachment.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Invalid file format. Only CSV files are supported.'}), 400

    model_folder = current_app.config.get(
        'MODEL_FOLDER',
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
    )
    model, scaler = load_model_and_scaler(model_folder)
    if model is None or scaler is None:
        return jsonify({
            'error': 'Models not trained yet. Please train the models before making predictions.'
        }), 400

    try:
        threshold = float(request.form.get('threshold', 0.5))
    except (ValueError, TypeError):
        threshold = 0.5

    try:
        df = pd.read_csv(file)
        missing_cols = [c for c in FEATURE_COLUMNS if c not in df.columns]
        if missing_cols:
            return jsonify({
                'error': f'Uploaded CSV missing required features ({len(missing_cols)}): {", ".join(missing_cols[:5])}'
            }), 400

        result_df = predict_batch(df, model, scaler, threshold=threshold)
        batch_id = str(uuid.uuid4())[:8]

        # Log predictions in DB in bulk
        try:
            logs = []
            for _, row in result_df.iterrows():
                amt = float(row.get('Amount', 0.0))
                prob_f = float(row['Probability_Fraud'])
                logs.append(PredictionLog(
                    timestamp=datetime.utcnow(),
                    transaction_amount=amt,
                    prediction=int(row['Predicted_Class']),
                    label=str(row['Predicted_Label']),
                    probability_fraud=round(prob_f, 6),
                    probability_legit=round(1.0 - prob_f, 6),
                    model_used='RandomForest',
                    source='batch',
                    batch_id=batch_id
                ))
            db.session.bulk_save_objects(logs)
            db.session.commit()
        except Exception as db_err:
            db.session.rollback()
            print(f"[ml] Failed to bulk log batch predictions: {db_err}")

        # Stream CSV back to client as downloadable file
        csv_buffer = io.BytesIO()
        result_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        filename = f"predictions_batch_{batch_id}.csv"
        return send_file(
            csv_buffer,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'error': f'Batch processing failed: {str(e)}'}), 500
