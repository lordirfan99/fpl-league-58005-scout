#!/bin/bash
# run_gw_scout.sh — Shell wrapper for cron execution
# Called by cron job after each GW finishes
# Fetches data for both leagues (58005 + 131997) and generates reports
# Passes GW number as argument or auto-detects

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
cd "$REPO_DIR" || exit 1

# Git-bash (MSYS) mangles /c/... paths when passing them to native Windows Python.
# Convert to a native Windows path so "python3 <script>" resolves correctly.
if command -v cygpath >/dev/null 2>&1; then
    SCRIPT_DIR_WIN="$(cygpath -w "$SCRIPT_DIR")"
else
    SCRIPT_DIR_WIN="$SCRIPT_DIR"
fi

# Check if we're in the right place
if [ ! -d "scripts" ] || [ ! -d "data" ]; then
    echo "ERROR: Not in fpl-league-58005-scout directory"
    exit 1
fi

# Determine GW from argument or latest event
GW="${1:-}"
if [ -z "$GW" ]; then
    GW=$(python3 -c "
import urllib.request, json
headers = {'User-Agent': 'Mozilla/5.0'}
req = urllib.request.Request('https://fantasy.premierleague.com/api/bootstrap-static/', headers=headers)
data = json.loads(urllib.request.urlopen(req).read().decode())
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
echo "Leagues: 58005 + 131997"
echo "Started: $(date -u)"

# Step 1: Fetch data for both leagues (deduplicated)
echo "--- Fetching data ---"
python3 "$SCRIPT_DIR_WIN/fetch_gw_data.py" --gw "$GW" --max 3000 --league 58005 131997
FETCH_EXIT=$?
if [ $FETCH_EXIT -ne 0 ]; then
    echo "ERROR: Fetch failed (exit $FETCH_EXIT)"
    exit 1
fi

# Step 2: Generate reports for each league
echo "--- Generating reports for League 58005 ---"
python3 "$SCRIPT_DIR_WIN/generate_analysis.py" --gw "$GW" --league 58005
ANALYSIS_EXIT_1=$?
if [ $ANALYSIS_EXIT_1 -ne 0 ]; then
    echo "ERROR: Analysis for league 58005 failed (exit $ANALYSIS_EXIT_1)"
fi

echo "--- Generating reports for League 131997 ---"
python3 "$SCRIPT_DIR_WIN/generate_analysis.py" --gw "$GW" --league 131997
ANALYSIS_EXIT_2=$?
if [ $ANALYSIS_EXIT_2 -ne 0 ]; then
    echo "ERROR: Analysis for league 131997 failed (exit $ANALYSIS_EXIT_2)"
fi

echo "=== GW${GW} Pipeline Complete ==="
echo "Finished: $(date -u)"
echo "Data: data/gw${GW}_league{58005,131997}_data.json"
echo "Reports: reports/GW${GW}/"

# Step 3: Commit and push to GitHub
echo "--- Committing to GitHub ---"
git add -A
git commit -m "chore: GW${GW} scout data + analysis" || echo "Nothing new to commit"
git push origin master
PUSH_EXIT=$?
if [ $PUSH_EXIT -eq 0 ]; then
    echo "✅ Pushed to GitHub — Netlify auto-deploy should trigger"
else
    echo "⚠️ Push failed (exit $PUSH_EXIT). Check git remote config."
fi

echo "=== GW${GW} Pipeline Fully Complete ==="