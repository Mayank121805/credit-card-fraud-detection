import os
from flask import Flask, render_template, jsonify
from flask_cors import CORS
from extensions import db
from config import config


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    CORS(app)
    db.init_app(app)

    # Create directories
    for folder in [app.config['UPLOAD_FOLDER'], app.config['PROCESSED_FOLDER'], app.config['MODEL_FOLDER']]:
        os.makedirs(folder, exist_ok=True)

    # Register blueprints
    from api.analytics import analytics_bp
    from api.ml import ml_bp
    from api.history import history_bp
    app.register_blueprint(analytics_bp)
    app.register_blueprint(ml_bp)
    app.register_blueprint(history_bp)

    # Create DB tables
    with app.app_context():
        db.create_all()

    # Page routes
    @app.route('/')
    def index():
        try:
            return render_template('index.html', active_page='dashboard')
        except Exception:
            return jsonify({
                'system': 'Credit Card Fraud Detection & Analytics System',
                'status': 'online',
                'active_page': 'dashboard',
                'endpoints': {
                    'analytics_overview': '/api/analytics/overview',
                    'analytics_distribution': '/api/analytics/distribution',
                    'analytics_timeseries': '/api/analytics/time-series',
                    'analytics_correlation': '/api/analytics/correlation',
                    'dataset_upload': '/api/dataset/upload',
                    'ml_train': '/api/ml/train',
                    'ml_train_status': '/api/ml/train/status',
                    'ml_metrics': '/api/ml/metrics',
                    'ml_predict': '/api/ml/predict',
                    'ml_predict_batch': '/api/ml/predict/batch',
                    'history': '/api/history',
                    'history_stats': '/api/history/stats',
                    'history_export': '/api/history/export'
                }
            }), 200

    @app.route('/analytics')
    def analytics():
        try:
            return render_template('analytics.html', active_page='analytics')
        except Exception:
            return jsonify({'system': 'Credit Card Fraud Detection API', 'status': 'online', 'active_page': 'analytics'}), 200

    @app.route('/detection')
    def detection():
        try:
            return render_template('detection.html', active_page='detection')
        except Exception:
            return jsonify({'system': 'Credit Card Fraud Detection API', 'status': 'online', 'active_page': 'detection'}), 200

    @app.route('/performance')
    def performance():
        try:
            return render_template('performance.html', active_page='performance')
        except Exception:
            return jsonify({'system': 'Credit Card Fraud Detection API', 'status': 'online', 'active_page': 'performance'}), 200

    @app.route('/history')
    def history():
        try:
            return render_template('history.html', active_page='history')
        except Exception:
            return jsonify({'system': 'Credit Card Fraud Detection API', 'status': 'online', 'active_page': 'history'}), 200

    @app.route('/about')
    def about():
        try:
            return render_template('about.html', active_page='about')
        except Exception:
            return jsonify({'system': 'Credit Card Fraud Detection API', 'status': 'online', 'active_page': 'about'}), 200

    # Error handlers
    @app.errorhandler(400)
    def bad_request(e):
        return {'error': 'Bad request', 'message': str(e)}, 400

    @app.errorhandler(404)
    def not_found(e):
        return {'error': 'Not found'}, 404

    @app.errorhandler(500)
    def server_error(e):
        return {'error': 'Internal server error', 'message': str(e)}, 500

    return app


if __name__ == '__main__':
    app = create_app('development')
    app.run(debug=True, host='0.0.0.0', port=5000)
