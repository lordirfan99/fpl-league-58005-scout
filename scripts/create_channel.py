#!/usr/bin/env python3
"""Create a new Discord channel for FPL GW Scout"""
import json
import os
import urllib.request
import urllib.error

# Load token
token = os.environ.get('DISCORD_BOT_TOKEN') or os.environ.get('DISCORD_TOKEN')
if not token:
    env_path = os.path.expanduser(r'C:\Users\irfan\AppData\Local\hermes\.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith('DISCORD_BOT_TOKEN=') or line.startswith('DISCORD_TOKEN='):
                    token = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
                    break

if not token:
    print("NO_TOKEN")
    exit(1)

# Create channel under the ⚽ fpl category
url = 'https://discord.com/api/v10/guilds/1538852589133766656/channels'
payload = {
    'name': 'gw-scout',
    'type': 0,  # text channel
    'topic': '📊 FPL GW Scout — Data & analysis mingguan. Ownership, elite watch, competitor tracking, strategy.',
    'parent_id': '1538863115192762439',  # ⚽ fpl category
    'position': 11
}

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode(),
    headers={
        'Authorization': f'Bot {token}',
        'Content-Type': 'application/json',
        'User-Agent': 'DiscordBot (https://hermes-agent.nousresearch.com, 1.0)'
    },
    method='POST'
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())
        print(f"OK: channel_id={body['id']} name={body['name']}")
except urllib.error.HTTPError as e:
    err = e.read().decode()
    print(f"HTTP {e.code}: {err[:500]}")