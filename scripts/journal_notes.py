"""Private guided-review adapter for the external Telegram bot runtime."""
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path

PROMPTS = {"worked": "What worked this gameweek?", "failed": "What failed or surprised you?", "change": "What will you change next week?", "public": "Optional public lesson"}
ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--season"); parser.add_argument("--gw", type=int, required=True)
    parser.add_argument("--user-id", required=True); parser.add_argument("--field", choices=PROMPTS, required=True); parser.add_argument("--text", required=True); parser.add_argument("--publish-public", action="store_true")
    args = parser.parse_args(); args.season = args.season or json.loads((ROOT / "data" / "journal" / "config.json").read_text(encoding="utf-8"))["active_season"]; root = Path(os.getenv("FPL_JOURNAL_PRIVATE_DIR", "/var/lib/fpl-autopilot/journal-private"))
    path = root / args.season / f"gw{args.gw:02d}" / f"{args.user_id}.json"; path.parent.mkdir(parents=True, exist_ok=True)
    record = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"schema_version": 1, "season": args.season, "gameweek": args.gw, "user_id": args.user_id, "answers": {}}
    record["answers"][args.field] = args.text.strip(); record["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    bucket_name = os.getenv("FPL_JOURNAL_BUCKET") or os.getenv("FPL_SNAPSHOT_BUCKET")
    if bucket_name:
        from google.cloud import storage
        bucket = storage.Client().bucket(bucket_name)
        bucket.blob(f"journal-private/{args.season}/gw{args.gw:02d}/{args.user_id}.json").upload_from_string(
            json.dumps(record, separators=(",", ":")), content_type="application/json")
        if args.publish_public:
            if args.field != "public": raise SystemExit("Only the explicit public lesson may be published")
            bucket.blob(f"journal-public/{args.season}/gw{args.gw:02d}/lesson.json").upload_from_string(
                json.dumps({"public_lesson": args.text.strip(), "published_at": record["updated_at"]}, separators=(",", ":")), content_type="application/json")
    print(json.dumps({"saved": True, "private": True, "next_prompt": next((value for key, value in PROMPTS.items() if key not in record["answers"]), None)}))

if __name__ == "__main__": main()
