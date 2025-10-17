"""
Song matching logic between Spotify and YouTube Music
Handles finding equivalent tracks across services with fuzzy matching
"""
import re
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
from songbird.sync.playlist_manager import SpotifyPlaylistManager, YouTubePlaylistManager


class SongMatcher:
    """Handles matching songs between Spotify and YouTube Music"""

    def __init__(self):
        self.spotify_manager = SpotifyPlaylistManager()
        self.youtube_manager = YouTubePlaylistManager()

    def find_matching_song(self, source_track: Dict, target_service: str) -> Optional[Dict]:
        """
        Find a matching song in the target service

        Args:
            source_track: Track from source service
            target_service: 'spotify' or 'youtube'

        Returns:
            Best matching track or None if no good match found
        """
        # Create search query
        search_query = self._build_search_query(source_track)

        # Search in target service
        search_results = self._search_in_service(search_query, target_service)

        if not search_results:
            return None

        # Find best match
        best_match = self._find_best_match(source_track, search_results)

        return best_match

    def batch_match_songs(self, source_tracks: List[Dict], target_service: str) -> Dict:
        """
        Match a batch of songs and return results

        Returns:
            {
                'matched': [(source_track, target_track), ...],
                'unmatched': [source_track, ...],
                'errors': [{'track': source_track, 'error': str}, ...]
            }
        """
        results = {
            'matched': [],
            'unmatched': [],
            'errors': []
        }

        for track in source_tracks:
            try:
                match = self.find_matching_song(track, target_service)
                if match:
                    results['matched'].append((track, match))
                else:
                    results['unmatched'].append(track)
            except Exception as e:
                results['errors'].append({'track': track, 'error': str(e)})

        return results

    def _build_search_query(self, track: Dict) -> str:
        """Build search query from track information"""
        # Extract clean artist and track names
        artist = self._clean_string(track['artist'])
        title = self._clean_string(track['name'])

        # Simple search query: "artist track"
        return f"{artist} {title}"

    def _clean_string(self, text: str) -> str:
        """Clean string for better matching"""
        if not text:
            return ""

        # Remove common annotations
        text = re.sub(r'\(.*?\)', '', text)  # Remove parentheses content
        text = re.sub(r'\[.*?\]', '', text)  # Remove bracket content
        text = re.sub(r'\s*-\s*.*$', '', text)  # Remove everything after dash

        # Remove common words that might interfere
        remove_words = ['feat', 'featuring', 'ft', 'remix', 'remaster', 'remastered']
        for word in remove_words:
            text = re.sub(rf'\b{word}\.?\b', '', text, flags=re.IGNORECASE)

        # Clean up whitespace
        text = ' '.join(text.split())

        return text.strip()

    def _search_in_service(self, query: str, service: str) -> List[Dict]:
        """Search for tracks in the specified service"""
        try:
            if service == 'spotify':
                return self.spotify_manager.search_tracks(query, limit=10)
            elif service == 'youtube':
                return self.youtube_manager.search_tracks(query, limit=10)
            else:
                raise ValueError(f"Unknown service: {service}")
        except Exception as e:
            print(f"Search error in {service}: {e}")
            return []

    def _find_best_match(self, source_track: Dict, candidates: List[Dict]) -> Optional[Dict]:
        """Find the best matching track from candidates"""
        if not candidates:
            return None

        best_match = None
        best_score = 0.0

        source_artist = self._clean_string(source_track['artist']).lower()
        source_title = self._clean_string(source_track['name']).lower()

        for candidate in candidates:
            candidate_artist = self._clean_string(candidate['artist']).lower()
            candidate_title = self._clean_string(candidate['name']).lower()

            # Calculate similarity scores
            artist_score = self._similarity_score(source_artist, candidate_artist)
            title_score = self._similarity_score(source_title, candidate_title)

            # Weight title more heavily than artist
            combined_score = (title_score * 0.7) + (artist_score * 0.3)

            # Bonus for exact matches
            if source_artist == candidate_artist:
                combined_score += 0.1
            if source_title == candidate_title:
                combined_score += 0.1

            # Duration similarity (if available)
            if 'duration_ms' in source_track and 'duration_ms' in candidate:
                duration_score = self._duration_similarity(
                    source_track['duration_ms'],
                    candidate['duration_ms']
                )
                combined_score = (combined_score * 0.9) + (duration_score * 0.1)

            if combined_score > best_score:
                best_score = combined_score
                best_match = candidate

        # Only return matches above threshold
        if best_score >= 0.8:  # 80% similarity threshold
            return best_match

        return None

    def _similarity_score(self, str1: str, str2: str) -> float:
        """Calculate similarity score between two strings"""
        if not str1 or not str2:
            return 0.0

        # Use SequenceMatcher for fuzzy string matching
        return SequenceMatcher(None, str1, str2).ratio()

    def _duration_similarity(self, duration1: int, duration2: int) -> float:
        """Calculate similarity score for track durations"""
        if not duration1 or not duration2:
            return 0.0

        # Allow up to 5 second difference
        diff = abs(duration1 - duration2)
        max_diff = 5000  # 5 seconds in milliseconds

        if diff <= max_diff:
            return 1.0 - (diff / max_diff)
        else:
            return 0.0

    def get_match_confidence(self, source_track: Dict, target_track: Dict) -> float:
        """Get confidence score for a manual match"""
        source_artist = self._clean_string(source_track['artist']).lower()
        source_title = self._clean_string(source_track['name']).lower()
        target_artist = self._clean_string(target_track['artist']).lower()
        target_title = self._clean_string(target_track['name']).lower()

        artist_score = self._similarity_score(source_artist, target_artist)
        title_score = self._similarity_score(source_title, target_title)

        return (title_score * 0.7) + (artist_score * 0.3)

    def suggest_manual_matches(self, unmatched_tracks: List[Dict], target_service: str) -> List[Dict]:
        """
        Suggest potential manual matches for unmatched tracks
        Returns lower confidence matches for user review
        """
        suggestions = []

        for track in unmatched_tracks:
            search_query = self._build_search_query(track)
            candidates = self._search_in_service(search_query, target_service)

            if candidates:
                # Get best candidate even if below threshold
                best_candidate = None
                best_score = 0.0

                source_artist = self._clean_string(track['artist']).lower()
                source_title = self._clean_string(track['name']).lower()

                for candidate in candidates:
                    candidate_artist = self._clean_string(candidate['artist']).lower()
                    candidate_title = self._clean_string(candidate['name']).lower()

                    artist_score = self._similarity_score(source_artist, candidate_artist)
                    title_score = self._similarity_score(source_title, candidate_title)
                    combined_score = (title_score * 0.7) + (artist_score * 0.3)

                    if combined_score > best_score:
                        best_score = combined_score
                        best_candidate = candidate

                if best_candidate and best_score >= 0.5:  # Lower threshold for suggestions
                    suggestions.append({
                        'source_track': track,
                        'suggested_match': best_candidate,
                        'confidence': best_score
                    })

        return suggestions