import json

def save_json(output, filename="output.json"):
    """
    Save a dictionary as a JSON file.
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
