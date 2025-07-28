
import json
import os
import pandas as pd
import os 
import requests
import time 
import pickle
from tqdm import tqdm
import numpy as np
from geopy.geocoders import Nominatim


CACHE_FILE = "cache_commute_times.json"

# Load existing cache if exists
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        commute_cache = json.load(f)
else:
    commute_cache = {}

def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(commute_cache, f)






# best commute time

def get_best_commute_time(origin, destination, api_key): # get the fasted commute time 
    modes = ["driving","transit","waling","bicycling"] # transit = public transport
    results = {}

    
    for mode in modes:
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            "origins":origin,
            "destinations":destination,
            "mode":mode,
            "units":"metric",
            "key":api_key,
            "region":"uk"
        }
        
    
        
        try:
            response = requests.get(url, params = params)
            data = response.json()
            if data["status"] == "OK":
                element = data["rows"][0]["elements"][0]
                if element["status"] == "OK":
                    duration = element["duration"]["value"]
                    results[mode] = duration
        except (KeyError, IndexError):
            pass 
        

    if results:
        best_mode = min(results, key=results.get)
        best_time = round(results[best_mode] / 60, 1)
        
        if best_mode == "transit":
            best_mode = "public transport"

        return best_mode, f"{best_time} mins"


    else:   
        return None, None 
    
# commute time for all methods (modes)

def get_commute_times_all_modes(origin, destination, api_key):
    modes = ["driving", "transit", "bicycling", "walking"]
    results = {}

    for mode in modes:
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            "origins": origin,
            "destinations": destination,
            "mode": mode,
            "units": "metric",
            "key": api_key
        }

        try:
            response = requests.get(url, params = params)
            data = response.json()
            if data["status"] == "OK":
                element = data["rows"][0]["elements"][0]
                if element["status"] == "OK":
                    duration_secs = element["duration"]["value"]
                    duration_text = element["duration"]["text"]
                    mode_label = "public transport" if mode == "transit" else mode
                    results[mode_label] = duration_text
        except Exception as e:
            print(f"Error retrieving {mode} time:", e)

    return results
