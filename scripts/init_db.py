from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from storage import DatabaseStorage


if __name__ == "__main__":
    storage = DatabaseStorage()
    storage.init_schema()
    print("Database schema initialized.")
