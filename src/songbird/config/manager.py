"""
Configuration management for Songbird
Handles playlist pairs, sync settings, and authentication status
"""
import boto3
from typing import Dict, List, Optional
from songbird.utils.s3_utils import validate_s3_bucket, save_json_to_s3, load_json_from_s3
from songbird.utils.datetime_utils import utc_now_iso


class ConfigManager:
    """Manages configuration, playlist pairs, and sync status"""

    # S3 keys for storing data
    CONFIG_KEY = 'config.json'
    ERRORS_KEY = 'errors.json'

    def __init__(self):
        # S3 configuration (always required)
        self.s3_bucket = validate_s3_bucket()
        self.s3_client = boto3.client('s3')

        # Simple cache for config to reduce S3 calls
        # Cache is invalidated on any write operation
        self._config_cache = None
        self._cache_valid = False

    def has_playlist_pairs(self) -> bool:
        """Check if any playlist pairs are configured"""
        config = self.load_config()
        pairs = config.get('playlist_pairs', [])
        return len(pairs) > 0

    def load_config(self, use_cache: bool = True) -> Dict:
        """Load configuration from S3 with optional caching

        Args:
            use_cache: If True, return cached config if available (default: True)
                      Set to False to force fresh S3 read
        """
        # Return cached config if valid and caching is enabled
        if use_cache and self._cache_valid and self._config_cache is not None:
            return self._config_cache.copy()  # Return copy to prevent external modifications

        # Load from S3
        try:
            config_data = load_json_from_s3(self.s3_client, self.s3_bucket, self.CONFIG_KEY)

            # Update cache
            self._config_cache = config_data
            self._cache_valid = True

            return config_data
        except self.s3_client.exceptions.NoSuchKey:
            # No config in S3 yet, return default
            config_data = self._get_default_config()
            self._config_cache = config_data
            self._cache_valid = True
            return config_data
        except Exception as e:
            print(f"❌ Failed to load config from S3: {e}")
            config_data = self._get_default_config()
            # Don't cache on error - might be temporary S3 issue
            return config_data

    def save_config(self, config: Dict):
        """Save configuration to S3 and update cache"""
        try:
            save_json_to_s3(self.s3_client, self.s3_bucket, self.CONFIG_KEY, config)

            # Update cache after successful save
            self._config_cache = config
            self._cache_valid = True

        except Exception as e:
            print(f"❌ Failed to save config to S3: {e}")
            # Invalidate cache on save failure
            self._cache_valid = False
            raise

    def invalidate_cache(self):
        """Manually invalidate the config cache (force next load from S3)"""
        self._cache_valid = False
        self._config_cache = None

    def _get_default_config(self) -> Dict:
        """Return default configuration"""
        return {
            'playlist_pairs': [],
            'sync_settings': {
                'schedule': 'daily',
                'last_sync': None,
                'sync_deletions': True
            }
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
            'created_at': utc_now_iso(),
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
                pair['last_sync'] = utc_now_iso()
                pair['last_sync_status'] = status
                if details:
                    pair['last_sync_details'] = details
                break

        # Update global sync status
        config['sync_settings']['last_sync'] = utc_now_iso()
        self.save_config(config)

    def get_playlist_snapshot(self, pair_id: int) -> Dict:
        """Get cached playlist snapshot for change detection"""
        config = self.load_config()
        pairs = config.get('playlist_pairs', [])

        for pair in pairs:
            if pair.get('id') == pair_id:
                return pair.get('snapshot', {})

        return {}

    def update_playlist_snapshot(self, pair_id: int, spotify_count: int, youtube_count: int,
                                 spotify_snapshot_id: str = None, youtube_snapshot_id: str = None):
        """Update playlist snapshot for change detection"""
        config = self.load_config()
        pairs = config.get('playlist_pairs', [])

        for pair in pairs:
            if pair.get('id') == pair_id:
                pair['snapshot'] = {
                    'spotify_count': spotify_count,
                    'youtube_count': youtube_count,
                    'spotify_snapshot_id': spotify_snapshot_id,
                    'youtube_snapshot_id': youtube_snapshot_id,
                    'updated_at': utc_now_iso()
                }
                break

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
        """Log an error to separate errors file (optimized for write performance)"""
        error_entry = {
            'timestamp': utc_now_iso(),
            'type': error_type,
            'message': message,
            'details': details or {}
        }

        try:
            # Load existing errors
            errors = self._load_errors()
            errors.append(error_entry)

            # Keep only last 100 errors
            errors = errors[-100:]

            # Save errors
            self._save_errors(errors)

        except Exception as e:
            print(f"⚠️  Failed to log error to S3: {e}")
            # Don't raise - error logging should not break the application

    def get_errors(self, limit: int = 10) -> List[Dict]:
        """Get recent errors from separate errors file"""
        errors = self._load_errors()
        return errors[-limit:]

    def clear_errors(self):
        """Clear all logged errors"""
        self._save_errors([])

    def _load_errors(self) -> List[Dict]:
        """Load errors from separate S3 file"""
        try:
            errors = load_json_from_s3(self.s3_client, self.s3_bucket, self.ERRORS_KEY)
            return errors if isinstance(errors, list) else []
        except self.s3_client.exceptions.NoSuchKey:
            # No errors file yet
            return []
        except Exception as e:
            print(f"⚠️  Failed to load errors from S3: {e}")
            return []

    def _save_errors(self, errors: List[Dict]):
        """Save errors to separate S3 file"""
        try:
            save_json_to_s3(self.s3_client, self.s3_bucket, self.ERRORS_KEY, errors)
        except Exception as e:
            print(f"⚠️  Failed to save errors to S3: {e}")
            # Don't raise - error logging should not break the application

    def clear_snapshots(self):
        """Clear all playlist snapshots (force re-sync on next run)"""
        config = self.load_config()
        pairs = config.get('playlist_pairs', [])

        for pair in pairs:
            if 'snapshot' in pair:
                del pair['snapshot']

        self.save_config(config)
        print("✅ Cleared snapshots for all playlist pairs")

    def reset_all(self):
        """Reset all configuration to defaults"""
        default_config = self._get_default_config()
        self.save_config(default_config)
        # Also clear errors since they're in a separate file now
        self.clear_errors()
        print("✅ Configuration reset to defaults")
        print("   - All playlist pairs removed")
        print("   - Sync history cleared")
        print("   - Error logs cleared")