"""
Unit tests for sync/manager.py
Tests the main synchronization orchestration logic
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone
from songbird.sync.manager import SyncManager


class TestSyncManager:
    """Test suite for SyncManager class"""

    @pytest.fixture
    def sync_manager(self):
        """Create SyncManager with mocked dependencies"""
        with patch('songbird.sync.manager.ConfigManager') as mock_config, \
             patch('songbird.sync.manager.SpotifyPlaylistManager') as mock_spotify, \
             patch('songbird.sync.manager.YouTubePlaylistManager') as mock_youtube, \
             patch('songbird.sync.manager.SongMatcher') as mock_matcher:

            manager = SyncManager()
            manager.config_manager = mock_config.return_value
            manager.spotify_manager = mock_spotify.return_value
            manager.youtube_manager = mock_youtube.return_value
            manager.song_matcher = mock_matcher.return_value

            yield manager

    @pytest.fixture
    def sample_pair(self):
        """Sample playlist pair"""
        return {
            'id': 1,
            'spotify': {
                'id': 'spotify123',
                'name': 'Test Playlist',
                'uri': 'spotify:playlist:123'
            },
            'youtube': {
                'id': 'youtube456',
                'name': 'Test Playlist'
            },
            'snapshot': {
                'spotify_count': 10,
                'youtube_count': 10,
                'updated_at': '2025-11-01T00:00:00+00:00'
            }
        }

    # Test manual sync
    def test_manual_sync_no_pairs_configured(self, sync_manager):
        """Test manual sync with no playlist pairs"""
        sync_manager.config_manager.get_playlist_pairs.return_value = []

        result = sync_manager.manual_sync()

        assert result is False

    def test_manual_sync_calls_run_sync(self, sync_manager, sample_pair):
        """Test that manual sync calls run_sync"""
        sync_manager.config_manager.get_playlist_pairs.return_value = [sample_pair]

        with patch.object(sync_manager, 'run_sync', return_value=True) as mock_run:
            result = sync_manager.manual_sync(verbose=True, force=True)

            mock_run.assert_called_once_with(verbose=True, force=True, dry_run=False)
            assert result is True

    def test_manual_sync_handles_exceptions(self, sync_manager, sample_pair):
        """Test that manual sync handles exceptions gracefully"""
        sync_manager.config_manager.get_playlist_pairs.return_value = [sample_pair]

        with patch.object(sync_manager, 'run_sync', side_effect=Exception("Test error")):
            result = sync_manager.manual_sync()

            assert result is False
            sync_manager.config_manager.log_error.assert_called_once()

    # Test run_sync
    def test_run_sync_no_pairs(self, sync_manager):
        """Test run_sync with no pairs"""
        sync_manager.config_manager.get_playlist_pairs.return_value = []

        result = sync_manager.run_sync()

        # Should complete successfully even with no pairs
        assert result is True

    def test_run_sync_success(self, sync_manager, sample_pair):
        """Test successful run_sync"""
        sync_manager.config_manager.get_playlist_pairs.return_value = [sample_pair]

        with patch.object(sync_manager, '_check_if_sync_needed', return_value=True), \
             patch.object(sync_manager, '_sync_playlist_pair', return_value=True):

            result = sync_manager.run_sync()

            assert result is True
            sync_manager.config_manager.update_sync_status.assert_called_once()

    def test_run_sync_force_skips_change_detection(self, sync_manager, sample_pair):
        """Test that force=True skips change detection"""
        sync_manager.config_manager.get_playlist_pairs.return_value = [sample_pair]

        with patch.object(sync_manager, '_check_if_sync_needed') as mock_check, \
             patch.object(sync_manager, '_sync_playlist_pair', return_value=True):

            sync_manager.run_sync(force=True)

            # Should not call change detection
            mock_check.assert_not_called()

    def test_run_sync_skips_unchanged_playlists(self, sync_manager, sample_pair):
        """Test that unchanged playlists are skipped"""
        sync_manager.config_manager.get_playlist_pairs.return_value = [sample_pair]

        with patch.object(sync_manager, '_check_if_sync_needed', return_value=False), \
             patch.object(sync_manager, '_sync_playlist_pair') as mock_sync:

            result = sync_manager.run_sync()

            # Should not sync if no changes detected
            mock_sync.assert_not_called()
            assert result is True

    def test_run_sync_dry_run_doesnt_update_status(self, sync_manager, sample_pair):
        """Test that dry_run doesn't update sync status"""
        sync_manager.config_manager.get_playlist_pairs.return_value = [sample_pair]

        with patch.object(sync_manager, '_check_if_sync_needed', return_value=True), \
             patch.object(sync_manager, '_sync_playlist_pair', return_value=True):

            sync_manager.run_sync(dry_run=True)

            # Should not update sync status in dry run mode
            sync_manager.config_manager.update_sync_status.assert_not_called()

    def test_run_sync_handles_pair_failure(self, sync_manager, sample_pair):
        """Test that run_sync handles individual pair failures"""
        sync_manager.config_manager.get_playlist_pairs.return_value = [sample_pair]

        with patch.object(sync_manager, '_check_if_sync_needed', return_value=True), \
             patch.object(sync_manager, '_sync_playlist_pair', return_value=False):

            result = sync_manager.run_sync()

            assert result is False
            # Should still update status to failed
            sync_manager.config_manager.update_sync_status.assert_called_with(1, 'failed')

    def test_run_sync_handles_exceptions_per_pair(self, sync_manager, sample_pair):
        """Test that exceptions in one pair don't stop others"""
        pair2 = sample_pair.copy()
        pair2['id'] = 2
        sync_manager.config_manager.get_playlist_pairs.return_value = [sample_pair, pair2]

        with patch.object(sync_manager, '_check_if_sync_needed', return_value=True), \
             patch.object(sync_manager, '_sync_playlist_pair', side_effect=[Exception("Error"), True]):

            result = sync_manager.run_sync()

            # Should log error for first pair but continue with second
            sync_manager.config_manager.log_error.assert_called_once()
            assert result is False  # Overall failure due to first pair

    # Test normalize_track
    def test_normalize_track_spotify(self, sync_manager):
        """Test normalizing Spotify track format"""
        track = {
            'name': 'Test Song',
            'artists': [{'name': 'Artist 1'}, {'name': 'Artist 2'}],
            'uri': 'spotify:track:123',
            'duration_ms': 180000,
            'id': '123'
        }

        normalized = sync_manager.normalize_track(track, 'spotify')

        assert normalized['name'] == 'Test Song'
        assert normalized['artist'] == 'Artist 1'
        assert normalized['service'] == 'spotify'
        assert normalized['id'] == '123'
        assert normalized['uri'] == 'spotify:track:123'
        assert normalized['duration_ms'] == 180000

    def test_normalize_track_youtube(self, sync_manager):
        """Test normalizing YouTube Music track format"""
        track = {
            'title': 'Test Song',
            'artists': [{'name': 'Artist 1'}],
            'videoId': 'vid123',
            'duration_seconds': 180
        }

        normalized = sync_manager.normalize_track(track, 'youtube')

        assert normalized['name'] == 'Test Song'
        assert normalized['artist'] == 'Artist 1'
        assert normalized['service'] == 'youtube'
        assert normalized['id'] == 'vid123'
        assert normalized['duration_ms'] == 180000  # Converted to ms

    def test_normalize_track_handles_missing_fields(self, sync_manager):
        """Test normalizing track with missing optional fields"""
        track = {
            'name': 'Test Song',
            'artists': []  # Empty artists
        }

        normalized = sync_manager.normalize_track(track, 'spotify')

        assert normalized['artist'] == 'Unknown'

    # Test track deduplication
    def test_deduplicate_tracks(self, sync_manager):
        """Test removing duplicate tracks"""
        tracks = [
            {'name': 'Song 1', 'artist': 'Artist 1', 'duration_ms': 180000},
            {'name': 'Song 1', 'artist': 'Artist 1', 'duration_ms': 180000},  # Duplicate
            {'name': 'Song 2', 'artist': 'Artist 2', 'duration_ms': 200000}
        ]

        deduplicated = sync_manager._deduplicate_tracks(tracks)

        assert len(deduplicated) == 2
        assert deduplicated[0]['name'] == 'Song 1'
        assert deduplicated[1]['name'] == 'Song 2'

    def test_deduplicate_tracks_empty(self, sync_manager):
        """Test deduplicating empty list"""
        deduplicated = sync_manager._deduplicate_tracks([])
        assert deduplicated == []

    def test_deduplicate_tracks_case_insensitive(self, sync_manager):
        """Test that deduplication is case insensitive"""
        tracks = [
            {'name': 'Song Name', 'artist': 'Artist Name', 'duration_ms': 180000},
            {'name': 'song name', 'artist': 'artist name', 'duration_ms': 180000}  # Same but different case
        ]

        deduplicated = sync_manager._deduplicate_tracks(tracks)

        assert len(deduplicated) == 1

    # Test creating normalized track key
    def test_create_track_key(self, sync_manager):
        """Test creating normalized track key for comparison"""
        track = {
            'name': 'Test Song (Remastered)',
            'artist': 'Artist feat. Someone'
        }

        key = sync_manager._create_track_key(track)

        # Should be normalized and lowercased
        assert 'remastered' not in key
        assert 'feat' not in key
        assert key == key.lower()

    def test_create_track_key_handles_special_chars(self, sync_manager):
        """Test that track key normalizes special characters"""
        track = {
            'name': 'Song [Live] - Remix',
            'artist': 'Artist'
        }

        key = sync_manager._create_track_key(track)

        # Should remove brackets and content after dash
        assert '[' not in key
        assert 'live' not in key.lower()
        assert '-' not in key or 'remix' not in key.lower()

    # Test check if sync needed
    def test_check_if_sync_needed_no_snapshot(self, sync_manager):
        """Test that sync is needed when no snapshot exists"""
        pair = {
            'id': 1,
            'spotify': {'id': 'sp123'},
            'youtube': {'id': 'yt456'}
            # No snapshot
        }

        with patch.object(sync_manager.spotify_manager, 'get_playlist_tracks', return_value=[]), \
             patch.object(sync_manager.youtube_manager, 'get_playlist_tracks', return_value=[]):

            needs_sync = sync_manager._check_if_sync_needed(pair)

            assert needs_sync is True

    def test_check_if_sync_needed_counts_changed(self, sync_manager):
        """Test that sync is needed when track counts changed"""
        pair = {
            'id': 1,
            'spotify': {'id': 'sp123'},
            'youtube': {'id': 'yt456'},
            'snapshot': {
                'spotify_count': 10,
                'youtube_count': 10
            }
        }

        # Return different counts
        spotify_tracks = [{'name': f'Track {i}', 'artists': []} for i in range(15)]
        youtube_tracks = [{'title': f'Track {i}', 'artists': []} for i in range(10)]

        with patch.object(sync_manager.spotify_manager, 'get_playlist_tracks', return_value=spotify_tracks), \
             patch.object(sync_manager.youtube_manager, 'get_playlist_tracks', return_value=youtube_tracks):

            needs_sync = sync_manager._check_if_sync_needed(pair)

            assert needs_sync is True

    def test_check_if_sync_needed_counts_unchanged(self, sync_manager):
        """Test that sync is skipped when counts unchanged"""
        pair = {
            'id': 1,
            'spotify': {'id': 'sp123'},
            'youtube': {'id': 'yt456'},
            'snapshot': {
                'spotify_count': 5,
                'youtube_count': 5
            }
        }

        # Return same counts
        spotify_tracks = [{'name': f'Track {i}', 'artists': []} for i in range(5)]
        youtube_tracks = [{'title': f'Track {i}', 'artists': []} for i in range(5)]

        with patch.object(sync_manager.spotify_manager, 'get_playlist_tracks', return_value=spotify_tracks), \
             patch.object(sync_manager.youtube_manager, 'get_playlist_tracks', return_value=youtube_tracks):

            needs_sync = sync_manager._check_if_sync_needed(pair)

            assert needs_sync is False

    # Test finding tracks only in source
    def test_find_tracks_only_in_source(self, sync_manager):
        """Test finding tracks that exist only in source"""
        source_tracks = [
            {'name': 'Track 1', 'artist': 'Artist 1'},
            {'name': 'Track 2', 'artist': 'Artist 2'},
            {'name': 'Track 3', 'artist': 'Artist 3'}
        ]

        target_tracks = [
            {'name': 'Track 1', 'artist': 'Artist 1'},
            {'name': 'Track 3', 'artist': 'Artist 3'}
        ]

        only_in_source = sync_manager._find_tracks_only_in_source(source_tracks, target_tracks)

        assert len(only_in_source) == 1
        assert only_in_source[0]['name'] == 'Track 2'

    def test_find_tracks_only_in_source_empty_target(self, sync_manager):
        """Test finding tracks when target is empty"""
        source_tracks = [
            {'name': 'Track 1', 'artist': 'Artist 1'}
        ]

        only_in_source = sync_manager._find_tracks_only_in_source(source_tracks, [])

        assert len(only_in_source) == 1

    def test_find_tracks_only_in_source_all_exist_in_target(self, sync_manager):
        """Test when all source tracks exist in target"""
        tracks = [
            {'name': 'Track 1', 'artist': 'Artist 1'}
        ]

        only_in_source = sync_manager._find_tracks_only_in_source(tracks, tracks)

        assert len(only_in_source) == 0
