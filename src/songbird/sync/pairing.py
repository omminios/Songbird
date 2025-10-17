"""
Interactive playlist pairing interface
Allows users to select and pair playlists between Spotify and YouTube Music
"""
import click
from typing import List, Dict, Optional
from songbird.sync.playlist_manager import SpotifyPlaylistManager, YouTubePlaylistManager
from songbird.config.manager import ConfigManager


class PlaylistPairing:
    """Handles interactive playlist pairing"""

    def __init__(self):
        self.spotify_manager = SpotifyPlaylistManager()
        self.youtube_manager = YouTubePlaylistManager()
        self.config_manager = ConfigManager()

    def start_pairing_process(self):
        """Start the interactive playlist pairing process"""
        click.echo("🔗 Starting playlist pairing process...\n")

        try:
            # Fetch playlists from both services
            spotify_playlists = self._get_spotify_playlists()
            youtube_playlists = self._get_youtube_playlists()

            if not spotify_playlists:
                click.echo("❌ No Spotify playlists found or authentication failed")
                return False

            if not youtube_playlists:
                click.echo("❌ YouTube Music playlist access failed")
                click.echo("📝 Make sure you've authenticated with 'songbird auth youtube'")
                return False

            # Interactive pairing
            return self._interactive_pairing(spotify_playlists, youtube_playlists)

        except Exception as e:
            click.echo(f"❌ Error during pairing: {e}")
            return False

    def _get_spotify_playlists(self) -> List[Dict]:
        """Fetch Spotify playlists with error handling"""
        try:
            click.echo("🎵 Fetching Spotify playlists...")
            playlists = self.spotify_manager.get_user_playlists()
            click.echo(f"✅ Found {len(playlists)} Spotify playlists\n")
            return playlists
        except Exception as e:
            click.echo(f"❌ Failed to fetch Spotify playlists: {e}")
            return []

    def _get_youtube_playlists(self) -> List[Dict]:
        """Fetch YouTube Music playlists with error handling"""
        try:
            click.echo("📺 Fetching YouTube Music playlists...")
            playlists = self.youtube_manager.get_user_playlists()
            if playlists:
                click.echo(f"✅ Found {len(playlists)} YouTube Music playlists\n")
            return playlists
        except Exception as e:
            click.echo(f"❌ Failed to fetch YouTube Music playlists: {e}")
            return []

    def _display_spotify_playlists(self, playlists: List[Dict]):
        """Display Spotify playlists in a formatted table"""
        if not playlists:
            click.echo("No playlists found")
            return

        click.echo("📋 Your Spotify Playlists:")
        click.echo("-" * 60)
        click.echo(f"{'#':<3} {'Name':<30} {'Tracks':<8} {'Public':<6}")
        click.echo("-" * 60)

        for i, playlist in enumerate(playlists, 1):
            name = playlist['name'][:29] + '...' if len(playlist['name']) > 29 else playlist['name']
            tracks = str(playlist['tracks_total'])
            public = 'Yes' if playlist['public'] else 'No'

            click.echo(f"{i:<3} {name:<30} {tracks:<8} {public:<6}")

        click.echo("-" * 60)

    def _interactive_pairing(self, spotify_playlists: List[Dict], youtube_playlists: List[Dict]) -> bool:
        """Full interactive pairing process"""
        click.echo("🎯 Interactive Playlist Pairing")

        while True:
            # Display playlists
            self._display_playlists_side_by_side(spotify_playlists, youtube_playlists)

            # Get user selections
            spotify_choice = self._get_playlist_choice("Spotify", spotify_playlists)
            if spotify_choice is None:
                break

            youtube_choice = self._get_playlist_choice("YouTube Music", youtube_playlists)
            if youtube_choice is None:
                continue

            # Confirm pairing
            spotify_name = spotify_playlists[spotify_choice]['name']
            youtube_name = youtube_playlists[youtube_choice]['name']

            if click.confirm(f"\n🔗 Pair '{spotify_name}' with '{youtube_name}'?"):
                self._save_playlist_pair(
                    spotify_playlists[spotify_choice],
                    youtube_playlists[youtube_choice]
                )

            if not click.confirm("\nPair another set of playlists?"):
                break

        return True

    def _display_playlists_side_by_side(self, spotify_playlists: List[Dict], youtube_playlists: List[Dict]):
        """Display both service playlists side by side"""
        click.echo("\n" + "="*80)
        click.echo(f"{'SPOTIFY PLAYLISTS':<40} {'YOUTUBE MUSIC PLAYLISTS':<40}")
        click.echo("="*80)

        max_len = max(len(spotify_playlists), len(youtube_playlists))

        for i in range(max_len):
            spotify_line = ""
            youtube_line = ""

            if i < len(spotify_playlists):
                spotify_pl = spotify_playlists[i]
                name = spotify_pl['name'][:35] + '...' if len(spotify_pl['name']) > 35 else spotify_pl['name']
                spotify_line = f"{i+1:>2}. {name:<37}"

            if i < len(youtube_playlists):
                youtube_pl = youtube_playlists[i]
                name = youtube_pl['name'][:35] + '...' if len(youtube_pl['name']) > 35 else youtube_pl['name']
                youtube_line = f"{i+1:>2}. {name:<37}"

            click.echo(f"{spotify_line:<40} {youtube_line:<40}")

        click.echo("="*80)

    def _get_playlist_choice(self, service_name: str, playlists: List[Dict]) -> Optional[int]:
        """Get user's playlist choice"""
        while True:
            try:
                choice = click.prompt(
                    f"\nSelect {service_name} playlist number (or 'q' to quit)",
                    type=str
                )

                if choice.lower() == 'q':
                    return None

                choice_num = int(choice) - 1
                if 0 <= choice_num < len(playlists):
                    return choice_num
                else:
                    click.echo(f"❌ Please enter a number between 1 and {len(playlists)}")

            except ValueError:
                click.echo("❌ Please enter a valid number or 'q' to quit")

    def _save_playlist_pair(self, spotify_playlist: Dict, youtube_playlist: Dict):
        """Save a playlist pair to configuration"""
        try:
            self.config_manager.add_playlist_pair(spotify_playlist, youtube_playlist)
        except Exception as e:
            click.echo(f"❌ Failed to save playlist pair: {e}")

    def show_current_pairs(self):
        """Display currently configured playlist pairs"""
        pairs = self.config_manager.get_playlist_pairs()

        if not pairs:
            click.echo("No playlist pairs configured")
            return

        click.echo("🔗 Configured Playlist Pairs:")
        click.echo("-" * 70)
        click.echo(f"{'ID':<3} {'Spotify Playlist':<25} {'YouTube Music Playlist':<25} {'Status':<15}")
        click.echo("-" * 70)

        for pair in pairs:
            pair_id = str(pair['id'])
            spotify_name = pair['spotify']['name'][:24] + '...' if len(pair['spotify']['name']) > 24 else pair['spotify']['name']
            youtube_name = pair['youtube']['name'][:24] + '...' if len(pair['youtube']['name']) > 24 else pair['youtube']['name']
            status = 'Active' if pair.get('last_sync') else 'Not synced'

            click.echo(f"{pair_id:<3} {spotify_name:<25} {youtube_name:<25} {status:<15}")

        click.echo("-" * 70)