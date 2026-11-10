from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix,
    roc_curve, precision_recall_curve
)


def downsample_list(lst, max_points: int = 200):
    """Evenly downsample a list to max_points while preserving endpoints."""
    if not lst:
        return []
    if len(lst) <= max_points:
        return [round(float(x), 6) for x in lst]
    indices = [int(round(i * (len(lst) - 1) / (max_points - 1))) for i in range(max_points)]
    return [round(float(lst[i]), 6) for i in indices]


def compute_all_metrics(model, X_test, y_test, model_name: str, threshold: float = 0.5) -> dict:
    """Compute complete metrics dict for a trained model."""
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()

    fpr, tpr, _ = roc_curve(y_test, y_prob)
    precision_vals, recall_vals, _ = precision_recall_curve(y_test, y_prob)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_test, y_prob)
    pr_auc = average_precision_score(y_test, y_prob)

    return {
        'model_name': model_name,
        'threshold': float(threshold),
        'accuracy': round(float(acc), 6),
        'precision': round(float(prec), 6),
        'recall': round(float(rec), 6),
        'f1': round(float(f1), 6),
        'roc_auc': round(float(roc_auc), 6),
        'pr_auc': round(float(pr_auc), 6),
        'confusion_matrix': {
            'tn': int(tn),
            'fp': int(fp),
            'fn': int(fn),
            'tp': int(tp)
        },
        'roc_curve': {
            'fpr': downsample_list(fpr.tolist(), 200),
            'tpr': downsample_list(tpr.tolist(), 200)
        },
        'pr_curve': {
            'precision': downsample_list(precision_vals.tolist(), 200),
            'recall': downsample_list(recall_vals.tolist(), 200)
        }
    }


def get_feature_importance(rf_model, feature_names: list) -> dict:
    """Extract top-20 feature importances from Random Forest."""
    if not hasattr(rf_model, 'feature_importances_'):
        return {'features': [], 'importances': []}

    importances = rf_model.feature_importances_
    paired = sorted(zip(feature_names, importances.tolist()), key=lambda x: x[1], reverse=True)[:20]
    return {
        'features': [p[0] for p in paired],
        'importances': [round(float(p[1]), 6) for p in paired]
    }
