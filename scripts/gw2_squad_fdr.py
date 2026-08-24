#!/usr/bin/env python3
"""CORRECTED GW2 fixture difficulty for my squad (team_h_difficulty for home, team_a for away)."""
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

# FDR semantics: team_h_difficulty = difficulty for HOME team's opponent rating;
# team_a_difficulty = difficulty for AWAY team. For a MY player:
#   home player -> FDR = team_h_difficulty ; away player -> FDR = team_a_difficulty
team_fdr = {}
for f in gw2:
    th, ta = teams[f['team_h']]['name'], teams[f['team_a']]['name']
    team_fdr[f['team_h']] = (th, 'H', f['team_h_difficulty'], ta)
    team_fdr[f['team_a']] = (ta, 'A', f['team_a_difficulty'], th)

my_squad = ['Raya','Gabriel','Truffert','Tarkowski','Guéhi','Senesi','Rice','Semenyo','Anderson','B.Fernandes','Calvert-Lewin','Kelleher','Sadiki','Igor Jesus','Strand Larsen']

player_info = {p['web_name']: p for p in bs['elements']}

print(f"{'Player':<18} {'Pos':<4} {'Team':<15} {'GW1':<5} {'Own%':<7} {'Cost':<6} GW2 (FDR)")
for name in my_squad:
    p = player_info.get(name)
    if not p:
        print(f"  {name:<18} NOT FOUND (accent?)")
        continue
    tid = p['team']
    tname, h_a, fdr, opp = team_fdr.get(tid, (teams.get(tid,{}).get('name','?'), '?', '-', '?'))
    news = p.get('news','')
    extra = f" | {news}" if news else ""
    print(f"  {name:<18} {pos_types.get(p['element_type'],'?'):<4} {tname:<15} {p['total_points']:<5} {p['selected_by_percent']:<7} £{p['now_cost']/10:<5} {h_a} vs {opp} (FDR {fdr}){extra}")