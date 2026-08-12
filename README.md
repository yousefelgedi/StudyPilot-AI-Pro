# 🎓 StudyPilot AI Pro — Intelligent Student Study & Risk Optimizer

> **Competition Presentation & Technical Documentation**  
> An end-to-end Machine Learning ecosystem, Explainable AI (XAI) engine, and intelligent study scheduling web platform designed to eliminate academic procrastination, prevent burnout, and optimize student performance.

---

## 🌟 Key Features & Innovations

1. **Advanced Supervised ML Engine**:
   - Uses domain feature engineering (`workload_density`, `weekly_capacity_usage`, `time_pressure_index`, `past_failure_risk`).
   - Benchmarks Gradient Boosting, Random Forest, and Extra Trees models using **Stratified 5-Fold Cross Validation**.
   - Achieves **0.989 ROC-AUC score** and **96.7% prediction accuracy**.

2. **Explainable AI (XAI) Feature Attribution**:
   - Provides real-time SHAP-style breakdown showing *why* a task is at risk (e.g., `+30% risk from imminent deadline`, `+18% risk from high difficulty`).
   - Live interactive risk preview in task creation modal.

3. **AI Smart Auto-Scheduler**:
   - Multi-attribute utility decision ranking combining ML delay risk (40%), deadline decay curve (25%), cognitive difficulty (20%), and user priority (15%).
   - Automatically generates cognitive load-balanced 3-day study calendar blocks (Morning, Afternoon, Evening).

4. **Burnout Protection Telemetry**:
   - Continuously monitors workload density and task backlog to calculate a live **Burnout Risk Index (0–100%)**.

5. **Focus & Energy Studio**:
   - Integrated Pomodoro focus timer with presets (25m, 50m, 5m, 15m).
   - Built-in **Web Audio API Ambient Sound Generator** (White Noise, Rainfall, Ocean Waves).
   - Real-time telemetry tracking daily and total focus time.

---

## 🏗 System Architecture

```
StudyPilot_AI_Pro/
├── app.py                      # Flask REST API server backend
├── train_model.py              # ML dataset generator & model training pipeline
├── requirements.txt            # Python environment dependencies
├── README.md                   # Competition documentation
├── data/
│   ├── study_tasks.csv         # 1,500 sample task training dataset
│   ├── user_tasks.json         # Active user task store
│   └── focus_sessions.json     # Focus studio activity logs
├── models/
│   ├── task_risk_model.joblib  # Production ensemble ML model weights
│   ├── scaler.joblib           # Feature standardizer scaler
│   ├── features.joblib         # Feature column names
│   └── model_metadata.json     # Model validation metrics & benchmarks
├── notebooks/
│   └── StudyPilot_ML_Pipeline.ipynb # Standalone Jupyter Notebook for judges
├── static/
│   ├── css/style.css           # Modern Dark Glassmorphism CSS design system
│   └── js/app.js               # ES6 Modular Frontend Application logic
└── templates/
    └── index.html              # HTML5 Web Application interface
```

---

## 🚀 Quick Start & Deployment

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Train Model & Export Artifacts
```bash
python train_model.py
```

### 3. Run Web Application
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:5000/`.

---

## 📊 Machine Learning Model Benchmarks

| Algorithm | ROC-AUC | Accuracy | F1-Score | Precision | Recall |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Random Forest** (Selected) | **0.9893** | **0.9673** | **0.8448** | 0.8841 | 0.8095 |
| **Extra Trees** | 0.9890 | 0.9613 | 0.7905 | 0.8752 | 0.7225 |
| **Gradient Boosting** | 0.9880 | 0.9673 | 0.8481 | 0.8805 | 0.8182 |

---

## 🏆 Presentation Highlights for Competition Judges

- **Jupyter Notebook Presentation**: Open `notebooks/StudyPilot_ML_Pipeline.ipynb` to view step-by-step model building, mathematical formulas, cross-validation charts, and export steps.
- **Live XAI Preview**: Slide task sliders in the "Create Task" modal to demonstrate real-time AI risk inference and feature factor attribution.
- **Ambient Focus Studio**: Test the built-in ambient sound synthesis directly in the Focus Studio tab.
