import json
import numpy as np
import pandas as pd
from pathlib import Path
import joblib
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, ExtraTreesClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

def generate_expanded_dataset(n_samples=1200, seed=42):
    np.random.seed(seed)
    subjects = ["Computer Science", "Math", "Physics", "Chemistry", "Biology", "English"]

    subject_choices = np.random.choice(subjects, size=n_samples)
    days_left = np.random.randint(1, 31, size=n_samples)
    estimated_hours = np.round(np.random.uniform(0.5, 10.0, size=n_samples), 1)
    difficulty = np.random.randint(1, 6, size=n_samples)
    priority = np.random.randint(1, 6, size=n_samples)
    past_completion_percent = np.round(np.random.uniform(25.0, 100.0, size=n_samples), 1)
    study_hours_per_week = np.round(np.random.uniform(2.0, 25.0, size=n_samples), 1)
    tasks_pending = np.random.randint(0, 10, size=n_samples)

    # Calculate realistic delay probability logit based on domain factors
    workload_density = estimated_hours / days_left
    capacity_ratio = estimated_hours / (study_hours_per_week / 7.0 + 1e-5)
    time_pressure = (tasks_pending + 1) * workload_density

    logit = (
        -2.5
        + 1.8 * workload_density
        + 0.8 * (difficulty / 5.0)
        + 0.6 * (priority / 5.0)
        - 0.035 * past_completion_percent
        + 0.25 * tasks_pending
        - 0.05 * study_hours_per_week
        + 0.5 * (days_left <= 3).astype(float)
        + np.random.normal(0, 0.4, size=n_samples)
    )

    prob = 1.0 / (1.0 + np.exp(-logit))
    delayed = (prob > 0.50).astype(int)
    status = np.where(delayed == 1, "At Risk", "On Time")

    df = pd.DataFrame({
        "subject": subject_choices,
        "days_left": days_left,
        "estimated_hours": estimated_hours,
        "difficulty": difficulty,
        "priority": priority,
        "past_completion_percent": past_completion_percent,
        "study_hours_per_week": study_hours_per_week,
        "tasks_pending": tasks_pending,
        "delayed": delayed,
        "status": status
    })
    return df

def engineer_features(df):
    data = df.copy()
    data["workload_density"] = data["estimated_hours"] / data["days_left"]
    data["weekly_capacity_usage"] = (data["estimated_hours"] / (data["study_hours_per_week"] + 1e-5)) * 100.0
    data["time_pressure_index"] = (data["tasks_pending"] + 1) * data["workload_density"]
    data["past_failure_risk"] = 100.0 - data["past_completion_percent"]
    return data

FEATURE_COLUMNS = [
    "days_left",
    "estimated_hours",
    "difficulty",
    "priority",
    "past_completion_percent",
    "study_hours_per_week",
    "tasks_pending",
    "workload_density",
    "weekly_capacity_usage",
    "time_pressure_index",
    "past_failure_risk"
]

