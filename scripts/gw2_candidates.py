#!/usr/bin/env python3
"""Candidate IN players — team + GW2 fixture difficulty."""
import urllib.request, json, sys
from collections import defaultdict
sys.stdout.reconfigure(line_buffering=True)

BASE = "https://fantasy.premierleague.com/api"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def api_get(path):
    req = urllib.request.Request(f"{BASE}/{path}", headers=HEADERS)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

bs = api_get("bootstrap-static/")
teams = {t['id']: t for t in bs['teams']}
pos_types = {e['id']: e['singular_name_short'] for e in bs['element_types']}
fix = api_get("fixtures/")
gw2 = [f for f in fix if f.get('event') == 2]

team_diff = {}
for f in gw2:
    team_diff[f['team_h']] = ('H', f.get('team_a_difficulty'), teams[f['team_a']]['name'])
    team_diff[f['team_a']] = ('A', f.get('team_h_difficulty'), teams[f['team_h']]['name'])

# candidates
cands = ['João Pedro', 'Calafiori', 'Haaland', 'Mbeumo', 'Saka', 'Palmer', 'Tzolis',
         'Amad', 'Zirkzee', 'Garnacho', 'Rashford', 'Eze', 'Mateta', 'Isak', 'Gordon',
         'Salah', 'Diaz', 'Jota', 'Havertz', 'Neto', 'Enzo', 'Jackson', 'Watkins']

print(f"{'Player':<15} {'Pos':<4} {'Team':<16} {'Cost':<6} {'GW1':<5} {'Own%':<7} GW2")
for p in bs['elements']:
    if p['web_name'] not in cands:
        continue
    tid = p['team']
    tname = teams.get(tid, {}).get('name', '?')
    opp = team_diff.get(tid)
    oppstr = '-'
    if opp:
        oppstr = f"{opp[0]} vs {opp[2]} (FDR {opp[1]})"
    print(f"{p['web_name']:<15} {pos_types.get(p['element_type'],'?'):<4} {tname:<16} £{p['now_cost']/10:<5} {p['total_points']:<5} {p['selected_by_percent']:<7} {oppstr}")
    print(f"   news: {p.get('news','') or '-'}")