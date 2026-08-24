import json, sys, urllib.request
from collections import defaultdict, Counter
sys.stdout.reconfigure(line_buffering=True)

DATA = r'C:\Users\irfan\projects\fpl-league-58005-scout\data\gw1_league58005_data.json'
d = json.load(open(DATA))
comps = d['competitors']
total = len(comps)
me = [c for c in comps if c['entry_id'] == 2797967][0]

# REAL ownership across all 737 teams (not just top30 from analysis)
player_count = Counter()
for c in comps:
    seen = set()
    for s in c.get('squad', []):
        if s['name'] not in seen:
            seen.add(s['name'])
            player_count[s['name']] += 1

print('=== MY 15 PLAYERS — REAL LEAGUE OWNERSHIP (737 teams) ===')
squad = me['squad']
for s in squad:
    cnt = player_count.get(s['name'], 0)
    print(f"{s['name']:<22} {s['position']:<4} {cnt:>4} teams  {cnt/total*100:5.1f}%")

# template check
print()
print('=== LEAGUE TEMPLATE WHAT I\'M MISSING ===')
template = [n for n, c in player_count.items() if c/total >= 0.50]
myset = {s['name'] for s in squad}
for n in sorted(template, key=lambda x: -player_count[x]):
    mark = '✔ HAVE' if n in myset else '✘ MISS'
    print(f"  {n:<22} {player_count[n]/total*100:5.1f}%  {mark}")

# GW2 fixtures for his players' teams
print()
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
req = urllib.request.Request('https://fantasy.premierleague.com/api/bootstrap-static/', headers=HEADERS)
bs = json.loads(urllib.request.urlopen(req, timeout=30).read())
teams = {t['id']: t['name'] for t in bs['teams']}
events = {e['id']: e for e in bs['events']}
gw2 = next((e for e in bs['events'] if e['id'] == 2), None)
print('GW2 deadline:', gw2.get('deadline_time') if gw2 else 'unknown')

req2 = urllib.request.Request('https://fantasy.premierleague.com/api/fixtures/', headers=HEADERS)
fix = json.loads(urllib.request.urlopen(req2, timeout=30).read())
gw2fix = [f for f in fix if f.get('event') == 2]
# difficulty per team in GW2: use team difficulty ratings
tdr = {}
for f in gw2fix:
    tdr.setdefault(f['team_h'], []).append(('H', teams.get(f['team_a'], '?')))
    tdr.setdefault(f['team_a'], []).append(('A', teams.get(f['team_h'], '?')))

myteams = ['Arsenal', 'Man City', 'Spurs', 'Everton', 'Man Utd', 'Leeds', 'Brentford', 'Sunderland', "Nott'm Forest", 'Crystal Palace', 'Bournemouth']
print()
print('=== MY PLAYERS\' TEAMS — GW2 FIXTURES ===')
for s in squad:
    t = s['team']
    opps = tdr.get(t, [])
    opstr = ', '.join(f"{h/a} vs {o}" for h, a in opps) if opps else 'no fixture?'
    print(f"  {s['name']:<22} {t:<15} GW2: {opstr}")

# chips analysis for league
chips = Counter()
for c in comps:
    ch = c.get('chips_used') or []
    if ch:
        for e in ch:
            chips[e.get('name', '?')] += 1
    else:
        ac = c.get('active_chip', 'none')
        if ac and ac != 'none':
            chips[ac] += 1
print()
print('=== CHIP USAGE LEAGUE 58005 ===')
for name, cnt in chips.items():
    print(f'  {name}: {cnt} teams ({cnt/total*100:.1f}%)')
print(f'  No chip: {total - sum(chips.values())} teams ({(total - sum(chips.values()))/total*100:.1f}%)')