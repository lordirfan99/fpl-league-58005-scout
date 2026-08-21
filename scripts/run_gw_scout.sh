#!/bin/bash
# run_gw_scout.sh — Shell wrapper for cron execution
# Called by cron job after each GW finishes
# Passes GW number as argument or auto-detects

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
cd "$REPO_DIR" || exit 1

# Check if we're in the right place
if [ ! -d "scripts" ] || [ ! -d "data" ]; then
    echo "ERROR: Not in fpl-league-58005-scout directory"
    exit 1
fi

# Determine GW from argument or latest event
GW="${1:-}"
if [ -z "$GW" ]; then
    GW=$(python3 -c "
import urllib.request, json, time
headers = {'User-Agent': 'Mozilla/5.0'}
req = urllib.request.Request('https://fantasy.premierleague.com/api/bootstrap-static/', headers=headers)
data = json.loads(urllib.request.urlopen(req).read().decode())
# Find the latest finished GW
for e in reversed(data['events']):
    if e.get('finished'):
        print(e['id'])
        break
")
fi

if [ -z "$GW" ] || [ "$GW" = "0" ]; then
    echo "ERROR: Could not determine GW"
    exit 1
fi

echo "=== GW${GW} Scout Pipeline ==="
echo "Started: $(date -u)"

# Step 1: Fetch data
python3 "$SCRIPT_DIR/fetch_gw_data.py" --gw "$GW" --max 686
FETCH_EXIT=$?
if [ $FETCH_EXIT -ne 0 ]; then
    echo "ERROR: Fetch failed (exit $FETCH_EXIT)"
    exit 1
fi

# Step 2: Generate reports
python3 "$SCRIPT_DIR/generate_analysis.py" --gw "$GW"
ANALYSIS_EXIT=$?
if [ $ANALYSIS_EXIT -ne 0 ]; then
    echo "ERROR: Analysis failed (exit $ANALYSIS_EXIT)"
    exit 1
fi

echo "=== GW${GW} Pipeline Complete ==="
echo "Finished: $(date -u)"
echo "Reports: reports/GW${GW}/"
echo "Data: data/gw${GW}_data.json"