def train_and_evaluate():
    print("Generating dataset...")
    df = generate_expanded_dataset(n_samples=1500)
    df.to_csv(DATA_DIR / "study_tasks.csv", index=False)

    df_feats = engineer_features(df)
    X = df_feats[FEATURE_COLUMNS]
    y = df_feats["delayed"]

    scaler = StandardScaler()
    X_scaled = pd.DataFrame(scaler.fit_transform(X), columns=FEATURE_COLUMNS)

    # Models comparison
    models = {
        "GradientBoosting": GradientBoostingClassifier(n_estimators=150, learning_rate=0.08, max_depth=4, random_state=42),
        "RandomForest": RandomForestClassifier(n_estimators=150, max_depth=6, random_state=42),
        "ExtraTrees": ExtraTreesClassifier(n_estimators=150, max_depth=6, random_state=42)
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    best_name = None
    best_score = -1
    best_model = None
    model_benchmarks = {}

    for name, model in models.items():
        scoring = ["accuracy", "precision", "recall", "f1", "roc_auc"]
        scores = cross_validate(model, X_scaled, y, cv=cv, scoring=scoring)

        acc = float(np.mean(scores["test_accuracy"]))
        prec = float(np.mean(scores["test_precision"]))
        rec = float(np.mean(scores["test_recall"]))
        f1 = float(np.mean(scores["test_f1"]))
        auc = float(np.mean(scores["test_roc_auc"]))

        model_benchmarks[name] = {
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(auc, 4)
        }

        print(f"[{name}] Accuracy: {acc:.4f} | ROC-AUC: {auc:.4f} | F1: {f1:.4f}")
        if auc > best_score:
            best_score = auc
            best_name = name
            best_model = model

    # Fit best model on all data
    best_model.fit(X_scaled, y)
    y_pred = best_model.predict(X_scaled)
    y_prob = best_model.predict_proba(X_scaled)[:, 1]

    cm = confusion_matrix(y, y_pred).tolist()
    importances = best_model.feature_importances_

    feature_importance_list = [
        {"feature": col, "importance": round(float(imp), 4)}
        for col, imp in sorted(zip(FEATURE_COLUMNS, importances), key=lambda x: x[1], reverse=True)
    ]

    # Export artifacts
    joblib.dump(best_model, MODELS_DIR / "task_risk_model.joblib")
    joblib.dump(scaler, MODELS_DIR / "scaler.joblib")
    joblib.dump(FEATURE_COLUMNS, MODELS_DIR / "features.joblib")

    metadata = {
        "best_model_name": best_name,
        "overall_roc_auc": round(float(roc_auc_score(y, y_prob)), 4),
        "overall_accuracy": round(float(accuracy_score(y, y_pred)), 4),
        "overall_f1": round(float(f1_score(y, y_pred)), 4),
        "benchmarks": model_benchmarks,
        "feature_importances": feature_importance_list,
        "confusion_matrix": cm,
        "dataset_size": len(df),
        "at_risk_ratio": round(float(y.mean()), 4)
    }

    with open(MODELS_DIR / "model_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # Initial sample user tasks JSON
    initial_user_tasks = [
        {
            "id": 2026081100001,
            "title": "Quantum Mechanics Problem Set 4",
            "subject": "Physics",
            "days_left": 3,
            "estimated_hours": 6.5,
            "difficulty": 5,
            "priority": 5,
            "past_completion": 78.0,
            "study_hours": 12.0,
            "tasks_pending": 4,
            "completed": False,
            "created_at": "2026-08-11"
        },
        {
            "id": 2026081100002,
            "title": "Data Structures & Algorithms Dynamic Programming Project",
            "subject": "Computer Science",
            "days_left": 5,
            "estimated_hours": 8.0,
            "difficulty": 4,
            "priority": 4,
            "past_completion": 92.0,
            "study_hours": 15.0,
            "tasks_pending": 2,
            "completed": False,
            "created_at": "2026-08-11"
        },
        {
            "id": 2026081100003,
            "title": "Organic Chemistry Reaction Mechanisms Chapter 8",
            "subject": "Chemistry",
            "days_left": 10,
            "estimated_hours": 3.0,
            "difficulty": 3,
            "priority": 2,
            "past_completion": 85.0,
            "study_hours": 10.0,
            "tasks_pending": 1,
            "completed": False,
            "created_at": "2026-08-11"
        },
        {
            "id": 2026081100004,
            "title": "Linear Algebra Matrix Decomposition Review",
            "subject": "Math",
            "days_left": 2,
            "estimated_hours": 4.5,
            "difficulty": 4,
            "priority": 5,
            "past_completion": 65.0,
            "study_hours": 8.0,
            "tasks_pending": 5,
            "completed": False,
            "created_at": "2026-08-11"
        },
        {
            "id": 2026081100005,
            "title": "English Literature Essay on Modernism",
            "subject": "English",
            "days_left": 14,
            "estimated_hours": 2.5,
            "difficulty": 2,
            "priority": 3,
            "past_completion": 95.0,
            "study_hours": 10.0,
            "tasks_pending": 1,
            "completed": True,
            "created_at": "2026-08-10"
        }
    ]

    with open(DATA_DIR / "user_tasks.json", "w", encoding="utf-8") as f:
        json.dump(initial_user_tasks, f, indent=2)

    print("Model training & artifact export completed successfully!")

if __name__ == "__main__":
    train_and_evaluate()
