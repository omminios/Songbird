"""
Sync manager for coordinating playlist synchronization
Handles the main sync logic and orchestrates all components
"""
import json
import boto3
import requests
from datetime import datetime
from typing import Dict, List, Tuple
from songbird.config.manager import ConfigManager
from songbird.sync.playlist_manager import SpotifyPlaylistManager, ApplePlaylistManager
from songbird.sync.song_matcher import SongMatcher


class SyncManager:
    """Manages playlist synchronization between services"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.spotify_manager = SpotifyPlaylistManager()
        self.apple_manager = ApplePlaylistManager()
        self.song_matcher = SongMatcher()

    def manual_sync(self) -> bool:
        """
        Trigger manual sync via AWS Lambda or local execution
        Returns True if sync was successful
        """
        pairs = self.config_manager.get_playlist_pairs()
        if not pairs:
            print("No playlist pairs configured")
            return False

        try:
            # For now, run sync locally
            # TODO: Replace with AWS Lambda invocation
            return self._run_local_sync()

        except Exception as e:
            self.config_manager.log_error('manual_sync', str(e))
            print(f"Manual sync failed: {e}")
            return False

    def _run_local_sync(self) -> bool:
        """Run synchronization locally (for testing/development)"""
        print("🔄 Starting local sync...")

        pairs = self.config_manager.get_playlist_pairs()
        all_success = True

        for pair in pairs:
            print(f"\n📋 Syncing: {pair['spotify']['name']} ↔ {pair['apple']['name']}")

            try:
                success = self._sync_playlist_pair(pair)
                if success:
                    self.config_manager.update_sync_status(
                        pair['id'],
                        'success',
                        {'synced_at': datetime.now(datetime.UTC).isoformat()}
                    )
                    print(f"✅ Sync completed for pair {pair['id']}")
                else:
                    all_success = False
                    self.config_manager.update_sync_status(
                        pair['id'],
                        'failed'
                    )
                    print(f"❌ Sync failed for pair {pair['id']}")

            except Exception as e:
                all_success = False
                self.config_manager.log_error(
                    'pair_sync',
                    f"Failed to sync pair {pair['id']}: {str(e)}",
                    {'pair_id': pair['id']}
                )
                print(f"❌ Error syncing pair {pair['id']}: {e}")

        return all_success

    def _sync_playlist_pair(self, pair: Dict) -> bool:
        """
        Synchronize a single playlist pair
        Returns True if successful
        """
        try:
            # Get current tracks from both playlists
            spotify_tracks = self._get_spotify_tracks(pair['spotify']['id'])
            apple_tracks = self._get_apple_tracks(pair['apple']['id'])

            print(f"  Spotify: {len(spotify_tracks)} tracks")
            print(f"  Apple Music: {len(apple_tracks)} tracks")

            # For demo mode (Apple Music not fully implemented)
            if not apple_tracks:
                return self._demo_sync_spotify_only(pair, spotify_tracks)

            # Determine what needs to be synced
            sync_plan = self._create_sync_plan(spotify_tracks, apple_tracks)

            # Execute sync plan
            return self._execute_sync_plan(pair, sync_plan)

        except Exception as e:
            print(f"  Error in sync: {e}")
            return False

    def _get_spotify_tracks(self, playlist_id: str) -> List[Dict]:
        """Get tracks from Spotify playlist"""
        try:
            return self.spotify_manager.get_playlist_tracks(playlist_id)
        except Exception as e:
            print(f"  Failed to get Spotify tracks: {e}")
            return []

    def _get_apple_tracks(self, playlist_id: str) -> List[Dict]:
        """Get tracks from Apple Music playlist"""
        try:
            # For now, return empty list since Apple Music integration is incomplete
            return self.apple_manager.get_playlist_tracks(playlist_id)
        except Exception as e:
            print(f"  Apple Music tracks not available: {e}")
            return []

    def _demo_sync_spotify_only(self, pair: Dict, spotify_tracks: List[Dict]) -> bool:
        """Demo sync for Spotify-only mode"""
        print("  🔧 Demo mode: Spotify playlist analysis")

        if not spotify_tracks:
            print("  No tracks found in Spotify playlist")
            return True

        # Analyze tracks
        print(f"  📊 Playlist contains {len(spotify_tracks)} tracks:")

        # Show sample tracks
        for i, track in enumerate(spotify_tracks[:3]):
            print(f"    {i+1}. {track['name']} by {track['artist']}")

        if len(spotify_tracks) > 3:
            print(f"    ... and {len(spotify_tracks) - 3} more")

        # Simulate matching process
        print("  🔍 Simulating song matching...")
        match_results = self.song_matcher.batch_match_songs(
            spotify_tracks[:5],  # Test with first 5 tracks
            'apple'
        )

        print(f"  📈 Match simulation results:")
        print(f"    - Matched: {len(match_results['matched'])}")
        print(f"    - Unmatched: {len(match_results['unmatched'])}")
        print(f"    - Errors: {len(match_results['errors'])}")

        return True

    def _create_sync_plan(self, spotify_tracks: List[Dict], apple_tracks: List[Dict]) -> Dict:
        """
        Create a sync plan by comparing playlists
        Returns what needs to be added/removed from each service
        """
        # Match existing tracks
        spotify_to_apple = self.song_matcher.batch_match_songs(spotify_tracks, 'apple')
        apple_to_spotify = self.song_matcher.batch_match_songs(apple_tracks, 'spotify')

        # Find tracks that need to be added
        spotify_only = [track for track in spotify_tracks
                       if not any(track['id'] == match[0]['id']
                                for match in apple_to_spotify['matched'])]

        apple_only = [track for track in apple_tracks
                     if not any(track['id'] == match[0]['id']
                              for match in spotify_to_apple['matched'])]

        return {
            'add_to_spotify': apple_only,
            'add_to_apple': spotify_only,
            'matched_tracks': spotify_to_apple['matched'],
            'unmatched_spotify': spotify_to_apple['unmatched'],
            'unmatched_apple': apple_to_spotify['unmatched']
        }

    def _execute_sync_plan(self, pair: Dict, sync_plan: Dict) -> bool:
        """Execute the synchronization plan"""
        success = True

        try:
            # Add Spotify tracks to Apple Music
            if sync_plan['add_to_apple']:
                print(f"  ➕ Adding {len(sync_plan['add_to_apple'])} tracks to Apple Music")
                # TODO: Implement when Apple Music is ready
                # success &= self._add_tracks_to_apple(pair['apple']['id'], sync_plan['add_to_apple'])

            # Add Apple Music tracks to Spotify
            if sync_plan['add_to_spotify']:
                print(f"  ➕ Adding {len(sync_plan['add_to_spotify'])} tracks to Spotify")
                # TODO: Implement when Apple Music is ready
                # success &= self._add_tracks_to_spotify(pair['spotify']['id'], sync_plan['add_to_spotify'])

            # Log unmatched tracks
            if sync_plan['unmatched_spotify'] or sync_plan['unmatched_apple']:
                self._log_unmatched_tracks(pair, sync_plan)

        except Exception as e:
            print(f"  Error executing sync plan: {e}")
            success = False

        return success

    def _add_tracks_to_spotify(self, playlist_id: str, tracks: List[Dict]) -> bool:
        """Add tracks to Spotify playlist"""
        try:
            # Find Spotify equivalents for the tracks
            spotify_uris = []
            for track in tracks:
                match = self.song_matcher.find_matching_song(track, 'spotify')
                if match:
                    spotify_uris.append(match['uri'])

            if spotify_uris:
                self.spotify_manager.add_tracks_to_playlist(playlist_id, spotify_uris)
                return True

        except Exception as e:
            print(f"Failed to add tracks to Spotify: {e}")

        return False

    def _log_unmatched_tracks(self, pair: Dict, sync_plan: Dict):
        """Log tracks that couldn't be matched"""
        unmatched_data = {
            'pair_id': pair['id'],
            'spotify_playlist': pair['spotify']['name'],
            'apple_playlist': pair['apple']['name'],
            'unmatched_spotify': sync_plan['unmatched_spotify'],
            'unmatched_apple': sync_plan['unmatched_apple'],
            'timestamp': datetime.now(datetime.UTC).isoformat()
        }

        self.config_manager.log_error(
            'unmatched_tracks',
            f"Found {len(sync_plan['unmatched_spotify']) + len(sync_plan['unmatched_apple'])} unmatched tracks",
            unmatched_data
        )

    def invoke_lambda_sync(self) -> bool:
        """
        Invoke AWS Lambda function for sync
        TODO: Implement when AWS infrastructure is ready
        """
        try:
            # This would invoke the Lambda function
            lambda_client = boto3.client('lambda')

            response = lambda_client.invoke(
                FunctionName='songbird-sync',
                InvocationType='RequestResponse',
                Payload=json.dumps({
                    'trigger': 'manual',
                    'timestamp': datetime.now(datetime.UTC).isoformat()
                })
            )

            result = json.loads(response['Payload'].read())
            return result.get('success', False)

        except Exception as e:
            print(f"Lambda invocation failed: {e}")
            return False

    def invoke_api_gateway_sync(self) -> bool:
        """
        Invoke sync via API Gateway endpoint
        TODO: Implement when API Gateway is set up
        """
        try:
            # This would call the API Gateway endpoint
            api_endpoint = "https://your-api-gateway-url/sync"

            response = requests.post(
                api_endpoint,
                json={
                    'trigger': 'manual',
                    'timestamp': datetime.now(datetime.UTC).isoformat()
                },
                timeout=30
            )

            return response.status_code == 200

        except Exception as e:
            print(f"API Gateway invocation failed: {e}")
            return False