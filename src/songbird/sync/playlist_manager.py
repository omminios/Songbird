"""
Playlist management for Spotify and YouTube Music
Handles fetching playlists and playlist data
"""
import requests
from typing import List, Dict, Optional
from songbird.auth.spotify import SpotifyAuth
from songbird.auth.youtube import YouTubeAuth


class SpotifyPlaylistManager:
    """Manages Spotify playlist operations"""

    def __init__(self):
        self.auth = SpotifyAuth()
        self.base_url = 'https://api.spotify.com/v1'

    def get_user_playlists(self) -> List[Dict]:
        """Get all user playlists from Spotify"""
        token = self.auth.get_valid_token()
        if not token:
            raise Exception("No valid Spotify token available")

        headers = {
            'Authorization': f'Bearer {token}'
        }

        playlists = []
        url = f'{self.base_url}/me/playlists'

        while url:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch playlists: {response.status_code}")

            data = response.json()
            for playlist in data['items']:
                # Only include playlists owned by the user
                if playlist['owner']['id'] == self._get_user_id():
                    playlists.append({
                        'id': playlist['id'],
                        'name': playlist['name'],
                        'uri': playlist['uri'],
                        'tracks_total': playlist['tracks']['total'],
                        'public': playlist['public']
                    })

            url = data.get('next')

        return playlists

    def get_playlist_tracks(self, playlist_id: str) -> List[Dict]:
        """Get all tracks from a specific playlist"""
        token = self.auth.get_valid_token()
        if not token:
            raise Exception("No valid Spotify token available")

        headers = {
            'Authorization': f'Bearer {token}'
        }

        tracks = []
        url = f'{self.base_url}/playlists/{playlist_id}/tracks'

        while url:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch tracks: {response.status_code}")

            data = response.json()
            for item in data['items']:
                if item['track'] and item['track']['type'] == 'track':
                    track = item['track']
                    tracks.append({
                        'id': track['id'],
                        'name': track['name'],
                        'artist': ', '.join([artist['name'] for artist in track['artists']]),
                        'album': track['album']['name'],
                        'uri': track['uri'],
                        'duration_ms': track['duration_ms']
                    })

            url = data.get('next')

        return tracks

    def add_tracks_to_playlist(self, playlist_id: str, track_uris: List[str]):
        """Add tracks to a Spotify playlist"""
        token = self.auth.get_valid_token()
        if not token:
            raise Exception("No valid Spotify token available")

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        # Spotify allows max 100 tracks per request
        chunk_size = 100
        for i in range(0, len(track_uris), chunk_size):
            chunk = track_uris[i:i + chunk_size]

            response = requests.post(
                f'{self.base_url}/playlists/{playlist_id}/tracks',
                headers=headers,
                json={'uris': chunk}
            )

            if response.status_code not in [200, 201]:
                raise Exception(f"Failed to add tracks: {response.status_code}")

    def remove_tracks_from_playlist(self, playlist_id: str, track_uris: List[str]):
        """Remove tracks from a Spotify playlist"""
        token = self.auth.get_valid_token()
        if not token:
            raise Exception("No valid Spotify token available")

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        # Format tracks for deletion
        tracks_to_remove = [{'uri': uri} for uri in track_uris]

        # Spotify allows max 100 tracks per request
        chunk_size = 100
        for i in range(0, len(tracks_to_remove), chunk_size):
            chunk = tracks_to_remove[i:i + chunk_size]

            response = requests.delete(
                f'{self.base_url}/playlists/{playlist_id}/tracks',
                headers=headers,
                json={'tracks': chunk}
            )

            if response.status_code not in [200, 201]:
                raise Exception(f"Failed to remove tracks: {response.status_code}")

    def search_tracks(self, query: str, limit: int = 20) -> List[Dict]:
        """Search for tracks on Spotify"""
        token = self.auth.get_valid_token()
        if not token:
            raise Exception("No valid Spotify token available")

        headers = {
            'Authorization': f'Bearer {token}'
        }

        params = {
            'q': query,
            'type': 'track',
            'limit': limit
        }

        response = requests.get(f'{self.base_url}/search', headers=headers, params=params)

        if response.status_code != 200:
            raise Exception(f"Search failed: {response.status_code}")

        data = response.json()
        tracks = []

        for track in data['tracks']['items']:
            tracks.append({
                'id': track['id'],
                'name': track['name'],
                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                'album': track['album']['name'],
                'uri': track['uri'],
                'duration_ms': track['duration_ms']
            })

        return tracks

    def _get_user_id(self) -> str:
        """Get the current user's Spotify ID"""
        token = self.auth.get_valid_token()
        if not token:
            raise Exception("No valid Spotify token available")

        headers = {
            'Authorization': f'Bearer {token}'
        }

        response = requests.get(f'{self.base_url}/me', headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to get user info: {response.status_code}")

        return response.json()['id']


class YouTubePlaylistManager:
    """Manages YouTube Music playlist operations"""

    def __init__(self):
        self.auth = YouTubeAuth()

    def get_user_playlists(self) -> List[Dict]:
        """
        Get user playlists from YouTube Music

        Returns:
            List of playlist dictionaries
        """
        client = self.auth.get_client()
        if not client:
            raise Exception("No valid YouTube Music client available")

        try:
            # Get library playlists from YouTube Music
            playlists = client.get_library_playlists(limit=100)

            # Format to match Spotify structure
            formatted = []
            for playlist in playlists:
                formatted.append({
                    'id': playlist['playlistId'],
                    'name': playlist['title'],
                    'uri': f"ytmusic:playlist:{playlist['playlistId']}",
                    'tracks_total': playlist.get('count', 0),
                    'public': True
                })

            return formatted

        except Exception as e:
            raise Exception(f"Failed to fetch YouTube playlists: {e}")

    def get_playlist_tracks(self, playlist_id: str) -> List[Dict]:
        """
        Get tracks from a YouTube Music playlist

        Args:
            playlist_id: YouTube Music playlist ID

        Returns:
            List of track dictionaries
        """
        client = self.auth.get_client()
        if not client:
            raise Exception("No valid YouTube Music client available")

        try:
            # Get playlist details including tracks
            playlist_data = client.get_playlist(playlist_id, limit=None)

            if 'tracks' not in playlist_data:
                return []

            # Format tracks to match Spotify structure
            formatted = []
            for track in playlist_data['tracks']:
                # Skip if track data is incomplete
                if not track.get('videoId'):
                    continue

                # Get artist names
                artists = []
                if track.get('artists'):
                    artists = [artist['name'] for artist in track['artists']]

                # Get duration in milliseconds (YouTube returns seconds)
                duration_ms = None
                if track.get('duration_seconds'):
                    duration_ms = int(track['duration_seconds']) * 1000

                formatted.append({
                    'id': track['videoId'],
                    'name': track.get('title', ''),
                    'artist': ', '.join(artists),
                    'album': '',  # YouTube Music doesn't always have album info
                    'uri': f"ytmusic:track:{track['videoId']}",
                    'duration_ms': duration_ms,
                    'setVideoId': track.get('setVideoId')  # Needed for removal
                })

            return formatted

        except Exception as e:
            raise Exception(f"Failed to fetch YouTube playlist tracks: {e}")

    def add_tracks_to_playlist(self, playlist_id: str, track_ids: List[str]):
        """
        Add tracks to a YouTube Music playlist

        Args:
            playlist_id: YouTube playlist ID
            track_ids: List of video IDs to add
        """
        if not track_ids:
            return

        client = self.auth.get_client()
        if not client:
            raise Exception("No valid YouTube Music client available")

        try:
            # YouTube Music API allows batch adding
            client.add_playlist_items(playlist_id, track_ids)

        except Exception as e:
            raise Exception(f"Failed to add tracks to YouTube playlist: {e}")

    def remove_tracks_from_playlist(self, playlist_id: str, set_video_ids: List[str]):
        """
        Remove tracks from a YouTube Music playlist

        Args:
            playlist_id: YouTube playlist ID
            set_video_ids: List of setVideoIds (unique playlist item identifiers)
        """
        if not set_video_ids:
            return

        client = self.auth.get_client()
        if not client:
            raise Exception("No valid YouTube Music client available")

        try:
            # YouTube Music API requires setVideoIds for removal
            client.remove_playlist_items(playlist_id, set_video_ids)

        except Exception as e:
            raise Exception(f"Failed to remove tracks from YouTube playlist: {e}")

    def search_tracks(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search for tracks on YouTube Music

        Args:
            query: Search query (track name and artist)
            limit: Maximum number of results

        Returns:
            List of track dictionaries
        """
        client = self.auth.get_client()
        if not client:
            raise Exception("No valid YouTube Music client available")

        try:
            # Search for songs on YouTube Music
            results = client.search(query, filter='songs', limit=limit)

            # Check if results is None or empty
            if results is None:
                return []

            if not isinstance(results, list):
                return []

            # Format results to match Spotify structure
            formatted = []
            for track in results:
                if not track or not isinstance(track, dict):
                    continue

                if not track.get('videoId'):
                    continue

                # Get artist names
                artists = []
                if track.get('artists'):
                    artists = [artist['name'] for artist in track['artists'] if artist and isinstance(artist, dict)]

                # Get duration
                duration_ms = None
                if track.get('duration_seconds'):
                    duration_ms = int(track['duration_seconds']) * 1000

                # Get album info safely
                album_name = ''
                if track.get('album') and isinstance(track.get('album'), dict):
                    album_name = track['album'].get('name', '')

                formatted.append({
                    'id': track['videoId'],
                    'name': track.get('title', ''),
                    'artist': ', '.join(artists),
                    'album': album_name,
                    'uri': f"ytmusic:track:{track['videoId']}",
                    'duration_ms': duration_ms
                })

            return formatted

        except Exception as e:
            raise Exception(f"YouTube Music search failed: {e}")