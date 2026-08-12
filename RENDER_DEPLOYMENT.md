# Render deployment

This project is a Flask web service and must be deployed as a **Web Service**, not a Static Site.

Recommended Render settings:
- Runtime: Python 3
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`

The ML artifacts in `models/` must remain in the repository.
The project pins scikit-learn to 1.9.0 because the serialized model was created with that version.

Note: Render's free service filesystem is ephemeral, so files written to `data/user_tasks.json`
and `data/focus_sessions.json` can reset after a restart/redeploy. This does not prevent the ML
prediction service from working.
