import json, sys
from collections import Counter
sys.stdout.reconfigure(line_buffering=True)

DATA = r'C:\Users\irfan\projects\fpl-league-58005-scout\data\gw1_league58005_data.json'
ANALYSIS = r'C:\Users\irfan\projects\fpl-league-58005-scout\reports\GW1\GW1_L58005_analysis.json'

d = json.load(open(DATA))
a = json.load(open(ANALYSIS))

me = [c for c in d['competitors'] if c['entry_id'] == 2797967][0]
print('=== KOKDIANG FC squad (GW1) ===')
print('entry:', me['entry_id'], '| manager:', me['player_name'], '| GW pts:', me['gw_points'], '| rank:', me['league_rank'])
print('captain:', me['captain'], '| vice:', me['vice_captain'], '| cost:', me['squad_cost'], '| chip:', me.get('active_chip'))
print('composition:', me['squad_composition'])
print()

# ownership map from analysis json
own = {t['name']: t['pct'] for t in a['squad_ownership']['top_owned']}
cap_pct = {c['name']: c['percentage'] for c in a['squad_ownership']['captain_choices']}

squad = me['squad']
print(f"{'Player':<22} {'Pos':<4} {'Team':<12} {'Cost':<6} {'Own%':<7} {'C/VC'}")
for s in squad:
    name = s['name']
    ownpct = own.get(name, 0.0)
    mark = 'C' if s['is_captain'] else ('VC' if s['is_vice_captain'] else '')
    print(f"{name:<22} {s['position']:<4} {s['team']:<12} £{s['cost']:<5} {ownpct:<7} {mark}")

# count how many of squad are template vs differential
template = set(a['squad_ownership']['template_players'])
n_template = sum(1 for s in squad if s['name'] in template)
n_low = sum(1 for s in squad if own.get(s['name'], 0) < 10 and own.get(s['name'], 0) > 0)
print()
print(f'Template players (>50% own) in squad: {n_template}/15 ({template & {s["name"] for s in squad}})')
print(f'Differentials (<10% own) in squad: {n_low}')

# top scorer captains / what won GW1
print()
print('=== GW1 top scorer captain edges ===')
for name, pct in sorted(cap_pct.items(), key=lambda x: -x[1])[:8]:
    print(f'  {name}: {pct}% captained')

# check who owns same captain differential
print()
print('=== Squad cost percentile ===')
costs = sorted(c['squad_cost'] for c in d['competitors'] if c.get('squad_cost'))
mycost = me['squad_cost']
below = sum(1 for c in costs if c < mycost)
print(f'  my cost {mycost}, percentile: {below/len(costs)*100:.1f}% cheaper than league')