# database.py
import json
import os

def retrieve(filename: str) -> dict:
    """Retrieve data from a local JSON file."""
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}  # Return an empty dict if file doesn't exist

def update(data, filename: str):
    """Update data in a local JSON file."""
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)
