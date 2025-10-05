"""
Playlist management for Spotify and Apple Music
Handles fetching playlists and playlist data
"""
import requests
from typing import List, Dict, Optional
from songbird.auth.spotify import SpotifyAuth
from songbird.auth.apple import AppleAuth


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


class ApplePlaylistManager:
    """Manages Apple Music playlist operations"""

    def __init__(self):
        self.auth = AppleAuth()
        self.base_url = 'https://api.music.apple.com/v1'

    def get_user_playlists(self) -> List[Dict]:
        """
        Get user playlists from Apple Music
        Note: This requires a user token, not just developer token
        """
        # For now, return empty list with instructions
        # TODO: Implement once user token flow is established
        print("⚠️  Apple Music playlist access requires user authentication")
        print(self.auth.get_user_token_instructions())
        return []

    def get_playlist_tracks(self, playlist_id: str) -> List[Dict]:
        """Get tracks from an Apple Music playlist"""
        # TODO: Implement once user token flow is established
        return []

    def search_tracks(self, query: str, limit: int = 20) -> List[Dict]:
        """Search for tracks on Apple Music"""
        token = self.auth.get_valid_token()
        if not token:
            raise Exception("No valid Apple Music token available")

        headers = {
            'Authorization': f'Bearer {token}'
        }

        params = {
            'term': query,
            'types': 'songs',
            'limit': limit
        }

        response = requests.get(
            f'{self.base_url}/catalog/us/search',
            headers=headers,
            params=params
        )

        if response.status_code != 200:
            raise Exception(f"Apple Music search failed: {response.status_code}")

        data = response.json()
        tracks = []

        if 'songs' in data['results']:
            for track in data['results']['songs']['data']:
                tracks.append({
                    'id': track['id'],
                    'name': track['attributes']['name'],
                    'artist': track['attributes']['artistName'],
                    'album': track['attributes']['albumName'],
                    'duration_ms': track['attributes']['durationInMillis']
                })

        return tracks