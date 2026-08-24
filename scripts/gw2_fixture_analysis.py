#!/usr/bin/env python3
"""GW2 fixtures + difficulty analysis for KOKDIANG FC."""
import urllib.request, json, sys
from collections import defaultdict
sys.stdout.reconfigure(line_buffering=True)

BASE = "https://fantasy.premierleague.com/api"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def api_get(path):
    req = urllib.request.Request(f"{BASE}/{path}", headers=HEADERS)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

# Bootstrap for team names + team strength + player map
bs = api_get("bootstrap-static/")
teams = {t['id']: t for t in bs['teams']}
events = {e['id']: e for e in bs['events']}

# Players map for my squad (web_name -> player)
players = {p['web_name']: p for p in bs['elements']}

fix = api_get("fixtures/")
print(f"Total fixtures in API: {len(fix)}")

# Group by event
by_event = defaultdict(list)
for f in fix:
    by_event[f.get('event')].append(f)

for ev in sorted([e for e in by_event if e], key=lambda x: x):
    done = sum(1 for f in by_event[ev] if f.get('finished'))
    print(f"  Event {ev}: {len(by_event[ev])} fixtures ({done} finished)")

# ---- GW1 actual RESULTS ----
print("\n=== GW1 RESULTS (actual scores) ===")
gw1 = [f for f in fix if f.get('event') == 1]
results = []
for f in gw1:
    if f.get('finished'):
        th, ta = teams[f['team_h']], teams[f['team_a']]
        results.append((th['name'], f['team_h_score'], ta['name'], f['team_a_score'], f.get('team_h_difficulty'), f.get('team_a_difficulty')))
for r in sorted(results, key=lambda x: -(x[1] + x[3])):
    print(f"  {r[0]} {r[1]} - {r[2]} {r[3]}  (H diff {r[4]}, A diff {r[5]})")

# ---- GW2 fixtures ----
print("\n=== GW2 FIXTURES ===")
gw2 = [f for f in fix if f.get('event') == 2]
print(f"GW2 fixture count: {len(gw2)}")
gw2_list = []
for f in gw2:
    th, ta = teams[f['team_h']], teams[f['team_a']]
    gw2_list.append((th['name'], ta['name'], f.get('team_h_difficulty'), f.get('team_a_difficulty'), f['id']))
for r in sorted(gw2_list, key=lambda x: x[2] + x[3]):
    print(f"  {r[0]} (H, diff {r[2]}) vs {r[1]} (A, diff {r[3]})")

# ---- MY SQUAD + GW2 opponent difficulty ----
print("\n=== MY SQUAD GW2 OPPONENTS ===")
my_squad = ['Raya','Gabriel','Truffert','Tarkowski','Guehi','Senesi','Rice','Semenyo','Anderson','B.Fernandes','Calvert-Lewin','Kelleher','Sadiki','Igor Jesus','Strand Larsen']
# B.Fernandes is web_name with dot
my_squad = ['Raya','Gabriel','Truffert','Tarkowski','Guehi','Senesi','Rice','Semenyo','Anderson','B.Fernandes','Calvert-Lewin','Kelleher','Sadiki','Igor Jesus','Strand Larsen']

# build team -> difficulty map for GW2
team_diff = {}
for f in gw2:
    team_diff[f['team_h']] = ('H', f.get('team_a_difficulty'), teams[f['team_a']]['name'])
    team_diff[f['team_a']] = ('A', f.get('team_h_difficulty'), teams[f['team_h']]['name'])

# map player -> team
player_team = {}
for p in bs['elements']:
    player_team[p['web_name']] = (p['team'], p['element_type'], p['now_cost']/10, p['total_points'], p['selected_by_percent'], p.get('status'), p.get('news',''))

for name in my_squad:
    info = player_team.get(name)
    if not info:
        print(f"  {name:<20} NOT FOUND")
        continue
    tid, etype, cost, tp, sel, status, news = info
    tname = teams.get(tid, {}).get('name', '?')
    opp = team_diff.get(tid)
    if opp:
        h_a, diff, oppname = opp
        diffstars = '★' * (5 - diff + 1) if diff else ''
        print(f"  {name:<20} {tname:<14} GW2: {h_a} vs {oppname:<14} (FDR {diff}){ ' | ' + news if news else ''}")
    else:
        print(f"  {name:<20} {tname:<14} GW2: NO FIXTURE?!")

# ---- Team strength ratings for guidance ----
print("\n=== TEAM STRENGTH RATINGS (attack/defence) ===")
for t in sorted(bs['teams'], key=lambda x: -x.get('strength_overall_home', 0))[:8]:
    print(f"  {t['name']:<18} Ovr {t.get('strength_overall_home',0)}/{t.get('strength_overall_away',0)} Att {t.get('strength_attack_home',0)}/{t.get('strength_attack_away',0)} Def {t.get('strength_defence_home',0)}/{t.get('strength_defence_away',0)}")

# Save GW2 fixtures for later use
with open(r'C:\Users\irfan\projects\fpl-league-58005-scout\data\gw2_fixtures.json', 'w') as f:
    json.dump({'gw2': [{'team_h': teams[x['team_h']]['name'], 'team_a': teams[x['team_a']]['name'], 'team_h_difficulty': x.get('team_h_difficulty'), 'team_a_difficulty': x.get('team_a_difficulty')} for x in gw2], 'gw1_results': [{'team_h': r[0], 'h': r[1], 'team_a': r[2], 'a': r[3]} for r in results]}, f, indent=2)
print("\nsaved gw2_fixtures.json")