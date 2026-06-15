#!/usr/bin/env python3
"""
RailRadar API - Indian Railways
pip install requests
"""
import os
import sys
import requests
import json

BASE_URL = "https://railradar.in/api/v1"

def get_api_key():
    """Get API key from environment - works with any system"""
    api_key = os.environ.get("RAILRADAR_API_KEY")
    if not api_key:
        print("Error: RAILRADAR_API_KEY not set")
        print("Get free key at: https://railradar.in")
        print("Then run: export RAILRADAR_API_KEY=your-key")
        sys.exit(1)
    return api_key

def search_stations(query):
    """Search railway stations"""
    api_key = get_api_key()
    url = f"{BASE_URL}/search/stations"
    params = {"q": query}
    headers = {"X-API-Key": api_key}
    
    resp = requests.get(url, params=params, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        for station in data.get("stations", [])[:10]:
            print(f"{station['code']} - {station['name']} ({station.get('city', 'N/A')})")
    else:
        print(f"Error: {resp.status_code} - {resp.text}")

def trains_between(from_code, to_code):
    """Find trains between stations"""
    api_key = get_api_key()
    url = f"{BASE_URL}/trains-between-stations"
    params = {"from": from_code, "to": to_code}
    headers = {"X-API-Key": api_key}
    
    resp = requests.get(url, params=params, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        for train in data.get("trains", [])[:10]:
            print(f"{train['number']} - {train['name']}")
            print(f"  Dep: {train['departure']} | Arr: {train['arrival']} | Dur: {train['duration']}")
            print(f"  Days: {train.get('running_days', 'N/A')}")
            print()
    else:
        print(f"Error: {resp.status_code} - {resp.text}")

def live_status(train_no):
    """Get live train status"""
    api_key = get_api_key()
    url = f"{BASE_URL}/live-train-status"
    params = {"train": train_no}
    headers = {"X-API-Key": api_key}
    
    resp = requests.get(url, params=params, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        status = data.get("status", {})
        print(f"Train: {status.get('train_name', 'N/A')} ({status.get('train_no', '')})")
        print(f"Status: {status.get('current_status', 'N/A')}")
        print(f"Location: {status.get('current_station', 'N/A')}")
        print(f"Last Update: {status.get('last_updated', 'N/A')}")
    else:
        print(f"Error: {resp.status_code} - {resp.text}")

def main():
    if len(sys.argv) < 2:
        print("RailRadar CLI")
        print("Usage: python railradar.py <command> [args]")
        print("Commands:")
        print("  stations <query>     - Search stations")
        print("  trains <from> <to>  - Find trains between stations")
        print("  live <train_no>     - Live train status")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "stations" and len(sys.argv) >= 3:
        search_stations(sys.argv[2])
    elif cmd == "trains" and len(sys.argv) >= 4:
        trains_between(sys.argv[2], sys.argv[3])
    elif cmd == "live" and len(sys.argv) >= 3:
        live_status(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
