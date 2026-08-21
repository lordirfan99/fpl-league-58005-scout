#!/usr/bin/env python3
"""Send welcome message to the new #gw-scout channel"""
import json
import os
import subprocess

script_path = r'C:\Users\irfan\AppData\Local\hermes\scripts\discord_embed.py'
if not os.path.exists(script_path):
    print("NO_SCRIPT")
    exit(1)

spec = {
    'title': '🚀 FPL GW Scout — Channel Aktif!',
    'description': 'Channel ni adalah **pusat** untuk semua data & analysis mingguan FPL Scout. Setiap GW lepas deadline, semua data competitor akan dikumpul dan analysis akan dihantar sini.',
    'color': 0x00FF00,
    'fields': [
        {
            'name': '📋 Liputan',
            'value': '**League 58005** — LIGA FPL KK OLD BOYS S5 (737 managers)\n**League 131997** — OVERALL IFE 26/27 [MUSIM KE-7] (1,816 managers)',
            'inline': False
        },
        {
            'name': '📊 Setiap GW Dapat:',
            'value': '• **GW Report** — ownership, top scorer, captain trends, formations\n• **Elite Watch** — squad detail setiap competitor top (Diesel FC, Go Kapit, Kiukiu Fc, dll)\n• **Strategy** — template weaknesses, differential opportunities, transfer trends',
            'inline': False
        },
        {
            'name': '⏰ Jadual',
            'value': '**GW1:** Malam ni 3:00 AM MYT (lepas deadline 1:30 AM)\n**GW2–38:** Setiap Sabtu 4:00 AM MYT',
            'inline': False
        },
        {
            'name': '📂 Repo GitHub',
            'value': 'Data penuh & historical tracking: github.com/lordirfan99/fpl-league-58005-scout',
            'inline': False
        }
    ],
    'footer': 'SPORTMANIA BOT • FPL Scout',
    'timestamp': True
}

spec_path = os.path.expanduser(r'C:\Users\irfan\AppData\Local\hermes\scripts\fpl_scout_welcome.json')
with open(spec_path, 'w') as f:
    json.dump(spec, f)

result = subprocess.run(
    ['python3', script_path, '--channel', '1540387928201629706', '--json', spec_path],
    capture_output=True, text=True
)
print(result.stdout)
if result.stderr:
    print('STDERR:', result.stderr[:500])