#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update History Recording Module - Simplified Version
Records detailed information for each update.
"""

import json

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from shared.logging import default_logger as logger


class UpdateHistoryManager:
    """Update History Manager (Simplified Edition)"""
    
    def __init__(self, history_file: str = "logs/update_history.json"):
        self.history_file = Path(history_file)
        self.history_data = {'updates': [], 'last_update': None}
        self._load_history()
    
    def _load_history(self):
        """Load history records"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history_data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load history records: {e}")
                self.history_data = {'updates': [], 'last_update': None}
        self._save_history()
    
    def _save_history(self):
        """Save history records"""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save history records: {e}")
    
    def add(self, from_version: str, to_version: str, status: str, **kwargs):
        """Add update record
        
        Args:
            from_version: Starting version
            to_version: Target version
            status: Status (success/failed/rollback)
            **kwargs: Other parameters (backup_path, duration, error, etc.)
        """
        record = {
            'from_version': from_version,
            'to_version': to_version,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        
        self.history_data['updates'].append(record)
        self.history_data['last_update'] = record['timestamp']
        self.history_data['updates'].sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        self._save_history()
        
        logger.info(f"Update recorded: {from_version} -> {to_version} ({status})")
    
    def get_recent(self, limit: int = 10) -> List[Dict]:
        """Get recent update records"""
        return self.history_data.get('updates', [])[:limit]
    
    def get_last(self) -> Optional[Dict]:
        """Get the last update record"""
        updates = self.history_data.get('updates', [])
        return updates[0] if updates else None


# Global singleton
update_history_manager = UpdateHistoryManager()


def add_update_history(from_version: str, to_version: str, status: str, **kwargs):
    """Convenience function: add update history"""
    update_history_manager.add(from_version, to_version, status, **kwargs)
