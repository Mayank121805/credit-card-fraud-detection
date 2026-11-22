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
    Return paginated list of prediction history records with advanced filtering and sorting.
    Query params:
        page (int): default 1
        per_page (int): default 20
        filter (str): 'all', 'fraud', 'legitimate'
        search (str): text match on label, model_used, source
        amount_min (float): minimum transaction amount
        amount_max (float): maximum transaction amount
        prob_min (float): minimum fraud probability (0.0 to 1.0)
        date_from (str): ISO date string
        date_to (str): ISO date string
        sort_by (str): 'timestamp_desc', 'timestamp_asc', 'prob_desc', 'prob_asc', 'amount_desc', 'amount_asc'
    """
    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = max(1, min(100, int(request.args.get('per_page', 20))))
    except (ValueError, TypeError):
        page = 1
        per_page = 20

    filter_type = request.args.get('filter', 'all').lower()
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'timestamp_desc').lower()

    query = db.session.query(PredictionLog)

    # Class filter
    if filter_type in ('fraud', '1'):
        query = query.filter(PredictionLog.prediction == 1)
    elif filter_type in ('legitimate', 'legit', '0'):
        query = query.filter(PredictionLog.prediction == 0)

    # Search filter (label, model_used, source)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (PredictionLog.label.ilike(search_pattern)) |
            (PredictionLog.model_used.ilike(search_pattern)) |
            (PredictionLog.source.ilike(search_pattern))
        )

    # Amount filters
    try:
        amt_min = request.args.get('amount_min')
        if amt_min not in (None, ''):
            query = query.filter(PredictionLog.transaction_amount >= float(amt_min))
    except (ValueError, TypeError):
        pass

    try:
        amt_max = request.args.get('amount_max')
        if amt_max not in (None, ''):
            query = query.filter(PredictionLog.transaction_amount <= float(amt_max))
    except (ValueError, TypeError):
        pass

    # Probability minimum filter
    try:
        prob_min = request.args.get('prob_min')
        if prob_min not in (None, ''):
            query = query.filter(PredictionLog.probability_fraud >= float(prob_min))
    except (ValueError, TypeError):
        pass

    # Date range filters
    date_from = request.args.get('date_from')
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.filter(PredictionLog.timestamp >= dt_from)
        except Exception:
            pass

    date_to = request.args.get('date_to')
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.filter(PredictionLog.timestamp <= dt_to)
        except Exception:
            pass

    # Sorting
    if sort_by == 'timestamp_asc':
        query = query.order_by(PredictionLog.timestamp.asc())
    elif sort_by == 'prob_desc':
        query = query.order_by(PredictionLog.probability_fraud.desc())
    elif sort_by == 'prob_asc':
        query = query.order_by(PredictionLog.probability_fraud.asc())
    elif sort_by == 'amount_desc':
        query = query.order_by(PredictionLog.transaction_amount.desc())
    elif sort_by == 'amount_asc':
        query = query.order_by(PredictionLog.transaction_amount.asc())
    else:  # timestamp_desc
        query = query.order_by(PredictionLog.timestamp.desc())

    total = query.count()
    pages = (total + per_page - 1) // per_page if total > 0 else 1

    records = (
        query.offset((page - 1) * per_page)
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
