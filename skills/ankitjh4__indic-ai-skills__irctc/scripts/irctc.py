#!/usr/bin/env python3
"""Indian Railways CLI using RailwayAPI.com"""

import os
import sys
import requests
import json
from datetime import datetime

API_BASE = "https://railwayapi.com/api/v2"

def get_api_key():
    key = os.environ.get("RAILWAYAPI_KEY")
    if not key:
        print("Error: RAILWAYAPI_KEY not set")
        print("Get free key at https://railwayapi.com")
        print("Add to Zo: Settings → Advanced → Secrets → RAILWAYAPI_KEY")
        sys.exit(1)
    return key

def pnr_status(pnr):
    api_key = get_api_key()
    url = f"{API_BASE}/pnr-status/pnr/{pnr}/apikey/{api_key}/"
    resp = requests.get(url)
    data = resp.json()
    
    if data.get("response_code") != 200:
        print(f"Error: {data.get('message', 'Failed')}")
        return
    
    print(f"\n📋 PNR: {pnr}")
    print(f"Train: {data.get('train_name')} ({data.get('train_num')})")
    print(f"From: {data.get('from_station_code')} → {data.get('to_station_code')}")
    print(f"Date: {data.get('doj')}")
    print(f"Class: {data.get('class')}")
    print(f"Total Passengers: {data.get('total_passengers')}")
    print("\nPassenger Status:")
    for p in data.get("passengers", []):
        print(f"  {p.get('sr')}. {p.get('booking_status')} | Current: {p.get('current_status')}")

def search_trains(from_stn, to_stn, date_str):
    api_key = get_api_key()
    # Format: DD-MM-YYYY
    date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d-%m-%Y")
    
    url = f"{API_BASE}/trains-between-stations/source/{from_stn}/destination/{to_stn}/date/{date}/apikey/{api_key}/"
    resp = requests.get(url)
    data = resp.json()
    
    if data.get("response_code") != 200:
        print(f"Error: {data.get('message', 'Failed')}")
        return
    
    trains = data.get("trains", [])
    print(f"\n🚂 Found {len(trains)} trains from {from_stn} to {to_stn} on {date_str}:\n")
    
    for t in trains:
        print(f"  {t['train_num']} | {t['name']}")
        print(f"  Depart: {t['departure_time']} → Arrive: {t['arrival_time']} | Duration: {t['duration']}")
        print(f"  Days: {t['days']}")
        print()

def live_status(train_num, date_str):
    api_key = get_api_key()
    date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d-%m-%Y")
    
    url = f"{API_BASE}/live-train-status/train/{train_num}/date/{date}/apikey/{api_key}/"
    resp = requests.get(url)
    data = resp.json()
    
    if data.get("response_code") != 200:
        print(f"Error: {data.get('message', 'Failed')}")
        return
    
    print(f"\n🚂 Live Status: {data.get('train_name')} ({data.get('train_num')})")
    print(f"Position: {data.get('position')}")
    print(f"Last Update: {data.get('last_updated')}")
    print("\nRoute:")
    for s in data.get("route", []):
        print(f"  {s['station_name']} ({s['station_code']}) - Arr: {s['arrival']}, Dep: {s['departure']}, Dist: {s['distance']}km")

def search_station(query):
    api_key = get_api_key()
    url = f"{API_BASE}/stations/name/{query}/apikey/{api_key}/"
    resp = requests.get(url)
    data = resp.json()
    
    if data.get("response_code") != 200:
        print(f"Error: {data.get('message', 'Failed')}")
        return
    
    stations = data.get("stations", [])
    print(f"\n🏢 Found {len(stations)} stations:\n")
    for s in stations:
        print(f"  {s['code']} | {s['name']} | {s.get('zone', 'N/A')} | {s.get('state', 'N/A')}")

def main():
    if len(sys.argv) < 2:
        print("Indian Railways CLI")
        print("Usage: python irctc.py <command> [args]")
        print("\nCommands:")
        print("  pnr <pnr_number>          - Check PNR status")
        print("  trains <from> <to> <date> - Search trains (date: YYYY-MM-DD)")
        print("  live <train_num> <date>  - Live train status")
        print("  station <name>           - Search stations")
        print("\nGet API key: https://railwayapi.com")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "pnr" and len(sys.argv) >= 3:
        pnr_status(sys.argv[2])
    elif cmd == "trains" and len(sys.argv) >= 4:
        search_trains(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "live" and len(sys.argv) >= 3:
        date = sys.argv[3] if len(sys.argv) >= 4 else datetime.now().strftime("%Y-%m-%d")
        live_status(sys.argv[2], date)
    elif cmd == "station" and len(sys.argv) >= 3:
        search_station(sys.argv[2])
    else:
        print("Invalid command. See usage above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
