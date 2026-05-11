import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from scipy import stats

def compute_behavioral_metrics(df):
    metrics = {}

    # Focus Score (inverse of switching & notifications)
    notif_norm = (df['notifications_per_day'] - df['notifications_per_day'].min()) / (df['notifications_per_day'].max() - df['notifications_per_day'].min() + 1e-9)
    pickup_norm = (df['phone_pickups_per_hour'] - df['phone_pickups_per_hour'].min()) / (df['phone_pickups_per_hour'].max() - df['phone_pickups_per_hour'].min() + 1e-9)
    metrics['focus_score'] = np.round((1 - (notif_norm * 0.5 + pickup_norm * 0.5)) * 10, 2)

    # Distraction Index
    binge_norm = (df['binge_sessions_per_week'] - df['binge_sessions_per_week'].min()) / (df['binge_sessions_per_week'].max() - df['binge_sessions_per_week'].min() + 1e-9)
    metrics['distraction_index'] = np.round((pickup_norm * 0.4 + binge_norm * 0.3 + notif_norm * 0.3) * 10, 2)

    # Digital Dependency Score
    screen_norm = (df['total_screen_time'] - df['total_screen_time'].min()) / (df['total_screen_time'].max() - df['total_screen_time'].min() + 1e-9)
    anxiety_norm = (df['anxiety_score'] - df['anxiety_score'].min()) / (df['anxiety_score'].max() - df['anxiety_score'].min() + 1e-9)
    metrics['digital_dependency_score'] = np.round((screen_norm * 0.4 + anxiety_norm * 0.3 + binge_norm * 0.3) * 10, 2)

    # Night Risk
    metrics['night_risk'] = np.where(df['nighttime_usage'] > 2, 'High', np.where(df['nighttime_usage'] > 1, 'Medium', 'Low'))

    # Notification dependency
    metrics['notification_dependency'] = np.round(df['notifications_per_day'] / (df['phone_pickups_per_hour'] + 1), 2)

    # Sleep disruption composite
    metrics['sleep_risk'] = np.where(df['sleep_hours'] < 5, 'Critical', np.where(df['sleep_hours'] < 6.5, 'High', 'Normal'))

    return pd.DataFrame(metrics, index=df.index)

def detect_anomalies(df):
    features = ['total_screen_time', 'notifications_per_day', 'nighttime_usage', 'binge_sessions_per_week']
    X = df[features].fillna(0)

    iso = IsolationForest(contamination=0.05, random_state=42)
    preds = iso.fit_predict(X)
    anomaly_scores = iso.decision_function(X)

    z_scores = np.abs(stats.zscore(df['total_screen_time'].fillna(0)))
    z_outliers = z_scores > 3

    return preds == -1, z_outliers, anomaly_scores

def addiction_pattern_analysis(df):
    patterns = {}

    # Continuous heavy usage (>8hrs/day)
    patterns['heavy_users_pct'] = round((df['total_screen_time'] > 8).mean() * 100, 1)

    # Dopamine loop: short sessions + high app opens
    patterns['dopamine_loop_pct'] = round(
        ((df['avg_session_duration'] < 10) & (df['daily_app_opens'] > 100)).mean() * 100, 1
    )

    # App dependency scoring
    patterns['avg_dependency_score'] = round(df['addiction_risk_score'].mean(), 1)

    # Night dominant users
    patterns['night_dominant_pct'] = round((df['nighttime_usage'] > 2).mean() * 100, 1)

    # Context switching (high pickups + high binge)
    patterns['high_switching_pct'] = round(
        ((df['phone_pickups_per_hour'] > 25) & (df['binge_sessions_per_week'] > 7)).mean() * 100, 1
    )

    # FOMO driven
    patterns['fomo_driven_pct'] = round((df['fomo_score'] >= 8).mean() * 100, 1)

    return patterns

def get_behavioral_insights(df):
    insights = []

    avg_screen = df['total_screen_time'].mean()
    if avg_screen > 10:
        insights.append(("🔴 Critical Screen Time", f"Average screen time of {avg_screen:.1f} hrs/day is severely above healthy limits (2-4 hrs recommended)."))
    elif avg_screen > 6:
        insights.append(("🟠 High Screen Time", f"Average screen time of {avg_screen:.1f} hrs/day exceeds recommended usage."))

    night_pct = (df['nighttime_usage'] > 1.5).mean() * 100
    if night_pct > 30:
        insights.append(("🌙 Widespread Night Usage", f"{night_pct:.1f}% of users show significant nighttime phone usage, impacting sleep quality."))

    binge_pct = (df['binge_sessions_per_week'] > 10).mean() * 100
    if binge_pct > 20:
        insights.append(("📱 Binge Session Alert", f"{binge_pct:.1f}% of users exhibit binge-watching behavior (>10 sessions/week)."))

    fomo = df['fomo_score'].mean()
    if fomo > 6:
        insights.append(("😰 High FOMO Culture", f"Mean FOMO score of {fomo:.1f}/10 indicates strong anxiety-driven digital behavior."))

    prod = df['productivity_score'].mean()
    if prod < 5:
        insights.append(("📉 Low Productivity", f"Mean productivity score of {prod:.1f}/10 suggests digital usage is significantly impacting work performance."))

    return insights
