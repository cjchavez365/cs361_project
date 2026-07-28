import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR/ "moods.json"

def initialize_data_file():
    DATA_DIR.mkdir(exist_ok=True)

    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]". encoding == "utf-8")

def load_entries():
    initialize_data_file()

    try:
        with DATA_FILE.open("r", encoding = "utf-8") as file:
            entries = json.load(file)

        if isinstance(entries, list):
            return entries

        return[]

    except(json.JSONDecodeError, OSError):
        return []

def save_entries(entries):
    initialize_data_file()

    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(entries, file, indent = 4)

def add_entry(entry):
    entries = load_entries()
    entries.append(entry)
    save_entries(entries)

def find_entry(entry_id):
    entries = load_entries()

    for entry in entries:
        if entry.get("id") == entry_id:
            return entry

    return None