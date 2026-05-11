"""
Adaptive Intelligence System for Digital Addiction Detection and Behavioral Management
Enterprise-Level Streamlit Application
"""

import os
import sys
import warnings
warnings.filterwarnings('ignore')

# Ensure local modules are importable
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import numpy as np

# --- AUTO-INSTALL MISSING DEPS ---
try:
    import pytesseract
except ImportError:
    import subprocess
    import sys
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pytesseract", "Pillow"])
        import pytesseract
    except:
        pytesseract = None
# --------------------------------
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PIL import Image
import sys

from auth.auth import init_db, login_user, signup_user, logout, get_all_users
from utils.data_loader import load_data, get_summary_stats
from behavior_analysis.analyzer import (
    compute_behavioral_metrics, detect_anomalies,
    addiction_pattern_analysis, get_behavioral_insights
)
from ml_models.models import (
    train_addiction_risk_model, predict_addiction_risk,
    train_screen_time_models, train_behavior_pattern_model,
    compute_risk_score, classify_risk
)
from utils.recommendations import get_recommendations
from integrations.adb_integration import (
    check_adb_connected, generate_simulated_mobile_data,
    get_real_mobile_data, process_usage_stats, simulate_app_usage_data,
    get_mobile_usage_summary, analyze_mobile_patterns
)
from utils.ocr_utils import extract_data_from_image, build_profile_from_ocr



# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AdaptiveAI — Digital Addiction System",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── DB Init ───────────────────────────────────────────────────────────────────
init_db()


# ══════════════════════════════════════════════════════════════════════════════
# AUTH PAGES
# ══════════════════════════════════════════════════════════════════════════════

def show_login_page():
    st.markdown("## 🧠 AdaptiveAI — Digital Addiction Intelligence System")
    st.markdown("---")
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])

    with tab1:
        st.subheader("Login to Your Account")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", width="stretch", type="primary"):
            if username and password:
                ok, user_info = login_user(username, password)
                if ok:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = user_info
                    st.success(f"Welcome back, {user_info['full_name'] or username}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")
            else:
                st.warning("Please enter username and password.")
     

    with tab2:
        st.subheader("Create New Account")
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("Full Name")
            new_user = st.text_input("Username")
            new_role = st.selectbox("Account Type", ["User", "Parent"])
        with c2:
            new_email = st.text_input("Email")
            new_pass = st.text_input("Password", type="password")
            new_pass2 = st.text_input("Confirm Password", type="password")
        if st.button("Create Account", width="stretch", type="primary"):
            if new_pass != new_pass2:
                st.error("Passwords do not match.")
            elif len(new_pass) < 6:
                st.error("Password must be at least 6 characters.")
            elif not new_user:
                st.error("Username required.")
            else:
                ok, msg = signup_user(new_user, new_pass, new_role, new_email, new_name)
                if ok:
                    st.success(msg + " Please login.")
                else:
                    st.error(msg)


# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING (cached)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def get_data(uploaded_file=None):
    return load_data(uploaded_file)

@st.cache_data(show_spinner=False)
def get_ml_results(data_hash):
    df = st.session_state.get('df')
    if df is None:
        return None, None, None
    r1 = train_addiction_risk_model(df)
    r2 = train_screen_time_models(df)
    r3 = train_behavior_pattern_model(df)
    return r1, r2, r3


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

def show_sidebar(user_info):
    with st.sidebar:
        st.markdown(f"### 👤 {user_info.get('full_name') or user_info['username']}")
        st.markdown(f"**Role:** `{user_info['role']}`")
        st.markdown("---")

        pages = ["Overview", "Advanced Dashboard", "Behavior Intelligence",
                 "ML Predictions", "Risk Scoring Engine", "Recommendation Engine",
                 "Samsung Support", "Settings / Profile", "AI Chatbot", "About"]
        icons = ["bar-chart-line", "graph-up", "activity", "robot", "lightning", "lightbulb", "plus-circle", "gear", "chat-dots", "info-circle"]

        if user_info['role'] == 'Admin':
            pages.append("Admin Panel")
            icons.append("tools")

        page = option_menu(
            menu_title="Navigation",
            options=pages,
            icons=icons,
            menu_icon="cast",
            default_index=0,
        )
        st.markdown("---")

        st.markdown("**Data Source**")
        data_mode = option_menu(
            menu_title=None,
            options=["Dataset", "Simulated Mobile", "Upload CSV"],
            icons=["folder", "phone", "cloud-upload"],
            default_index=0,
        )
        st.markdown("---")
        
        # Ensure ghost data doesn't leak into Dataset mode
        if data_mode not in ["Simulated Mobile", "Connect Phone"]:
            for key in ['phone_profile', 'phone_df', 'phone_meta']:
                if key in st.session_state:
                    del st.session_state[key]

        if st.button("🚪 Logout", width="stretch"):
            logout()
            st.rerun()

    return page, data_mode


# ══════════════════════════════════════════════════════════════════════════════
# MODULE: OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════

