import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that can handle datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class JSONStore:
    """Simple JSON file-based storage for status updates."""
    
    def __init__(self, file_path: str):
        """Initialize the JSON store.
        
        Args:
            file_path: Path to the JSON file for storing data.
        """
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._save_data({})
    
    def _load_data(self) -> Dict[str, Any]:
        """Load data from the JSON file."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_data(self, data: Dict[str, Any]) -> None:
        """Save data to the JSON file."""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
    
    def get(self, key: str) -> Optional[List[Dict[str, Any]]]:
        """Get stored data for a specific key."""
        data = self._load_data()
        return data.get(key)
    
    def get_all(self) -> Dict[str, Any]:
        """Get all stored data."""
        return self._load_data()
    
    def save(self, key: str, value: List[Dict[str, Any]]) -> None:
        """Save data for a specific key."""
        data = self._load_data()
        data[key] = value
        self._save_data(data)
    
    def delete(self, key: str) -> None:
        """Delete data for a specific key."""
        data = self._load_data()
        if key in data:
            del data[key]
            self._save_data(data) 