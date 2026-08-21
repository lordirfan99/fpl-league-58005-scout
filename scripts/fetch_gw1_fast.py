#!/usr/bin/env python3
"""Fast GW1 data fetcher — concurrent, minimal delays, no buffering."""
import urllib.request
import json
import time
import os
import sys
import concurrent.futures
from collections import defaultdict

BASE_URL = "https://fantasy.premierleague.com/api"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

sys.stdout.reconfigure(line_buffering=True)  # Force line buffering
sys.stderr.reconfigure(line_buffering=True)

def api_get(path, retries=3):
    url = f"{BASE_URL}/{path.lstrip('/')}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=30)
            return json.loads(resp.read().decode())
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                print(f"  ⚠️ Failed {url}: {e}", file=sys.stderr, flush=True)
                return None

def get_league_standings_fast(league_id):
    """Get ALL standings for a league using concurrent page fetches."""
    print(f"📊 Fetching league {league_id} standings...", file=sys.stderr, flush=True)
    
    # First page to get total count
    first = api_get(f"leagues-classic/{league_id}/standings/")
    if not first:
        return []
    
    results = []
    for r in first.get('standings', {}).get('results', []):
        results.append({
            'rank': r.get('rank', 0),
            'entry_id': r.get('entry', 0),
            'entry_name': r.get('entry_name', ''),
            'player_name': r.get('player_name', ''),
            'total_points': r.get('total', 0),
            'last_rank': r.get('last_rank', r.get('rank', 0)),
            'rank_sort': r.get('rank_sort', 0),
        })
    
    has_more = first.get('standings', {}).get('has_next', False)
    if not has_more:
        return results
    
    # Fetch remaining pages concurrently
    remaining_pages = []
    page = 2
    # First, discover how many pages exist by parallel fetch
    # We'll just fetch pages until we get empties (up to 50 pages)
    print(f"  League has results, fetching remaining pages...", file=sys.stderr, flush=True)
    
    # Fetch pages in parallel batches
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        for pg in range(2, 51):
            fut = executor.submit(api_get, f"leagues-classic/{league_id}/standings/?page={pg}")
            futures[pg] = fut
        
        for pg in sorted(futures.keys()):
            try:
                data = futures[pg].result(timeout=30)
                if not data:
                    break
                standings = data.get('standings', {})
                page_results = standings.get('results', [])
                if not page_results:
                    break
                for r in page_results:
                    results.append({
                        'rank': r.get('rank', 0),
                        'entry_id': r.get('entry', 0),
                        'entry_name': r.get('entry_name', ''),
                        'player_name': r.get('player_name', ''),
                        'total_points': r.get('total', 0),
                        'last_rank': r.get('last_rank', r.get('rank', 0)),
                        'rank_sort': r.get('rank_sort', 0),
                    })
            except Exception as e:
                print(f"  ⚠️ Page {pg} failed: {e}", file=sys.stderr, flush=True)
                break
    
    print(f"  → {len(results)} entries total", file=sys.stderr, flush=True)
    return results

