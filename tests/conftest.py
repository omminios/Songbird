"""
Pytest configuration and fixtures
"""
import os
import pytest
from unittest.mock import Mock, MagicMock
from moto import mock_aws
import boto3


@pytest.fixture(scope="session")
def test_env_vars():
    """Set up test environment variables"""
    os.environ["SONGBIRD_CONFIG_BUCKET"] = "test-songbird-bucket"
    os.environ["SPOTIFY_CLIENT_ID"] = "test_spotify_id"
    os.environ["SPOTIFY_CLIENT_SECRET"] = "test_spotify_secret"
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def mock_s3_bucket(test_env_vars):
    """Create a mock S3 bucket for testing"""
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-songbird-bucket")
        yield s3


@pytest.fixture
def sample_spotify_track():
    """Sample Spotify track data"""
    return {
        "name": "Bohemian Rhapsody",
        "artists": [{"name": "Queen"}],
        "duration_ms": 354000,
        "uri": "spotify:track:4u7EnebtmKWzUH433cf5Qv",
        "id": "4u7EnebtmKWzUH433cf5Qv"
    }


@pytest.fixture
def sample_youtube_track():
    """Sample YouTube Music track data"""
    return {
        "title": "Bohemian Rhapsody",
        "artists": [{"name": "Queen"}],
        "duration_seconds": 354,
        "videoId": "fJ9rUzIMcZQ"
    }


@pytest.fixture
def sample_spotify_playlist():
    """Sample Spotify playlist response"""
    return {
        "id": "test_playlist_id",
        "name": "Test Playlist",
        "tracks": {
            "items": [
                {
                    "track": {
                        "name": "Song 1",
                        "artists": [{"name": "Artist 1"}],
                        "duration_ms": 180000,
                        "uri": "spotify:track:1",
                        "id": "1"
                    }
                },
                {
                    "track": {
                        "name": "Song 2",
                        "artists": [{"name": "Artist 2"}],
                        "duration_ms": 200000,
                        "uri": "spotify:track:2",
                        "id": "2"
                    }
                }
            ]
        }
    }


@pytest.fixture
def sample_youtube_playlist():
    """Sample YouTube Music playlist response"""
    return [
        {
            "videoId": "video1",
            "title": "Song 1",
            "artists": [{"name": "Artist 1"}],
            "duration_seconds": 180
        },
        {
            "videoId": "video2",
            "title": "Song 2",
            "artists": [{"name": "Artist 2"}],
            "duration_seconds": 200
        }
    ]


@pytest.fixture
def mock_spotify_manager():
    """Mock Spotify playlist manager"""
    mock = MagicMock()
    mock.get_playlist_tracks.return_value = []
    mock.add_tracks_to_playlist.return_value = True
    mock.search_track.return_value = []
    return mock


@pytest.fixture
def mock_youtube_manager():
    """Mock YouTube Music playlist manager"""
    mock = MagicMock()
    mock.get_playlist_tracks.return_value = []
    mock.add_tracks_to_playlist.return_value = True
    mock.search_track.return_value = []
    return mock


@pytest.fixture
def sample_config():
    """Sample Songbird configuration"""
    return {
        "playlist_pairs": [
            {
                "id": 1,
                "spotify": {
                    "id": "spotify_playlist_1",
                    "name": "My Playlist",
                    "uri": "spotify:playlist:123"
                },
                "youtube": {
                    "id": "youtube_playlist_1",
                    "name": "My Playlist"
                },
                "snapshot": {
                    "spotify_count": 10,
                    "youtube_count": 10,
                    "updated_at": "2025-11-07T00:00:00+00:00"
                },
                "last_sync": "2025-11-07T00:00:00+00:00",
                "last_sync_status": "success"
            }
        ],
        "sync_settings": {
            "schedule": "daily",
            "last_sync": "2025-11-07T00:00:00+00:00",
            "sync_deletions": False
        },
        "error_log": []
    }
