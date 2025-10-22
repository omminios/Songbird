"""
One-time script to remove duplicate tracks from synced playlists
This will clean up duplicates in both Spotify and YouTube Music playlists
"""
from songbird.config.manager import ConfigManager
from songbird.sync.playlist_manager import SpotifyPlaylistManager, YouTubePlaylistManager

def remove_duplicates_from_spotify(playlist_id: str, playlist_name: str):
    """Remove duplicate tracks from a Spotify playlist"""
    print(f"\n🔍 Checking Spotify playlist: {playlist_name}")

    manager = SpotifyPlaylistManager()
    tracks = manager.get_playlist_tracks(playlist_id)

    print(f"  Total tracks: {len(tracks)}")

    # Find duplicates by track URI
    seen_uris = set()
    duplicates = []

    for track in tracks:
        if track['uri'] in seen_uris:
            duplicates.append(track['uri'])
        else:
            seen_uris.add(track['uri'])

    if duplicates:
        print(f"  Found {len(duplicates)} duplicate tracks")
        print(f"  ❌ Removing duplicates...")

        # Remove duplicates in batches
        batch_size = 100
        for i in range(0, len(duplicates), batch_size):
            batch = duplicates[i:i + batch_size]
            manager.remove_tracks_from_playlist(playlist_id, batch)
            print(f"    Removed {len(batch)} duplicates")

        print(f"  ✅ Removed {len(duplicates)} duplicate tracks from Spotify")
    else:
        print(f"  ✅ No duplicates found in Spotify")

    return len(duplicates)


def remove_duplicates_from_youtube(playlist_id: str, playlist_name: str):
    """Remove duplicate tracks from a YouTube Music playlist"""
    print(f"\n🔍 Checking YouTube Music playlist: {playlist_name}")

    manager = YouTubePlaylistManager()
    tracks = manager.get_playlist_tracks(playlist_id)

    print(f"  Total tracks: {len(tracks)}")

    # Find duplicates by video ID
    # Keep track of first occurrence's setVideoId
    seen_videos = {}  # video_id -> first setVideoId
    duplicates = []  # setVideoIds to remove

    for track in tracks:
        video_id = track['id']
        set_video_id = track.get('setVideoId')

        if not set_video_id:
            continue

        if video_id in seen_videos:
            # This is a duplicate - add to removal list
            duplicates.append(set_video_id)
        else:
            # First occurrence - remember it
            seen_videos[video_id] = set_video_id

    if duplicates:
        print(f"  Found {len(duplicates)} duplicate tracks")
        print(f"  ❌ Removing duplicates...")

        # YouTube Music API might have limits, so do in smaller batches
        batch_size = 50
        for i in range(0, len(duplicates), batch_size):
            batch = duplicates[i:i + batch_size]
            try:
                manager.remove_tracks_from_playlist(playlist_id, batch)
                print(f"    Removed {len(batch)} duplicates")
            except Exception as e:
                print(f"    ⚠️  Error removing batch: {e}")

        print(f"  ✅ Removed {len(duplicates)} duplicate tracks from YouTube Music")
    else:
        print(f"  ✅ No duplicates found in YouTube Music")

    return len(duplicates)


def main():
    """Main function to remove duplicates from all paired playlists"""
    print("=" * 70)
    print("DUPLICATE TRACK REMOVER")
    print("=" * 70)
    print("\nThis script will remove duplicate tracks from your synced playlists.")
    print("It will check both Spotify and YouTube Music playlists.\n")

    response = input("Do you want to continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cancelled.")
        return

    config_manager = ConfigManager()
    pairs = config_manager.get_playlist_pairs()

    if not pairs:
        print("\n❌ No playlist pairs found.")
        return

    print(f"\nFound {len(pairs)} playlist pair(s)\n")

    total_spotify_duplicates = 0
    total_youtube_duplicates = 0

    for pair in pairs:
        print("\n" + "=" * 70)
        print(f"Processing pair: {pair['spotify']['name']} ↔ {pair['youtube']['name']}")
        print("=" * 70)

        # Remove duplicates from Spotify
        try:
            spotify_dupes = remove_duplicates_from_spotify(
                pair['spotify']['id'],
                pair['spotify']['name']
            )
            total_spotify_duplicates += spotify_dupes
        except Exception as e:
            print(f"  ❌ Error processing Spotify playlist: {e}")

        # Remove duplicates from YouTube Music
        try:
            youtube_dupes = remove_duplicates_from_youtube(
                pair['youtube']['id'],
                pair['youtube']['name']
            )
            total_youtube_duplicates += youtube_dupes
        except Exception as e:
            print(f"  ❌ Error processing YouTube Music playlist: {e}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total Spotify duplicates removed: {total_spotify_duplicates}")
    print(f"Total YouTube Music duplicates removed: {total_youtube_duplicates}")
    print(f"Total duplicates removed: {total_spotify_duplicates + total_youtube_duplicates}")
    print("\n✅ Duplicate removal complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
