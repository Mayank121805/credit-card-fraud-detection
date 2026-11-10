import io
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file
from sqlalchemy import func
import pandas as pd

from extensions import db
from database.models import PredictionLog

history_bp = Blueprint('history', __name__)


@history_bp.route('/api/history', methods=['GET'])
def get_prediction_history():
    """
    Return paginated list of prediction history records.
    Query params: page (default 1), per_page (default 20), filter ('all', 'fraud', 'legitimate').
    """
    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = max(1, min(100, int(request.args.get('per_page', 20))))
    except (ValueError, TypeError):
        page = 1
        per_page = 20

    filter_type = request.args.get('filter', 'all').lower()

    query = db.session.query(PredictionLog)

    if filter_type in ('fraud', '1'):
        query = query.filter(PredictionLog.prediction == 1)
    elif filter_type in ('legitimate', 'legit', '0'):
        query = query.filter(PredictionLog.prediction == 0)

    total = query.count()
    pages = (total + per_page - 1) // per_page if total > 0 else 1

    records = (
        query.order_by(PredictionLog.timestamp.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    history = [r.to_dict() for r in records]

    return jsonify({
        'history': history,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': pages
    }), 200


@history_bp.route('/api/history/export', methods=['GET'])
@history_bp.route('/history/export', methods=['GET'])
def export_prediction_history():
    """Export all prediction records as a downloadable CSV."""
    records = db.session.query(PredictionLog).order_by(PredictionLog.timestamp.desc()).all()
    data = [r.to_dict() for r in records]

    if not data:
        # Return empty CSV with proper headers
        df = pd.DataFrame(columns=[
            'id', 'timestamp', 'transaction_amount', 'prediction', 'label',
            'probability_fraud', 'probability_legit', 'model_used', 'source', 'batch_id'
        ])
    else:
        df = pd.DataFrame(data)

    csv_buf = io.BytesIO()
    df.to_csv(csv_buf, index=False)
    csv_buf.seek(0)

    return send_file(
        csv_buf,
        mimetype='text/csv',
        as_attachment=True,
        download_name='prediction_history.csv'
    )


@history_bp.route('/api/history/clear', methods=['DELETE', 'POST'])
@history_bp.route('/history/clear', methods=['DELETE', 'POST'])
def clear_prediction_history():
    """Clear all prediction records from the database."""
    try:
        deleted_count = db.session.query(PredictionLog).delete()
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Successfully cleared {deleted_count} prediction record(s).',
            'count': deleted_count
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Failed to clear history: {str(e)}'}), 500


@history_bp.route('/api/history/stats', methods=['GET'])
@history_bp.route('/history/stats', methods=['GET'])
def get_history_stats():
    """Return summary statistics of predictions."""
    total = db.session.query(PredictionLog).count()
    fraud = db.session.query(PredictionLog).filter(PredictionLog.prediction == 1).count()
    legit = db.session.query(PredictionLog).filter(PredictionLog.prediction == 0).count()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = db.session.query(PredictionLog).filter(PredictionLog.timestamp >= today_start).count()

    avg_fraud_prob_res = db.session.query(func.avg(PredictionLog.probability_fraud)).scalar()
    avg_fraud_prob = float(avg_fraud_prob_res) if avg_fraud_prob_res is not None else 0.0

    return jsonify({
        'total_predictions': total,
        'fraud_predictions': fraud,
        'legit_predictions': legit,
        'avg_fraud_probability': round(avg_fraud_prob, 4),
        'predictions_today': today_count
    }), 200
