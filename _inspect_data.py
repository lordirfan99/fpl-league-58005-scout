import json

for league in (58005, 131997):
    path = f"data/gw1_league{league}_data.json"
    d = json.load(open(path))
    comps = d.get('competitors', [])
    print(f"=== League {league} ===")
    print("  total_entries:", d.get('total_entries'))
    print("  errors:", d.get('errors'))
    print("  competitors:", len(comps))
    if comps:
        c = comps[0]
        print("  sample keys:", list(c.keys()))
        print("  sample:", c.get('entry_name'), "| gw_pts:", c.get('gw_points'), "| picks:", len(c.get('picks', []) or []))
    now = d.get('fetched_at')
    print("  fetched_at:", now)
