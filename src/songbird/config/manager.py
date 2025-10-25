"""
Configuration management for Songbird
Handles playlist pairs, sync settings, and authentication status
"""
import os
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from songbird.auth.spotify import SpotifyAuth
from songbird.auth.youtube import YouTubeAuth

try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class ConfigManager:
    """Manages configuration, playlist pairs, and sync status"""

    def __init__(self):
        # S3 configuration (always required)
        self.s3_bucket = os.getenv('SONGBIRD_CONFIG_BUCKET')
        if not self.s3_bucket:
            raise ValueError(
                "Missing SONGBIRD_CONFIG_BUCKET environment variable.\n"
                "Please set it to your S3 bucket name:\n"
                "  export SONGBIRD_CONFIG_BUCKET=your-bucket-name"
            )

        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for S3 storage.\n"
                "Install with: pip install boto3"
            )

        self.s3_client = boto3.client('s3')

    def has_valid_auth(self) -> bool:
        """Check if both Spotify and YouTube Music are authenticated"""
        try:
            spotify_auth = SpotifyAuth()
            youtube_auth = YouTubeAuth()
            return spotify_auth.is_authenticated() and youtube_auth.is_authenticated()
        except Exception:
            return False

    def has_playlist_pairs(self) -> bool:
        """Check if any playlist pairs are configured"""
        config = self.load_config()
        pairs = config.get('playlist_pairs', [])
        return len(pairs) > 0

    def load_config(self) -> Dict:
        """Load configuration from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key='config.json'
            )
            config_data = json.loads(response['Body'].read())
            return config_data
        except self.s3_client.exceptions.NoSuchKey:
            # No config in S3 yet, return default
            return self._get_default_config()
        except Exception as e:
            print(f"❌ Failed to load config from S3: {e}")
            return self._get_default_config()

    def save_config(self, config: Dict):
        """Save configuration to S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key='config.json',
                Body=json.dumps(config, indent=2),
                ServerSideEncryption='AES256',
                ContentType='application/json'
            )
        except Exception as e:
            print(f"❌ Failed to save config to S3: {e}")
            raise

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

    def add_playlist_pair(self, spotify_playlist: Dict, youtube_playlist: Dict):
        """Add a new playlist pair"""
        config = self.load_config()

        pair = {
            'id': len(config['playlist_pairs']) + 1,
            'spotify': {
                'id': spotify_playlist['id'],
                'name': spotify_playlist['name'],
                'uri': spotify_playlist['uri']
            },
            'youtube': {
                'id': youtube_playlist['id'],
                'name': youtube_playlist['name']
            },
            'created_at': datetime.now(timezone.utc).isoformat(),
            'last_sync': None
        }

        config['playlist_pairs'].append(pair)
        self.save_config(config)

        print(f"✅ Paired '{spotify_playlist['name']}' with '{youtube_playlist['name']}'")

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
                pair['last_sync'] = datetime.now(timezone.utc).isoformat()
                pair['last_sync_status'] = status
                if details:
                    pair['last_sync_details'] = details
                break

        # Update global sync status
        config['sync_settings']['last_sync'] = datetime.now(timezone.utc).isoformat()
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
            'timestamp': datetime.now(timezone.utc).isoformat(),
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

    def reset_all(self):
        """Reset all configuration to defaults"""
        default_config = self._get_default_config()
        self.save_config(default_config)
        print("✅ Configuration reset to defaults")
        print("   - All playlist pairs removed")
        print("   - Sync history cleared")
        print("   - Error logs cleared")