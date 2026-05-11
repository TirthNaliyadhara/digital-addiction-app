import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (confusion_matrix, accuracy_score, classification_report,
                             mean_absolute_error, mean_squared_error)
import warnings
warnings.filterwarnings('ignore')


# ── TAB 1: Addiction Risk Classification ───────────────────────────────────

def train_addiction_risk_model(df):
    features = ['total_screen_time', 'nighttime_usage', 'notifications_per_day',
                 'binge_sessions_per_week', 'fomo_score', 'anxiety_score',
                 'phone_pickups_per_hour', 'sleep_disruption_score']
    target = 'addiction_label'

    data = df[features + [target]].dropna()
    X = data[features]
    y = data[target].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(X_train_s, y_train)

    y_pred = model.predict(X_test_s)
    y_prob = model.predict_proba(X_test_s)[:, 1]

    results = {
        'model': model,
        'scaler': scaler,
        'features': features,
        'accuracy': round(accuracy_score(y_test, y_pred) * 100, 2),
        'confusion_matrix': confusion_matrix(y_test, y_pred),
        'classification_report': classification_report(y_test, y_pred, output_dict=True),
        'feature_importance': dict(zip(features, np.abs(model.coef_[0]))),
        'X_test': X_test,
        'y_test': y_test,
        'y_pred': y_pred,
        'y_prob': y_prob,
    }
    return results


def predict_addiction_risk(model_results, input_data: dict):
    model = model_results['model']
    scaler = model_results['scaler']
    features = model_results['features']
    X = np.array([[input_data.get(f, 0) for f in features]])
    X_s = scaler.transform(X)
    pred = model.predict(X_s)[0]
    prob = model.predict_proba(X_s)[0]
    label_map = {0: 'Low Risk', 1: 'High Risk'}
    return label_map[pred], prob


# ── TAB 2: Screen Time Prediction ──────────────────────────────────────────

def train_screen_time_models(df):
    features_lr = ['notifications_per_day']
    features_mlr = ['notifications_per_day', 'nighttime_usage', 'binge_sessions_per_week',
                     'fomo_score', 'phone_pickups_per_hour', 'daily_app_opens']
    target = 'total_screen_time'

    data = df[list(set(features_mlr + [target]))].dropna()
    X_mlr = data[features_mlr]
    X_lr = data[features_lr]
    y = data[target]

    X_train, X_test, y_train, y_test = train_test_split(X_mlr, y, test_size=0.2, random_state=42)

    # Simple LR
    lr = LinearRegression()
    lr.fit(X_train[features_lr], y_train)
    y_pred_lr = lr.predict(X_test[features_lr])

    # MLR
    mlr = LinearRegression()
    mlr.fit(X_train, y_train)
    y_pred_mlr = mlr.predict(X_test)

    return {
        'lr_model': lr,
        'mlr_model': mlr,
        'features_lr': features_lr,
        'features_mlr': features_mlr,
        'X_test': X_test,
        'y_test': y_test,
        'y_pred_lr': y_pred_lr,
        'y_pred_mlr': y_pred_mlr,
        'lr_mae': round(mean_absolute_error(y_test, y_pred_lr), 3),
        'lr_rmse': round(np.sqrt(mean_squared_error(y_test, y_pred_lr)), 3),
        'mlr_mae': round(mean_absolute_error(y_test, y_pred_mlr), 3),
        'mlr_rmse': round(np.sqrt(mean_squared_error(y_test, y_pred_mlr)), 3),
    }


# ── TAB 3: Behavior Pattern Prediction ─────────────────────────────────────

def train_behavior_pattern_model(df):
    features = ['total_screen_time', 'nighttime_usage', 'notifications_per_day',
                 'binge_sessions_per_week', 'fomo_score', 'anxiety_score',
                 'productivity_score', 'sleep_hours', 'physical_activity',
                 'phone_pickups_per_hour', 'daily_app_opens']

    def label_behavior(row):
        if row['productivity_score'] >= 7 and row['total_screen_time'] < 6:
            return 'Productive'
        elif row['addiction_risk_score'] >= 60 or row['total_screen_time'] > 12:
            return 'Addictive'
        else:
            return 'Neutral'

    df = df.copy()
    df['behavior_label'] = df.apply(label_behavior, axis=1)
    data = df[features + ['behavior_label']].dropna()

    le = LabelEncoder()
    y = le.fit_transform(data['behavior_label'])
    X = data[features]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    y_pred = rf.predict(X_test)
    y_prob = rf.predict_proba(X_test)

    return {
        'model': rf,
        'label_encoder': le,
        'features': features,
        'accuracy': round(accuracy_score(y_test, y_pred) * 100, 2),
        'confusion_matrix': confusion_matrix(y_test, y_pred),
        'feature_importance': dict(zip(features, rf.feature_importances_)),
        'X_test': X_test,
        'y_test': y_test,
        'y_pred': y_pred,
        'y_prob': y_prob,
        'classes': le.classes_,
    }


# ── Risk Scoring Engine ─────────────────────────────────────────────────────

def compute_risk_score(row: dict) -> float:
    """
    Compute addiction risk score (0–100).

    If `build_risk_profile_from_real` already embedded a sigmoid-normalized
    precomputed score (key: '_precomputed_risk_score'), we use it directly —
    it was calculated with exponential recency weighting on 7-day data and is
    more accurate than the simple additive formula below.

    For dataset/manual rows (no precomputed score), we use a log-normalized
    composite formula:
        score = Σ w_i * log1p(x_i / ref_i) / log1p(1)
    clamped to [0, 100].
    """
    # ── Use precomputed score from 7-day real-data pipeline if available ──────
    if '_precomputed_risk_score' in row:
        return float(row['_precomputed_risk_score'])

    # ── Fallback: improved formula for dataset / manual input rows ───────────
    def log_norm(val, ref):
        """Log-normalised value in [0, 1]."""
        return min(1.0, np.log1p(max(0.0, float(val))) / np.log1p(float(ref) + 1e-9))

    screen       = log_norm(row.get('total_screen_time',       0),  16) * 40
    night        = log_norm(row.get('nighttime_usage',         0),   5) * 15
    notif        = log_norm(row.get('notifications_per_day',   0), 300) * 15
    binge        = log_norm(row.get('binge_sessions_per_week', 0),  14) * 15
    fomo_contrib = log_norm(row.get('fomo_score',              0),  10) *  8
    sleep_dis    = log_norm(row.get('sleep_disruption_score',  0),  10) *  7

    raw   = screen + night + notif + binge + fomo_contrib + sleep_dis
    # Sigmoid normalisation
    score = 100.0 / (1.0 + np.exp(-0.06 * (raw - 50.0)))
    return round(min(100.0, max(0.0, score)), 1)

def classify_risk(score):
    if score <= 30:
        return 'Low', '🟢'
    elif score <= 70:
        return 'Medium', '🟡'
    else:
        return 'High', '🔴'
