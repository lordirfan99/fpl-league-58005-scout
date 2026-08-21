#!/usr/bin/env python3
"""
FPL GW Scout Pipeline — one-command runner for:
1. Fetch GW data (picks, points, transfers, chips) for all league members
2. Generate comprehensive analysis reports
3. Output ready-to-commit reports

Usage: python3 run_gw_pipeline.py [--gw <num>] [--no-fetch] [--compact]

Schedule: Run after each GW deadline (typically Tue/Wed after GW finishes)
          2026-27 schedule: GW1=21 Aug, GW2=28 Aug, GW3=4 Sep...
          Normally run ~2 hours after each GW deadline when data is final.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(REPO_DIR, "data")
REPORTS_DIR = os.path.join(REPO_DIR, "reports")

def detect_latest_gw():
    """Detect the latest finished GW from the FPL API."""
    import urllib.request
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    req = urllib.request.Request('https://fantasy.premierleague.com/api/bootstrap-static/', headers=headers)
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read().decode())
    
    for e in data.get('events', []):
        if e.get('finished'):
            return e['id']
    
    # Fallback: find the most recent event past deadline
    now = time.time()
    last_gw = 0
    for e in data.get('events', []):
        if e.get('deadline_time_epoch', 0) < now and e['id'] > last_gw:
            last_gw = e['id']
    return last_gw or 0

def main():
    parser = argparse.ArgumentParser(description='FPL GW Scout Pipeline')
    parser.add_argument('--gw', type=int, default=0, help='GW to analyze (default: auto-detect)')
    parser.add_argument('--no-fetch', action='store_true', help='Skip fetch, only generate reports')
    parser.add_argument('--compact', action='store_true', help='Use compact data (no individual squad details)')
    parser.add_argument('--max-entries', type=int, default=686, help='Max entries to fetch')
    args = parser.parse_args()
    
    # Detect GW
    gw = args.gw if args.gw else detect_latest_gw()
    if not gw:
        print("❌ Could not determine GW. Use --gw to specify.")
        return 1
    
    print(f"🎯 FPL GW{gw} Scout Pipeline")
    print(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"📁 Repo: {REPO_DIR}")
    print()
    
    # Step 1: Fetch data
    if not args.no_fetch:
        print("=" * 60)
        print(f"📡 STEP 1: Fetching GW{gw} data...")
        print("=" * 60)
        
        fetch_script = os.path.join(SCRIPT_DIR, "fetch_gw_data.py")
        fetch_cmd = [sys.executable, fetch_script, "--gw", str(gw), "--max", str(args.max_entries)]
        
        result = subprocess.run(fetch_cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        if result.returncode != 0:
            print(f"❌ Fetch failed (exit {result.returncode})")
            return 1
        
        # Verify data was created
        data_path = os.path.join(DATA_DIR, f"gw{gw}_data.json")
        if not os.path.exists(data_path):
            print(f"❌ Data file not created: {data_path}")
            return 1
        
        print("✅ Fetch complete!")
    else:
        print("⏭️ Skipping fetch (--no-fetch)")
    
    print()
    
    # Step 2: Generate reports
    print("=" * 60)
    print(f"📊 STEP 2: Generating analysis reports for GW{gw}...")
    print("=" * 60)
    
    analyze_script = os.path.join(SCRIPT_DIR, "generate_analysis.py")
    analyze_cmd = [sys.executable, analyze_script, "--gw", str(gw)]
    if args.compact:
        analyze_cmd.append("--compact")
    
    result = subprocess.run(analyze_cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        print(f"❌ Analysis failed (exit {result.returncode})")
        return 1
    
    print("✅ Analysis complete!")
    print()
    
    # Step 3: Summary
    print("=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    output_dir = os.path.join(REPORTS_DIR, f"GW{gw}")
    
    print(f"📁 Reports generated in: {output_dir}/")
    for f in sorted(os.listdir(output_dir)):
        fpath = os.path.join(output_dir, f)
        size = os.path.getsize(fpath)
        print(f"  📄 {f} ({size:,} bytes)")
    
    print()
    print(f"📁 Data files:")
    for f in [f"gw{gw}_data.json", f"gw{gw}_data_compact.json"]:
        fpath = os.path.join(DATA_DIR, f)
        if os.path.exists(fpath):
            print(f"  📄 {f} ({os.path.getsize(fpath):,} bytes)")
    
    print()
    print("✅ GW{} pipeline complete! Ready to commit.".format(gw))
    
    return 0

if __name__ == '__main__':
    sys.exit(main())