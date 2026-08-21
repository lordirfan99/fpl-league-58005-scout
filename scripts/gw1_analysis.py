#!/usr/bin/env python3
"""GW1 Analysis — works with standings event_total and picks data."""
import urllib.request
import json
import os
import sys
from collections import defaultdict, Counter

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

def api_get(path):
    url = f"https://fantasy.premierleague.com/api/{path.lstrip('/')}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  ⚠️ {url}: {e}", file=sys.stderr, flush=True)
        return None

def get_standings_with_scores(league_id):
    """Get standings with event_total (actual GW scores)."""
    data = api_get(f"leagues-classic/{league_id}/standings/")
    if not data:
        return []
    results = []
    for r in data.get('standings', {}).get('results', []):
        results.append({
            'entry_id': r.get('entry', 0),
            'entry_name': r.get('entry_name', ''),
            'player_name': r.get('player_name', ''),
            'rank': r.get('rank', 0),
            'event_total': r.get('event_total', 0),
            'total': r.get('total', 0),
        })
    return results

def get_player_map():
    bootstrap = api_get("bootstrap-static/")
    if not bootstrap:
        return {}
    teams = {t['id']: t['name'] for t in bootstrap.get('teams', [])}
    pos_types = {e['id']: e['singular_name_short'] for e in bootstrap.get('element_types', [])}
    player_map = {}
    for p in bootstrap.get('elements', []):
        player_map[p['id']] = {
            'name': p['web_name'],
            'full_name': p['first_name'] + ' ' + p['second_name'],
            'team': teams.get(p['team'], '?'),
            'position': pos_types.get(p['element_type'], '?'),
            'cost': p['now_cost'] / 10,
            'selected_by': float(p.get('selected_by_percent', 0) or 0),
        }
    return player_map

def get_entry_picks(entry_id, gw=1):
    return api_get(f"entry/{entry_id}/event/{gw}/picks/")

def get_entry_history(entry_id):
    return api_get(f"entry/{entry_id}/history/")

