import json, sys
sys.stdout.reconfigure(line_buffering=True)
CACHE = r'C:\Users\irfan\projects\fpl-league-58005-scout\data\bootstrap_cache.json'
bs = json.load(open(CACHE))
# GW1 player totals from bootstrap
bps = {p['web_name']: {'total': p['total_points'], 'form': float(p.get('form',0) or 0), 'cost': p['now_cost']/10, 'sel': p['selected_by_percent']} for p in bs['elements']}

print('=== TEMPLATE PLAYER GW1 POINTS (yang aku MISS) ===')
for n in ['João Pedro', 'Haaland', 'Calafiori', 'Mbeumo', 'B.Fernandes']:
    i = bps.get(n, {})
    print(f"  {n:<22} GW1: {i.get('total',0)} pts | cost £{i.get('cost','?')}m | owned {i.get('sel','?')}%")

print()
print('=== MY PLAYERS GW1 (full 15) ===')
mynames = ['Raya','Gabriel','Truffert','Tarkowski','Guéhi','Senesi','Rice','Semenyo','Anderson','B.Fernandes','Calvert-Lewin','Kelleher','Sadiki','Igor Jesus','Strand Larsen']
for n in mynames:
    i = bps.get(n, {})
    print(f"  {n:<22} GW1: {i.get('total',0):>2} pts | cost £{i.get('cost','?')}m | owned {i.get('sel','?')}%")

print()
print('=== OPPORTUNITY COST (my team vs template combo) ===')
my_pts = {'Raya':6,'Gabriel':5,'Truffert':1,'Tarkowski':6,'Guéhi':10,'Senesi':3,'Rice':3,'Semenyo':2,'Anderson':2,'B.Fernandes':2,'Calvert-Lewin':1,'Kelleher':7,'Sadiki':2,'Igor Jesus':2,'Strand Larsen':1}
template_pts = {'João Pedro': None, 'Haaland': None, 'Calafiori': None, 'Mbeumo': None, 'B.Fernandes': 2}
for n, t in [('João Pedro', bps.get('João Pedro',{}).get('total',0)), ('Haaland', bps.get('Haaland',{}).get('total',0)), ('Calafiori', bps.get('Calafiori',{}).get('total',0)), ('Mbeumo', bps.get('Mbeumo',{}).get('total',0))]:
    print(f"  {n}: GW1 {t} pts — kalau aku ada dia, +{t} vs gantian aku")