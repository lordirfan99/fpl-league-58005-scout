#!/usr/bin/env python3
"""Check the data structure of full_scout_data.json"""
import json
from collections import Counter

with open(r'C:\Users\irfan\projects\fpl-league-58005-scout\data\full_scout_data.json') as f:
    d = json.load(f)

print('keys:', list(d.keys()))
print()

leagues = d.get('leagues', [])
print('leagues:')
for l in leagues:
    print(f'  {l["league_id"]}: {l["league_name"]} ({l["member_count"]} members)')
print()

memberships = d.get('memberships', [])
print(f'memberships: {len(memberships)} items')
league_counts = Counter()
for m in memberships:
    if isinstance(m, dict):
        league_counts[m.get('league_id', '?')] += 1
for lid, cnt in sorted(league_counts.items()):
    print(f'  League {lid}: {cnt} members')
print()

if memberships and isinstance(memberships[0], dict):
    print('Sample membership:', json.dumps(memberships[0], indent=2)[:400])