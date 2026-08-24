#!/usr/bin/env python3
"""Full GW1 performance fetcher — ALL league members from pre-season scout data.

Standings API pagination is broken (returns same top-50 each page), so this uses
full_scout_data.json memberships to enumerate every entry in leagues 58005 + 131997,
then fetches history + picks concurrently for real GW1 points/ranks/captains.
"""
import urllib.request
import json
import time
import os
import sys
import threading
from collections import defaultdict

BASE_URL = "https://fantasy.premierleague.com/api"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_DIR, "data")
TRACKED_LEAGUES = [58005, 131997]

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# ---- tiny token-bucket rate limiter: ~10 req/s aggregate ----
_lock = threading.Lock()
_tokens = 10.0
_last_refill = time.monotonic()

def _throttle():
    global _tokens, _last_refill
    while True:
        with _lock:
            now = time.monotonic()
            _tokens = min(10.0, _tokens + (now - _last_refill) * 10.0)
            _last_refill = now
            if _tokens >= 1.0:
                _tokens -= 1.0
                return
        time.sleep(0.02)

def api_get(path, retries=4):
    url = f"{BASE_URL}/{path.lstrip('/')}"
    for attempt in range(retries):
        _throttle()
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=30)
            return json.loads(resp.read().decode())
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(0.5 + attempt)
            else:
                print(f"  WARN {url}: {e}", file=sys.stderr, flush=True)
                return None

def load_players():
    cache = os.path.join(DATA_DIR, "bootstrap_cache.json")
    if os.path.exists(cache) and time.time() - os.path.getmtime(cache) < 3600:
        with open(cache) as f:
            bootstrap = json.load(f)
    else:
        bootstrap = api_get("bootstrap-static/")
        if bootstrap:
            with open(cache, "w") as f:
                json.dump(bootstrap, f)
    teams = {t['id']: t['name'] for t in bootstrap['teams']}
    pos = {e['id']: e['singular_name_short'] for e in bootstrap['element_types']}
    pm = {}
    for p in bootstrap['elements']:
        pm[p['id']] = {
            'name': p['web_name'], 'team': teams.get(p['team'], '?'),
            'position': pos.get(p['element_type'], '?'), 'cost': p['now_cost'] / 10.0,
            'selected_by': float(p.get('selected_by_percent', 0) or 0),
            'status': p.get('status', 'a'),
            'chance_of_playing': p.get('chance_of_playing_next_round', 100),
        }
    return pm

def load_memberships():
    path = os.path.join(DATA_DIR, "full_scout_data.json")
    with open(path) as f:
        data = json.load(f)
    memberships = data.get('memberships', [])
    seen = set()
    out = []
    for m in memberships:
        lid = m.get('league_id')
        if lid not in TRACKED_LEAGUES:
            continue
        eid = m.get('entry', 0)
        if not eid or eid in seen:
            continue
        seen.add(eid)
        out.append({
            'entry_id': eid,
            'entry_name': m.get('entry_name', ''),
            'player_name': m.get('player_name', ''),
            'league_id': lid,
            'joined_time': m.get('joined_time', ''),
        })
    return out

