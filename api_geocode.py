import pandas as pd
import os 
import requests
import time 
import pickle
from tqdm import tqdm
import numpy as np

def geocode_address(address, api_key):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": api_key
    }

    response = requests.get(url, params=params)
    data = response.json()

    if data["status"] == "OK":
        result = data["results"][0]
        lat = result["geometry"]["location"]["lat"]
        lng = result["geometry"]["location"]["lng"]
        formatted_address = result["formatted_address"]

        components = result["address_components"]
        postcode = next((c["long_name"] for c in components if "postal_code" in c["types"]), None)
        locality = next((c["long_name"] for c in components if "postal_town" in c["types"] or "neighborhood" in c["types"]), None)

        return {
            "lat": lat,
            "lng": lng,
            "postcode": postcode,
            "locality": locality,
            "full_address": formatted_address
        }
        
    else:
        print("Geocoding failed:", data.get("status"))
        return None


def reverse_geocode(lat, lng, api_key):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "latlng": f"{lat},{lng}",
        "key": api_key,
        "region": "uk"  # Adds UK bias but doesn't restrict
    }

    response = requests.get(url, params=params)
    data = response.json()

    if data["status"] == "OK":
        result = data["results"][0]

        # extract components
        components = result["address_components"]
        country = next((c["long_name"] for c in components if "country" in c["types"]), None)
        admin_area = next((c["long_name"] for c in components if "administrative_area_level_2" in c["types"]), None)

        # Greater London only
        if country != "United Kingdom" or admin_area != "Greater London":
            return None

        # get postcode and outcode
        postcode = next((c["long_name"] for c in components if "postal_code" in c["types"]), None)
        outcode = postcode.split()[0] if postcode else None
        return outcode

    else:
        print("Reverse geocoding failed:", data.get("status"))
        return None
       