def main():
    print("=" * 60, file=sys.stderr, flush=True)
    print("GW1 Scout Analysis Pipeline", file=sys.stderr, flush=True)
    print("=" * 60, file=sys.stderr, flush=True)
    
    # Load player map
    print("📦 Loading player data...", file=sys.stderr, flush=True)
    player_map = get_player_map()
    print(f"✅ {len(player_map)} players loaded", file=sys.stderr, flush=True)
    
    # Fetch standings for both leagues
    league_ids = [58005, 131997]
    league_names = {
        58005: "LIGA FPL KK OLD BOYS S5",
        131997: "OVERALL IFE 26/27",
    }
    
    all_standings = {}
    for lid in league_ids:
        print(f"📊 Fetching league {lid} standings...", file=sys.stderr, flush=True)
        standings = get_standings_with_scores(lid)
        all_standings[lid] = standings
        print(f"  → {len(standings)} entries", file=sys.stderr, flush=True)
    
    # Fetch picks for each entry (deduplicated across leagues)
    all_entry_ids = set()
    for lid, standings in all_standings.items():
        for s in standings:
            all_entry_ids.add(s['entry_id'])
    
    print(f"🎯 Total unique entries: {len(all_entry_ids)}", file=sys.stderr, flush=True)
    
    # Fetch picks for all entries
    entry_picks = {}
    entry_histories = {}
    for i, eid in enumerate(sorted(all_entry_ids)):
        if i % 20 == 0:
            print(f"  Fetching picks: {i}/{len(all_entry_ids)}", file=sys.stderr, flush=True)
        picks = get_entry_picks(eid, 1)
        if picks:
            entry_picks[eid] = picks
        history = get_entry_history(eid)
        if history:
            entry_histories[eid] = history
    
    print(f"✅ Picks fetched for {len(entry_picks)} entries", file=sys.stderr, flush=True)
    
    # Build full competitor data
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(os.path.join(REPORTS_DIR, "GW1"), exist_ok=True)
    
    for lid in league_ids:
        standings = all_standings.get(lid, [])
        competitors = []
        
        for s in standings:
            eid = s['entry_id']
            picks = entry_picks.get(eid, {})
            hist = entry_histories.get(eid, {})
            
            comp = {
                'entry_id': eid,
                'entry_name': s.get('entry_name', ''),
                'player_name': s.get('player_name', ''),
                'league_rank': s.get('rank', 0),
                'gw_points': s.get('event_total', 0),
                'total_points': s.get('total', 0),
            }
            
            # Process picks
            squad = []
            if picks:
                for pick in picks.get('picks', []):
                    pid = pick['element']
                    p = player_map.get(pid, {})
                    squad.append({
                        'element': pid,
                        'name': p.get('name', f'Player_{pid}'),
                        'position': p.get('position', '?'),
                        'team': p.get('team', '?'),
                        'cost': p.get('cost', 0),
                        'is_captain': pick.get('is_captain', False),
                        'is_vice_captain': pick.get('is_vice_captain', False),
                        'multiplier': pick.get('multiplier', 1),
                        'selected_by': p.get('selected_by', 0),
                    })
                
                captain = next((s for s in squad if s['is_captain']), None)
                vice = next((s for s in squad if s['is_vice_captain']), None)
                comp['captain'] = captain['name'] if captain else 'N/A'
                comp['vice_captain'] = vice['name'] if vice else 'N/A'
                comp['active_chip'] = picks.get('active_chip', 'none')
                
                positions = defaultdict(int)
                teams_in_squad = defaultdict(int)
                for s in squad:
                    positions[s['position']] += 1
                    if s['team'] and s['team'] != '?':
                        teams_in_squad[s['team']] += 1
                comp['squad_composition'] = dict(positions)
                comp['squad_teams'] = dict(teams_in_squad)
                comp['squad_cost'] = sum(s['cost'] for s in squad)
            
            comp['squad'] = squad
            
            # Process history for transfers
            if hist:
                for gw_entry in hist.get('current', []):
                    if gw_entry.get('event') == 1:
                        comp['gw_transfers'] = gw_entry.get('event_transfers', 0)
                        comp['gw_transfers_cost'] = gw_entry.get('event_transfers_cost', 0)
                        comp['gw_bank'] = gw_entry.get('bank', 0)
                        comp['gw_value'] = gw_entry.get('value', 0)
                        break
            
            competitors.append(comp)
        
        # Save data
        gw_data_path = os.path.join(DATA_DIR, f"gw1_league{lid}_data.json")
        with open(gw_data_path, 'w') as f:
            json.dump({
                'gw': 1,
                'league_id': lid,
                'fetched_at': '2026-08-22T00:00:00Z',
                'total_entries': len(competitors),
                'competitors': competitors,
            }, f, indent=2)
        print(f"✅ League {lid}: {len(competitors)} entries → {gw_data_path}", file=sys.stderr, flush=True)
        
        # ===== ANALYSIS =====
        print(f"\n📈 ANALYZING LEAGUE {lid}: {league_names.get(lid, '?')}", file=sys.stderr, flush=True)
        
        total = len(competitors)
        
        # GW points
        gw_points = [c.get('gw_points', 0) or 0 for c in competitors]
        avg_gw = round(sum(gw_points) / len(gw_points), 1) if gw_points else 0
        max_gw = max(gw_points) if gw_points else 0
        min_gw = min(gw_points) if gw_points else 0
        
        # Top scorer
        sorted_comp = sorted(competitors, key=lambda c: (c.get('gw_points', 0) or 0), reverse=True)
        top_scorer = sorted_comp[0] if sorted_comp else None
        
        # Captain choices
        captains = [c.get('captain', 'N/A') for c in competitors if c.get('captain')]
        cap_counter = Counter(captains)
        most_popular_captain = cap_counter.most_common(1)
        
        # Ownership
        all_players = defaultdict(int)
        for c in competitors:
            for s in c.get('squad', []):
                all_players[s['name']] += 1
        
        ownership_pct = {name: round(count / total * 100, 1) for name, count in all_players.items()}
        top_owned = sorted(ownership_pct.items(), key=lambda x: -x[1])[:10]
        
        # Template players (>50%)
        template = [name for name, pct in ownership_pct.items() if pct >= 50]
        
        # Formations
        formations = defaultdict(int)
        for c in competitors:
            comp_d = c.get('squad_composition', {})
            deff = comp_d.get('DEF', 0)
            mid = comp_d.get('MID', 0)
            fwd = comp_d.get('FWD', 0)
            formation = f"{deff}-{mid}-{fwd}"
            formations[formation] += 1
        top_formations = sorted(formations.items(), key=lambda x: -x[1])
        
        # Differentials (owned by <10%)
        diffs = [(name, pct) for name, pct in ownership_pct.items() if pct < 10 and pct > 0]
        diffs_sorted = sorted(diffs, key=lambda x: x[1])
        
        # Chips
        chips_used = Counter(c.get('active_chip', 'none') for c in competitors)
        
        # Transfers
        teams_with_transfers = sum(1 for c in competitors if c.get('gw_transfers', 0) > 0)
        hit_takers = sum(1 for c in competitors if c.get('gw_transfers_cost', 0) > 0)
        
        # Squad costs
        squad_costs = [c.get('squad_cost', 0) or 0 for c in competitors if c.get('squad_cost')]
        avg_cost = round(sum(squad_costs) / len(squad_costs), 1) if squad_costs else 0
        
        print(f"  Total entries: {total}", file=sys.stderr, flush=True)
        print(f"  Avg GW points: {avg_gw}", file=sys.stderr, flush=True)
        print(f"  Max GW points: {max_gw}", file=sys.stderr, flush=True)
        print(f"  Top scorer: {top_scorer.get('entry_name','?')} ({top_scorer.get('gw_points',0)}pts)", file=sys.stderr, flush=True)
        print(f"  Most popular captain: {most_popular_captain[0][0] if most_popular_captain else 'N/A'} ({most_popular_captain[0][1] if most_popular_captain else 0} teams)", file=sys.stderr, flush=True)
        print(f"  Template players: {template[:5]}", file=sys.stderr, flush=True)
        print(f"  Top formation: {top_formations[0][0] if top_formations else 'N/A'}", file=sys.stderr, flush=True)
        print(f"  Chips used: {dict(chips_used)}", file=sys.stderr, flush=True)
        print(f"  Teams with transfers: {teams_with_transfers}", file=sys.stderr, flush=True)
        print(f"  Hit takers: {hit_takers}", file=sys.stderr, flush=True)
        print(f"  Avg squad cost: £{avg_cost}m", file=sys.stderr, flush=True)
        print(f"  Top 10 owned: {top_owned[:10]}", file=sys.stderr, flush=True)
        print(f"  Differentials (<10%): {diffs_sorted[:10]}", file=sys.stderr, flush=True)
        print(f"  Captains breakdown: {cap_counter.most_common(10)}", file=sys.stderr, flush=True)
        print(f"  Formations: {top_formations}", file=sys.stderr, flush=True)
        
        print(f"\n", file=sys.stderr, flush=True)
    
    # ===== ELITE WATCH =====
    print("=" * 60, file=sys.stderr, flush=True)
    print("🔍 ELITE WATCH", file=sys.stderr, flush=True)
    print("=" * 60, file=sys.stderr, flush=True)
    
    elite_entries = {
        2168452: {"name": "Diesel FC", "manager": "Sashe S"},
        214526: {"name": "Go Kapit", "manager": "ALEXANDER JONATHAN"},
        63274: {"name": "Kiukiu Fc", "manager": "AIMAN MUSTAPA"},
        33078: {"name": "MARZUKI MADI FC", "manager": "MARZUKI MADI-EM-"},
        139793: {"name": "ChupkeChupke", "manager": "Zaid Azman"},
    }
    
    for eid, info in elite_entries.items():
        picks = entry_picks.get(eid)
        hist = entry_histories.get(eid)
        
        print(f"\n  {info['name']} ({info['manager']})", file=sys.stderr, flush=True)
        
        # Find their score in standings
        gw_score = 0
        for lid, standings in all_standings.items():
            for s in standings:
                if s['entry_id'] == eid:
                    gw_score = s.get('event_total', 0)
                    break
        
        # Get captain
        captain = 'N/A'
        vc = 'N/A'
        chip = 'none'
        if picks:
            for p in picks.get('picks', []):
                pid = p['element']
                pname = player_map.get(pid, {}).get('name', f'Player_{pid}')
                if p.get('is_captain'):
                    captain = pname
                    chip = picks.get('active_chip', 'none')
                if p.get('is_vice_captain'):
                    vc = pname
        
        # Get transfers
        transfers = 0
        if hist:
            for gw_entry in hist.get('current', []):
                if gw_entry.get('event') == 1:
                    transfers = gw_entry.get('event_transfers', 0)
                    break
        
        print(f"    GW Points: {gw_score}", file=sys.stderr, flush=True)
        print(f"    Captain: {captain} (VC: {vc})", file=sys.stderr, flush=True)
        print(f"    Chip: {chip}", file=sys.stderr, flush=True)
        print(f"    Transfers: {transfers}", file=sys.stderr, flush=True)
        
        # Squad
        if picks:
            for p in picks.get('picks', []):
                pid = p['element']
                pname = player_map.get(pid, {}).get('name', f'Player_{pid}')
                label = 'C' if p.get('is_captain') else ('VC' if p.get('is_vice_captain') else '')
                mult = p.get('multiplier', 1)
                print(f"    {pname} {'[' + label + ']' if label else ''} x{mult}", file=sys.stderr, flush=True)
    
    print(f"\nDone!", file=sys.stderr, flush=True)

if __name__ == '__main__':
    main()