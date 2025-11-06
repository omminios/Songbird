"""
Sync manager for coordinating playlist synchronization
Handles the main sync logic and orchestrates all components
"""
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from songbird.config.manager import ConfigManager
from songbird.sync.playlist_manager import SpotifyPlaylistManager, YouTubePlaylistManager
from songbird.sync.song_matcher import SongMatcher


class SyncManager:
    """Manages playlist synchronization between services"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.spotify_manager = SpotifyPlaylistManager()
        self.youtube_manager = YouTubePlaylistManager()
        self.song_matcher = SongMatcher()

    def manual_sync(self, verbose: bool = False, force: bool = False, dry_run: bool = False) -> bool:
        """
        Trigger manual sync from CLI
        Returns True if sync was successful

        Note: Scheduled syncs are triggered by EventBridge -> Lambda
        """
        pairs = self.config_manager.get_playlist_pairs()
        if not pairs:
            print("No playlist pairs configured")
            return False

        try:
            return self.run_sync(verbose=verbose, force=force, dry_run=dry_run)

        except Exception as e:
            self.config_manager.log_error('manual_sync', str(e))
            print(f"Manual sync failed: {e}")
            return False

    def run_sync(self, verbose: bool = False, force: bool = False, dry_run: bool = False) -> bool:
        """
        Core synchronization logic - works in both CLI and Lambda environments
        Returns True if sync was successful
        """
        if dry_run:
            print("🔍 Analyzing playlists (dry run - no changes will be made)...")
        else:
            print("🔄 Starting local sync...")

        pairs = self.config_manager.get_playlist_pairs()
        all_success = True
        skipped_count = 0

        for pair in pairs:
            print(f"\n📋 {'Analyzing' if dry_run else 'Syncing'}: {pair['spotify']['name']} ↔ {pair['youtube']['name']}")

            try:
                # Quick change detection if not forced
                if not force:
                    needs_sync = self._check_if_sync_needed(pair, verbose=verbose)
                    if not needs_sync:
                        print(f"  ⏩ No changes detected")
                        skipped_count += 1
                        continue

                success = self._sync_playlist_pair(pair, verbose=verbose, dry_run=dry_run)
                if success:
                    if not dry_run:
                        self.config_manager.update_sync_status(
                            pair['id'],
                            'success',
                            {'synced_at': datetime.now(timezone.utc).isoformat()}
                        )
                        print(f"✅ Sync completed for pair {pair['id']}")
                    else:
                        print(f"✅ Analysis completed for pair {pair['id']}")
                else:
                    all_success = False
                    if not dry_run:
                        self.config_manager.update_sync_status(
                            pair['id'],
                            'failed'
                        )
                        print(f"❌ Sync failed for pair {pair['id']}")
                    else:
                        print(f"❌ Analysis failed for pair {pair['id']}")

            except Exception as e:
                all_success = False
                if not dry_run:
                    self.config_manager.log_error(
                        'pair_sync',
                        f"Failed to sync pair {pair['id']}: {str(e)}",
                        {'pair_id': pair['id']}
                    )
                print(f"❌ Error {'analyzing' if dry_run else 'syncing'} pair {pair['id']}: {e}")

        if skipped_count > 0:
            print(f"\n⏩ {skipped_count} playlist(s) with no changes")

        return all_success

    def _check_if_sync_needed(self, pair: Dict, verbose: bool = False) -> bool:
        """
        Quick check to see if sync is needed by comparing track counts
        Returns True if sync is needed, False if playlists appear unchanged
        """
        try:
            # Get current track counts (fast - doesn't fetch full track lists)
            spotify_tracks = self.spotify_manager.get_playlist_tracks(pair['spotify']['id'])
            youtube_tracks = self.youtube_manager.get_playlist_tracks(pair['youtube']['id'])

            current_spotify_count = len(spotify_tracks)
            current_youtube_count = len(youtube_tracks)

            # Get cached snapshot
            snapshot = self.config_manager.get_playlist_snapshot(pair['id'])

            if not snapshot:
                # No snapshot yet, sync needed
                if verbose:
                    print(f"  ℹ️  No previous snapshot found")
                return True

            # Compare track counts
            prev_spotify = snapshot.get('spotify_count', 0)
            prev_youtube = snapshot.get('youtube_count', 0)

            if current_spotify_count != prev_spotify or current_youtube_count != prev_youtube:
                if verbose:
                    print(f"  ℹ️  Changes detected:")
                    if current_spotify_count != prev_spotify:
                        print(f"    Spotify: {prev_spotify} → {current_spotify_count} tracks")
                    if current_youtube_count != prev_youtube:
                        print(f"    YouTube: {prev_youtube} → {current_youtube_count} tracks")
                return True

            # Counts match, likely no changes
            return False

        except Exception as e:
            # If check fails, assume sync is needed
            if verbose:
                print(f"  ⚠️  Change detection failed: {e}")
            return True

    def _sync_playlist_pair(self, pair: Dict, verbose: bool = False, dry_run: bool = False) -> bool:
        """
        Synchronize a single playlist pair
        Returns True if successful
        """
        try:
            # Get current tracks from both playlists
            spotify_tracks = self._get_spotify_tracks(pair['spotify']['id'])
            youtube_tracks = self._get_youtube_tracks(pair['youtube']['id'])

            print(f"  Spotify: {len(spotify_tracks)} tracks")
            print(f"  YouTube Music: {len(youtube_tracks)} tracks")

            # Determine what needs to be synced
            sync_plan = self._create_sync_plan(spotify_tracks, youtube_tracks, verbose=verbose)

            # Execute sync plan (or just preview in dry-run mode)
            if dry_run:
                success = self._preview_sync_plan(sync_plan)
            else:
                success = self._execute_sync_plan(pair, sync_plan)

            # Update snapshot after sync (even if partial success)
            # This prevents re-syncing the same tracks on next run
            if success and not dry_run:
                # Refetch counts after sync to get accurate snapshot
                final_spotify = self._get_spotify_tracks(pair['spotify']['id'])
                final_youtube = self._get_youtube_tracks(pair['youtube']['id'])

                self.config_manager.update_playlist_snapshot(
                    pair['id'],
                    len(final_spotify),
                    len(final_youtube)
                )

            return success

        except Exception as e:
            print(f"  Error in {'analysis' if dry_run else 'sync'}: {e}")
            return False

    def _get_spotify_tracks(self, playlist_id: str) -> List[Dict]:
        """Get tracks from Spotify playlist"""
        try:
            return self.spotify_manager.get_playlist_tracks(playlist_id)
        except Exception as e:
            print(f"  Failed to get Spotify tracks: {e}")
            return []

    def _get_youtube_tracks(self, playlist_id: str) -> List[Dict]:
        """Get tracks from YouTube Music playlist"""
        try:
            return self.youtube_manager.get_playlist_tracks(playlist_id)
        except Exception as e:
            print(f"  YouTube Music tracks not available: {e}")
            return []

    def _create_sync_plan(self, spotify_tracks: List[Dict], youtube_tracks: List[Dict], verbose: bool = False) -> Dict:
        """
        Create a sync plan by comparing playlists
        Returns what needs to be added/removed from each service
        """
        # Get track names/artists for comparison (normalized for matching)
        def normalize_track(track):
            return (
                self.song_matcher._clean_string(track['name']).lower(),
                self.song_matcher._clean_string(track['artist']).lower()
            )

        # Deduplicate tracks by keeping only first occurrence
        # This prevents issues with playlists that have duplicate tracks
        seen_spotify = set()
        deduplicated_spotify = []
        for track in spotify_tracks:
            norm = normalize_track(track)
            if norm not in seen_spotify:
                seen_spotify.add(norm)
                deduplicated_spotify.append(track)

        seen_youtube = set()
        deduplicated_youtube = []
        for track in youtube_tracks:
            norm = normalize_track(track)
            if norm not in seen_youtube:
                seen_youtube.add(norm)
                deduplicated_youtube.append(track)

        if verbose and (len(spotify_tracks) != len(deduplicated_spotify) or len(youtube_tracks) != len(deduplicated_youtube)):
            print(f"\n  ℹ️  Removed duplicates:")
            if len(spotify_tracks) != len(deduplicated_spotify):
                print(f"    Spotify: {len(spotify_tracks)} → {len(deduplicated_spotify)} tracks")
            if len(youtube_tracks) != len(deduplicated_youtube):
                print(f"    YouTube: {len(youtube_tracks)} → {len(deduplicated_youtube)} tracks")

        # Create sets of normalized track identifiers from deduplicated lists
        spotify_track_set = {normalize_track(t) for t in deduplicated_spotify}
        youtube_track_set = {normalize_track(t) for t in deduplicated_youtube}

        # Find tracks that exist in one playlist but not the other
        spotify_only_normalized = spotify_track_set - youtube_track_set
        youtube_only_normalized = youtube_track_set - spotify_track_set

        # Get the actual track objects that need to be synced (from deduplicated lists)
        spotify_only = [t for t in deduplicated_spotify if normalize_track(t) in spotify_only_normalized]
        youtube_only = [t for t in deduplicated_youtube if normalize_track(t) in youtube_only_normalized]

        if verbose:
            print(f"\n  📊 Sync Plan:")
            print(f"    Tracks only in Spotify: {len(spotify_only)}")
            print(f"    Tracks only in YouTube: {len(youtube_only)}")
            print(f"    Tracks in both: {len(spotify_track_set & youtube_track_set)}")

            if youtube_only:
                print(f"\n  📋 YouTube tracks to add to Spotify:")
                for track in youtube_only[:5]:  # Show first 5
                    print(f"    - {track['name']} by {track['artist']}")
                if len(youtube_only) > 5:
                    print(f"    ... and {len(youtube_only) - 5} more")

            if spotify_only:
                print(f"\n  📋 Spotify tracks to add to YouTube:")
                for track in spotify_only[:5]:  # Show first 5
                    print(f"    - {track['name']} by {track['artist']}")
                if len(spotify_only) > 5:
                    print(f"    ... and {len(spotify_only) - 5} more")

        # Match the tracks that need to be synced
        spotify_to_youtube_matches = []
        youtube_to_spotify_matches = []
        unmatched_spotify = []
        unmatched_youtube = []

        # Decide whether to use parallel matching based on number of tracks
        use_parallel = len(spotify_only) > 5 or len(youtube_only) > 5

        # Match Spotify-only tracks to YouTube
        if spotify_only:
            if verbose:
                mode = "parallel" if use_parallel and len(spotify_only) > 5 else "sequential"
                print(f"\n  🔍 Finding YouTube versions of Spotify tracks ({mode})...")

            if use_parallel and len(spotify_only) > 5:
                # Use parallel matching for better performance
                results = self.song_matcher.batch_match_songs_parallel(
                    spotify_only, 'youtube', max_workers=5, verbose=verbose
                )
                spotify_to_youtube_matches = results['matched']
                unmatched_spotify = results['unmatched']
            else:
                # Use sequential matching for small batches
                for track in spotify_only:
                    if verbose:
                        print(f"    Searching: {track['name']} - {track['artist']}")
                    match = self.song_matcher.find_matching_song(track, 'youtube')
                    if match:
                        spotify_to_youtube_matches.append((track, match))
                        if verbose:
                            print(f"      ✅ Found: {match['name']}")
                    else:
                        unmatched_spotify.append(track)
                        if verbose:
                            print(f"      ❌ No match")

        # Match YouTube-only tracks to Spotify
        if youtube_only:
            if verbose:
                mode = "parallel" if use_parallel and len(youtube_only) > 5 else "sequential"
                print(f"\n  🔍 Finding Spotify versions of YouTube tracks ({mode})...")

            if use_parallel and len(youtube_only) > 5:
                # Use parallel matching for better performance
                results = self.song_matcher.batch_match_songs_parallel(
                    youtube_only, 'spotify', max_workers=5, verbose=verbose
                )
                youtube_to_spotify_matches = results['matched']
                unmatched_youtube = results['unmatched']
            else:
                # Use sequential matching for small batches
                for track in youtube_only:
                    if verbose:
                        print(f"    Searching: {track['name']} - {track['artist']}")
                    match = self.song_matcher.find_matching_song(track, 'spotify')
                    if match:
                        youtube_to_spotify_matches.append((track, match))
                        if verbose:
                            print(f"      ✅ Found: {match['name']}")
                    else:
                        unmatched_youtube.append(track)
                        if verbose:
                            print(f"      ❌ No match")

        return {
            'add_to_spotify': youtube_only,
            'add_to_youtube': spotify_only,
            'matched_tracks': spotify_to_youtube_matches,
            'unmatched_spotify': unmatched_spotify,
            'unmatched_youtube': unmatched_youtube
        }

    def _preview_sync_plan(self, sync_plan: Dict) -> bool:
        """Preview the synchronization plan without making changes"""
        print("\n  📋 Sync Plan Preview:")
        print("  " + "=" * 60)

        # Preview additions to YouTube
        if sync_plan['add_to_youtube']:
            print(f"\n  ➕ Would add {len(sync_plan['add_to_youtube'])} tracks to YouTube Music:")
            for i, track in enumerate(sync_plan['add_to_youtube'][:5], 1):  # Show first 5
                print(f"     {i}. {track['name']} - {track['artist']}")
            if len(sync_plan['add_to_youtube']) > 5:
                print(f"     ... and {len(sync_plan['add_to_youtube']) - 5} more")
        else:
            print(f"\n  ✓ No tracks to add to YouTube Music")

        # Preview additions to Spotify
        if sync_plan['add_to_spotify']:
            print(f"\n  ➕ Would add {len(sync_plan['add_to_spotify'])} tracks to Spotify:")
            for i, track in enumerate(sync_plan['add_to_spotify'][:5], 1):  # Show first 5
                print(f"     {i}. {track['name']} - {track['artist']}")
            if len(sync_plan['add_to_spotify']) > 5:
                print(f"     ... and {len(sync_plan['add_to_spotify']) - 5} more")
        else:
            print(f"\n  ✓ No tracks to add to Spotify")

        # Show unmatched tracks
        if sync_plan['unmatched_spotify']:
            print(f"\n  ⚠️  {len(sync_plan['unmatched_spotify'])} Spotify tracks couldn't be matched:")
            for i, track in enumerate(sync_plan['unmatched_spotify'][:3], 1):  # Show first 3
                print(f"     {i}. {track['name']} - {track['artist']}")
            if len(sync_plan['unmatched_spotify']) > 3:
                print(f"     ... and {len(sync_plan['unmatched_spotify']) - 3} more")

        if sync_plan['unmatched_youtube']:
            print(f"\n  ⚠️  {len(sync_plan['unmatched_youtube'])} YouTube tracks couldn't be matched:")
            for i, track in enumerate(sync_plan['unmatched_youtube'][:3], 1):  # Show first 3
                print(f"     {i}. {track['name']} - {track['artist']}")
            if len(sync_plan['unmatched_youtube']) > 3:
                print(f"     ... and {len(sync_plan['unmatched_youtube']) - 3} more")

        print("\n  " + "=" * 60)

        # Summary
        total_changes = len(sync_plan['add_to_youtube']) + len(sync_plan['add_to_spotify'])
        if total_changes == 0:
            print("  ✓ Playlists are in sync - no changes needed")
        else:
            print(f"  📊 Total changes: {total_changes} tracks would be added")

        return True

    def _execute_sync_plan(self, pair: Dict, sync_plan: Dict) -> bool:
        """Execute the synchronization plan"""
        success = True

        try:
            # Add Spotify tracks to YouTube Music
            if sync_plan['add_to_youtube']:
                print(f"  ➕ Adding {len(sync_plan['add_to_youtube'])} tracks to YouTube Music")
                success &= self._add_tracks_to_youtube(pair['youtube']['id'], sync_plan['add_to_youtube'])

            # Add YouTube Music tracks to Spotify
            if sync_plan['add_to_spotify']:
                print(f"  ➕ Adding {len(sync_plan['add_to_spotify'])} tracks to Spotify")
                success &= self._add_tracks_to_spotify(pair['spotify']['id'], sync_plan['add_to_spotify'])

            # Log unmatched tracks
            if sync_plan['unmatched_spotify'] or sync_plan['unmatched_youtube']:
                self._log_unmatched_tracks(pair, sync_plan)

        except Exception as e:
            print(f"  Error executing sync plan: {e}")
            success = False

        return success

    def _add_tracks_to_spotify(self, playlist_id: str, tracks: List[Dict]) -> bool:
        """Add tracks to Spotify playlist"""
        try:
            # Get existing tracks to prevent duplicates
            existing_tracks = self.spotify_manager.get_playlist_tracks(playlist_id)
            existing_uris = {track['uri'] for track in existing_tracks}

            # Find Spotify equivalents for the tracks
            spotify_uris = []
            unmatched_count = 0
            already_exists_count = 0

            for track in tracks:
                match = self.song_matcher.find_matching_song(track, 'spotify')
                if match:
                    # Check if track already exists in playlist
                    if match['uri'] in existing_uris:
                        already_exists_count += 1
                    else:
                        spotify_uris.append(match['uri'])
                        existing_uris.add(match['uri'])  # Track it to avoid duplicates within this batch
                else:
                    unmatched_count += 1

            if spotify_uris:
                self.spotify_manager.add_tracks_to_playlist(playlist_id, spotify_uris)
                print(f"    ✅ Added {len(spotify_uris)} tracks to Spotify")

            if already_exists_count > 0:
                print(f"    ℹ️  Skipped {already_exists_count} tracks (already in playlist)")

            if unmatched_count > 0:
                print(f"    ⚠️  Could not find Spotify matches for {unmatched_count} tracks")

            # Return True if we processed all tracks (even if some couldn't be matched)
            return True

        except Exception as e:
            print(f"    ❌ Failed to add tracks to Spotify: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _add_tracks_to_youtube(self, playlist_id: str, tracks: List[Dict]) -> bool:
        """Add tracks to YouTube Music playlist"""
        try:
            # Get existing tracks to prevent duplicates
            existing_tracks = self.youtube_manager.get_playlist_tracks(playlist_id)
            existing_ids = {track['id'] for track in existing_tracks}

            # Find YouTube equivalents for the tracks
            youtube_ids = []
            unmatched_count = 0
            already_exists_count = 0

            for track in tracks:
                match = self.song_matcher.find_matching_song(track, 'youtube')
                if match:
                    # Check if track already exists in playlist
                    if match['id'] in existing_ids:
                        already_exists_count += 1
                    else:
                        youtube_ids.append(match['id'])
                        existing_ids.add(match['id'])  # Track it to avoid duplicates within this batch
                else:
                    unmatched_count += 1

            if youtube_ids:
                self.youtube_manager.add_tracks_to_playlist(playlist_id, youtube_ids)
                print(f"    ✅ Added {len(youtube_ids)} tracks to YouTube Music")

            if already_exists_count > 0:
                print(f"    ℹ️  Skipped {already_exists_count} tracks (already in playlist)")

            if unmatched_count > 0:
                print(f"    ⚠️  Could not find YouTube Music matches for {unmatched_count} tracks")

            # Return True if we processed all tracks (even if some couldn't be matched)
            return True

        except Exception as e:
            print(f"    ❌ Failed to add tracks to YouTube Music: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _log_unmatched_tracks(self, pair: Dict, sync_plan: Dict):
        """Log tracks that couldn't be matched"""
        unmatched_data = {
            'pair_id': pair['id'],
            'spotify_playlist': pair['spotify']['name'],
            'youtube_playlist': pair['youtube']['name'],
            'unmatched_spotify': sync_plan['unmatched_spotify'],
            'unmatched_youtube': sync_plan['unmatched_youtube'],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        self.config_manager.log_error(
            'unmatched_tracks',
            f"Found {len(sync_plan['unmatched_spotify']) + len(sync_plan['unmatched_youtube'])} unmatched tracks",
            unmatched_data
        )