def main():
    league_ids = [58005, 131997]
    gw = 1
    max_entries = 3000
    
    # Load bootstrap
    print("📦 Loading bootstrap data...", file=sys.stderr, flush=True)
    bootstrap = api_get("bootstrap-static/")
    if not bootstrap:
        print("❌ Failed to load bootstrap!", file=sys.stderr, flush=True)
        return 1
    
    teams = {t['id']: t['name'] for t in bootstrap.get('teams', [])}
    pos_types = {e['id']: e['singular_name_short'] for e in bootstrap.get('element_types', [])}
    
    player_map = {}
    for p in bootstrap.get('elements', []):
        player_map[p['id']] = {
            'name': p['web_name'],
            'full_name': p['first_name'] + ' ' + p['second_name'],
            'team': teams.get(p['team'], 'Unknown'),
            'position': pos_types.get(p['element_type'], '?'),
            'cost': p['now_cost'] / 10,
            'form': float(p.get('form', 0) or 0),
            'total_points': p['total_points'],
            'points_per_game': float(p.get('points_per_game', 0) or 0),
            'selected_by': float(p.get('selected_by_percent', 0) or 0),
            'status': p.get('status', 'a'),
            'chance_of_playing': p.get('chance_of_playing_next_round', 100),
            'news': p.get('news', ''),
        }
    print(f"✅ Loaded {len(player_map)} players, {len(teams)} teams", file=sys.stderr, flush=True)
    
    # Fetch standings for both leagues concurrently
    standings_by_league = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = {lid: executor.submit(get_league_standings_fast, lid) for lid in league_ids}
        for lid in league_ids:
            standings_by_league[lid] = futures[lid].result(timeout=120)
    
    # Deduplicate entries across leagues
    all_entry_ids_set = set()
    all_entries_per_league = {}
    for lid in league_ids:
        unique = []
        for s in standings_by_league.get(lid, []):
            eid = s['entry_id']
            if eid and eid not in all_entry_ids_set:
                all_entry_ids_set.add(eid)
                unique.append(s)
        all_entries_per_league[lid] = unique
        print(f"  League {lid}: {len(unique)} unique entries", file=sys.stderr, flush=True)
    
    total_unique = len(all_entry_ids_set)
    print(f"🎯 Total unique entries: {total_unique}", file=sys.stderr, flush=True)
    
    # Build reverse mapping
    entry_id_to_league = {}
    for lid, entries in all_entries_per_league.items():
        for s in entries:
            eid = s['entry_id']
            if eid not in entry_id_to_league:
                entry_id_to_league[eid] = {'league_id': lid, 'standing': s}
    
    all_entry_ids = list(all_entry_ids_set)
    if max_entries and max_entries < len(all_entry_ids):
        all_entry_ids = all_entry_ids[:max_entries]
    
    # Fetch individual entry data concurrently
    print(f"⏳ Fetching data for {len(all_entry_ids)} entries...", file=sys.stderr, flush=True)
    
    def fetch_entry_data(entry_id):
        result = {
            'entry_id': entry_id,
            'gw': gw,
            'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        }
        
        # Entry history (for GW points, transfers, etc.)
        history = api_get(f"entry/{entry_id}/history/")
        if history:
            result['history'] = history
            for gw_entry in history.get('current', []):
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
            chips = history.get('chips', [])
            result['chips_used'] = [c for c in chips if c.get('event') == gw]
        
        # Picks
        picks = api_get(f"entry/{entry_id}/event/{gw}/picks/")
        if picks:
            result['picks'] = picks
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
            captain = next((s for s in squad if s['is_captain']), None)
            vice = next((s for s in squad if s['is_vice_captain']), None)
            result['captain'] = captain['name'] if captain else 'N/A'
            result['vice_captain'] = vice['name'] if vice else 'N/A'
            
            positions = defaultdict(int)
            teams_in_squad = defaultdict(int)
            for s in squad:
                positions[s['position']] += 1
                if s['team'] and s['team'] != '?':
                    teams_in_squad[s['team']] += 1
            result['squad_composition'] = dict(positions)
            result['squad_teams'] = dict(teams_in_squad)
            result['squad_cost'] = sum(s['cost'] for s in squad)
            
            active = [s for s in squad if s['status'] == 'a' and (s['chance_of_playing'] is None or s['chance_of_playing'] >= 75)]
            result['active_players_count'] = len(active)
            injured = [s for s in squad if s['status'] != 'a' or (s['chance_of_playing'] is not None and s['chance_of_playing'] < 50)]
            result['injured_players'] = [s['name'] for s in injured]
            result['injured_count'] = len(injured)
        
        # Transfers
        transfers = api_get(f"entry/{entry_id}/event/{gw}/transfers/")
        if transfers:
            result['transfers'] = transfers
            transfers_list = transfers.get('transfers', [])
            result['transfers_made'] = len(transfers_list)
            if transfers_list:
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
        
        # Assign league info
        li = entry_id_to_league.get(entry_id, {})
        result['league_id'] = li.get('league_id', 0)
        result['league_rank'] = li.get('standing', {}).get('rank', 0)
        result['entry_name'] = li.get('standing', {}).get('entry_name', '')
        result['player_name'] = li.get('standing', {}).get('player_name', '')
        result['league_total'] = li.get('standing', {}).get('total_points', 0)
        result['league_last_rank'] = li.get('standing', {}).get('last_rank', 0)
        
        return result
    
    # Use ThreadPoolExecutor for concurrent entry fetches
    all_data = {lid: [] for lid in league_ids}
    errors = 0
    count = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_to_eid = {executor.submit(fetch_entry_data, eid): eid for eid in all_entry_ids}
        for i, future in enumerate(concurrent.futures.as_completed(future_to_eid)):
            eid = future_to_eid[future]
            try:
                comp_data = future.result(timeout=60)
                lid = comp_data.get('league_id', 0)
                if lid in all_data:
                    all_data[lid].append(comp_data)
                count += 1
                if count % 100 == 0:
                    print(f"  Progress: {count}/{len(all_entry_ids)} (errors: {errors})", file=sys.stderr, flush=True)
            except Exception as e:
                errors += 1
                if errors % 10 == 0:
                    print(f"  ⚠️ Error on entry {eid}: {e}", file=sys.stderr, flush=True)
    
    print(f"⏱️ Done fetching. Success: {count}, Errors: {errors}", file=sys.stderr, flush=True)
    
    # Output files
    for lid in league_ids:
        output_path = os.path.join(DATA_DIR, f"gw{gw}_league{lid}_data.json")
        with open(output_path, 'w') as f:
            json.dump({
                'gw': gw,
                'league_id': lid,
                'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'total_entries': len(all_data.get(lid, [])),
                'errors': errors,
                'competitors': all_data.get(lid, []),
            }, f, indent=2)
        print(f"✅ League {lid}: {len(all_data.get(lid, []))} competitors → {output_path}", file=sys.stderr, flush=True)
        
        # Compact version
        compact_path = os.path.join(DATA_DIR, f"gw{gw}_league{lid}_compact.json")
        compact = {
            'gw': gw, 'league_id': lid,
            'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'total_entries': len(all_data.get(lid, [])),
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
            } for c in all_data.get(lid, [])]
        }
        with open(compact_path, 'w') as f:
            json.dump(compact, f, indent=2)
        print(f"  Compact: {compact_path}", file=sys.stderr, flush=True)
    
    print(f"✅ Done! {count} total unique competitors across {len(league_ids)} leagues", file=sys.stderr, flush=True)
    return 0

if __name__ == '__main__':
    sys.exit(main())