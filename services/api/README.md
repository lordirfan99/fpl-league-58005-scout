# Fantasy Scout API

Versioned FastAPI read service for the dashboard. It currently reads the collector's JSON snapshots through a repository adapter; replacing that adapter with Firestore or Cloud SQL does not change the HTTP contract.

## Run locally

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8080
```

Run those commands from `services/api`.

## Safety boundary

The service intentionally exposes no transfer or captain write endpoints. Telegram approvals remain disabled until a stable HTTPS webhook, a verified Telegram user ID, and a webhook secret are configured.