def page_overview(df):
    st.title("📊 Overview Dashboard")
    stats = get_summary_stats(df)

    # KPI Row
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total Records", f"{stats['total_records']:,}")
    k2.metric("Avg Screen Time", f"{stats['avg_screen_time']} hrs")
    k3.metric("Avg Risk Score", f"{stats['avg_risk_score']}")
    k4.metric("High Risk %", f"{stats['high_risk_pct']}%")
    k5.metric("Avg Sleep", f"{stats['avg_sleep']} hrs")
    k6.metric("Avg Notifications", f"{stats['avg_notifications']}")

    st.markdown("---")
    c1, c2 = st.columns(2)

    with c1:
        # Risk Category Pie
        risk_counts = df['risk_category'].value_counts().reset_index()
        risk_counts.columns = ['Risk Category', 'Count']
        fig = px.pie(risk_counts, values='Count', names='Risk Category',
                     title='Risk Category Distribution',
                     hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(height=380)
        st.plotly_chart(fig, width="stretch")

    with c2:
        # Platform usage bar
        platform_counts = df['most_used_platform'].value_counts().head(10).reset_index()
        platform_counts.columns = ['Platform', 'Count']
        fig2 = px.bar(platform_counts, x='Count', y='Platform', orientation='h',
                      title='Top 10 Most Used Platforms',
                      color='Count', color_continuous_scale='Blues')
        fig2.update_layout(height=380, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig2, width="stretch")

    c3, c4 = st.columns(2)

    with c3:
        # Screen time distribution
        fig3 = px.histogram(df, x='total_screen_time', nbins=40,
                            title='Screen Time Distribution (hrs/day)',
                            color_discrete_sequence=['#636EFA'])
        fig3.update_layout(height=340)
        st.plotly_chart(fig3, width="stretch")

    with c4:
        # Addiction label bar
        label_counts = df['addiction_label'].map({0: 'Not Addicted', 1: 'Addicted'}).value_counts().reset_index()
        label_counts.columns = ['Label', 'Count']
        fig4 = px.bar(label_counts, x='Label', y='Count',
                      title='Addiction Label Distribution',
                      color='Label', color_discrete_sequence=['#00CC96', '#EF553B'])
        fig4.update_layout(height=340)
        st.plotly_chart(fig4, width="stretch")

    # Notification density
    st.subheader("📬 Notification Density & Session Burst Analysis")
    c5, c6 = st.columns(2)
    with c5:
        # Support both normalized and raw uploaded header names
        risk_col = 'risk_category' if 'risk_category' in df.columns else 'Risk Category'
        notif_col = 'notifications_per_day' if 'notifications_per_day' in df.columns else 'Notifications per Day'

        if risk_col in df.columns and notif_col in df.columns:
            notif_df = df[[risk_col, notif_col]].dropna().copy()
            fig5 = px.histogram(
                notif_df,
                x=notif_col,
                color=risk_col,
                nbins=35,
                histnorm='probability density',
                barmode='overlay',
                opacity=0.65,
                title='Notification Density by Risk Category'
            )
            fig5.update_layout(
                height=340,
                xaxis_title='Notifications per Day',
                yaxis_title='Density',
                legend_title_text='Risk Category'
            )
            st.plotly_chart(fig5, width="stretch")
        else:
            st.info("Required columns for the notification density chart are missing in the uploaded dataset.")
    with c6:
        fig6 = px.scatter(df.sample(min(2000, len(df))), x='total_screen_time',
                          y='binge_sessions_per_week',
                          color='risk_category', size='notifications_per_day',
                          title='Session Bursts vs Screen Time', opacity=0.6)
        fig6.update_layout(height=340)
        st.plotly_chart(fig6, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# MODULE: ADVANCED DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

def page_advanced_dashboard(df):
    st.title("📈 Advanced Dashboard")

    # Filters
    with st.expander("🔧 Filters", expanded=True):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            risk_filter = st.multiselect("Risk Category", df['risk_category'].unique().tolist(),
                                          default=df['risk_category'].unique().tolist())
        with fc2:
            occ_filter = st.multiselect("Occupation", df['occupation'].dropna().unique().tolist(),
                                         default=df['occupation'].dropna().unique().tolist()[:5])
        with fc3:
            gender_filter = st.multiselect("Gender", df['gender'].dropna().unique().tolist(),
                                            default=df['gender'].dropna().unique().tolist())

    dff = df[
        df['risk_category'].isin(risk_filter) &
        df['occupation'].isin(occ_filter) &
        df['gender'].isin(gender_filter)
    ]
    st.caption(f"Showing **{len(dff):,}** records after filters")
    st.markdown("---")

    # Screen time trend by month
    if 'month' in dff.columns:
        monthly = dff.groupby('month')['total_screen_time'].mean().reset_index()
        monthly.columns = ['Month', 'Avg Screen Time (hrs)']
        fig = px.line(monthly, x='Month', y='Avg Screen Time (hrs)',
                      title='Monthly Average Screen Time Trend', markers=True)
        fig.update_layout(height=320)
        st.plotly_chart(fig, width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        # Day vs Night usage
        day_night = dff[['total_screen_time', 'nighttime_usage']].mean()
        fig2 = go.Figure(go.Bar(
            x=['Day Usage (Total)', 'Night Usage'],
            y=[day_night['total_screen_time'], day_night['nighttime_usage']],
            marker_color=['#636EFA', '#EF553B']
        ))
        fig2.update_layout(title='Day vs Night Usage Comparison', height=340)
        st.plotly_chart(fig2, width="stretch")

    with c2:
        # App category distribution (using platform)
        platform_risk = dff.groupby(['most_used_platform', 'risk_category']).size().reset_index(name='count')
        fig3 = px.bar(platform_risk, x='most_used_platform', y='count',
                      color='risk_category', title='Platform Usage by Risk Category',
                      barmode='stack')
        fig3.update_layout(height=340, xaxis_tickangle=-45)
        st.plotly_chart(fig3, width="stretch")

    # Notification Heatmap
    st.subheader("🔥 Notification Spikes Heatmap")
    if 'day_of_week' in dff.columns:
        dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        heat_data = dff.groupby(['day_of_week', 'risk_category'])['notifications_per_day'].mean().reset_index()
        heat_pivot = heat_data.pivot(index='risk_category', columns='day_of_week', values='notifications_per_day')
        # Reorder columns
        cols_present = [c for c in dow_order if c in heat_pivot.columns]
        heat_pivot = heat_pivot[cols_present]
        fig4 = px.imshow(heat_pivot, text_auto='.0f', aspect='auto',
                         title='Avg Notifications: Risk Category × Day of Week',
                         color_continuous_scale='Reds')
        fig4.update_layout(height=300)
        st.plotly_chart(fig4, width="stretch")

    # Occupation breakdown
    c3, c4 = st.columns(2)
    with c3:
        occ_screen = dff.groupby('occupation')['total_screen_time'].mean().reset_index()
        fig5 = px.bar(occ_screen, x='occupation', y='total_screen_time',
                      title='Avg Screen Time by Occupation', color='total_screen_time',
                      color_continuous_scale='Viridis')
        fig5.update_layout(height=340, xaxis_tickangle=-30)
        st.plotly_chart(fig5, width="stretch")

    with c4:
        fig6 = px.scatter(dff.sample(min(1500, len(dff))), x='sleep_hours', y='productivity_score',
                          color='risk_category', title='Sleep Hours vs Productivity Score',
                          opacity=0.5)
        fig6.update_layout(height=340)
        st.plotly_chart(fig6, width="stretch")

    # Correlation Heatmap
    st.subheader("📊 Feature Correlation Matrix")
    corr_cols = ['total_screen_time', 'nighttime_usage', 'notifications_per_day',
                  'binge_sessions_per_week', 'sleep_hours', 'productivity_score',
                  'addiction_risk_score', 'fomo_score', 'anxiety_score', 'physical_activity']
    corr = dff[corr_cols].corr().round(2)
    fig7 = px.imshow(corr, text_auto=True, aspect='auto',
                     title='Feature Correlation Heatmap', color_continuous_scale='RdBu_r')
    fig7.update_layout(height=500)
    st.plotly_chart(fig7, width="stretch")

    # Sunburst chart (last section)
    st.subheader("🌞 Risk Hierarchy Sunburst")
    sunburst_cols = ['risk_category', 'occupation', 'most_used_platform']
    if all(col in dff.columns for col in sunburst_cols):
        sunburst_data = dff[sunburst_cols].dropna().copy()
        if not sunburst_data.empty:
            sunburst_data['records'] = 1
            fig8 = px.sunburst(
                sunburst_data,
                path=['risk_category', 'occupation', 'most_used_platform'],
                values='records',
                color='risk_category',
                title='Risk Category → Occupation → Most Used Platform'
            )
            fig8.update_layout(height=560)
            st.plotly_chart(fig8, width="stretch")
        else:
            st.info("Sunburst chart unavailable: filtered records are empty after removing missing values.")
    else:
        st.info("Sunburst chart unavailable: required columns are missing in the filtered dataset.")


# ══════════════════════════════════════════════════════════════════════════════
# MODULE: BEHAVIOR INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════

def page_behavior_intelligence(df):
    st.title("🧠 Behavior Intelligence Module")

    with st.spinner("Computing behavioral metrics..."):
        bm = compute_behavioral_metrics(df)
        iso_anomalies, z_anomalies, iso_scores = detect_anomalies(df)
        patterns = addiction_pattern_analysis(df)
        insights = get_behavioral_insights(df)

    # Metrics
    st.subheader("📐 Computed Behavioral Metrics")
    m1, m2, m3 = st.columns(3)
    m1.metric("Avg Focus Score", f"{bm['focus_score'].mean():.2f} / 10")
    m2.metric("Avg Distraction Index", f"{bm['distraction_index'].mean():.2f} / 10")
    m3.metric("Avg Digital Dependency", f"{bm['digital_dependency_score'].mean():.2f} / 10")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        fig = px.histogram(bm['focus_score'], nbins=30, title='Focus Score Distribution',
                           color_discrete_sequence=['#00CC96'])
        st.plotly_chart(fig, width="stretch")
    with c2:
        fig2 = px.histogram(bm['digital_dependency_score'], nbins=30,
                            title='Digital Dependency Score Distribution',
                            color_discrete_sequence=['#EF553B'])
        st.plotly_chart(fig2, width="stretch")

    # Pattern Analysis
    st.subheader("🔍 Addiction Pattern Analysis")
    p1, p2, p3, p4, p5, p6 = st.columns(6)
    p1.metric("Heavy Users", f"{patterns['heavy_users_pct']}%")
    p2.metric("Dopamine Loop", f"{patterns['dopamine_loop_pct']}%")
    p3.metric("Night Dominant", f"{patterns['night_dominant_pct']}%")
    p4.metric("High Switching", f"{patterns['high_switching_pct']}%")
    p5.metric("FOMO Driven", f"{patterns['fomo_driven_pct']}%")
    p6.metric("Avg Dep Score", f"{patterns['avg_dependency_score']}")

    # Anomaly Detection
    st.subheader("⚠️ Anomaly Detection")
    df_plot = df.copy()
    df_plot['iso_anomaly'] = iso_anomalies
    df_plot['z_anomaly'] = z_anomalies
    df_plot['anomaly_score'] = iso_scores

    c3, c4 = st.columns(2)
    with c3:
        anomaly_count = iso_anomalies.sum()
        st.info(f"**Isolation Forest** detected **{anomaly_count}** anomalous records ({anomaly_count/len(df)*100:.1f}%)")
        fig3 = px.scatter(df_plot.sample(min(2000, len(df_plot))),
                          x='total_screen_time', y='notifications_per_day',
                          color='iso_anomaly', title='Anomaly Detection (Isolation Forest)',
                          color_discrete_map={True: 'red', False: 'steelblue'})
        st.plotly_chart(fig3, width="stretch")

    with c4:
        z_count = z_anomalies.sum()
        st.info(f"**Z-Score method** detected **{z_count}** outliers in screen time (z > 3)")
        fig4 = px.histogram(iso_scores, nbins=40, title='Isolation Forest Anomaly Scores',
                            color_discrete_sequence=['#AB63FA'])
        fig4.add_vline(x=0, line_dash='dash', line_color='red', annotation_text='Threshold')
        st.plotly_chart(fig4, width="stretch")

    # Night usage
    st.subheader("🌙 Night Usage Behavior")
    c5, c6 = st.columns(2)
    with c5:
        fig5 = px.histogram(df, x='nighttime_usage', nbins=40, color='risk_category',
                            title='Nighttime Usage Distribution by Risk Category')
        st.plotly_chart(fig5, width="stretch")
    with c6:
        night_risk = bm['night_risk']
        nr_counts = pd.Series(night_risk).value_counts().reset_index()
        nr_counts.columns = ['Night Risk', 'Count']
        fig6 = px.pie(nr_counts, values='Count', names='Night Risk',
                      title='Night Risk Classification', hole=0.4)
        st.plotly_chart(fig6, width="stretch")

    # Notification dependency
    st.subheader("🔔 Notification Dependency Analysis")
    c7, c8 = st.columns(2)
    with c7:
        fig7 = px.scatter(df.sample(min(2000, len(df))), x='notifications_per_day',
                          y='phone_pickups_per_hour', color='risk_category',
                          title='Notification Count vs Phone Pickups', opacity=0.5)
        st.plotly_chart(fig7, width="stretch")
    with c8:
        fig8 = px.box(df, x='risk_category', y='phone_pickups_per_hour',
                      color='risk_category', title='Phone Pickups per Hour by Risk')
        st.plotly_chart(fig8, width="stretch")

    # Auto insights
    st.subheader("💡 Auto-Generated Insights")
    for title, text in insights:
        st.warning(f"**{title}**: {text}")

    if not insights:
        st.success("✅ No critical behavioral anomalies detected.")


# ══════════════════════════════════════════════════════════════════════════════
# MODULE: ML PREDICTIONS
# ══════════════════════════════════════════════════════════════════════════════

def page_ml_predictions(df):
    st.title("🤖 Machine Learning Predictions")
    
    view_mode = st.radio("Display Mode:", ["🟢 Simple View (User Friendly)", "⚙️ Advanced View (Technical Details)"], horizontal=True)

    with st.spinner("Training ML models on dataset..."):
        r1 = train_addiction_risk_model(df)
        r2 = train_screen_time_models(df)
        r3 = train_behavior_pattern_model(df)

    if "Simple View" in view_mode:
        st.subheader("🔮 Live AI Risk Prediction")
        pf = st.session_state.get('phone_profile', {})
        is_mobile = st.session_state.get('sidebar_data_mode', '') in ["Simulated Mobile", "Connect Phone"]
        
        if pf and is_mobile:
            st.info("📱 Analyzing real-time data automatically from your connected device...")
            st_val, nu_val = pf.get('total_screen_time', 8.0), pf.get('nighttime_usage', 1.0)
            notif_val, binge_val = pf.get('notifications_per_day', 150), pf.get('binge_sessions_per_week', 5)
            fomo_val, anx_val = pf.get('fomo_score', 5), pf.get('anxiety_score', 5)
            pickup_val, sleep_dis = pf.get('phone_pickups_per_hour', 20), pf.get('sleep_disruption_score', 5)
            submitted = True
        else:
            st.info("📊 You are in Dataset mode. Simply drag the sliders below to manually test the AI!")
            with st.form("risk_form"):
                fc1, fc2 = st.columns(2)
                with fc1:
                    st_val = st.slider("Total Screen Time (hrs)", 0.0, 24.0, 8.0, 0.5)
                    nu_val = st.slider("Nighttime Usage (hrs)", 0.0, 8.0, 1.0, 0.1)
                    notif_val = st.slider("Notifications per Day", 0, 500, 150)
                    binge_val = st.slider("Binge Sessions / Week", 0, 20, 5)
                with fc2:
                    fomo_val = st.slider("FOMO Score (1-10)", 1, 10, 5)
                    anx_val = st.slider("Anxiety Score (1-10)", 1, 10, 5)
                    pickup_val = st.slider("Phone Pickups / Hour", 0, 60, 20)
                    sleep_dis = st.slider("Sleep Disruption Score (1-10)", 1, 10, 5)
                submitted = st.form_submit_button("Predict AI Behavior Strategy", type="primary", width="stretch")

        if submitted:
            input_data = {
                'total_screen_time': st_val, 'nighttime_usage': nu_val,
                'notifications_per_day': notif_val, 'binge_sessions_per_week': binge_val,
                'fomo_score': fomo_val, 'anxiety_score': anx_val,
                'phone_pickups_per_hour': pickup_val, 'sleep_disruption_score': sleep_dis
            }
            label, probs = predict_addiction_risk(r1, input_data)
            
            st.markdown("### AI Summary Report 📋")
            if 'High' in label:
                st.error(f"🔴 **Action Required:** The AI classifies your usage pattern as **{label}** (Confidence: {probs[1]:.1%})")
                st.write("**Why did the AI decide this?**")
                if st_val > 6.0: st.markdown("- 📉 **Screen Time:** It is heavily inflated compared to the healthy baseline.")
                if nu_val > 2.0: st.markdown("- 🌙 **Night Habits:** Too much nighttime phone usage is directly impacting your sleep disruption logic.")
                if binge_val > 5: st.markdown("- ⏱️ **Frequency:** High frequency of continuous 'binge-sessions' detected.")
                if notif_val > 150: st.markdown("- 🔔 **Distractions:** Heavy notification loads correspond to your high FOMO/Anxiety predictions.")
            else:
                st.success(f"🟢 **Good Job:** The AI classifies your usage pattern as **{label}** (Confidence: {probs[0]:.1%})")
                st.write("Your usage is currently healthy and within balanced boundaries based on our dataset averages.")
            
            # Simple bar chart
            fig_prob = go.Figure(go.Bar(
                x=['Not Addicted', 'Addicted'], y=[probs[0], probs[1]],
                marker_color=['#00CC96', '#EF553B']
            ))
            fig_prob.update_layout(title='AI Probability Distribution', height=300, yaxis_range=[0, 1])
            st.plotly_chart(fig_prob, width="stretch")

    else:
        tab1, tab2, tab3 = st.tabs([
            "🎯 Tab 1: Addiction Risk (LogReg)",
            "📉 Tab 2: Screen Time Forecast (LR / MLR)",
            "🌲 Tab 3: Behavior Patterns (Random Forest)"
        ])

        # ── TAB 1 ──────────────────────────────────────────────────────────────
        with tab1:
            st.subheader("Addiction Risk Prediction — Logistic Regression")
            a1, a2, a3 = st.columns(3)
            a1.metric("Model Accuracy", f"{r1['accuracy']}%")
            a2.metric("Precision (Addicted)", f"{r1['classification_report']['1']['precision']:.2%}")
            a3.metric("Recall (Addicted)", f"{r1['classification_report']['1']['recall']:.2%}")

            c1, c2 = st.columns(2)
            with c1:
                # Confusion Matrix
                cm = r1['confusion_matrix']
                fig_cm = px.imshow(cm, text_auto=True, aspect='auto',
                                   x=['Pred: Not Addicted', 'Pred: Addicted'],
                                   y=['True: Not Addicted', 'True: Addicted'],
                                   title='Confusion Matrix', color_continuous_scale='Blues')
                st.plotly_chart(fig_cm, width="stretch")
            with c2:
                # Feature importance
                fi = pd.DataFrame.from_dict(r1['feature_importance'], orient='index', columns=['Importance'])
                fi = fi.sort_values('Importance', ascending=True)
                fig_fi = px.bar(fi, x='Importance', y=fi.index, orientation='h',
                                title='Feature Importance (|Coefficients|)',
                                color='Importance', color_continuous_scale='Reds')
                st.plotly_chart(fig_fi, width="stretch")



        # ── TAB 2 ──────────────────────────────────────────────────────────────
        with tab2:
            st.subheader("Screen Time Prediction — Linear & Multiple Linear Regression")
            t2c1, t2c2 = st.columns(2)
            t2c1.metric("LR — MAE", f"{r2['lr_mae']} hrs")
            t2c1.metric("LR — RMSE", f"{r2['lr_rmse']} hrs")
            t2c2.metric("MLR — MAE", f"{r2['mlr_mae']} hrs")
            t2c2.metric("MLR — RMSE", f"{r2['mlr_rmse']} hrs")

            sample_n = min(300, len(r2['y_test']))
            y_test_s = r2['y_test'].values[:sample_n]
            y_pred_lr_s = r2['y_pred_lr'][:sample_n]
            y_pred_mlr_s = r2['y_pred_mlr'][:sample_n]
            x_idx = list(range(sample_n))

            fig_lr = go.Figure()
            fig_lr.add_trace(go.Scatter(x=x_idx, y=y_test_s, mode='lines', name='Actual', line=dict(color='blue')))
            fig_lr.add_trace(go.Scatter(x=x_idx, y=y_pred_lr_s, mode='lines', name='LR Predicted', line=dict(color='orange', dash='dash')))
            fig_lr.add_trace(go.Scatter(x=x_idx, y=y_pred_mlr_s, mode='lines', name='MLR Predicted', line=dict(color='green', dash='dot')))
            fig_lr.update_layout(title='Actual vs Predicted Screen Time (LR & MLR)', height=400,
                                 xaxis_title='Sample Index', yaxis_title='Screen Time (hrs)')
            st.plotly_chart(fig_lr, width="stretch")

            # Residual
            residuals_mlr = y_test_s - y_pred_mlr_s
            fig_res = px.histogram(residuals_mlr, nbins=40, title='MLR Residuals Distribution',
                                   color_discrete_sequence=['#636EFA'])
            fig_res.add_vline(x=0, line_dash='dash', line_color='red')
            st.plotly_chart(fig_res, width="stretch")

        # ── TAB 3 ──────────────────────────────────────────────────────────────
        with tab3:
            st.subheader("Behavior Pattern Prediction — Random Forest")
            t3c1, t3c2, t3c3 = st.columns(3)
            t3c1.metric("RF Accuracy", f"{r3['accuracy']}%")
            t3c2.metric("Classes", str(list(r3['classes'])))
            t3c3.metric("N Estimators", "100")

            # Feature importance
            fi3 = pd.DataFrame.from_dict(r3['feature_importance'], orient='index', columns=['Importance'])
            fi3 = fi3.sort_values('Importance', ascending=True)
            fig_fi3 = px.bar(fi3, x='Importance', y=fi3.index, orientation='h',
                             title='Random Forest Feature Importance',
                             color='Importance', color_continuous_scale='Greens')
            fig_fi3.update_layout(height=420)
            st.plotly_chart(fig_fi3, width="stretch")

            # Confusion matrix
            cm3 = r3['confusion_matrix']
            classes = r3['classes']
            fig_cm3 = px.imshow(cm3, text_auto=True, aspect='auto',
                                x=[f'Pred: {c}' for c in classes],
                                y=[f'True: {c}' for c in classes],
                                title='RF Confusion Matrix', color_continuous_scale='Greens')
            st.plotly_chart(fig_cm3, width="stretch")

            # Prediction confidence sample
            probs3 = r3['y_prob'][:50]
            df_prob = pd.DataFrame(probs3, columns=classes)
            df_prob['Index'] = range(len(df_prob))
            df_melt = df_prob.melt(id_vars='Index', var_name='Class', value_name='Probability')
            fig_conf = px.bar(df_melt, x='Index', y='Probability', color='Class',
                              title='Prediction Confidence (First 50 Samples)', barmode='stack')
            st.plotly_chart(fig_conf, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# MODULE: RISK SCORING ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def page_risk_scoring(df):
    st.title("⚡ Addiction Risk Scoring Engine")
    st.markdown("Custom risk formula: **Screen Time (40%) + Night Usage (20%) + Notifications (20%) + Session Frequency (20%)**")

    st.subheader("🔢 Computed Custom Risk Score")
    pf = st.session_state.get('phone_profile', {})
    is_mobile = st.session_state.get('sidebar_data_mode', '') in ["Simulated Mobile", "Connect Phone"]
    
    if pf and is_mobile:
        st.info("📱 Calculating risk score automatically based on your active device usage...")
        rs_screen = pf.get('total_screen_time', 8.0)
        rs_night = pf.get('nighttime_usage', 1.5)
        rs_notif = pf.get('notifications_per_day', 150)
        rs_binge = pf.get('binge_sessions_per_week', 5)
        calc = True
    else:
        st.info("📊 You are in Dataset mode. Use the sliders below to compute a custom test score!")
        with st.form("risk_score_form"):
            rc1, rc2 = st.columns(2)
            with rc1:
                rs_screen = st.slider("Total Screen Time (hrs)", 0.0, 24.0, 8.0, 0.5)
                rs_night = st.slider("Nighttime Usage (hrs)", 0.0, 8.0, 1.5, 0.1)
            with rc2:
                rs_notif = st.slider("Notifications per Day", 0, 500, 150)
                rs_binge = st.slider("Binge Sessions / Week", 0, 20, 5)
            calc = st.form_submit_button("Calculate Example Risk Score", type="primary", width="stretch")

    if calc:
        score = compute_risk_score({
            'total_screen_time': rs_screen,
            'nighttime_usage': rs_night,
            'notifications_per_day': rs_notif,
            'binge_sessions_per_week': rs_binge
        })
        level, emoji = classify_risk(score)

        # Gauge
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': f"Addiction Risk Score — {emoji} {level}"},
            delta={'reference': 50},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': 'darkblue'},
                'steps': [
                    {'range': [0, 30], 'color': 'lightgreen'},
                    {'range': [30, 70], 'color': 'yellow'},
                    {'range': [70, 100], 'color': 'red'},
                ],
                'threshold': {'line': {'color': 'red', 'width': 4}, 'thickness': 0.75, 'value': 70}
            }
        ))
        fig_gauge.update_layout(height=400)
        st.plotly_chart(fig_gauge, width="stretch")

        # Breakdown
        
        breakdown = {
            'Screen Time (40%)': round((rs_screen / 20) * 40, 1),
            'Night Usage (20%)': round((rs_night / 6) * 20, 1),
            'Notifications (20%)': round((rs_notif / 400) * 20, 1),
            'Session Frequency (20%)': round((rs_binge / 15) * 20, 1),
        }
        fig_break = px.bar(x=list(breakdown.keys()), y=list(breakdown.values()),
                           title='Risk Score Metrics Breakdown', color=list(breakdown.values()),
                           color_continuous_scale='RdYlGn_r', text_auto=True)
        fig_break.update_layout(height=320)
        st.plotly_chart(fig_break, width="stretch")

    # Population risk distribution
    st.subheader("📊 Population Risk Score Distribution")
    df2 = df.copy()
    df2['custom_risk'] = df2.apply(
        lambda r: compute_risk_score({
            'total_screen_time': r.get('total_screen_time', 0),
            'nighttime_usage': r.get('nighttime_usage', 0),
            'notifications_per_day': r.get('notifications_per_day', 0),
            'binge_sessions_per_week': r.get('binge_sessions_per_week', 0)
        }), axis=1
    )
    rc1, rc2 = st.columns(2)
    with rc1:
        fig_dist = px.histogram(df2, x='custom_risk', nbins=50,
                                title='Custom Risk Score Distribution',
                                color_discrete_sequence=['#636EFA'])
        st.plotly_chart(fig_dist, width="stretch")
    with rc2:
        fig_comp = px.scatter(df2.sample(min(2000, len(df2))), x='addiction_risk_score', y='custom_risk',
                              color='risk_category', title='Dataset Risk Score vs Custom Score',
                              opacity=0.4)
        st.plotly_chart(fig_comp, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# MODULE: RECOMMENDATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def page_recommendations(df):
    st.title("💡 Personalized Recommendation Engine")

    st.subheader("Automated Detox Plan")
    pf = st.session_state.get('phone_profile', {})
    is_mobile = st.session_state.get('sidebar_data_mode', '') in ["Simulated Mobile", "Connect Phone"]
    
    if pf and is_mobile:
        st.info("📱 Personalization generated automatically from your connected device's profile.")
        metrics = pf
        get_recs = True
    else:
        st.info("📊 You are in Dataset mode. Fill out the mock profile below to see an AI Detox Plan.")
        with st.form("rec_form"):
            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                rec_screen = st.slider("Screen Time (hrs/day)", 0.0, 24.0, 8.0)
                rec_night = st.slider("Night Usage (hrs)", 0.0, 6.0, 1.5)
                rec_notif = st.slider("Notifications / Day", 0, 400, 150)
            with rc2:
                rec_pickup = st.slider("Phone Pickups / Hour", 0, 60, 20)
                rec_binge = st.slider("Binge Sessions / Week", 0, 20, 5)
                rec_sleep = st.slider("Sleep Hours", 3.0, 12.0, 7.0)
            with rc3:
                rec_prod = st.slider("Productivity Score (1-10)", 1, 10, 5)
                rec_fomo = st.slider("FOMO Score (1-10)", 1, 10, 5)
                rec_anxiety = st.slider("Anxiety Score (1-10)", 1, 10, 5)
            get_recs = st.form_submit_button("Generate Recommendations", type="primary", width="stretch")
            metrics = {
                'total_screen_time': rec_screen, 'nighttime_usage': rec_night,
                'notifications_per_day': rec_notif, 'phone_pickups_per_hour': rec_pickup,
                'binge_sessions_per_week': rec_binge, 'sleep_hours': rec_sleep,
                'productivity_score': rec_prod, 'fomo_score': rec_fomo, 'anxiety_score': rec_anxiety
            }

    if get_recs:
        recs = get_recommendations(metrics)
        score = compute_risk_score(metrics)
        level, emoji = classify_risk(score)
        
        st.markdown(f"### Overall Risk Status: {emoji} **{level}** (Score: {score})")
        st.markdown("---")

        if recs.get('critical'):
            st.subheader("🚨 Critical Action Required")
            critical_text = "Based on the latest behavioral scans, the artificial intelligence has detected critical issues requiring **immediate attention** to prevent severe addiction loops:\n\n"
            for r in recs['critical']:
                critical_text += f"- **{r}**\n"
            st.error(critical_text)

        if recs.get('warnings'):
            st.subheader("⚠️ Urgent Behavioral Warnings")
            warn_text = "We have identified several usage habits that are actively driving up your addiction risk score and disrupting your daily baseline:\n\n"
            for r in recs['warnings']:
                warn_text += f"- {r}\n"
            st.warning(warn_text)

        if recs.get('tips'):
            st.subheader("💡 Focus & Improvement Tips")
            tips_text = "Regaining your digital wellbeing is a step-by-step process. The engine has generated the following intelligent suggestions to help you regain your focus and lower your anxiety levels:\n\n"
            for r in recs['tips']:
                tips_text += f"- {r}\n"
            st.info(tips_text)

        if recs.get('detox_plan'):
            st.subheader("🧘 Digital Detox Protocol")
            detox_text = "If you are feeling overwhelmed by technology, we highly recommend following this strict Digital Detox protocol immediately to reset your dopamine receptors:\n\n"
            for r in recs['detox_plan']:
                detox_text += f"- {r}\n"
            st.success(detox_text)

        st.subheader("📅 Your 7-Day Digital Wellness Schedule")
        weekly_text = "A structured schedule effectively combats random doom-scrolling. Try adhering to this day-by-day plan to slowly reclaim your time and productivity:\n\n"
        for day_plan in recs.get('weekly_plan', []):
            weekly_text += f"- **{day_plan}**\n"
        st.markdown(weekly_text)

    # Population-level insights
    st.markdown("---")
    st.subheader("📊 Population Behavior Benchmarks")
    cols = ['total_screen_time', 'nighttime_usage', 'notifications_per_day', 'sleep_hours', 'productivity_score']
    bench = df[cols].describe().round(2)
    st.dataframe(bench, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# MODULE: SETTINGS / PROFILE
# ══════════════════════════════════════════════════════════════════════════════

def page_settings(df, user_info):
    st.title("⚙️ Settings & User Profile")

    tab1, tab2, tab3 = st.tabs(["👤 Profile", "📁 Data Management", "📱 Mobile Integration"])

    with tab1:
        st.subheader("Your Profile")
        st.write(f"**Username:** {user_info['username']}")
        st.write(f"**Full Name:** {user_info.get('full_name', 'N/A')}")
        st.write(f"**Email:** {user_info.get('email', 'N/A')}")
        st.write(f"**Role:** {user_info['role']}")

    with tab2:
        st.subheader("Upload Custom Dataset")
        uploaded = st.file_uploader("Upload CSV (must match dataset schema)", type=['csv'])
        if uploaded:
            try:
                new_df = load_data(uploaded)
                st.success(f"Dataset loaded: {len(new_df):,} records")
                st.session_state['df'] = new_df
                st.dataframe(new_df.head(10), width="stretch")
            except Exception as e:
                st.error(f"Error: {e}")

        st.subheader("Current Dataset Info")
        st.write(f"Records: **{len(df):,}** | Columns: **{len(df.columns)}**")
        st.dataframe(df.describe().round(2), width="stretch")

    with tab3:
        st.subheader("📱 Mobile Device Integration")
        adb_connected = check_adb_connected()
        if adb_connected:
            st.success("✅ ADB Device Connected")
            if st.button("Fetch Real Device Data"):
                st.info("Fetching data via ADB...")
        else:
            st.warning("⚠️ No ADB device detected. Using Simulation Mode.")
            if st.button("Generate Simulated Mobile Data"):
                sim_df = generate_simulated_mobile_data(200)
                st.success(f"Generated {len(sim_df)} simulated mobile records")
                st.dataframe(sim_df.head(20), width="stretch")

                # Charts
                fig = px.bar(sim_df.groupby('app_name')['usage_time_min'].sum().reset_index(),
                             x='app_name', y='usage_time_min', title='App Usage Time (Simulated)',
                             color='usage_time_min', color_continuous_scale='Blues')
                st.plotly_chart(fig, width="stretch")

                fig2 = px.bar(sim_df.groupby('category')['usage_time_min'].sum().reset_index(),
                              x='category', y='usage_time_min', title='Category Breakdown (Simulated)')
                st.plotly_chart(fig2, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# MODULE: AI CHATBOT  (Groq API — versatile model selector)
# ══════════════════════════════════════════════════════════════════════════════

# ── Groq model catalogue ──────────────────────────────────────────────────────
GROQ_MODELS = {
    "⚡ Llama 3.3 70B  (Fast & Powerful)"         : "llama-3.3-70b-versatile",
    "🧠 Llama 3.1 8B   (Ultra-fast / lightweight)": "llama-3.1-8b-instant",
    "🔬 DeepSeek R1 Distill Llama 70B (Reasoning)": "deepseek-r1-distill-llama-70b",
    "🌟 Gemma 2 9B      (Google / Balanced)"       : "gemma2-9b-it",
    "🦅 Llama 3 Groq 70B Tool Use"                 : "llama3-groq-70b-8192-tool-use-preview",
    "🎯 Mixtral 8x7B   (MoE / Creative)"           : "mixtral-8x7b-32768",
}

def _groq_chat(api_key: str, model: str, system: str, messages: list, temperature: float = 0.7) -> str:
    """Call Groq /openai/v1/chat/completions and return the assistant reply text."""
    import requests, json

    groq_messages = [{"role": "system", "content": system}] + messages

    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": groq_messages,
            "max_tokens": 1024,
            "temperature": temperature,
            "stream": False,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def page_chatbot():
    st.title("🤖 AI Wellness Chatbot")
    st.markdown(
        "Powered by **[Groq](https://groq.com)** — blazing-fast inference. "
        "Ask anything about digital addiction, screen time, or your phone usage data."
    )

    # ── API key & model config in a collapsible panel ────────────────────────
    with st.expander("⚙️ Groq API Settings", expanded=(not st.session_state.get("groq_api_key"))):
        col_key, col_model = st.columns([3, 2])
        with col_key:
            entered_key = st.text_input(
                "Groq API Key",
                value=st.session_state.get("groq_api_key", ""),
                type="password",
                placeholder="gsk_...",
                help="Get a free key at https://console.groq.com",
            )
            if entered_key:
                st.session_state["groq_api_key"] = entered_key.strip()

        with col_model:
            model_label = st.selectbox(
                "Model",
                options=list(GROQ_MODELS.keys()),
                index=0,
                key="groq_model_label",
            )
            selected_model_id = GROQ_MODELS[model_label]
            st.caption(f"`{selected_model_id}`")

        temperature = st.slider("🌡️ Temperature (creativity)", 0.0, 1.0, 0.7, 0.05)

        if not st.session_state.get("groq_api_key"):
            st.info(
                "🔑 Enter your **Groq API key** above to activate the chatbot.  \n"
                "Get one for free at [console.groq.com](https://console.groq.com) — no credit card needed."
            )

    st.markdown("---")

    # ── Initialize chat history ───────────────────────────────────────────────
    if "chatbot_messages" not in st.session_state:
        st.session_state["chatbot_messages"] = [
            {
                "role": "assistant",
                "content": (
                    "Hi! I'm your **digital wellness assistant** powered by Groq ⚡  \n"
                    "Ask me about screen time, app addiction, productivity tips, "
                    "or how to interpret your risk score. 📱"
                ),
            }
        ]

    # ── Build system prompt with optional phone-profile context ──────────────
    profile = st.session_state.get("phone_profile", {})
    profile_context = ""
    if profile:
        score = profile.get("_precomputed_risk_score", None)
        score_text = f"Risk Score: {score}/100\n" if score else ""
        profile_context = (
            "The user's phone data summary:\n"
            f"{score_text}"
            f"Daily Screen Time: {profile.get('total_screen_time', 'N/A')} hrs\n"
            f"FOMO Score: {profile.get('fomo_score', 'N/A')}/10\n"
            f"Sleep Hours: {profile.get('sleep_hours', 'N/A')} hrs\n"
            f"Binge Sessions/Week: {profile.get('binge_sessions_per_week', 'N/A')}\n"
            f"Productivity Score: {profile.get('productivity_score', 'N/A')}/10\n\n"
        )

    system_prompt = (
        "You are a compassionate and knowledgeable digital wellness AI counselor. "
        "Your role is to help users understand their smartphone usage patterns, "
        "reduce digital addiction, and build healthier tech habits. "
        "Provide practical, evidence-based advice. Be empathetic but direct. "
        "Keep responses concise (3-5 sentences unless the user asks for detail). "
        "Use markdown formatting (bullet points, bold) when helpful. "
        "Do not diagnose medical conditions.\n\n"
        + (f"Context about this user:\n{profile_context}" if profile_context else "")
    )

    # ── Render chat history ───────────────────────────────────────────────────
    for msg in st.session_state["chatbot_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Chat input ────────────────────────────────────────────────────────────
    user_input = st.chat_input("Type your question here...")
    if user_input:
        st.session_state["chatbot_messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        groq_key = st.session_state.get("groq_api_key", "")

        with st.chat_message("assistant"):
            if not groq_key:
                reply = (
                    "⚠️ **Groq API key not set.**  \n"
                    "Please expand **⚙️ Groq API Settings** above, enter your key, and try again.  \n"
                    "Get a free key at [console.groq.com](https://console.groq.com)."
                )
                st.markdown(reply)
            else:
                with st.spinner(f"Thinking via `{selected_model_id}`..."):
                    try:
                        # Keep last 10 turns for context window efficiency
                        history = st.session_state["chatbot_messages"][-10:]
                        api_messages = [
                            {"role": m["role"], "content": m["content"]}
                            for m in history
                            if m["role"] in ("user", "assistant")
                        ]

                        reply = _groq_chat(
                            api_key=groq_key,
                            model=selected_model_id,
                            system=system_prompt,
                            messages=api_messages,
                            temperature=temperature,
                        )
                    except Exception as e:
                        err_str = str(e)
                        if "401" in err_str or "invalid_api_key" in err_str.lower():
                            reply = (
                                "❌ **Invalid API key.** Please check your Groq API key in the settings panel above."
                            )
                        elif "model_not_found" in err_str.lower():
                            reply = (
                                f"❌ Model `{selected_model_id}` is not available. "
                                "Try selecting a different model in the settings panel."
                            )
                        else:
                            reply = (
                                "I'm having trouble connecting to Groq right now. "
                                "Please check your API key and internet connection, then try again.\n\n"
                                f"*(Error: {e})*"
                            )
                st.markdown(reply)

        st.session_state["chatbot_messages"].append({"role": "assistant", "content": reply})

    # ── Bottom toolbar ────────────────────────────────────────────────────────
    col_clear, col_info = st.columns([1, 3])
    with col_clear:
        if st.button("🗑️ Clear Chat", type="secondary"):
            st.session_state["chatbot_messages"] = [
                {
                    "role": "assistant",
                    "content": "Chat cleared! How can I help you with your digital wellness today? 📱",
                }
            ]
            st.rerun()
    with col_info:
        st.caption(
            f"🔋 Active model: `{selected_model_id}` &nbsp;|&nbsp; "
            "API: [Groq](https://groq.com) &nbsp;|&nbsp; "
            "History: last 10 turns"
        )


# ══════════════════════════════════════════════════════════════════════════════
# MODULE: ABOUT
# ══════════════════════════════════════════════════════════════════════════════

def page_about():
    st.title("ℹ️ About AdaptiveAI")

    st.markdown("""
    ## 🧠 AdaptiveAI — Digital Addiction Intelligence System

    AdaptiveAI is an enterprise-grade behavioral analytics platform designed to help
    individuals and researchers understand and combat smartphone addiction through
    data-driven insights and AI-powered recommendations.

    ---
    """)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🎯 What It Does")
        st.markdown("""
        - **Real Phone Analysis** — Connect via ADB to fetch actual usage data
        - **7-Day Trend Tracking** — Pulls historical data via Android UsageStats API
        - **Risk Scoring** — Mathematically rigorous addiction risk calculation
        - **ML Predictions** — Logistic Regression & Random Forest classifiers
        - **Smart Recommendations** — Personalized digital detox plans
        - **AI Chatbot** — Talk to an AI wellness counselor anytime
        """)

    with col2:
        st.subheader("🔬 Risk Score Math")
        st.markdown("""
        The risk score uses a **5-component weighted model**:
        | Component | Weight |
        |-----------|--------|
        | Screen Time (log-scaled) | 40% |
        | Social / FOMO | 20% |
        | Binge Sessions | 20% |
        | Sleep Disruption | 10% |
        | Productivity Penalty | 10% |

        All inputs are **exponentially recency-weighted** (half-life = 3 days)
        and the final score is **sigmoid-normalized** to [0–100].
        """)

    st.markdown("---")
    st.subheader("📡 Data Sources")
    c1, c2 = st.columns(2)
    with c1:
        st.info("""
        **Primary: Android UsageStats API**
        `dumpsys usagestats`
        - Genuine 7-day per-day breakdown
        - Works across charges/reboots
        - Requires USB Debugging
        """)
    with c2:
        st.warning("""
        **Fallback: BatteryStats**
        `dumpsys batterystats --charged`
        - Since-last-charge only
        - Used if UsageStats unavailable
        - Usage spread evenly across 7 days
        """)

    st.markdown("---")
    st.subheader("🛠️ Tech Stack")
    tech_cols = st.columns(4)
    tech_cols[0].success("**Frontend**\nStreamlit")
    tech_cols[1].success("**ML**\nScikit-Learn")
    tech_cols[2].success("**Data**\nPandas / NumPy")
    tech_cols[3].success("**Phone**\nADB (Android Debug Bridge)")

    st.markdown("---")
    st.subheader("⚠️ Privacy Notice")
    st.markdown("""
    - All data is processed **locally on your machine** — nothing is sent to external servers (except the AI Chatbot which uses Anthropic's API).
    - Phone data is fetched only when you explicitly connect and click **Fetch Data**.
    - No personal data is stored permanently beyond the local SQLite database (`data/users.db`).
    """)

    st.markdown("---")
    st.caption("AdaptiveAI v1.0 | Built with ❤️ for Digital Wellness Research")


# MODULE: ADMIN PANEL
# ══════════════════════════════════════════════════════════════════════════════

def page_admin(df):
    st.title("🛠️ Admin Panel")
    st.subheader("Registered Users")
    users = get_all_users()
    if users:
        user_df = pd.DataFrame(users, columns=['ID', 'Username', 'Role', 'Email', 'Full Name', 'Created At'])
        st.dataframe(user_df, width="stretch")
    else:
        st.info("No users found.")

    st.subheader("Dataset Statistics")
    stats = get_summary_stats(df)
    for k, v in stats.items():
        st.write(f"**{k.replace('_', ' ').title()}:** {v}")

    st.subheader("Risk Category Breakdown")
    risk_breakdown = df['risk_category'].value_counts()
    st.bar_chart(risk_breakdown)


# ══════════════════════════════════════════════════════════════════════════════
# MODULE: MOBILE DEVICE INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════

def page_mobile_connect():
    st.title("📱 Mobile Device Intelligence")

    status, raw_output = get_adb_status()
    adb_path = _find_adb()

    # ── NOT INSTALLED ─────────────────────────────────────────────────────────
    if status == AdbStatus.NOT_INSTALLED:
        st.error("❌ ADB (Android Debug Bridge) is not installed or not found on this PC.")
        st.markdown("")

        st.warning(
            "**ADB is required** to communicate with your Android phone. "
            "It's a free tool from Google — follow the steps below to install it."
        )

        with st.expander("📥 Step 1 — Download ADB (Android Platform Tools)", expanded=True):
            st.markdown("""
**Download Link:** https://developer.android.com/tools/releases/platform-tools

| Step | Action |
|------|---------|
| 1 | Click the link above → Download **"SDK Platform-Tools for Windows"** |
| 2 | Extract the downloaded ZIP file (e.g. to `C:\\platform-tools\\`) |
| 3 | Inside the folder you should see `adb.exe`, `fastboot.exe`, etc. |
            """)

        with st.expander("⚙️ Step 2 — Add ADB to System PATH (Recommended)", expanded=True):
            st.markdown("""
Adding ADB to PATH lets you run it from anywhere:

| Step | Action |
|------|---------|
| 1 | Press **Win + S**, search **"Environment Variables"** → Open it |
| 2 | Click **"Environment Variables..."** button |
| 3 | Under **"System variables"**, find and select **Path** → click **Edit** |
| 4 | Click **New** → paste the folder path, e.g. `C:\\platform-tools` |
| 5 | Click **OK** on all dialogs |
| 6 | **Restart this Streamlit app** |

> 💡 **Alternatively**, just place the extracted `platform-tools` folder at one of these
> paths and the app will find it automatically without any PATH changes:
> - `C:\\platform-tools\\`
> - `C:\\adb\\`
> - `C:\\android\\platform-tools\\`
> - `%USERPROFILE%\\platform-tools\\`
            """)

        with st.expander("✅ Step 3 — Verify ADB Works", expanded=False):
            st.markdown("""
Open **Command Prompt** or **PowerShell** and run:
```
adb version
```
You should see something like:
```
Android Debug Bridge version 1.0.41
```
If it works, continue to the phone setup steps below.
            """)

        st.markdown("---")
        if st.button("🔄 I've installed ADB — Check Again", type="primary", width="stretch"):
            st.rerun()

    # ── UNAUTHORIZED (device found but not allowed yet) ───────────────────────
    elif status == AdbStatus.UNAUTHORIZED:
        st.warning("⚠️ Android device detected but **not yet authorised**.")
        st.markdown("")
        st.info(
            "Your phone is connected and visible to ADB, but you need to **approve the "
            "USB Debugging prompt** that appeared on your phone's screen."
        )

        with st.expander("🔓 How to Authorise USB Debugging", expanded=True):
            st.markdown("""
| Step | Action |
|------|---------|
| 1 | Look at your **phone screen** — there should be a dialog: **"Allow USB Debugging?"** |
| 2 | Tap **ALLOW** |
| 3 | Optionally check **"Always allow from this computer"** to avoid future prompts |
| 4 | If no dialog appeared, **unplug and replug the USB cable** |
| 5 | If the dialog still doesn't appear, go to **Settings → Developer Options → Revoke USB Debugging Authorisations**, tap OK, then replug |
            """)

        st.code(f"ADB output:\n{raw_output}", language="text")
        st.markdown("---")
        if st.button("🔄 I've tapped Allow — Refresh", type="primary", width="stretch"):
            st.rerun()

    # ── OFFLINE ───────────────────────────────────────────────────────────────
    elif status == AdbStatus.OFFLINE:
        st.error("🔌 Device detected but shows as **OFFLINE**.")
        st.markdown("")

        with st.expander("🔧 How to Fix Offline Status", expanded=True):
            st.markdown("""
| Step | Action |
|------|---------|
| 1 | **Unplug** the USB cable from the phone |
| 2 | Wait 5 seconds, then **plug it back in** |
| 3 | On your phone, set USB mode to **File Transfer / MTP** (not just Charging) |
| 4 | Check for the **"Allow USB Debugging?"** dialog and tap Allow |
| 5 | If still offline, open CMD and run: `adb kill-server` then `adb start-server` |
            """)

        st.code(f"ADB output:\n{raw_output}", language="text")
        st.markdown("---")
        if st.button("🔄 Refresh", type="primary", width="stretch"):
            st.rerun()

    # ── NO_DEVICE (ADB works but no phone plugged in) ─────────────────────────
    elif status == AdbStatus.NO_DEVICE:
        st.error("❌ No Android device detected. ADB is installed but no phone is connected.")
        st.markdown("")
        st.info(
            "✅ Good news — ADB is installed correctly. Now connect your phone "
            "and enable Developer Mode + USB Debugging."
        )
        if adb_path:
            st.caption(f"ADB found at: `{adb_path}`")

        with st.expander("📖 Step 1 — Enable Developer Options on your phone", expanded=True):
            st.markdown("""
| Step | Action |
|------|---------|
| 1 | Open **Settings** on your Android phone |
| 2 | Scroll to **About Phone** (or **About Device**) |
| 3 | Find **Build Number** |
| 4 | **Tap Build Number 7 times** rapidly until you see 🎉 *"You are now a developer!"* |

> ⚠️ Location by brand:
> - **Samsung** → `Settings › About Phone › Software Information › Build Number`
> - **Google Pixel** → `Settings › About Phone › Build Number`
> - **OnePlus** → `Settings › About Device › Build Number`
> - **Xiaomi / Redmi** → `Settings › About Phone › All Specs › MIUI Version`
            """)

        with st.expander("🔓 Step 2 — Enable USB Debugging", expanded=True):
            st.markdown("""
| Step | Action |
|------|---------|
| 1 | Go to **Settings → Developer Options** (now visible) |
| 2 | Toggle the **Developer Options** master switch **ON** |
| 3 | Scroll down and enable **USB Debugging** |
| 4 | Tap **OK** on the confirmation dialog |

> ✅ Xiaomi/MIUI: also enable **"Install via USB"** and **"USB Debugging (Security Settings)"**
            """)

        with st.expander("🔌 Step 3 — Connect via USB Cable", expanded=True):
            st.markdown("""
| Step | Action |
|------|---------|
| 1 | Use a **data-capable USB cable** (not just a charging cable) |
| 2 | Plug it into this PC |
| 3 | A dialog appears on your phone: **"Allow USB Debugging?"** → tap **Allow** |
| 4 | Set USB mode to **File Transfer / MTP** if prompted |

> 🔁 No dialog? Unplug and replug the cable.
            """)

        st.markdown("---")
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🔄 Refresh / Check Again", type="primary", width="stretch"):
                st.rerun()
        with col2:
            st.caption("After completing above steps, click **Refresh** to detect your phone.")

    # ── CONNECTED ──────────────────────────────────────────────────
    elif status == "connected":
        dev = get_adb_device_info()
        battery = fetch_adb_battery()
        screen  = fetch_adb_screen_state()

        # Device info header
        di1, di2, di3, di4 = st.columns(4)
        di1.success("✅ Device Connected")
        di2.metric("Device", f"{dev.get('brand','')} {dev.get('model','')}")
        di3.metric("Android", f"v{dev.get('android','?')}")
        di4.metric("Battery", f"{battery}%" if battery else "N/A")

        st.markdown("---")

        if 'phone_df' not in st.session_state:
            with st.spinner("📡 Fetching real-time usage data from your phone..."):
                df_real, meta = fetch_real_mobile_data()

            if df_real is None:
                st.error(f"⚠️ Could not fetch data: {meta}")
                st.info(
                    "Make sure **USB Debugging** is enabled and you have allowed the "
                    "debugging prompt on your phone."
                )
                col_retry, col_diag = st.columns(2)
                with col_retry:
                    if st.button("🔄 Retry", type="primary"):
                        st.rerun()
                with col_diag:
                    if st.button("🔍 Run Diagnostics", type="secondary"):
                        with st.spinner("Running diagnostics..."):
                            diag = diagnose_adb_data_fetch()
                        st.session_state['adb_diagnostics'] = diag
                        st.rerun()

                # Show diagnostics results if available
                if 'adb_diagnostics' in st.session_state:
                    diag = st.session_state['adb_diagnostics']
                    with st.expander("📋 Diagnostic Results", expanded=True):
                        st.write(f"**ADB Status:** {diag['adb_status']}")
                        st.write(f"**Device Info:** {diag.get('device_info', {})}")
                        st.write(f"**Third-party apps found:** {diag.get('third_party_count', 0)}")
                        if diag.get('errors'):
                            st.error("**Errors:**")
                            for err in diag['errors']:
                                st.write(f"- {err}")
                        st.write("**UsageStats sample (first 500 chars):**")
                        st.code(diag.get('usagestats_sample', '')[:500])
                        st.write("**Batterystats sample (first 500 chars):**")
                        st.code(diag.get('batterystats_sample', '')[:500])
                        if st.button("🗑️ Clear Diagnostics", type="secondary"):
                            del st.session_state['adb_diagnostics']
                            st.rerun()
                return

            st.session_state['phone_df'] = df_real
            st.session_state['phone_meta'] = meta
            st.session_state['phone_profile'] = build_risk_profile_from_real(df_real)

        df_real = st.session_state['phone_df']
        meta = st.session_state['phone_meta']

        st.success(f"✅ Fetched data from **{meta['total_apps']}** apps — {meta['fetched_at']}")


        st.subheader("📊 App Usage Breakdown")

        # --- Day-wise Filter ---
        col_filter, _ = st.columns([1, 3])
        with col_filter:
            days_filter = st.selectbox(
                "📅 Select Data Range:",
                options=[1, 3, 7],
                index=2, # Default to 7
                format_func=lambda x: f"Last {x} Day{'s' if x > 1 else ''}"
            )

        # Filter df_real based on timestamp
        if 'timestamp' in df_real.columns:
            df_real_copy = df_real.copy()
            df_real_copy['timestamp'] = pd.to_datetime(df_real_copy['timestamp'], errors='coerce')
            cutoff = pd.Timestamp.now() - pd.Timedelta(days=days_filter)
            df_filtered = df_real_copy[(df_real_copy['timestamp'] >= cutoff) | (df_real_copy['timestamp'].isna())]
        else:
            df_filtered = df_real

        # Save selected profile to session state so other tabs can use it!
        st.session_state['phone_profile'] = build_risk_profile_from_real(df_filtered)

        if df_filtered.empty:
            st.info(f"No usage data found for the last {days_filter} days.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                top_n = df_filtered.groupby('app_name')['usage_time_min'].sum().reset_index()
                top_n = top_n.sort_values('usage_time_min', ascending=False).head(10)

                fig_bar = px.bar(
                    top_n, x='usage_time_min', y='app_name', orientation='h',
                    color='usage_time_min', color_continuous_scale='Blues',
                    title=f'Top 10 Apps by Usage (Last {days_filter} Days)', text_auto='.1f'
                )
                fig_bar.update_layout(height=380, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig_bar, width="stretch")

            with c2:
                cat_sum = df_filtered.groupby('category')['usage_time_min'].sum().reset_index()
                fig_pie = px.pie(
                    cat_sum, values='usage_time_min', names='category',
                    title=f'Usage by Category (Last {days_filter} Days)', hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig_pie.update_layout(height=380)
                st.plotly_chart(fig_pie, width="stretch")

            # Sessions vs Usage scatter
            agg_df = df_filtered.groupby(['app_name', 'category']).agg({
                'usage_time_min': 'sum',
                'session_count': 'sum'
            }).reset_index()

            fig_scatter = px.scatter(
                agg_df, x='usage_time_min', y='session_count', color='category',
                size='usage_time_min', hover_name='app_name',
                title='Sessions vs Usage Time per App'
            )
            st.plotly_chart(fig_scatter, width="stretch")

        st.markdown("---")
        st.subheader("🧠 Section 2: Behavior Intelligence & Risk Classification")

        # Load ML model directly from session state or train it
        if 'df' not in st.session_state:
            with st.spinner("Initializing AI Models..."):
                st.session_state['df'] = get_data()

        df_train = st.session_state['df']
        profile = st.session_state['phone_profile']

        from ml_models.models import train_addiction_risk_model, predict_addiction_risk, compute_risk_score, classify_risk
        from utils.recommendations import get_recommendations

        lr_model_bundle = train_addiction_risk_model(df_train)

        # 1. Deterministic Behavioral Risk Gauge (7-day weighted sigmoid model)
        score = compute_risk_score(profile)  # uses _precomputed_risk_score if available
        level, emoji = classify_risk(score)

        # Show data source label
        src = st.session_state.get('phone_meta', {}).get('source', '')
        day_label = f"{days_filter}-day" if days_filter > 1 else "1-day"
        if '7 day' in src or 'usagestats' in src:
            st.success(f"📊 Risk score computed from **genuine {day_label} usage data** (Android UsageStats API) — exponentially recency-weighted.")
        else:
            st.warning(f"⚠️ UsageStats unavailable — score estimated from **since-last-charge** data spread across {day_label}. Connect longer for more accurate results.")

        c1_b, c2_b = st.columns(2)
        with c1_b:
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=score,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': f"{days_filter}-Day Addiction Risk Score — {emoji} {level}", 'font': {'size': 18}},
                delta={'reference': 50, 'increasing': {'color': 'red'}},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': 'darkblue'},
                    'steps': [
                        {'range': [0,  30], 'color': '#d4edda'},
                        {'range': [30, 70], 'color': '#fff3cd'},
                        {'range': [70,100], 'color': '#f8d7da'},
                    ],
                    'threshold': {'line': {'color': 'red', 'width': 4}, 'thickness': 0.75, 'value': 70}
                }
            ))
            fig_gauge.update_layout(height=350)
            st.plotly_chart(fig_gauge, width="stretch")

            # Show sub-component breakdown if available
            if '_screen_component' in profile:
                with st.expander("📐 Risk Score Breakdown (How it was calculated)"):
                    st.markdown(f"""
| Component | Value | Weight |
|-----------|-------|--------|
| 📱 Screen Time (log-scaled) | {profile.get('_screen_component', 0):.1f}/100 | 40% |
| 😰 Social / FOMO | {profile.get('_fomo_component', 0):.1f}/100 | 20% |
| 🎯 Binge Sessions | {profile.get('_binge_component', 0):.1f}/100 | 20% |
| 😴 Sleep Disruption | {profile.get('_sleep_component', 0):.1f}/100 | 10% |
| 💼 Productivity Penalty | {profile.get('_prod_component', 0):.1f}/100 | 10% |

*Inputs exponentially recency-weighted (half-life = 3 days). Final score sigmoid-normalized.*
""")

        with c2_b:
            st.markdown("<br><br>", unsafe_allow_html=True)
            day_label = f"{days_filter}-Day" if days_filter > 1 else "1-Day"
            st.write(f"**Key Extracted Phone Metrics ({day_label} Weighted):**")
            st.metric("📅 Avg Screen Time", f"{profile.get('total_screen_time', 0)} hrs")
            st.metric("🔔 Est. Daily Notifications", profile['notifications_per_day'])
            st.metric("😰 FOMO Score", f"{profile['fomo_score']}/10")
            st.metric("😟 Anxiety Correlation", f"{profile['anxiety_score']}/10")
            st.metric("😴 Sleep Hours (Estimated)", f"{profile.get('sleep_hours', 8)} hrs")
            st.metric("💼 Productivity Score", f"{profile.get('productivity_score', 5)}/10")

        # 2. ML Prediction Classification
        st.markdown("---")
        st.subheader("🤖 Section 3: AI Logistics Regression Prediction")

        label, probs = predict_addiction_risk(lr_model_bundle, profile)
        if 'High' in label:
            st.error(f"🔴 **AI Prediction: {label}** | Model Confidence: {probs[1]:.1%}")
        else:
            st.success(f"🟢 **AI Prediction: {label}** | Model Confidence: {probs[0]:.1%}")

        fig_prob = go.Figure(go.Bar(
            x=['Not Addicted', 'Addicted'],
            y=[probs[0], probs[1]],
            marker_color=['#00CC96', '#EF553B']
        ))
        fig_prob.update_layout(title='AI Probability Distribution', height=250, yaxis_range=[0, 1])
        st.plotly_chart(fig_prob, width="stretch")

        # 3. Recommendations
        st.markdown("---")
        st.subheader("💡 Section 4: Smart Detox Recommendations")
        recs = get_recommendations(profile)

        r_col1, r_col2 = st.columns(2)
        with r_col1:
            if recs.get('critical'):
                st.error("🚨 Critical Action Required")
                for r in recs['critical']:
                    st.write(f"- {r}")
                st.write("")
            if recs.get('warnings'):
                st.warning("⚠️ Behavior Warnings")
                for r in recs['warnings']:
                    st.write(f"- {r}")
        with r_col2:
            if recs.get('tips'):
                st.info("💡 Personalized Tips")
                for r in recs['tips']:
                    st.write(f"- {r}")
            if recs.get('detox_plan'):
                st.success("🧘 Digital Detox Plan")
                for r in recs['detox_plan']:
                    st.write(f"- {r}")

        st.markdown("---")
        st.caption(f"Data fetched at {meta['fetched_at']} | Screen: {screen} | Battery: {battery}%")

        if st.button("🔄 Refresh Phone Data", type="primary"):
            if 'phone_df' in st.session_state:
                del st.session_state['phone_df']
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MODULE: SAMSUNG / MANUAL SUPPORT
# ══════════════════════════════════════════════════════════════════════════════

def page_samsung_support(df):
    st.title("🔧 Samsung & Manual Data Support")
    st.markdown("""
    Some devices (especially Samsung) may have restrictions that prevent data fetching via ADB.
    Use this page to provide your usage data manually or via screenshots.
    """)

    tab1, tab2, tab3 = st.tabs([
        "📸 Option 1: Upload Screenshots (OCR)",
        "📝 Option 2: Manual Data Entry",
        "⚙️ Samsung ADB Troubleshooting"
    ])

    with tab3:
        st.subheader("Fixing Samsung ADB Connection Issues")
        st.markdown("""
        Samsung devices have additional security restrictions that often prevent ADB data fetching.
        Follow these steps to enable full data access:
        """)

        with st.expander("Step 1: Enable 'USB Debugging (Security Settings)'", expanded=True):
            st.markdown("""
            On Samsung devices, there's an **additional** setting beyond regular USB Debugging:

            1. Go to **Settings → Developer Options**
            2. Scroll down and find **"USB Debugging (Security Settings)"**
            3. **Enable it** and confirm any prompts
            4. This allows ADB to access app usage data (required for Samsung)
            """)

        with st.expander("Step 2: Disable Battery Optimization for Usage Stats"):
            st.markdown("""
            Samsung's battery optimization can block usage stats collection:

            1. Go to **Settings → Battery and Device Care → Battery**
            2. Tap **Background Usage Limits**
            3. Find **"Android System"** or **"Usage Stats"** service
            4. Set it to **"Not Optimized"**
            5. Alternatively, go to **Settings → Apps → Show System Apps**
            6. Find **"Usage Stats"** or **"Usage Data Access"**
            7. Set **Battery → Unrestricted**
            """)

        with st.expander("Step 3: Grant Usage Stats Permission via ADB"):
            st.markdown("""
            If the above doesn't work, try granting permissions manually via ADB:

            ```bash
            # Grant usage stats permission to the shell
            adb shell pm grant com.android.shell android.permission.PACKAGE_USAGE_STATS

            # For Samsung devices, also try:
            adb shell settings put global restricted_device_id null
            ```

            Run these commands in Command Prompt or PowerShell with your phone connected.
            """)

        with st.expander("Step 4: Check for Knox or MDM Restrictions"):
            st.markdown("""
            Samsung Knox or corporate MDM policies may block ADB access:

            1. Go to **Settings → About Phone → Software Information**
            2. Look for **"Knox Version"** - if present, Knox may be restricting access
            3. If your device is managed by an organization (work profile), ADB may be disabled
            4. For corporate devices, contact your IT administrator
            """)

        st.info("""
        **Still not working?** After completing these steps:
        1. Unplug and re-plug your USB cable
        2. Wait 2-3 minutes for usage data to accumulate
        3. Try fetching data again from the Mobile Device Intelligence page
        4. Use the **🔍 Run Diagnostics** button if available to see detailed error information
        """)

    with tab1:
        st.subheader("Extract Data from Screenshots")
        st.info("Open **Settings > Digital Wellbeing** on your phone and take a screenshot of the main usage dashboard.")
        
        uploaded_file = st.file_uploader("Upload Digital Wellbeing Screenshot", type=["png", "jpg", "jpeg"])
        
        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Screenshot", width="stretch")
            
            if st.button("🔍 Extract Data with AI (OCR)", type="primary"):
                with st.spinner("Processing image..."):
                    results, err = extract_data_from_image(image)
                    
                    if err:
                        st.error(err)
                        if "Tesseract" in err:
                            st.markdown("""
                            > **Tip:** If Tesseract is not installed, you can still use **Option 2: Manual Data Entry** to provide the numbers yourself.
                            """)
                    else:
                        st.success("✅ Data extracted successfully!")
                        
                        # Show extracted data in columns
                        c1, c2, c3 = st.columns(3)
                        ext_st = c1.number_input("Extracted Screen Time (hrs)", value=float(results['total_screen_time']), step=0.1)
                        ext_notif = c2.number_input("Extracted Notifications", value=int(results['notifications_per_day']))
                        ext_pickups = c3.number_input("Extracted Unlocks (as pickups/hr)", value=float(results['phone_pickups_per_hour']), step=0.1)
                        
                        if st.button("🚀 Sync to Analysis Dashboard", key="sync_ocr"):
                            profile = build_profile_from_ocr({
                                'total_screen_time': ext_st,
                                'notifications_per_day': ext_notif,
                                'phone_pickups_per_hour': ext_pickups
                            })
                            st.session_state['phone_profile'] = profile
                            st.session_state['sidebar_data_mode'] = "Simulated Mobile"
                            st.success("Analysis updated! Navigate to 'Overview' or 'ML Predictions' to see your results.")

    with tab2:
        st.subheader("Manual Data Entry Form")
        st.markdown("Fill in the values from your phone's Digital Wellbeing dashboard.")
        
        with st.form("manual_entry_form"):
            m1, m2 = st.columns(2)
            with m1:
                m_st = st.slider("Total Screen Time (hrs)", 0.0, 24.0, 8.0, 0.5)
                m_nu = st.slider("Nighttime Usage (hrs)", 0.0, 8.0, 1.5, 0.1)
                m_notif = st.number_input("Notifications per Day", 0, 1000, 150)
                m_binge = st.slider("Binge Sessions / Week", 0, 50, 5)
            with m2:
                m_fomo = st.slider("FOMO Score (1-10)", 1, 10, 5)
                m_anx = st.slider("Anxiety Score (1-10)", 1, 10, 5)
                m_pickup = st.slider("Phone Pickups / Hour", 0, 100, 20)
                m_sleep = st.slider("Sleep Hours", 0.0, 15.0, 7.0, 0.5)
            
            submitted = st.form_submit_button("Update AI Profile", type="primary", width="stretch")
            
            if submitted:
                profile = {
                    'total_screen_time': m_st,
                    'nighttime_usage': m_nu,
                    'notifications_per_day': m_notif,
                    'binge_sessions_per_week': m_binge,
                    'fomo_score': m_fomo,
                    'anxiety_score': m_anx,
                    'phone_pickups_per_hour': m_pickup,
                    'sleep_hours': m_sleep,
                    'productivity_score': 5.0, # Default
                    'sleep_disruption_score': 5.0 # Default
                }
                st.session_state['phone_profile'] = profile
                st.session_state['sidebar_data_mode'] = "Simulated Mobile"
                st.success("✅ Profile updated manually! All dashboard predictions will now use this data.")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if not st.session_state.get('logged_in'):
        show_login_page()
        return

    user_info = st.session_state['user_info']
    page, data_mode = show_sidebar(user_info)
    st.session_state['sidebar_data_mode'] = data_mode

    # ── Always load background dataset so ML Models can train ────────────
    if 'df' not in st.session_state or st.session_state.get('data_mode') != 'dataset':
        with st.spinner("Loading background dataset for ML Models..."):
            st.session_state['df'] = get_data()
            st.session_state['data_mode'] = 'dataset'

    df = st.session_state.get('df')

    # ── Page routing ──────────────────────────────────────────────────
    # If the user is in "Simulated Mobile" mode, the Overview page acts as the Phone Connection hub
    if "Simulated Mobile" in data_mode and page == "Overview":
        st.info("📱 **Phone Mode Active** — You are viewing real-time device data. Navigate to other tabs to see your personalized ML analysis.")
        page_mobile_connect()
        return

    if df is None:
        st.error("No background data loaded. Please check the dataset.")
        return

    # Regular routing applies to everything else
    if "Overview" in page:
        page_overview(df)
    elif "Advanced Dashboard" in page:
        page_advanced_dashboard(df)
    elif "Behavior Intelligence" in page:
        page_behavior_intelligence(df)
    elif "ML Predictions" in page:
        page_ml_predictions(df)
    elif "Risk Scoring" in page:
        page_risk_scoring(df)
    elif "Recommendation" in page:
        page_recommendations(df)
    elif "Samsung Support" in page:
        page_samsung_support(df)
    elif "Settings" in page:
        page_settings(df, user_info)
    elif "Chatbot" in page:
        page_chatbot()
    elif "About" in page:
        page_about()
    elif "Admin" in page:
        if user_info['role'] == 'Admin':
            page_admin(df)
        else:
            st.error("Access denied.")

if __name__ == "__main__":
    main()
