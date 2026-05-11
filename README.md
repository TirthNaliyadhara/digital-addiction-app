# 🧠 Adaptive Intelligence System for Digital Addiction Detection

## Enterprise-Level Streamlit Application

---

## 📁 Project Structure

```
digital_addiction_app/
├── app.py                        # Main Streamlit application
├── requirements.txt              # Python dependencies
├── adb_integration.py            # Android ADB + simulation module
├── auth/
│   ├── __init__.py
│   └── auth.py                   # Login, signup, session, SQLite
├── data/
│   └── users.db                  # Auto-created SQLite database
├── dataset/
│   └── sample_data.csv           # Your 20,000-record dataset
├── ml_models/
│   ├── __init__.py
│   └── models.py                 # LogReg, LR, MLR, Random Forest
├── behavior_analysis/
│   ├── __init__.py
│   └── analyzer.py               # Behavioral metrics, anomaly detection
└── utils/
    ├── __init__.py
    ├── data_loader.py             # CSV parsing + feature engineering
    └── recommendations.py        # Personalized recommendation engine
```

---

## 🚀 How to Run

### 1. Clone and Setup
```bash
git clone https://github.com/TirthNaliyadhara/digital-addiction-app.git
cd digital-addiction-app
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch the App
```bash
streamlit run app.py
```

### 4. Open Browser
Visit: `http://localhost:8501`

---

## 🔐 Demo Login Credentials

| Role   | Username | Password   |
|--------|----------|------------|
| Admin  | admin    | admin123   |
| Parent | parent   | parent123  |
| User   | Sign up  | Any (≥6 chars) |

---

## 📊 Features

### 1. Authentication System
- Signup / Login / Logout
- SHA-256 password hashing
- Role-based access: User, Parent, Admin
- SQLite persistent storage

### 2. Overview Dashboard
- KPI cards (screen time, risk score, sleep, notifications)
- Risk category pie chart
- Platform usage bar chart
- Screen time histogram
- Notification density analysis

### 3. Advanced Dashboard
- Monthly screen time trend (line chart)
- Day vs Night usage comparison
- Platform × Risk heatmap
- Correlation matrix
- Occupation-wise breakdown
- Filterable by risk, occupation, gender

### 4. Behavior Intelligence
- Focus Score, Distraction Index, Digital Dependency Score
- Addiction pattern detection (heavy users, dopamine loops, FOMO)
- Anomaly detection: Isolation Forest + Z-Score
- Night usage behavior analysis
- Notification dependency charts
- Auto-generated text insights

### 5. ML Predictions (3 Tabs)
- **Tab 1**: Logistic Regression — Addiction Risk (binary)
  - Confusion matrix, accuracy, feature importance
  - Live prediction form
- **Tab 2**: Linear + Multiple Linear Regression — Screen Time Forecast
  - Actual vs Predicted charts, MAE, RMSE, residuals
- **Tab 3**: Random Forest — Behavior Pattern Classification
  - Productive / Neutral / Addictive
  - Feature importance, confidence chart

### 6. Risk Scoring Engine
- Custom formula: 40% screen + 20% night + 20% notifications + 20% sessions
- Plotly gauge chart
- Score breakdown bar chart
- Population distribution comparison

### 7. Recommendation Engine
- Critical alerts, warnings, personalized tips
- Digital detox plan
- 7-day wellness plan

### 8. Admin Panel (Admin role only)
- View all registered users
- Dataset statistics

### 9. Settings / Profile
- Profile viewer
- CSV upload for custom datasets
- ADB device connection or simulated mobile data

---

## 📱 Mobile Integration (ADB)

### Real Mode
```bash
# Connect Android device via USB with USB Debugging enabled
adb devices
# App will auto-detect and offer to fetch real data
```

### Simulation Mode
- Click "Generate Simulated Mobile Data" in Settings → Mobile Integration
- Generates 200 realistic app usage records

---

## 🧪 Dataset Schema

The dataset must contain (row 3 = headers):
- Demographics: Age, Gender, Occupation, Education Level
- Screen time: Social Media, Gaming, Streaming, Work/Study, Browsing, Total
- Behavioral: Daily App Opens, Avg Session Duration, Nighttime Usage
- Psychological: FOMO Score, Anxiety Score, Sleep Disruption Score
- Impact: Productivity Score, Sleep Hours, Physical Activity
- Labels: Addiction Risk Score, Risk Category, Addiction Label

---

## 🛠️ Tech Stack

| Component       | Technology              |
|-----------------|-------------------------|
| Frontend UI     | Streamlit (default theme) |
| Visualizations  | Plotly                  |
| ML Models       | Scikit-learn            |
| Data Processing | Pandas, NumPy           |
| Auth / DB       | SQLite + SHA-256        |
| Mobile Data     | ADB / Simulation        |

---

## ⚙️ System Requirements

- Python 3.8+
- 4GB RAM minimum (8GB recommended for 20K records)
- Any OS: Windows, macOS, Linux

---

## 🔧 Troubleshooting

### Common Issues

1. **Module Not Found Errors**
   ```bash
   pip install -r requirements.txt
   ```

2. **ADB Connection Issues**
   - Ensure USB Debugging is enabled on Android device
   - Install Android SDK Platform Tools
   - Check device connection with `adb devices`

3. **Database Issues**
   - The SQLite database is auto-created on first run
   - Ensure `data/` directory exists and is writable

4. **Port Already in Use**
   ```bash
   streamlit run app.py --server.port 8502
   ```

### Dependencies Installation

If you encounter issues with package installation, try:
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 📞 Support

For support, please open an issue in the GitHub repository or contact the project maintainer.