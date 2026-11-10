# 🛡️ FraudGuard AI — Credit Card Fraud Detection & Analytics System

> A production-inspired, end-to-end fraud detection platform built as a BCA AI & Data Science final-year portfolio project.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey?logo=flask)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.4+-orange?logo=scikit-learn&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-blue?logo=sqlite)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple?logo=bootstrap)
![Chart.js](https://img.shields.io/badge/Chart.js-4.4-pink?logo=chartdotjs)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📌 Project Overview

FraudGuard AI is a full-stack data analytics and machine learning application that:

- **Analyses** 284,807 real European credit card transactions
- **Detects** fraudulent transactions using Random Forest and Logistic Regression
- **Visualises** patterns, distributions, and anomalies through an interactive dashboard
- **Predicts** fraud risk for new transactions via a REST API (single & batch)
- **Logs** every prediction with timestamps for auditability

This is not a Jupyter notebook demo. It is a complete, deployable web application with a Flask REST backend, SQLite persistence, and a dark fintech-style frontend dashboard.

---

## 🎯 Problem Statement

Credit card fraud is a critical problem in the financial industry. The [ULB Credit Card Fraud dataset](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud) contains transactions made by European cardholders in September 2013. With only **492 fraudulent transactions out of 284,807** (0.172%), the dataset is **highly imbalanced**, making standard accuracy a misleading metric.

**Goals:**
- Handle severe class imbalance without data leakage
- Maximise fraud recall (catch as many real frauds as possible)
- Provide interpretable, actionable insights through a dashboard
- Build a deployable prediction API

---

## 🗂️ Dataset

| Property | Value |
|---|---|
| Source | [Kaggle — ULB MLG Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud) |
| Transactions | 284,807 |
| Fraudulent | 492 (0.172%) |
| Legitimate | 284,315 (99.828%) |
| Features | V1–V28 (PCA-anonymised), `Time`, `Amount`, `Class` |
| Format | CSV (~150 MB) |

> The dataset is **not included** in this repository. Download `creditcard.csv` from Kaggle and place it in `data/raw/` or upload it via the dashboard.

---

## 🏗️ System Architecture

```
Browser (HTML + Chart.js)
        │
        ▼
Flask Web Server (app.py)
        │
   ┌────┴────┐
   │         │
Page       REST API Blueprints
Routes     ├── /api/analytics/*   → DataPreprocessor
           ├── /api/ml/*          → ModelTrainer / Predictor
           └── /api/history/*     → SQLite (SQLAlchemy)
                                        │
                                   ┌────┴────────────┐
                                 Models          Prediction Log
                             (Random Forest,   (PredictionLog,
                            Logistic Reg.)     ModelRegistry,
                             .pkl + .json)     DatasetUpload)
```

---

## ⚙️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11, Flask 3.0, Flask-SQLAlchemy, Flask-CORS |
| **ML / Data** | scikit-learn, pandas, NumPy, joblib |
| **Visualisation** | Matplotlib, Seaborn (server-side), Chart.js (client-side) |
| **Database** | SQLite 3 via SQLAlchemy ORM |
| **Frontend** | HTML5, CSS3, Bootstrap 5.3, Chart.js 4.4, Bootstrap Icons |
| **Dev Tools** | python-dotenv, Werkzeug |

---

## 🤖 Machine Learning Pipeline

### 1. Preprocessing
- Validate required columns (`V1`–`V28`, `Time`, `Amount`, `Class`)
- Drop exact duplicate rows
- Scale `Time` and `Amount` using `StandardScaler` **fitted only on training data** (no leakage)
- PCA features V1–V28 are already scaled at source

### 2. Class Imbalance Strategy
- Use `class_weight='balanced'` in both classifiers (no SMOTE to avoid leakage risk)
- Stratified train-test split (80/20) preserves fraud ratio in both sets

### 3. Models Trained
| Model | Purpose |
|---|---|
| **Logistic Regression** | Baseline — fast, interpretable linear classifier |
| **Random Forest** | Primary — ensemble, handles non-linearity, provides feature importance |

### 4. Evaluation Metrics
Because accuracy is misleading on imbalanced data, evaluation focuses on:

- **Precision** — Of flagged frauds, how many are real?
- **Recall** — Of real frauds, how many did we catch?
- **F1-Score** — Harmonic mean of Precision and Recall
- **ROC-AUC** — Area under the Receiver Operating Characteristic curve
- **PR-AUC** — Area under the Precision-Recall curve (most informative for imbalanced data)
- **Confusion Matrix** — TP / FP / FN / TN counts

### 5. No Data Leakage
- Scaler is fitted **only on X_train**, then applied to X_test
- No preprocessing steps cross the train/test boundary

---

## 📊 Dashboard Pages

| Page | Description |
|---|---|
| **Dashboard** | KPI cards, class distribution doughnut, 48-hour time series, amount range bar chart, stats table |
| **Transaction Analytics** | Amount distribution, hourly frequency, correlation heatmap, class imbalance visualisation |
| **Fraud Detection** | Single transaction scorer (28 PCA features + Amount + Time) and batch CSV uploader |
| **Model Performance** | LR vs RF comparison table, ROC curve, PR curve, confusion matrix, feature importance |
| **Prediction History** | Paginated audit log with filters, CSV export, history purge |
| **About** | Architecture, ML methodology, dataset details, limitations, roadmap |

---

## 📁 Project Structure

```
credit-card-fraud-detection/
│
├── app.py                    # Flask application factory + page routes
├── config.py                 # Configuration classes (dev/prod)
├── extensions.py             # Shared SQLAlchemy instance
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
├── api/
│   ├── analytics.py          # Analytics REST endpoints
│   ├── ml.py                 # Train, status, predict, batch endpoints
│   └── history.py            # Prediction history CRUD endpoints
│
├── src/
│   ├── preprocessing.py      # DataPreprocessor — validation, cleaning, analytics
│   ├── train.py              # ModelTrainer — async background training
│   ├── evaluation.py         # Metric computation (ROC, PR, confusion matrix)
│   └── predict.py            # Single & batch inference
│
├── database/
│   └── models.py             # SQLAlchemy ORM models
│
├── data/
│   ├── raw/                  # Place creditcard.csv here
│   └── processed/            # Cleaned data artifacts
│
├── models/                   # Saved .pkl model files + metrics.json
│
├── templates/                # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html            # Dashboard Overview
│   ├── analytics.html        # Transaction Analytics
│   ├── detection.html        # Fraud Detection
│   ├── performance.html      # Model Performance
│   ├── history.html          # Prediction History
│   └── about.html
│
├── static/
│   ├── css/
│   │   ├── main.css          # Design system (CSS variables, typography)
│   │   ├── dashboard.css     # KPI cards, charts, upload zone
│   │   └── components.css    # Sidebar, navbar, tables, forms
│   └── js/
│       ├── app.js            # Core API wrapper, formatters, toast, Chart.js factory
│       ├── dashboard.js      # Dashboard controller
│       ├── analytics.js      # Analytics charts controller
│       ├── detection.js      # Prediction form controller
│       ├── performance.js    # Model training + evaluation controller
│       └── history.js        # Audit log controller
│
└── screenshots/
```

---

## 🚀 Installation & Running Locally

### Prerequisites
- Python 3.10+
- Git

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/credit-card-fraud-detection.git
cd credit-card-fraud-detection

# 2. Create and activate a virtual environment (recommended)
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (optional — SQLite works with defaults)
cp .env.example .env
# Edit .env if needed

# 5. Run the application
python app.py
```

Open your browser at **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

### Loading the Dataset

1. Download `creditcard.csv` from [Kaggle](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud)
2. Either:
   - Drag and drop it onto the Dashboard upload zone, **or**
   - Place it at `data/raw/creditcard.csv`
3. The app auto-detects the file on the next page load

### Training the Models

1. Navigate to **Model Performance** page
2. Click **"Start Training"**
3. Watch the live progress bar — training takes ~2–5 minutes on a standard laptop
4. Metrics appear immediately after training completes

---

## 🔐 Environment Variables

```env
FLASK_ENV=development
SECRET_KEY=change-this-to-a-random-secret-key
DATABASE_URL=sqlite:///fraudguard.db
```

See [`.env.example`](.env.example) for all available variables. No real credentials are required for the default SQLite setup.

---

## ⚠️ Limitations

- **Dataset is anonymised** — V1–V28 are PCA components; original feature names are unavailable for business interpretation
- **No real-time streaming** — predictions are on-demand, not live transaction monitoring
- **Single-user, no auth** — authentication was intentionally skipped for portfolio simplicity
- **Model drift** — the trained model reflects 2013 European transaction patterns; it should be retrained on current data for real use

---

## 🗺️ Future Improvements

- [ ] Add SMOTE oversampling within training folds using `imbalanced-learn`
- [ ] Add XGBoost / LightGBM models for comparison
- [ ] Real-time prediction WebSocket feed
- [ ] User authentication and role-based access
- [ ] Containerise with Docker
- [ ] Deploy to Railway / Render / AWS

---

## 👤 Author

**Mayank Karki**  
BCA — AI & Data Science  
📧 mayankkarki1818@gmail.com

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

> **Disclaimer:** This system is built for educational and portfolio purposes. Predictions are model-based risk assessments, not guaranteed fraud confirmations. Do not use this system to make real financial or legal decisions.
