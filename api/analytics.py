import os
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import pandas as pd

from extensions import db
from database.models import DatasetUpload
from src.preprocessing import DataPreprocessor

analytics_bp = Blueprint('analytics', __name__)

# Module-level in-memory cache
_analytics_cache = {}
_dataset_df = None


def invalidate_analytics_cache():
    """Clear analytics cache and cached DataFrame."""
    global _analytics_cache, _dataset_df
    _analytics_cache.clear()
    _dataset_df = None


def get_dataset():
    """
    Return cached DataFrame or attempt to load from raw data folder.
    Returns None if no dataset file exists.
    """
    global _dataset_df

    if _dataset_df is not None:
        return _dataset_df

    upload_folder = current_app.config.get(
        'UPLOAD_FOLDER',
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw')
    )

    # Check for default or uploaded files
    candidate_files = ['creditcard.csv']
    if os.path.exists(upload_folder):
        all_csvs = [f for f in os.listdir(upload_folder) if f.lower().endswith('.csv')]
        candidate_files.extend(all_csvs)

    for fname in candidate_files:
        fpath = os.path.join(upload_folder, fname)
        if os.path.exists(fpath) and os.path.getsize(fpath) > 0:
            try:
                preprocessor = DataPreprocessor()
                df, _ = preprocessor.load_and_validate(fpath)
                _dataset_df = preprocessor.clean_data(df)
                return _dataset_df
            except Exception as e:
                print(f"[analytics] Error loading dataset from {fpath}: {e}")

    return None


def _load_analytics():
    """Compute and cache analytics data dictionary."""
    global _analytics_cache

    if _analytics_cache:
        return _analytics_cache

    df = get_dataset()
    if df is None:
        return None

    try:
        preprocessor = DataPreprocessor()
        data = preprocessor.get_analytics_data(df)
        _analytics_cache.clear()
        _analytics_cache.update(data)
        return _analytics_cache
    except Exception as e:
        print(f"[analytics] Error generating analytics: {e}")
        return None


@analytics_bp.route('/api/analytics/overview', methods=['GET'])
@analytics_bp.route('/analytics/overview', methods=['GET'])
def get_overview():
    """Return overview KPI metrics."""
    analytics = _load_analytics()
    if analytics is None:
        return jsonify({'dataset_loaded': False, 'message': 'No dataset loaded. Please upload a dataset first.'}), 200

    resp = {'dataset_loaded': True}
    resp.update(analytics.get('overview', {}))
    return jsonify(resp), 200


@analytics_bp.route('/api/analytics/distribution', methods=['GET'])
@analytics_bp.route('/analytics/distribution', methods=['GET'])
def get_distribution():
    """Return fraud vs legit distribution metrics."""
    analytics = _load_analytics()
    if analytics is None:
        return jsonify({'dataset_loaded': False, 'message': 'No dataset loaded.'}), 200

    resp = {'dataset_loaded': True}
    resp.update(analytics.get('distribution', {}))
    return jsonify(resp), 200


@analytics_bp.route('/api/analytics/time-series', methods=['GET'])
@analytics_bp.route('/analytics/time-series', methods=['GET'])
def get_time_series():
    """Return time-binned fraud/legit counts (48 hourly bins)."""
    analytics = _load_analytics()
    if analytics is None:
        return jsonify({'dataset_loaded': False, 'message': 'No dataset loaded.'}), 200

    ts = analytics.get('time_series', {})
    resp = {'dataset_loaded': True}
    resp.update(ts)
    # Frontend expects 'bin_labels' (alias for 'bins')
    if 'bins' in ts and 'bin_labels' not in ts:
        resp['bin_labels'] = ts['bins']
    return jsonify(resp), 200


@analytics_bp.route('/api/analytics/amount-ranges', methods=['GET'])
@analytics_bp.route('/analytics/amount-ranges', methods=['GET'])
def get_amount_ranges():
    """Return fraud/legit counts across transaction amount buckets."""
    analytics = _load_analytics()
    if analytics is None:
        return jsonify({'dataset_loaded': False, 'message': 'No dataset loaded.'}), 200

    ar = analytics.get('amount_ranges', {})
    resp = {'dataset_loaded': True}
    resp.update(ar)
    # Frontend expects 'ranges' (alias for 'labels')
    if 'labels' in ar and 'ranges' not in ar:
        resp['ranges'] = ar['labels']
    return jsonify(resp), 200


@analytics_bp.route('/api/analytics/correlation', methods=['GET'])
@analytics_bp.route('/analytics/correlation', methods=['GET'])
def get_correlation():
    """Return correlation matrix for V1-V14 + Amount."""
    analytics = _load_analytics()
    if analytics is None:
        return jsonify({'dataset_loaded': False, 'message': 'No dataset loaded.'}), 200

    resp = {'dataset_loaded': True}
    resp.update(analytics.get('correlation', {}))
    return jsonify(resp), 200


