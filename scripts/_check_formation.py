import json
with open('C:/Users/irfan/projects/fpl-league-58005-scout/data/gw1_league58005_data.json') as f:
    d = json.load(f)

# Check first competitor - use position index (0-10 = starters, 11-14 = bench)
c = d['competitors'][0]
print(f'Team: {c["entry_name"]}')
print(f'Squad composition (from API): {c["squad_composition"]}')
print()
for i, p in enumerate(c['squad']):
    status = 'START' if i < 11 else 'BENCH'
    print(f'  [{i:2d}] {p["name"]:20s} {p["position"]:4s} {p["team"]:15s} {status}')

# Count on-field formation
from collections import Counter
onfield = [p['position'] for i, p in enumerate(c['squad']) if i < 11]
print(f'\nOn-field formation: {dict(Counter(onfield))}')

# Check all competitors
formations = Counter()
for c in d['competitors']:
    of = tuple(sorted([p['position'] for i, p in enumerate(c['squad']) if i < 11]))
    formations[of] += 1
print(f'\nFormation diversity across all {len(d["competitors"])} competitors:')
for f, n in formations.most_common(10):
    # Format nicely
    parts = {}
    for pos in f:
        parts[pos] = parts.get(pos, 0) + 1
    formatted = f"{parts.get('GKP',0)}-{parts.get('DEF',0)}-{parts.get('MID',0)}-{parts.get('FWD',0)}"
    print(f'  {formatted:15s} = {n} managers ({n/len(d["competitors"])*100:.1f}%)')