import json

# --- compact.json ---
with open(r'C:\Users\irfan\projects\fpl-league-58005-scout\data\gw1_league58005_compact.json') as f:
    compact = json.load(f)

c = compact['competitors'][0]
print("=== COMPACT.JSON ===")
print("Top-level keys:", list(compact.keys()))
print("Competitor keys:", list(c.keys()))
print()
print("league_last_rank:", c.get('league_last_rank', 'MISSING'))
print("entry_name:", c.get('entry_name'))
print("player_name:", c.get('player_name'))
print("league_rank:", c.get('league_rank'))
print("gw_points:", c.get('gw_points'))
print("total_points:", c.get('total_points'))
print("captain:", c.get('captain'))
print("transfers_made:", c.get('transfers_made'))
print("entry_id:", c.get('entry_id'))

# Check all competitors for league_last_rank
has_last_rank = [x for x in compact['competitors'] if 'league_last_rank' in x]
print(f"\nCompetitors WITH league_last_rank: {len(has_last_rank)} / {len(compact['competitors'])}")

# Check what fields the dashboard uses from compact.json
print("\n=== DASHBOARD USAGE FROM COMPACT ===")
print("Required fields: entry_id, entry_name, player_name, league_rank, league_last_rank, gw_points, total_points, captain, transfers_made")

# --- data.json ---
with open(r'C:\Users\irfan\projects\fpl-league-58005-scout\data\gw1_league58005_data.json') as f:
    data = json.load(f)

c2 = data['competitors'][0]
print("\n=== DATA.JSON ===")
print("Top-level keys:", list(data.keys()))
print("Competitor keys:", list(c2.keys()))
print("entry_name:", c2.get('entry_name', 'MISSING'))
print("player_name:", c2.get('player_name', 'MISSING'))
print("gw_points:", c2.get('gw_points', 'MISSING'))
print("total_points:", c2.get('total_points', 'MISSING'))
print("entry_id:", c2.get('entry_id', 'MISSING'))
print("league_rank:", c2.get('league_rank', 'MISSING'))
print("captain:", c2.get('captain', 'MISSING'))
print("transfers_made:", c2.get('transfers_made', 'MISSING'))
print("squad_cost:", c2.get('squad_cost', 'MISSING'))
print("Squad[0] keys:", list(c2['squad'][0].keys()))
print("chips_used:", c2.get('chips_used', 'MISSING'))

# Check for transfer_details
has_transfer_details = [c for c in data['competitors'] if c.get('transfer_details')]
print(f"\nCompetitors with transfer_details: {len(has_transfer_details)}")
if has_transfer_details:
    print("Sample transfer_details[0]:", json.dumps(has_transfer_details[0]['transfer_details'][0], indent=2))
else:
    # Check if any competitor has a different key for transfers
    for c in data['competitors'][:5]:
        extra = [k for k in c.keys() if k not in ('entry_id', 'gw', 'fetched_at', 'gw_points', 'total_points', 'overall_rank', 'gw_transfers', 'gw_transfers_cost', 'chips_used', 'squad')]
        if extra:
            print(f"Extra keys in competitor {c['entry_id']}: {extra}")

# Check for squad_cost on full data competitors
has_squad_cost = [c for c in data['competitors'] if 'squad_cost' in c]
print(f"\nCompetitors with squad_cost: {len(has_squad_cost)}")

# Check for entry_name / player_name
has_entry_name = [c for c in data['competitors'] if 'entry_name' in c]
has_player_name = [c for c in data['competitors'] if 'player_name' in c]
print(f"Competitors with entry_name: {len(has_entry_name)}")
print(f"Competitors with player_name: {len(has_player_name)}")