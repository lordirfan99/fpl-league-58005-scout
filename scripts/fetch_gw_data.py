#!/usr/bin/env python3
"""
FPL GW Data Fetcher — pulls picks, points, transfers, chips for every league member.
Run after each GW finishes. Generates structured data for analysis.

Usage: python3 fetch_gw_data.py [--gw <num>] [--league 58005] [--entry-ids FILE]
"""

import urllib.request
import json
import time
import os
import sys
import argparse
from collections import defaultdict

BASE_URL = "https://fantasy.premierleague.com/api"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")

def api_get(path, retries=3):
    """Fetch from FPL API with retry."""
    url = f"{BASE_URL}/{path.lstrip('/')}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=30)
            return json.loads(resp.read().decode())
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  ⚠️ Failed {url}: {e}", file=sys.stderr)
                return None

def load_bootstrap():
    """Load and cache bootstrap data (players, teams, events)."""
    cache_path = os.path.join(DATA_DIR, "bootstrap_cache.json")
    if os.path.exists(cache_path) and time.time() - os.path.getmtime(cache_path) < 3600:
        with open(cache_path) as f:
            return json.load(f)
    
    data = api_get("bootstrap-static/")
    if data:
        with open(cache_path, "w") as f:
            json.dump(data, f)
    return data

def build_player_map(bootstrap):
    """Build player_id -> {name, team, position, cost} mapping."""
    teams = {t['id']: t['name'] for t in bootstrap.get('teams', [])}
    pos_types = {e['id']: e['singular_name_short'] for e in bootstrap.get('element_types', [])}
    
    players = {}
    for p in bootstrap.get('elements', []):
        players[p['id']] = {
            'name': p['web_name'],
            'full_name': p['first_name'] + ' ' + p['second_name'],
            'team': teams.get(p['team'], 'Unknown'),
            'team_id': p['team'],
            'position': pos_types.get(p['element_type'], '?'),
            'position_id': p['element_type'],
            'cost': p['now_cost'] / 10,
            'form': float(p.get('form', 0) or 0),
            'total_points': p['total_points'],
            'points_per_game': float(p.get('points_per_game', 0) or 0),
            'selected_by': float(p.get('selected_by_percent', 0) or 0),
            'status': p.get('status', 'a'),
            'chance_of_playing': p.get('chance_of_playing_next_round', 100),
            'news': p.get('news', ''),
        }
    return players

def get_league_standings(league_id, gw):
    """Get league standings for a given GW."""
    # Post-GW, standings should have data
    data = api_get(f"leagues-classic/{league_id}/standings/")
    if not data:
        return []
    
    results = []
    standings = data.get('standings', {})
    for r in standings.get('results', []):
        results.append({
            'rank': r.get('rank', 0),
            'entry_id': r.get('entry', 0),
            'entry_name': r.get('entry_name', ''),
            'player_name': r.get('player_name', ''),
            'total_points': r.get('total', 0),
            'last_rank': r.get('last_rank', r.get('rank', 0)),
            'rank_sort': r.get('rank_sort', 0),
        })
    
    # Check pagination
    has_more = standings.get('has_next', False)
    page = 2
    while has_more:
        data = api_get(f"leagues-classic/{league_id}/standings/?page={page}")
        if not data:
            break
        standings = data.get('standings', {})
        for r in standings.get('results', []):
            results.append({
                'rank': r.get('rank', 0),
                'entry_id': r.get('entry', 0),
                'entry_name': r.get('entry_name', ''),
                'player_name': r.get('player_name', ''),
                'total_points': r.get('total', 0),
                'last_rank': r.get('last_rank', r.get('rank', 0)),
                'rank_sort': r.get('rank_sort', 0),
            })
        has_more = standings.get('has_next', False)
        page += 1
        time.sleep(0.3)
    
    return results

def get_entry_picks(entry_id, gw):
    """Get a team's picks for a specific GW."""
    return api_get(f"entry/{entry_id}/event/{gw}/picks/")

def get_entry_history(entry_id):
    """Get full entry history (all GWs this season)."""
    return api_get(f"entry/{entry_id}/history/")

def get_entry_transfers(entry_id, gw):
    """Get transfers made in a specific GW."""
    return api_get(f"entry/{entry_id}/event/{gw}/transfers/")

def get_live_entry_data(entry_id):
    """Get live entry data (current season info)."""
    return api_get(f"entry/{entry_id}/")

