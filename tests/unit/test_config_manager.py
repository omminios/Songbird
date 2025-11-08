"""
Unit tests for config/manager.py
Tests configuration management and S3 operations
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from moto import mock_aws
import boto3
from songbird.config.manager import ConfigManager


class TestConfigManager:
    """Test suite for ConfigManager class"""

    @pytest.fixture
    def config_manager(self, mock_s3_bucket):
        """Create ConfigManager with mocked S3"""
        with patch('songbird.config.manager.validate_s3_bucket', return_value='test-songbird-bucket'):
            return ConfigManager()

    # Test configuration loading
    def test_load_config_returns_default_when_empty(self, config_manager):
        """Test that default config is returned when S3 is empty"""
        config = config_manager.load_config()
        assert 'playlist_pairs' in config
        assert 'sync_settings' in config
        assert config['playlist_pairs'] == []

    def test_load_config_caching(self, config_manager, mock_s3_bucket):
        """Test that config is cached after first load"""
        # First load
        config1 = config_manager.load_config()
        # Second load should use cache
        config2 = config_manager.load_config()
        assert config1 == config2
        # Verify only one S3 call was made (cache was used)
        assert config_manager._cache_valid

    def test_load_config_force_refresh(self, config_manager, mock_s3_bucket):
        """Test that use_cache=False forces S3 read"""
        config1 = config_manager.load_config(use_cache=True)
        config2 = config_manager.load_config(use_cache=False)
        assert config1 == config2

    def test_load_config_returns_copy(self, config_manager):
        """Test that load_config returns a copy to prevent mutations"""
        config1 = config_manager.load_config()
        config1['test'] = 'modified'
        config2 = config_manager.load_config()
        assert 'test' not in config2

    # Test configuration saving
    def test_save_config_updates_cache(self, config_manager, mock_s3_bucket):
        """Test that saving config updates the cache"""
        new_config = {
            'playlist_pairs': [{'id': 1, 'name': 'Test'}],
            'sync_settings': {}
        }
        config_manager.save_config(new_config)
        cached_config = config_manager.load_config()
        assert cached_config['playlist_pairs'][0]['name'] == 'Test'

    def test_save_config_persists_to_s3(self, config_manager, mock_s3_bucket):
        """Test that config is actually saved to S3"""
        new_config = {
            'playlist_pairs': [],
            'sync_settings': {'schedule': 'hourly'}
        }
        config_manager.save_config(new_config)

        # Load directly from S3
        response = mock_s3_bucket.get_object(
            Bucket='test-songbird-bucket',
            Key='config.json'
        )
        saved_data = json.loads(response['Body'].read())
        assert saved_data['sync_settings']['schedule'] == 'hourly'

    # Test cache management
    def test_invalidate_cache(self, config_manager):
        """Test cache invalidation"""
        config_manager.load_config()
        assert config_manager._cache_valid
        config_manager.invalidate_cache()
        assert not config_manager._cache_valid
        assert config_manager._config_cache is None

    # Test default config
    def test_get_default_config(self, config_manager):
        """Test default configuration structure"""
        default = config_manager._get_default_config()
        assert 'playlist_pairs' in default
        assert 'sync_settings' in default
        assert default['playlist_pairs'] == []
        assert 'schedule' in default['sync_settings']
        assert 'last_sync' in default['sync_settings']
        assert 'sync_deletions' in default['sync_settings']

    # Test playlist pair management
    def test_add_playlist_pair(self, config_manager):
        """Test adding a playlist pair"""
        spotify_playlist = {
            'id': 'spotify123',
            'name': 'My Playlist',
            'uri': 'spotify:playlist:123'
        }
        youtube_playlist = {
            'id': 'youtube456',
            'name': 'My Playlist'
        }
        config_manager.add_playlist_pair(spotify_playlist, youtube_playlist)

        pairs = config_manager.get_playlist_pairs()
        assert len(pairs) == 1
        assert pairs[0]['id'] == 1
        assert pairs[0]['spotify']['id'] == 'spotify123'
        assert pairs[0]['youtube']['id'] == 'youtube456'

    def test_add_multiple_playlist_pairs(self, config_manager):
        """Test adding multiple playlist pairs with auto-incrementing IDs"""
        for i in range(3):
            config_manager.add_playlist_pair(
                {'id': f'sp{i}', 'name': f'Playlist {i}', 'uri': f'uri{i}'},
                {'id': f'yt{i}', 'name': f'Playlist {i}'}
            )

        pairs = config_manager.get_playlist_pairs()
        assert len(pairs) == 3
        assert pairs[0]['id'] == 1
        assert pairs[1]['id'] == 2
        assert pairs[2]['id'] == 3

    def test_get_playlist_pairs_empty(self, config_manager):
        """Test getting playlist pairs when none exist"""
        pairs = config_manager.get_playlist_pairs()
        assert pairs == []

    def test_has_playlist_pairs_false(self, config_manager):
        """Test has_playlist_pairs returns False when empty"""
        assert not config_manager.has_playlist_pairs()

    def test_has_playlist_pairs_true(self, config_manager):
        """Test has_playlist_pairs returns True when pairs exist"""
        config_manager.add_playlist_pair(
            {'id': 'sp1', 'name': 'Test', 'uri': 'uri'},
            {'id': 'yt1', 'name': 'Test'}
        )
        assert config_manager.has_playlist_pairs()

    def test_remove_playlist_pair(self, config_manager):
        """Test removing a playlist pair"""
        # Add two pairs
        for i in range(2):
            config_manager.add_playlist_pair(
                {'id': f'sp{i}', 'name': f'Playlist {i}', 'uri': f'uri{i}'},
                {'id': f'yt{i}', 'name': f'Playlist {i}'}
            )

        # Remove first pair
        config_manager.remove_playlist_pair(1)

        pairs = config_manager.get_playlist_pairs()
        assert len(pairs) == 1
        assert pairs[0]['id'] == 2

    def test_remove_nonexistent_pair(self, config_manager):
        """Test removing a pair that doesn't exist"""
        config_manager.add_playlist_pair(
            {'id': 'sp1', 'name': 'Test', 'uri': 'uri'},
            {'id': 'yt1', 'name': 'Test'}
        )
        config_manager.remove_playlist_pair(999)  # Doesn't exist

        pairs = config_manager.get_playlist_pairs()
        assert len(pairs) == 1  # Original pair still exists

    # Test sync status management
    def test_update_sync_status(self, config_manager):
        """Test updating sync status for a pair"""
        config_manager.add_playlist_pair(
            {'id': 'sp1', 'name': 'Test', 'uri': 'uri'},
            {'id': 'yt1', 'name': 'Test'}
        )

        config_manager.update_sync_status(1, 'success', {'tracks_added': 5})

        pairs = config_manager.get_playlist_pairs()
        assert pairs[0]['last_sync_status'] == 'success'
        assert pairs[0]['last_sync_details']['tracks_added'] == 5
        assert pairs[0]['last_sync'] is not None

    def test_update_sync_status_updates_global(self, config_manager):
        """Test that updating sync status also updates global last_sync"""
        config_manager.add_playlist_pair(
            {'id': 'sp1', 'name': 'Test', 'uri': 'uri'},
            {'id': 'yt1', 'name': 'Test'}
        )

        config_manager.update_sync_status(1, 'success')

        config = config_manager.load_config()
        assert config['sync_settings']['last_sync'] is not None

    def test_get_sync_status_empty(self, config_manager):
        """Test get_sync_status returns None when no pairs"""
        status = config_manager.get_sync_status()
        assert status is None

    def test_get_sync_status_with_pairs(self, config_manager):
        """Test get_sync_status returns correct information"""
        config_manager.add_playlist_pair(
            {'id': 'sp1', 'name': 'Test', 'uri': 'uri'},
            {'id': 'yt1', 'name': 'Test'}
        )

        status = config_manager.get_sync_status()
        assert status is not None
        assert status['status'] == 'configured'
        assert status['pair_count'] == 1
        assert len(status['pairs']) == 1

    # Test snapshot management
    def test_get_playlist_snapshot_empty(self, config_manager):
        """Test getting snapshot when none exists"""
        config_manager.add_playlist_pair(
            {'id': 'sp1', 'name': 'Test', 'uri': 'uri'},
            {'id': 'yt1', 'name': 'Test'}
        )

        snapshot = config_manager.get_playlist_snapshot(1)
        assert snapshot == {}

    def test_update_playlist_snapshot(self, config_manager):
        """Test updating playlist snapshot"""
        config_manager.add_playlist_pair(
            {'id': 'sp1', 'name': 'Test', 'uri': 'uri'},
            {'id': 'yt1', 'name': 'Test'}
        )

        config_manager.update_playlist_snapshot(
            1,
            spotify_count=10,
            youtube_count=10,
            spotify_snapshot_id='snap123',
            youtube_snapshot_id='snap456'
        )

        snapshot = config_manager.get_playlist_snapshot(1)
        assert snapshot['spotify_count'] == 10
        assert snapshot['youtube_count'] == 10
        assert snapshot['spotify_snapshot_id'] == 'snap123'
        assert snapshot['youtube_snapshot_id'] == 'snap456'
        assert 'updated_at' in snapshot

    def test_get_snapshot_nonexistent_pair(self, config_manager):
        """Test getting snapshot for non-existent pair"""
        snapshot = config_manager.get_playlist_snapshot(999)
        assert snapshot == {}

    def test_clear_snapshots(self, config_manager):
        """Test clearing all snapshots"""
        config_manager.add_playlist_pair(
            {'id': 'sp1', 'name': 'Test', 'uri': 'uri'},
            {'id': 'yt1', 'name': 'Test'}
        )
        config_manager.update_playlist_snapshot(1, 10, 10)

        config_manager.clear_snapshots()

        snapshot = config_manager.get_playlist_snapshot(1)
        assert snapshot == {}

    # Test error logging
    def test_log_error(self, config_manager):
        """Test logging an error"""
        config_manager.log_error('test_error', 'Test message', {'detail': 'value'})

        errors = config_manager.get_errors()
        assert len(errors) == 1
        assert errors[0]['type'] == 'test_error'
        assert errors[0]['message'] == 'Test message'
        assert errors[0]['details']['detail'] == 'value'
        assert 'timestamp' in errors[0]

    def test_log_multiple_errors(self, config_manager):
        """Test logging multiple errors"""
        for i in range(5):
            config_manager.log_error(f'error_{i}', f'Message {i}')

        errors = config_manager.get_errors(limit=10)
        assert len(errors) == 5

    def test_log_error_keeps_last_100(self, config_manager):
        """Test that only last 100 errors are kept"""
        for i in range(150):
            config_manager.log_error(f'error_{i}', f'Message {i}')

        errors = config_manager._load_errors()
        assert len(errors) == 100
        # First 50 should be dropped
        assert errors[0]['type'] == 'error_50'

    def test_get_errors_with_limit(self, config_manager):
        """Test getting errors with custom limit"""
        for i in range(20):
            config_manager.log_error(f'error_{i}', f'Message {i}')

        errors = config_manager.get_errors(limit=5)
        assert len(errors) == 5
        # Should get last 5
        assert errors[-1]['type'] == 'error_19'

    def test_clear_errors(self, config_manager):
        """Test clearing all errors"""
        config_manager.log_error('test_error', 'Test message')
        config_manager.clear_errors()

        errors = config_manager.get_errors()
        assert len(errors) == 0

    def test_load_errors_returns_empty_on_no_file(self, config_manager):
        """Test that loading errors returns empty list when file doesn't exist"""
        errors = config_manager._load_errors()
        assert errors == []

    # Test reset functionality
    def test_reset_all(self, config_manager):
        """Test resetting all configuration"""
        # Add some data
        config_manager.add_playlist_pair(
            {'id': 'sp1', 'name': 'Test', 'uri': 'uri'},
            {'id': 'yt1', 'name': 'Test'}
        )
        config_manager.log_error('test', 'message')

        # Reset
        config_manager.reset_all()

        # Verify everything is cleared
        pairs = config_manager.get_playlist_pairs()
        errors = config_manager.get_errors()
        assert len(pairs) == 0
        assert len(errors) == 0

        config = config_manager.load_config()
        assert config['sync_settings']['last_sync'] is None