def fetch_entry(entry_id, gw, pm):
    res = {'entry_id': entry_id, 'gw': gw,
           'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    hist = api_get(f"entry/{entry_id}/history/")
    if hist:
        for g in hist.get('current', []):
            if g.get('event') == gw:
                res['gw_points'] = g.get('points', 0)
                res['total_points'] = g.get('total_points', 0)
                res['overall_rank'] = g.get('rank', 0)
                res['gw_transfers'] = g.get('event_transfers', 0)
                res['gw_transfers_cost'] = g.get('event_transfers_cost', 0)
                break
        res['chips_used'] = [{'name': c.get('name'), 'event': c.get('event')}
                             for c in hist.get('chips', []) if c.get('event') == gw]
    picks = api_get(f"entry/{entry_id}/event/{gw}/picks/")
    if picks:
        squad = []
        for pick in picks.get('picks', []):
            pid = pick['element']
            p = pm.get(pid, {})
            squad.append({
                'element': pid, 'name': p.get('name', f'Player_{pid}'),
                'position': p.get('position', '?'), 'team': p.get('team', '?'),
                'cost': p.get('cost', 0), 'is_captain': pick.get('is_captain', False),
                'is_vice_captain': pick.get('is_vice_captain', False),
                'multiplier': pick.get('multiplier', 1),
                'selected_by': p.get('selected_by', 0),
            })
        res['squad'] = squad
        cap = next((s for s in squad if s['is_captain']), None)
        vc = next((s for s in squad if s['is_vice_captain']), None)
        res['captain'] = cap['name'] if cap else 'N/A'
        res['vice_captain'] = vc['name'] if vc else 'N/A'
        positions = defaultdict(int)
        teams_in = defaultdict(int)
        for s in squad:
            positions[s['position']] += 1
            if s['team'] != '?':
                teams_in[s['team']] += 1
        res['squad_composition'] = dict(positions)
        res['squad_teams'] = dict(teams_in)
        res['squad_cost'] = round(sum(s['cost'] for s in squad), 1)
        res['active_chip'] = picks.get('active_chip', 'none')
    return res

def main():
    gw = 1
    print("Building player map...", file=sys.stderr, flush=True)
    pm = load_players()
    print(f"  {len(pm)} players", file=sys.stderr, flush=True)
    members = load_memberships()
    print(f"Memberships (unique): {len(members)}", file=sys.stderr, flush=True)

    from concurrent.futures import ThreadPoolExecutor, as_completed
    results = []
    errors = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(fetch_entry, m['entry_id'], gw, pm): m for m in members}
        done = 0
        for fut in as_completed(futs):
            m = futs[fut]
            try:
                r = fut.result(timeout=90)
                r['entry_name'] = m['entry_name']
                r['player_name'] = m['player_name']
                r['league_id'] = m['league_id']
                results.append(r)
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"  ERR {m['entry_id']}: {e}", file=sys.stderr, flush=True)
            done += 1
            if done % 200 == 0:
                print(f"  {done}/{len(members)} (errors {errors})", file=sys.stderr, flush=True)

    print(f"Done: {len(results)} ok, {errors} errors", file=sys.stderr, flush=True)

    for lid in TRACKED_LEAGUES:
        comps = [r for r in results if r['league_id'] == lid]
        comps.sort(key=lambda c: (c.get('gw_points', 0) or 0, -(c.get('squad_cost', 0) or 0)), reverse=True)
        for i, c in enumerate(comps, 1):
            c['league_rank'] = i
        out = {
            'gw': gw, 'league_id': lid,
            'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'total_entries': len(comps), 'errors': errors, 'competitors': comps,
        }
        with open(os.path.join(DATA_DIR, f"gw{gw}_league{lid}_data.json"), 'w') as f:
            json.dump(out, f, indent=2)
        compact = {
            'gw': gw, 'league_id': lid,
            'fetched_at': out['fetched_at'], 'total_entries': len(comps),
            'competitors': [{
                'entry_id': c['entry_id'], 'entry_name': c['entry_name'],
                'player_name': c['player_name'], 'league_rank': c['league_rank'],
                'gw_points': c.get('gw_points', 0), 'total_points': c.get('total_points', 0),
                'overall_rank': c.get('overall_rank', 0),
                'squad_cost': c.get('squad_cost', 0), 'captain': c.get('captain', 'N/A'),
                'vice_captain': c.get('vice_captain', 'N/A'),
                'active_chip': c.get('active_chip', 'none'),
                'transfers_made': c.get('gw_transfers', 0),
                'squad_composition': c.get('squad_composition', {}),
                'squad_teams': c.get('squad_teams', {}),
            } for c in comps]
        }
        with open(os.path.join(DATA_DIR, f"gw{gw}_league{lid}_compact.json"), 'w') as f:
            json.dump(compact, f, indent=2)
        print(f"League {lid}: {len(comps)} competitors saved", file=sys.stderr, flush=True)
    return 0

if __name__ == '__main__':
    sys.exit(main())