"""
Configuration management for Songbird
Handles playlist pairs, sync settings, and authentication status
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from songbird.auth.spotify import SpotifyAuth
from songbird.auth.apple import AppleAuth


class ConfigManager:
    """Manages configuration, playlist pairs, and sync status"""

    def __init__(self):
        self.config_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')
        self.config_file = os.path.join(self.config_dir, 'config.json')
        self.ensure_config_dir()

    def ensure_config_dir(self):
        """Ensure configuration directory exists"""
        os.makedirs(self.config_dir, exist_ok=True)

    def has_valid_auth(self) -> bool:
        """Check if both Spotify and Apple Music are authenticated"""
        try:
            spotify_auth = SpotifyAuth()
            apple_auth = AppleAuth()

            return spotify_auth.is_authenticated() and apple_auth.is_authenticated()
        except Exception:
            return False

    def has_playlist_pairs(self) -> bool:
        """Check if any playlist pairs are configured"""
        config = self.load_config()
        pairs = config.get('playlist_pairs', [])
        return len(pairs) > 0

    def load_config(self) -> Dict:
        """Load configuration from file"""
        if not os.path.exists(self.config_file):
            return self._get_default_config()

        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return self._get_default_config()

    def save_config(self, config: Dict):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def _get_default_config(self) -> Dict:
        """Return default configuration"""
        return {
            'playlist_pairs': [],
            'sync_settings': {
                'schedule': 'daily',
                'last_sync': None,
                'sync_deletions': True
            },
            'error_log': []
        }

    def add_playlist_pair(self, spotify_playlist: Dict, apple_playlist: Dict):
        """Add a new playlist pair"""
        config = self.load_config()

        pair = {
            'id': len(config['playlist_pairs']) + 1,
            'spotify': {
                'id': spotify_playlist['id'],
                'name': spotify_playlist['name'],
                'uri': spotify_playlist['uri']
            },
            'apple': {
                'id': apple_playlist['id'],
                'name': apple_playlist['name']
            },
            'created_at': datetime.now(datetime.UTC).isoformat(),
            'last_sync': None
        }

        config['playlist_pairs'].append(pair)
        self.save_config(config)

        print(f"✅ Paired '{spotify_playlist['name']}' with '{apple_playlist['name']}'")

    def get_playlist_pairs(self) -> List[Dict]:
        """Get all configured playlist pairs"""
        config = self.load_config()
        return config.get('playlist_pairs', [])

    def remove_playlist_pair(self, pair_id: int):
        """Remove a playlist pair by ID"""
        config = self.load_config()
        pairs = config.get('playlist_pairs', [])

        config['playlist_pairs'] = [pair for pair in pairs if pair.get('id') != pair_id]
        self.save_config(config)

    def update_sync_status(self, pair_id: int, status: str, details: Dict = None):
        """Update sync status for a playlist pair"""
        config = self.load_config()
        pairs = config.get('playlist_pairs', [])

        for pair in pairs:
            if pair.get('id') == pair_id:
                pair['last_sync'] = datetime.now(datetime.UTC).isoformat()
                pair['last_sync_status'] = status
                if details:
                    pair['last_sync_details'] = details
                break

        # Update global sync status
        config['sync_settings']['last_sync'] = datetime.now(datetime.UTC).isoformat()
        self.save_config(config)

    def get_sync_status(self) -> Optional[Dict]:
        """Get overall sync status information"""
        config = self.load_config()
        pairs = config.get('playlist_pairs', [])

        if not pairs:
            return None

        return {
            'last_sync': config['sync_settings'].get('last_sync'),
            'status': 'configured',
            'pair_count': len(pairs),
            'pairs': pairs
        }

    def log_error(self, error_type: str, message: str, details: Dict = None):
        """Log an error to the configuration"""
        config = self.load_config()

        error_entry = {
            'timestamp': datetime.now(datetime.UTC).isoformat(),
            'type': error_type,
            'message': message,
            'details': details or {}
        }

        if 'error_log' not in config:
            config['error_log'] = []

        config['error_log'].append(error_entry)

        # Keep only last 100 errors
        config['error_log'] = config['error_log'][-100:]

        self.save_config(config)

    def get_errors(self, limit: int = 10) -> List[Dict]:
        """Get recent errors"""
        config = self.load_config()
        errors = config.get('error_log', [])
        return errors[-limit:]

    def clear_errors(self):
        """Clear all logged errors"""
        config = self.load_config()
        config['error_log'] = []
        self.save_config(config)