# FPL Season Journal

The journal is the durable memory for decisions, outcomes and research evidence.

## Weekly lifecycle

1. `.github/workflows/capture-journal.yml` runs hourly, but writes only during the final
   six hours before the next deadline.
2. A valid production decision, V5 catalogue and FPL baseline are written once to
   `gs://$FPL_JOURNAL_BUCKET/journal-raw/<season>/gwNN/predeadline.json`.
3. The existing completed-GW workflow waits for `finished=true` and `data_checked=true`.
4. `scripts/build_gameweek_journal.py` joins the deadline bundle, official live results,
   personal-team snapshot and both league reports.
5. Compact public JSON/CSV files are committed under `data/journal/<season>/`.
6. Transfer decisions receive reproducible 4- and 6-GW follow-up evaluations when those
   result windows close.
7. Cloud Run serves read-only journal APIs and Netlify renders the timeline.

The deadline file is immutable. Missing evidence is reported as a quality issue and is
never replaced with invented values.

## Telegram guided reflection contract

The hardened Telegram bot lives on the Autopilot VM and is not stored in this repository.
Its post-GW handler should call `scripts/journal_notes.py` once for each answer:

```text
worked  -> What worked this gameweek?
failed  -> What failed or surprised you?
change  -> What will you change next week?
public  -> Optional public lesson
```

Example adapter call:

```bash
python scripts/journal_notes.py --gw 2 --user-id "$TELEGRAM_USER_ID" \
  --field worked --text "Rolled the transfer and preserved flexibility."
```

All answers are private. Only `--field public --publish-public` writes a separate publishable
lesson. The public API never reads the private GCS prefix.

## Research archive

Public compact exports:

- `gameweeks.csv` — one decision/outcome row per GW;
- `players.csv` — the personal 15-player squad outcome per GW;
- `manifest.json` — schema and coverage metadata;
- `README.md` — portable archive explanation.

Full player/model evidence remains in GCS. To start a new season, change only
`data/journal/config.json`; old season directories remain readable.

## Recovery and verification

Run a deterministic backfill:

```bash
python scripts/build_gameweek_journal.py --gw 1
```

Verify the archive object:

```bash
gcloud storage ls "gs://$FPL_JOURNAL_BUCKET/journal-raw/2026-27/gw02/predeadline.json"
```

Public endpoints:

```text
GET /v1/journal?season=2026-27
GET /v1/journal/2026-27/gw/1
GET /v1/journal/2026-27/export?filename=gameweeks.csv
```
