import json
from pathlib import Path
from datetime import date, datetime
from flask import Flask, render_template, request, jsonify
import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
TASKS_FILE = DATA_DIR / "user_tasks.json"
FOCUS_LOG_FILE = DATA_DIR / "focus_sessions.json"

app = Flask(__name__, template_folder="templates", static_folder="static")

# Load trained model artifacts
try:
    model = joblib.load(MODELS_DIR / "task_risk_model.joblib")
    scaler = joblib.load(MODELS_DIR / "scaler.joblib")
    features = joblib.load(MODELS_DIR / "features.joblib")
    with open(MODELS_DIR / "model_metadata.json", "r", encoding="utf-8") as f:
        metadata = json.load(f)
except Exception as e:
    print(f"Warning: Model load issue ({e}). Run train_model.py first.")
    model = None
    scaler = None
    features = []
    metadata = {}

# Ensure dataset exists
try:
    dataset = pd.read_csv(DATA_DIR / "study_tasks.csv")
except Exception:
    dataset = pd.DataFrame()


def load_tasks():
    if not TASKS_FILE.exists():
        return []
    try:
        return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_tasks(tasks):
    DATA_DIR.mkdir(exist_ok=True)
    TASKS_FILE.write_text(json.dumps(tasks, indent=2), encoding="utf-8")


