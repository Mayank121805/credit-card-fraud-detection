import os
import joblib
import numpy as np
import pandas as pd

FEATURE_COLUMNS = ['Time'] + [f'V{i}' for i in range(1, 29)] + ['Amount']  # 30 features, no Class


def load_model_and_scaler(model_folder: str):
    """Load Random Forest model and scaler. Return (model, scaler) or (None, None)."""
    rf_path = os.path.join(model_folder, 'random_forest.pkl')
    scaler_path = os.path.join(model_folder, 'scaler.pkl')

    if not os.path.exists(rf_path) or not os.path.exists(scaler_path):
        return None, None

    try:
        model = joblib.load(rf_path)
        scaler = joblib.load(scaler_path)
        return model, scaler
    except Exception as e:
        print(f"[predict] Error loading model or scaler: {e}")
        return None, None


def load_lr_model(model_folder: str):
    """Load Logistic Regression model or return None."""
    lr_path = os.path.join(model_folder, 'logistic_regression.pkl')
    if not os.path.exists(lr_path):
        return None
    try:
        return joblib.load(lr_path)
    except Exception as e:
        print(f"[predict] Error loading LR model: {e}")
        return None


def preprocess_input(transaction_dict: dict, scaler) -> np.ndarray:
    """Preprocess a single transaction dict for prediction."""
    row = []
    for col in FEATURE_COLUMNS:
        val = transaction_dict.get(col, 0.0)
        try:
            row.append(float(val))
        except (ValueError, TypeError):
            row.append(0.0)

    arr = np.array(row, dtype=np.float64).reshape(1, -1)
    # Scale Time (index 0) and Amount (index 29)
    if scaler is not None:
        arr[:, [0, 29]] = scaler.transform(arr[:, [0, 29]])

    return arr


def predict_single(transaction_dict: dict, model, scaler, threshold: float = 0.5) -> dict:
    """Predict fraud for a single transaction."""
    X = preprocess_input(transaction_dict, scaler)
    probs = model.predict_proba(X)[0]
    prob_fraud = float(probs[1]) if len(probs) > 1 else float(probs[0])
    prob_legit = 1.0 - prob_fraud

    prediction = 1 if prob_fraud >= threshold else 0
    label = 'Fraudulent' if prediction == 1 else 'Legitimate'

    if prob_fraud >= 0.7:
        risk_level = 'High'
    elif prob_fraud >= 0.3:
        risk_level = 'Medium'
    else:
        risk_level = 'Low'

    model_name = 'RandomForest'
    if hasattr(model, '__class__'):
        cls_name = model.__class__.__name__
        if 'Logistic' in cls_name:
            model_name = 'LogisticRegression'
        elif 'Forest' in cls_name:
            model_name = 'RandomForest'

    return {
        'prediction': int(prediction),
        'probability_fraud': round(float(prob_fraud), 6),
        'probability_legit': round(float(prob_legit), 6),
        'label': label,
        'risk_level': risk_level,
        'model_used': model_name,
        'threshold': float(threshold)
    }


def predict_batch(df: pd.DataFrame, model, scaler, threshold: float = 0.5) -> pd.DataFrame:
    """
    Predict fraud for a batch DataFrame.
    Scales features and appends Predicted_Class, Predicted_Label, Probability_Fraud, Risk_Level.
    """
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Batch dataset missing required feature columns ({len(missing)}): {', '.join(missing[:5])}")

    X = df[FEATURE_COLUMNS].copy().astype(float)
    if scaler is not None:
        X[['Time', 'Amount']] = scaler.transform(X[['Time', 'Amount']])

    X_arr = X.to_numpy(dtype=np.float64)
    probs_all = model.predict_proba(X_arr)
    probs = probs_all[:, 1] if probs_all.shape[1] > 1 else probs_all[:, 0]

    predictions = (probs >= threshold).astype(int)
    labels = ['Fraudulent' if p == 1 else 'Legitimate' for p in predictions]

    risk_levels = []
    for p in probs:
        if p >= 0.7:
            risk_levels.append('High')
        elif p >= 0.3:
            risk_levels.append('Medium')
        else:
            risk_levels.append('Low')

    result_df = df.copy()
    result_df['Predicted_Class'] = predictions
    result_df['Predicted_Label'] = labels
    result_df['Probability_Fraud'] = [round(float(p), 6) for p in probs]
    result_df['Risk_Level'] = risk_levels

    return result_df
