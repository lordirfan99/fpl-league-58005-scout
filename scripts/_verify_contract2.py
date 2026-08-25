import json

with open(r'C:\Users\irfan\projects\fpl-league-58005-scout\data\gw1_league58005_data.json') as f:
    d = json.load(f)

c = d['competitors'][0]
print("gw_transfers:", c.get('gw_transfers'))
print("gw_transfers_cost:", c.get('gw_transfers_cost'))
print("captain:", c.get('captain'))
print("vice_captain:", c.get('vice_captain'))
print("active_chip:", c.get('active_chip'))
print("entry_id:", c.get('entry_id'))
print("squad_cost:", c.get('squad_cost'))
print("league_rank:", c.get('league_rank'))
print("entry_name:", c.get('entry_name'))
print("player_name:", c.get('player_name'))

# Check squad for form field
print("\nSquad[0] keys:", list(c['squad'][0].keys()))
print("Has form:", 'form' in c['squad'][0])

# Check if there's any competitor with transfer_details
has_td = [c for c in d['competitors'] if 'transfer_details' in c]
print(f"\nCompetitors with transfer_details: {len(has_td)}")

# Check if transfer_details is a nested key within any structure
# Let's look at all keys of first 3 competitors
for i, c2 in enumerate(d['competitors'][:3]):
    print(f"\nCompetitor {i} all keys: {list(c2.keys())}")

# Check chips_used structure
print(f"\nCompetitor 0 chips_used: {c.get('chips_used')}")
print(f"Competitor 1 chips_used: {d['competitors'][1].get('chips_used')}")

# Check if any chips_used has 'chip_name' key
for c2 in d['competitors'][:5]:
    chips = c2.get('chips_used', [])
    for chip in chips:
        print(f"  chip keys: {list(chip.keys())}, chip_name: {chip.get('chip_name', 'MISSING')}")

# Check for 'form' in any squad
has_form = any('form' in p for c2 in d['competitors'][:5] for p in c2.get('squad', []))
print(f"\nForm field in squad: {has_form}")