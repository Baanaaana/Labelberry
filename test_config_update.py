#!/usr/bin/env python3
import requests
import json

# Test updating config via API
pi_id = "5c2d13c6-7bf4-407e-85d3-c61d4851ee55"
config = {
    "default_darkness": 5,
    "default_speed": 6,
    "override_settings": True
}

url = f"http://localhost:8080/api/pis/{pi_id}/config"
response = requests.put(url, json=config)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")