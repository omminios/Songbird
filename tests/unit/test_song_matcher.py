"""
Unit tests for song_matcher.py
Tests the fuzzy matching logic and song comparison algorithms
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from songbird.sync.song_matcher import SongMatcher


class TestSongMatcher:
    """Test suite for SongMatcher class"""

    @pytest.fixture
    def song_matcher(self, mock_spotify_manager, mock_youtube_manager):
        """Create SongMatcher instance with mocked managers"""
        with patch('songbird.sync.song_matcher.SpotifyPlaylistManager', return_value=mock_spotify_manager), \
             patch('songbird.sync.song_matcher.YouTubePlaylistManager', return_value=mock_youtube_manager):
            return SongMatcher()

    # Test string cleaning and normalization
    def test_clean_string_removes_parentheses(self, song_matcher):
        """Test that parentheses content is removed"""
        result = song_matcher._clean_string("Song Name (Remastered)")
        assert result == "Song Name"

    def test_clean_string_removes_brackets(self, song_matcher):
        """Test that bracket content is removed"""
        result = song_matcher._clean_string("Song Name [Radio Edit]")
        assert result == "Song Name"

    def test_clean_string_removes_after_dash(self, song_matcher):
        """Test that content after dash is removed"""
        result = song_matcher._clean_string("Song Name - Live Version")
        assert result == "Song Name"

    def test_clean_string_removes_feat(self, song_matcher):
        """Test that featuring annotations are removed"""
        test_cases = [
            ("Song feat. Artist", "Song"),
            ("Song featuring Artist", "Song"),
            ("Song ft Artist", "Song"),
            ("Song ft. Artist", "Song"),
        ]
        for input_str, expected in test_cases:
            result = song_matcher._clean_string(input_str)
            assert result == expected

    def test_clean_string_removes_remix_remaster(self, song_matcher):
        """Test that remix/remaster keywords are removed"""
        assert song_matcher._clean_string("Song remix") == "Song"
        assert song_matcher._clean_string("Song remastered") == "Song"
        assert song_matcher._clean_string("Song remaster") == "Song"

    def test_clean_string_handles_empty_input(self, song_matcher):
        """Test that empty strings are handled"""
        assert song_matcher._clean_string("") == ""
        assert song_matcher._clean_string(None) == ""

    def test_clean_string_normalizes_whitespace(self, song_matcher):
        """Test that extra whitespace is normalized"""
        result = song_matcher._clean_string("Song   Name   Here")
        assert result == "Song Name Here"

    # Test search query building
    def test_build_search_query(self, song_matcher):
        """Test search query construction"""
        track = {
            "name": "Bohemian Rhapsody (Remastered)",
            "artist": "Queen"
        }
        query = song_matcher._build_search_query(track)
        assert query == "Queen Bohemian Rhapsody"

    def test_build_search_query_cleans_both_fields(self, song_matcher):
        """Test that both artist and name are cleaned"""
        track = {
            "name": "Song [Live]",
            "artist": "Artist feat. Someone"
        }
        query = song_matcher._build_search_query(track)
        assert query == "Artist Song"

    # Test similarity scoring
    def test_similarity_score_identical_strings(self, song_matcher):
        """Test that identical strings return 1.0"""
        score = song_matcher._similarity_score("hello", "hello")
        assert score == 1.0

    def test_similarity_score_completely_different(self, song_matcher):
        """Test that completely different strings return low score"""
        score = song_matcher._similarity_score("hello", "xyz")
        assert score < 0.3

    def test_similarity_score_similar_strings(self, song_matcher):
        """Test that similar strings return high score"""
        score = song_matcher._similarity_score("hello world", "hello word")
        assert score > 0.8

    def test_similarity_score_empty_strings(self, song_matcher):
        """Test that empty strings return 0.0"""
        assert song_matcher._similarity_score("", "") == 0.0
        assert song_matcher._similarity_score("hello", "") == 0.0
        assert song_matcher._similarity_score("", "world") == 0.0

    # Test duration similarity
    def test_duration_similarity_identical(self, song_matcher):
        """Test identical durations return 1.0"""
        score = song_matcher._duration_similarity(180000, 180000)
        assert score == 1.0

    def test_duration_similarity_within_threshold(self, song_matcher):
        """Test durations within 5 seconds return high score"""
        score = song_matcher._duration_similarity(180000, 182000)  # 2 second diff
        assert score > 0.6

    def test_duration_similarity_outside_threshold(self, song_matcher):
        """Test durations > 5 seconds apart return 0.0"""
        score = song_matcher._duration_similarity(180000, 190000)  # 10 second diff
        assert score == 0.0

    def test_duration_similarity_handles_zero(self, song_matcher):
        """Test that zero durations return 0.0"""
        assert song_matcher._duration_similarity(0, 180000) == 0.0
        assert song_matcher._duration_similarity(180000, 0) == 0.0

    # Test best match finding
    def test_find_best_match_exact_match(self, song_matcher):
        """Test finding exact match returns highest score"""
        source_track = {
            "name": "Bohemian Rhapsody",
            "artist": "Queen",
            "duration_ms": 354000
        }
        candidates = [
            {
                "name": "Bohemian Rhapsody",
                "artist": "Queen",
                "duration_ms": 354000
            },
            {
                "name": "Bohemian Rhapsody Cover",
                "artist": "Some Band",
                "duration_ms": 360000
            }
        ]
        match = song_matcher._find_best_match(source_track, candidates)
        assert match is not None
        assert match["name"] == "Bohemian Rhapsody"
        assert match["artist"] == "Queen"

    def test_find_best_match_no_candidates(self, song_matcher):
        """Test that empty candidates return None"""
        source_track = {"name": "Song", "artist": "Artist"}
        match = song_matcher._find_best_match(source_track, [])
        assert match is None

    def test_find_best_match_below_threshold(self, song_matcher):
        """Test that matches below 80% threshold return None"""
        source_track = {
            "name": "Bohemian Rhapsody",
            "artist": "Queen"
        }
        candidates = [
            {
                "name": "Completely Different Song",
                "artist": "Different Artist"
            }
        ]
        match = song_matcher._find_best_match(source_track, candidates)
        assert match is None

    def test_find_best_match_with_duration_bonus(self, song_matcher):
        """Test that duration similarity affects scoring"""
        source_track = {
            "name": "Song Name",
            "artist": "Artist",
            "duration_ms": 180000
        }
        candidates = [
            {
                "name": "Song Name",
                "artist": "Artist",
                "duration_ms": 181000  # 1 second diff
            },
            {
                "name": "Song Name",
                "artist": "Artist",
                "duration_ms": 200000  # 20 second diff
            }
        ]
        match = song_matcher._find_best_match(source_track, candidates)
        assert match["duration_ms"] == 181000  # Should pick closer duration

    # Test confidence scoring
    def test_get_match_confidence_exact_match(self, song_matcher):
        """Test confidence for exact match"""
        track1 = {"name": "Song", "artist": "Artist"}
        track2 = {"name": "Song", "artist": "Artist"}
        confidence = song_matcher.get_match_confidence(track1, track2)
        assert confidence == 1.0

    def test_get_match_confidence_no_match(self, song_matcher):
        """Test confidence for completely different tracks"""
        track1 = {"name": "Song A", "artist": "Artist A"}
        track2 = {"name": "Song B", "artist": "Artist B"}
        confidence = song_matcher.get_match_confidence(track1, track2)
        assert confidence < 0.5

    def test_get_match_confidence_partial_match(self, song_matcher):
        """Test confidence for partial match"""
        track1 = {"name": "Bohemian Rhapsody", "artist": "Queen"}
        track2 = {"name": "Bohemian Rhapsody (Live)", "artist": "Queen"}
        confidence = song_matcher.get_match_confidence(track1, track2)
        assert 0.8 < confidence < 1.0  # High but not perfect

    # Test batch matching
    def test_batch_match_songs_empty_list(self, song_matcher):
        """Test batch matching with empty list"""
        result = song_matcher.batch_match_songs([], 'spotify')
        assert result['matched'] == []
        assert result['unmatched'] == []
        assert result['errors'] == []

    def test_batch_match_songs_all_matched(self, song_matcher):
        """Test batch matching when all tracks match"""
        tracks = [
            {"name": "Song 1", "artist": "Artist 1"},
            {"name": "Song 2", "artist": "Artist 2"}
        ]
        with patch.object(song_matcher, 'find_matching_song') as mock_find:
            mock_find.side_effect = [
                {"name": "Song 1", "artist": "Artist 1"},
                {"name": "Song 2", "artist": "Artist 2"}
            ]
            result = song_matcher.batch_match_songs(tracks, 'spotify')
            assert len(result['matched']) == 2
            assert len(result['unmatched']) == 0

    def test_batch_match_songs_some_unmatched(self, song_matcher):
        """Test batch matching with some unmatched tracks"""
        tracks = [
            {"name": "Song 1", "artist": "Artist 1"},
            {"name": "Song 2", "artist": "Artist 2"}
        ]
        with patch.object(song_matcher, 'find_matching_song') as mock_find:
            mock_find.side_effect = [
                {"name": "Song 1", "artist": "Artist 1"},
                None  # Second track not found
            ]
            result = song_matcher.batch_match_songs(tracks, 'spotify')
            assert len(result['matched']) == 1
            assert len(result['unmatched']) == 1

    def test_batch_match_songs_handles_errors(self, song_matcher):
        """Test batch matching handles exceptions"""
        tracks = [{"name": "Song 1", "artist": "Artist 1"}]
        with patch.object(song_matcher, 'find_matching_song') as mock_find:
            mock_find.side_effect = Exception("API Error")
            result = song_matcher.batch_match_songs(tracks, 'spotify')
            assert len(result['errors']) == 1
            assert 'API Error' in result['errors'][0]['error']

    # Test search in service
    def test_search_in_service_spotify(self, song_matcher, mock_spotify_manager):
        """Test searching in Spotify service"""
        mock_spotify_manager.search_tracks.return_value = [
            {"name": "Song", "artist": "Artist"}
        ]
        results = song_matcher._search_in_service("test query", "spotify")
        assert len(results) == 1
        mock_spotify_manager.search_tracks.assert_called_once_with("test query", limit=10)

    def test_search_in_service_youtube(self, song_matcher, mock_youtube_manager):
        """Test searching in YouTube service"""
        mock_youtube_manager.search_tracks.return_value = [
            {"title": "Song", "artists": [{"name": "Artist"}]}
        ]
        results = song_matcher._search_in_service("test query", "youtube")
        assert len(results) == 1
        mock_youtube_manager.search_tracks.assert_called_once_with("test query", limit=10)

    def test_search_in_service_youtube_returns_none(self, song_matcher, mock_youtube_manager):
        """Test that None from YouTube is converted to empty list"""
        mock_youtube_manager.search_tracks.return_value = None
        results = song_matcher._search_in_service("test query", "youtube")
        assert results == []

    def test_search_in_service_invalid_service(self, song_matcher):
        """Test that invalid service raises ValueError"""
        results = song_matcher._search_in_service("query", "invalid_service")
        assert results == []  # Returns empty list on error

    def test_search_in_service_handles_exception(self, song_matcher, mock_spotify_manager):
        """Test that exceptions are caught and return empty list"""
        mock_spotify_manager.search_tracks.side_effect = Exception("Network error")
        results = song_matcher._search_in_service("query", "spotify")
        assert results == []

    # Test parallel batch matching
    def test_batch_match_songs_parallel_empty(self, song_matcher):
        """Test parallel matching with empty list"""
        result = song_matcher.batch_match_songs_parallel([], 'spotify')
        assert result['matched'] == []
        assert result['unmatched'] == []
        assert result['errors'] == []

    def test_batch_match_songs_parallel_rate_limiting(self, song_matcher):
        """Test that parallel matching respects rate limits"""
        tracks = [
            {"name": f"Song {i}", "artist": f"Artist {i}"}
            for i in range(5)
        ]
        with patch.object(song_matcher, 'find_matching_song') as mock_find:
            mock_find.return_value = None
            import time
            start_time = time.time()
            song_matcher.batch_match_songs_parallel(tracks, 'youtube', max_workers=3)
            elapsed = time.time() - start_time
            # With rate limiting of 2 req/sec for YouTube, 5 tracks should take at least 2 seconds
            assert elapsed >= 1.0

    # Test manual match suggestions
    def test_suggest_manual_matches_empty(self, song_matcher):
        """Test suggesting matches for empty list"""
        suggestions = song_matcher.suggest_manual_matches([], 'spotify')
        assert suggestions == []

    def test_suggest_manual_matches_returns_low_confidence(self, song_matcher, mock_spotify_manager):
        """Test that suggestions include lower confidence matches"""
        mock_spotify_manager.search_tracks.return_value = [
            {"name": "Similar Song", "artist": "Similar Artist"}
        ]
        tracks = [{"name": "Song", "artist": "Artist"}]

        with patch.object(song_matcher, '_search_in_service') as mock_search:
            mock_search.return_value = [
                {"name": "Song Name", "artist": "Artist Name"}
            ]
            suggestions = song_matcher.suggest_manual_matches(tracks, 'spotify')
            assert len(suggestions) > 0
            assert 'confidence' in suggestions[0]
            assert 0.5 <= suggestions[0]['confidence'] < 0.8  # Below auto-match threshold

    def test_suggest_manual_matches_ignores_very_low_confidence(self, song_matcher):
        """Test that very low confidence matches are ignored"""
        tracks = [{"name": "Song A", "artist": "Artist A"}]
        with patch.object(song_matcher, '_search_in_service') as mock_search:
            mock_search.return_value = [
                {"name": "Completely Different", "artist": "Different Artist"}
            ]
            suggestions = song_matcher.suggest_manual_matches(tracks, 'spotify')
            # Should not suggest matches below 50% confidence
            assert all(s['confidence'] >= 0.5 for s in suggestions)