@analytics_bp.route('/api/analytics/stats', methods=['GET'])
@analytics_bp.route('/analytics/stats', methods=['GET'])
def get_stats():
    """Return statistical summary for Amount column by class."""
    analytics = _load_analytics()
    if analytics is None:
        return jsonify({'dataset_loaded': False, 'message': 'No dataset loaded.'}), 200

    stats = analytics.get('stats', {})
    resp = {'dataset_loaded': True}
    resp.update(stats)

    # Frontend expects 'fraud_amount_stats' / 'legit_amount_stats' with
    # keys q25/q50/q75 (backend uses p25/median/p75). Normalize both.
    def _normalize_stats(raw: dict) -> dict:
        if not raw:
            return raw
        normalized = dict(raw)
        if 'p25' in normalized and 'q25' not in normalized:
            normalized['q25'] = normalized['p25']
        if 'median' in normalized and 'q50' not in normalized:
            normalized['q50'] = normalized['median']
        if 'p75' in normalized and 'q75' not in normalized:
            normalized['q75'] = normalized['p75']
        return normalized

    if 'fraud_amount' in stats:
        resp['fraud_amount_stats'] = _normalize_stats(stats['fraud_amount'])
    if 'legit_amount' in stats:
        resp['legit_amount_stats'] = _normalize_stats(stats['legit_amount'])

    return jsonify(resp), 200


@analytics_bp.route('/api/analytics/all', methods=['GET'])
@analytics_bp.route('/analytics/all', methods=['GET'])
def get_all_analytics():
    """Return complete analytics dataset."""
    analytics = _load_analytics()
    if analytics is None:
        return jsonify({'dataset_loaded': False, 'message': 'No dataset loaded.'}), 200

    resp = {'dataset_loaded': True}
    resp.update(analytics)
    return jsonify(resp), 200


@analytics_bp.route('/api/dataset/upload', methods=['POST'])
@analytics_bp.route('/api/analytics/upload', methods=['POST'])
@analytics_bp.route('/dataset/upload', methods=['POST'])
def upload_dataset():
    """Accept multipart file upload of creditcard.csv, validate, and refresh cache."""
    global _dataset_df, _analytics_cache

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part in request'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    if not file.filename.lower().endswith('.csv'):
        return jsonify({'success': False, 'error': 'Invalid file format. Only CSV files are supported.'}), 400

    filename = secure_filename(file.filename)
    upload_folder = current_app.config.get(
        'UPLOAD_FOLDER',
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw')
    )
    os.makedirs(upload_folder, exist_ok=True)
    save_path = os.path.join(upload_folder, filename)

    try:
        file.save(save_path)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to save file: {str(e)}'}), 500

    try:
        preprocessor = DataPreprocessor()
        df, info = preprocessor.load_and_validate(save_path)
        cleaned_df = preprocessor.clean_data(df)

        row_count = int(len(cleaned_df))
        fraud_count = int((cleaned_df['Class'] == 1).sum())
        legit_count = int((cleaned_df['Class'] == 0).sum())
        fraud_rate = float(fraud_count / row_count * 100.0) if row_count > 0 else 0.0
        file_size_mb = float(os.path.getsize(save_path) / (1024 * 1024))

        # Record upload in database
        try:
            upload_entry = DatasetUpload(
                filename=filename,
                uploaded_at=datetime.utcnow(),
                row_count=row_count,
                fraud_count=fraud_count,
                legit_count=legit_count,
                fraud_rate=round(fraud_rate, 4),
                file_size_mb=round(file_size_mb, 2)
            )
            db.session.add(upload_entry)
            db.session.commit()
        except Exception as db_err:
            db.session.rollback()
            print(f"[analytics] Database record error: {db_err}")

        # Update cache
        _dataset_df = cleaned_df
        _analytics_cache.clear()
        _analytics_cache.update(preprocessor.get_analytics_data(cleaned_df))

        return jsonify({
            'success': True,
            'dataset_loaded': True,
            'message': 'Dataset successfully uploaded, validated, and processed.',
            'dataset': {
                'filename': filename,
                'row_count': row_count,
                'fraud_count': fraud_count,
                'legit_count': legit_count,
                'fraud_rate': round(fraud_rate, 4),
                'file_size_mb': round(file_size_mb, 2)
            }
        }), 200

    except Exception as e:
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
            except OSError:
                pass
        return jsonify({'success': False, 'error': f'Validation failed: {str(e)}'}), 400
