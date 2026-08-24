import json, sys
sys.stdout.reconfigure(line_buffering=True)

DATA = r'C:\Users\irfan\projects\fpl-league-58005-scout\data\gw1_league58005_data.json'
CACHE = r'C:\Users\irfan\projects\fpl-league-58005-scout\data\bootstrap_cache.json'
d = json.load(open(DATA))
bs = json.load(open(CACHE))

# player id -> total points (GW1 cumulative) from bootstrap
bps = {}
for p in bs['elements']:
    bps[p['web_name']] = {'total': p['total_points'], 'form': float(p.get('form', 0) or 0), 'pts_per_game': p.get('points_per_game', 0), 'news': p.get('news', '')}

me = [c for c in d['competitors'] if c['entry_id'] == 2797967][0]
squad = me['squad']

print('=== GW1 SCORECARD — KOKDIANG FC ===')
total_pts = 0
for s in squad:
    info = bps.get(s['name'], {})
    mult = 2 if s['is_captain'] else 1
    scored = info.get('total', 0) * mult
    total_pts += scored
    mark = 'C' if s['is_captain'] else ('VC' if s['is_vice_captain'] else '')
    news = f" | {info['news']}" if info.get('news') else ''
    print(f"  {s['name']:<22} {s['position']:<4} x{mult} = {scored:>3} pts (base {info.get('total',0)}) {mark}{news}")
print(f'  TOTAL (captain doubled): {total_pts}')

# captain wasted or not?
print()
print('=== WHO WAS THE CROWD — LEADERBOARD DIFFERENTIAL ===')
# key: how many in top10 owned him vs his difference
# quick sanity: GW avg 46.1, his squad sum
print(f'  League avg GW pts: 46.1 | His squad total: {total_pts} | diff: {total_pts - 46.1:+.1f}')
print(f'  His GW1 official: 43 | squad sum (from bootstrap cumulative): {total_pts}')

# his players on bench (multiplier 0 means bench in picks? no — multiplier is 1 unless captain)
# check whether any of his differentials actually scored
print()
print('=== DIFFERENTIAL PERFORMANCE (his <10% players) ===')
diffs = ['Truffert', 'Guéhi', 'Senesi', 'Rice', 'Anderson', 'Kelleher', 'Sadiki', 'Igor Jesus', 'Strand Larsen']
for n in diffs:
    info = bps.get(n, {})
    print(f"  {n:<22} GW1: {info.get('total', 0)} pts | form: {info.get('form', 0)} | ppg: {info.get('pts_per_game', 0)}")