def load_focus_sessions():
    if not FOCUS_LOG_FILE.exists():
        return []
    try:
        return json.loads(FOCUS_LOG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_focus_sessions(sessions):
    DATA_DIR.mkdir(exist_ok=True)
    FOCUS_LOG_FILE.write_text(json.dumps(sessions, indent=2), encoding="utf-8")


def engineer_row(task):
    days_left = float(task["days_left"])
    estimated_hours = float(task["estimated_hours"])
    difficulty = float(task["difficulty"])
    priority = float(task["priority"])
    past_completion = float(task["past_completion"])
    study_hours = float(task["study_hours"])
    tasks_pending = float(task["tasks_pending"])

    workload_density = estimated_hours / max(1.0, days_left)
    weekly_capacity_usage = (estimated_hours / max(0.5, study_hours)) * 100.0
    time_pressure_index = (tasks_pending + 1.0) * workload_density
    past_failure_risk = 100.0 - past_completion

    return {
        "days_left": days_left,
        "estimated_hours": estimated_hours,
        "difficulty": difficulty,
        "priority": priority,
        "past_completion_percent": past_completion,
        "study_hours_per_week": study_hours,
        "tasks_pending": tasks_pending,
        "workload_density": workload_density,
        "weekly_capacity_usage": weekly_capacity_usage,
        "time_pressure_index": time_pressure_index,
        "past_failure_risk": past_failure_risk,
    }


def validate_task(data):
    required = ["title", "subject", "days_left", "estimated_hours", "difficulty",
                "priority", "past_completion", "study_hours", "tasks_pending"]
    missing = [x for x in required if x not in data or str(data[x]).strip() == ""]
    if missing:
        raise ValueError("Missing field(s): " + ", ".join(missing))

    return {
        "title": str(data["title"]).strip()[:100],
        "subject": str(data["subject"]).strip()[:50],
        "days_left": max(1, min(365, float(data["days_left"]))),
        "estimated_hours": max(0.25, min(100, float(data["estimated_hours"]))),
        "difficulty": max(1, min(5, float(data["difficulty"]))),
        "priority": max(1, min(5, float(data["priority"]))),
        "past_completion": max(0, min(100, float(data["past_completion"]))),
        "study_hours": max(0.5, min(168, float(data["study_hours"]))),
        "tasks_pending": max(0, min(100, float(data["tasks_pending"]))),
    }


def analyze(task):
    row_dict = engineer_row(task)
    if model is None or scaler is None or not features:
        # Fallback estimation if model not trained
        prob = min(0.95, max(0.05, row_dict["workload_density"] * 0.4 + row_dict["difficulty"] * 0.1))
    else:
        df_single = pd.DataFrame([row_dict])[features]
        df_scaled = pd.DataFrame(scaler.transform(df_single), columns=features)
        prob = float(model.predict_proba(df_scaled)[0][1])

    status = "At Risk" if prob >= 0.50 else "Likely On Time"
    risk_level = "High" if prob >= 0.70 else ("Medium" if prob >= 0.40 else "Low")

    # Calculate Explainable AI (XAI) feature contribution breakdown
    shap_contributions = []
    wd = row_dict["workload_density"]
    if wd > 0.8:
        shap_contributions.append({"factor": "High Workload Density", "impact": round(min(40, wd * 25), 1), "type": "negative"})
    if task["days_left"] <= 3:
        shap_contributions.append({"factor": "Imminent Deadline (≤3 days)", "impact": 30.0, "type": "negative"})
    if task["difficulty"] >= 4:
        shap_contributions.append({"factor": "High Cognitive Complexity (Diff ≥ 4)", "impact": 18.5, "type": "negative"})
    if task["tasks_pending"] >= 4:
        shap_contributions.append({"factor": "Task Backlog Accumulation", "impact": 15.0, "type": "negative"})
    if task["past_completion"] >= 85:
        shap_contributions.append({"factor": "Strong Historical Completion Rate", "impact": -20.0, "type": "positive"})
    if task["study_hours"] >= 12:
        shap_contributions.append({"factor": "High Dedicated Weekly Study Capacity", "impact": -15.0, "type": "positive"})

    if not shap_contributions:
        shap_contributions.append({"factor": "Balanced Workload Parameters", "impact": 0.0, "type": "neutral"})

    # Actionable AI recommendations
    recommendations = []
    if task["days_left"] <= 3:
        recommendations.append("⚡ Immediate Priority: Reserve a uninterrupted 60-min session today.")
    if task["estimated_hours"] >= 5:
        recommendations.append("🧩 Chunk Workload: Divide task into 3-4 sub-sessions of 45 minutes.")
    if task["difficulty"] >= 4:
        recommendations.append("🧠 Cognitive Load Warning: Schedule during peak energy hours (morning).")
    if task["tasks_pending"] >= 5:
        recommendations.append("🧹 Queue Cleanup: Finish 2 quick pending tasks before starting this.")
    if prob >= 0.70:
        recommendations.append("🔥 Critical Risk: Allocate priority slot in Smart Auto-Scheduler.")
    if not recommendations:
        recommendations.append("✅ Manageable Task: Add to your weekly study calendar with standard buffer.")

    return {
        "status": status,
        "risk_probability": round(prob * 100.0, 1),
        "risk_level": risk_level,
        "shap_contributions": shap_contributions,
        "recommendations": recommendations,
        "workload_density": round(wd, 2),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/predict", methods=["POST"])
def predict():
    try:
        task = validate_task(request.get_json(force=True))
        result = analyze(task)
        return jsonify(result)
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/tasks", methods=["GET", "POST"])
def tasks():
    if request.method == "GET":
        items = load_tasks()
        for item in items:
            item["analysis"] = analyze(item)
        return jsonify(items)

    try:
        task = validate_task(request.get_json(force=True))
        items = load_tasks()
        existing_ids = [int(x.get("id", 0)) for x in items]
        task["id"] = max(existing_ids, default=int(date.today().strftime("%Y%m%d")) * 100000) + 1
        task["completed"] = False
        task["created_at"] = date.today().isoformat()
        items.append(task)
        save_tasks(items)
        task["analysis"] = analyze(task)
        return jsonify(task), 201
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/tasks/<int:task_id>", methods=["PATCH", "DELETE"])
def task_detail(task_id):
    items = load_tasks()
    index = next((i for i, x in enumerate(items) if x["id"] == task_id), None)
    if index is None:
        return jsonify({"error": "Task not found"}), 404

    if request.method == "DELETE":
        items.pop(index)
    else:
        payload = request.get_json(force=True)
        items[index]["completed"] = bool(payload.get("completed", items[index].get("completed", False)))
    save_tasks(items)
    return jsonify({"ok": True})


@app.route("/api/overview")
def overview():
    items = load_tasks()
    active = [x for x in items if not x.get("completed")]
    analyses = [analyze(x) for x in active]

    risk_count = sum(a["status"] == "At Risk" for a in analyses)
    total_hours = sum(x["estimated_hours"] for x in active)

    # Burnout warning index calculation
    avg_pending = np.mean([x["tasks_pending"] for x in active]) if active else 0
    avg_density = np.mean([a["workload_density"] for a in analyses]) if analyses else 0
    burnout_index = min(100, round((risk_count / max(1, len(active))) * 40 + avg_pending * 4 + avg_density * 25, 1))

    subject_counts = {}
    for x in active:
        subject_counts[x["subject"]] = subject_counts.get(x["subject"], 0) + 1

    return jsonify({
        "total": len(active),
        "at_risk": risk_count,
        "on_time": len(active) - risk_count,
        "hours": round(total_hours, 1),
        "burnout_index": burnout_index,
        "subjects": subject_counts,
    })


@app.route("/api/plan")
def plan():
    items = [x for x in load_tasks() if not x.get("completed")]
    for x in items:
        a = analyze(x)
        x["analysis"] = a

        # Multi-attribute decision score
        # Combination of ML risk (40%), Deadline decay (25%), Cognitive load (20%), Priority (15%)
        risk_score = a["risk_probability"] * 0.40
        deadline_score = max(0, 100.0 - x["days_left"] * 3.2) * 0.25
        difficulty_score = (x["difficulty"] / 5.0) * 100.0 * 0.20
        priority_score = (x["priority"] / 5.0) * 100.0 * 0.15

        x["score"] = round(risk_score + deadline_score + difficulty_score + priority_score, 1)

    items.sort(key=lambda x: x["score"], reverse=True)

    # Generate Smart Calendar Study Schedule Blocks
    schedule_blocks = []
    time_slots = ["Morning Focus (09:00 - 11:00)", "Afternoon Block (14:00 - 16:00)", "Evening Review (19:00 - 20:30)"]
    for i, t in enumerate(items[:6]):
        slot = time_slots[i % len(time_slots)]
        schedule_blocks.append({
            "day": f"Day {(i // len(time_slots)) + 1}",
            "time_slot": slot,
            "task_id": t["id"],
            "title": t["title"],
            "subject": t["subject"],
            "duration_minutes": int(min(120, t["estimated_hours"] * 60)),
            "difficulty": t["difficulty"],
            "risk_level": t["analysis"]["risk_level"]
        })

    return jsonify({
        "ranked_tasks": items,
        "schedule_blocks": schedule_blocks
    })


@app.route("/api/insights")
def insights():
    d = dataset.copy()
    if not d.empty:
        subject_risk = (
            d.groupby("subject")["delayed"].mean().mul(100).round(1).sort_values(ascending=False).to_dict()
        )
        dataset_tasks = len(d)
        dataset_risk = round(float(d["delayed"].mean() * 100.0), 1)
    else:
        subject_risk = {}
        dataset_tasks = 0
        dataset_risk = 0.0

    return jsonify({
        "metadata": metadata,
        "dataset_tasks": dataset_tasks,
        "dataset_risk": dataset_risk,
        "subjects": subject_risk,
    })


@app.route("/api/focus", methods=["GET", "POST"])
def focus():
    if request.method == "POST":
        data = request.get_json(force=True)
        minutes = int(data.get("minutes", 25))
        task_id = data.get("task_id")
        task_title = data.get("task_title", "General Focus Session")

        sessions = load_focus_sessions()
        session = {
            "id": len(sessions) + 1,
            "timestamp": datetime.now().isoformat(),
            "minutes": minutes,
            "task_id": task_id,
            "task_title": task_title
        }
        sessions.append(session)
        save_focus_sessions(sessions)
        return jsonify({"ok": True, "session": session})

    sessions = load_focus_sessions()
    total_minutes = sum(s["minutes"] for s in sessions)
    today_str = date.today().isoformat()
    today_minutes = sum(s["minutes"] for s in sessions if s["timestamp"].startswith(today_str))

    return jsonify({
        "sessions": sessions[-10:],
        "total_minutes": total_minutes,
        "today_minutes": today_minutes,
        "total_sessions": len(sessions)
    })


@app.route("/api/reset_demo", methods=["POST"])
def reset_demo():
    if (ROOT / "train_model.py").exists():
        import train_model
        train_model.train_and_evaluate()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