def fetch_competitor_data(entry_id, gw, player_map):
    """Fetch all data for a single competitor for a GW."""
    result = {
        'entry_id': entry_id,
        'gw': gw,
        'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }
    
    # Entry info
    entry_info = get_entry_history(entry_id)
    if entry_info:
        result['history'] = entry_info
        current = entry_info.get('current', [])
        for gw_entry in current:
            if gw_entry.get('event') == gw:
                result['gw_points'] = gw_entry.get('points', 0)
                result['total_points'] = gw_entry.get('total_points', 0)
                result['rank'] = gw_entry.get('rank', 0)
                result['rank_sort'] = gw_entry.get('rank_sort', 0)
                result['gw_transfers'] = gw_entry.get('event_transfers', 0)
                result['gw_transfers_cost'] = gw_entry.get('event_transfers_cost', 0)
                result['gw_bank'] = gw_entry.get('bank', 0)
                result['gw_value'] = gw_entry.get('value', 0)
                break
    
    # Picks (squad)
    picks = get_entry_picks(entry_id, gw)
    if picks:
        result['picks'] = picks
        # Analyze squad
        squad = []
        for pick in picks.get('picks', []):
            pid = pick['element']
            player = player_map.get(pid, {})
            squad.append({
                'element': pid,
                'name': player.get('name', f'Player_{pid}'),
                'position': player.get('position', '?'),
                'team': player.get('team', '?'),
                'cost': player.get('cost', 0),
                'is_captain': pick.get('is_captain', False),
                'is_vice_captain': pick.get('is_vice_captain', False),
                'multiplier': pick.get('multiplier', 1),
                'position_order': pick.get('position', 0),
                'selected_by': player.get('selected_by', 0),
                'form': player.get('form', 0),
                'total_points': player.get('total_points', 0),
                'points_per_game': player.get('points_per_game', 0),
                'status': player.get('status', 'a'),
                'chance_of_playing': player.get('chance_of_playing', 100),
                'news': player.get('news', ''),
            })
        result['squad'] = squad
        
        # Captain analysis
        captain = next((s for s in squad if s['is_captain']), None)
        vice = next((s for s in squad if s['is_vice_captain']), None)
        result['captain'] = captain['name'] if captain else 'N/A'
        result['vice_captain'] = vice['name'] if vice else 'N/A'
        
        # Squad composition
        positions = defaultdict(int)
        teams_in_squad = defaultdict(int)
        for s in squad:
            positions[s['position']] += 1
            if s['team'] and s['team'] != '?':
                teams_in_squad[s['team']] += 1
        result['squad_composition'] = dict(positions)
        result['squad_teams'] = dict(teams_in_squad)
        
        # Total squad cost
        result['squad_cost'] = sum(s['cost'] for s in squad)
        
        # Active players (playing, not injured)
        active = [s for s in squad if s['status'] == 'a' and (s['chance_of_playing'] is None or s['chance_of_playing'] >= 75)]
        result['active_players_count'] = len(active)
        injured = [s for s in squad if s['status'] != 'a' or (s['chance_of_playing'] is not None and s['chance_of_playing'] < 50)]
        result['injured_players'] = [s['name'] for s in injured]
        result['injured_count'] = len(injured)
    
    # Transfers
    transfers = get_entry_transfers(entry_id, gw)
    if transfers:
        result['transfers'] = transfers
        transfers_list = transfers.get('transfers', [])
        result['transfers_made'] = len(transfers_list)
        if transfers_list:
            # Decode transfer details
            transfer_details = []
            for t in transfers_list:
                out_player = player_map.get(t.get('element_out', 0), {})
                in_player = player_map.get(t.get('element_in', 0), {})
                transfer_details.append({
                    'out': out_player.get('name', f"Player_{t.get('element_out',0)}"),
                    'in': in_player.get('name', f"Player_{t.get('element_in',0)}"),
                    'cost': t.get('element_in_cost', 0) / 10,
                    'sold_for': t.get('element_out_cost', 0) / 10,
                })
            result['transfer_details'] = transfer_details
    
    # Chip usage
    if entry_info:
        chips = entry_info.get('chips', [])
        result['chips_used'] = [c for c in chips if c.get('event') == gw]
    
    return result

def main():
    parser = argparse.ArgumentParser(description='FPL GW Data Fetcher')
    parser.add_argument('--gw', type=int, help='Gameweek to fetch (default: auto-detect)')
    parser.add_argument('--league', type=int, default=58005, help='League ID')
    parser.add_argument('--entry-ids', help='JSON file with entry IDs array')
    parser.add_argument('--max', type=int, default=686, help='Max entries to fetch')
    parser.add_argument('--output', help='Output file path')
    args = parser.parse_args()
    
    # Load bootstrap
    print("📦 Loading bootstrap data...", file=sys.stderr)
    bootstrap = load_bootstrap()
    if not bootstrap:
        print("❌ Failed to load bootstrap static!", file=sys.stderr)
        return 1
    player_map = build_player_map(bootstrap)
    print(f"✅ Loaded {len(player_map)} players, {len(bootstrap.get('teams',[]))} teams", file=sys.stderr)
    
    # Detect GW if not specified
    gw = args.gw
    if not gw:
        for e in bootstrap.get('events', []):
            if e.get('finished'):
                gw = e['id']
        if not gw:
            # Find the most recent finished or current event
            events = [e for e in bootstrap.get('events', []) if e.get('id', 0) > 0]
            finished = [e for e in events if e.get('finished')]
            if finished:
                gw = finished[-1]['id']
            else:
                # Check the most recent event that's past deadline
                import time
                now = time.time()
                for e in reversed(events):
                    if e.get('deadline_time_epoch', 0) < now:
                        gw = e['id']
                        break
    
    if not gw:
        print("❌ Could not determine current GW!", file=sys.stderr)
        return 1
    print(f"🎯 Target: GW {gw}", file=sys.stderr)
    
    # Get league standings to get entry IDs
    print(f"📊 Fetching league {args.league} standings...", file=sys.stderr)
    standings = get_league_standings(args.league, gw)
    print(f"✅ Found {len(standings)} entries in standings", file=sys.stderr)
    
    # If standings are empty (pre-season), fall back to existing entry IDs
    if not standings:
        print("⚠️ Standings empty — using existing entry IDs from scout data", file=sys.stderr)
        existing_path = os.path.join(DATA_DIR, "full_scout_data.json")
        if os.path.exists(existing_path):
            with open(existing_path) as f:
                existing = json.load(f)
            entry_ids = [e['entry_id'] for e in existing[:args.max]]
            standings = [{'entry_id': eid, 'entry_name': '', 'player_name': '', 'rank': i+1, 'total_points': 0} 
                        for i, eid in enumerate(entry_ids)]
        else:
            print("❌ No existing entry data found!", file=sys.stderr)
            return 1
    else:
        entry_ids = [s['entry_id'] for s in standings[:args.max]]
    
    print(f"🎯 Fetching data for {min(len(entry_ids), args.max)} competitors...", file=sys.stderr)
    
    # Fetch data for each competitor
    all_data = []
    errors = 0
    for i, entry_id in enumerate(entry_ids):
        if i >= args.max:
            break
        if i % 50 == 0 and i > 0:
            print(f"  Progress: {i}/{min(len(entry_ids), args.max)} (errors: {errors})", file=sys.stderr)
        
        comp_data = fetch_competitor_data(entry_id, gw, player_map)
        # Merge with standings info
        standing = next((s for s in standings if s['entry_id'] == entry_id), {})
        comp_data['league_rank'] = standing.get('rank', 0)
        comp_data['entry_name'] = standing.get('entry_name', '')
        comp_data['player_name'] = standing.get('player_name', '')
        comp_data['league_total'] = standing.get('total_points', 0)
        comp_data['league_last_rank'] = standing.get('last_rank', 0)
        all_data.append(comp_data)
        time.sleep(0.15)  # Rate limiting
    
    # Output
    output_path = args.output or os.path.join(DATA_DIR, f"gw{gw}_data.json")
    with open(output_path, 'w') as f:
        json.dump({
            'gw': gw,
            'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'total_entries': len(all_data),
            'errors': errors,
            'competitors': all_data,
        }, f, indent=2)
    
    print(f"\n✅ Done! {len(all_data)} competitors fetched (errors: {errors})", file=sys.stderr)
    print(f"📁 Output: {output_path}", file=sys.stderr)
    
    # Also output a compact version for analysis
    compact_path = os.path.join(DATA_DIR, f"gw{gw}_data_compact.json")
    compact = {
        'gw': gw,
        'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 
        'total_entries': len(all_data),
        'competitors': [{
            'entry_id': c['entry_id'],
            'entry_name': c.get('entry_name', ''),
            'player_name': c.get('player_name', ''),
            'league_rank': c.get('league_rank', 0),
            'gw_points': c.get('gw_points', 0),
            'total_points': c.get('total_points', 0),
            'rank': c.get('rank', 0),
            'squad_cost': c.get('squad_cost', 0),
            'captain': c.get('captain', 'N/A'),
            'vice_captain': c.get('vice_captain', 'N/A'),
            'transfers_made': c.get('transfers_made', 0),
            'injured_count': c.get('injured_count', 0),
            'active_players_count': c.get('active_players_count', 0),
            'squad_composition': c.get('squad_composition', {}),
            'squad_teams': c.get('squad_teams', {}),
        } for c in all_data]
    }
    with open(compact_path, 'w') as f:
        json.dump(compact, f, indent=2)
    print(f"📁 Compact: {compact_path}", file=sys.stderr)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())