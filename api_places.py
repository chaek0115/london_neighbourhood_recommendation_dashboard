import pandas as pd
import os 
import requests
import time 
import pickle
from tqdm import tqdm
import numpy as np

def get_places_nearby(lat, lng, place_type, api_key):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": 1000,  # meters
        "type": place_type,
        "key": api_key
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if data["status"] == "OK":
            return [place["name"] for place in data["results"]]
        else:
            print("No places found:", data.get("status", "Unknown error"))
            return []

    except Exception as e:
        print(f"Error retrieving places: {e}")
        return []
