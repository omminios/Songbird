"""
Songbird CLI - Main entry point for all commands
"""
import click
from songbird.auth.spotify import SpotifyAuth as SPA
from songbird.auth.youtube import YouTubeAuth as YTA
from songbird.config.manager import ConfigManager
from songbird.sync.manager import SyncManager


@click.group()
@click.version_option('1.0.0')
def cli():
    """Songbird - Sync playlists between Spotify and YouTube Music"""
    pass


@cli.group()
def auth():
    """Authentication commands for music services"""
    pass


@auth.command()
def spotify():
    """Authenticate with Spotify"""
    click.echo("🎵 Starting Spotify authentication...")
    auth_handler = SPA()
    if auth_handler.authenticate():
        click.echo("✅ Spotify authentication successful!")
    else:
        click.echo("❌ Spotify authentication failed!")


@auth.command()
def youtube():
    """Authenticate with YouTube Music"""
    click.echo("📺 Starting YouTube Music authentication...")
    auth_handler = YTA()
    if auth_handler.authenticate():
        click.echo("✅ YouTube Music authentication successful!")
    else:
        click.echo("❌ YouTube Music authentication failed!")


@auth.command(name='token-info')
@click.option('--debug', is_flag=True, help='Show detailed debugging information')
def token_info(debug):
    """Show token status for Spotify and YouTube Music"""
    click.echo("\n" + "=" * 70)
    click.echo("Authentication Token Information")
    if debug:
        click.echo("DEBUG MODE ENABLED")
    click.echo("=" * 70)

    # Spotify Token Info
    click.echo("\nSPOTIFY:")
    click.echo("-" * 70)
    try:
        spotify_auth = SPA()
        spotify_auth.display_token_info(debug=debug)
    except Exception as e:
        click.echo(f"  Error retrieving Spotify token info: {e}")
        if debug:
            import traceback
            click.echo("\n  Full traceback:")
            click.echo(traceback.format_exc())

    # YouTube Music Token Info
    click.echo("\nYOUTUBE MUSIC:")
    click.echo("-" * 70)
    try:
        youtube_auth = YTA()
        youtube_auth.display_token_info(debug=debug)
    except Exception as e:
        click.echo(f"  Error retrieving YouTube token info: {e}")
        if debug:
            import traceback
            click.echo("\n  Full traceback:")
            click.echo(traceback.format_exc())

    click.echo("\n" + "=" * 70)


@cli.command()
def pair():
    """Select and pair playlists between services"""
    from songbird.sync.pairing import PlaylistPairing

    config = ConfigManager()

    # Check Spotify authentication (required)
    try:
        from songbird.auth.spotify import SpotifyAuth as SPA
        spotify_auth = SPA()
        if not spotify_auth.is_authenticated():
            click.echo("❌ Please authenticate with Spotify first:")
            click.echo("  songbird auth spotify")
            return
    except Exception as e:
        click.echo(f"❌ Spotify authentication check failed: {e}")
        return

    # Start pairing process
    pairing = PlaylistPairing()
    pairing.start_pairing_process()


@cli.command()
def sync():
    """Manually trigger playlist synchronization"""
    click.echo("🔄 Starting manual sync...")

    config = ConfigManager()
    if not config.has_playlist_pairs():
        click.echo("❌ No playlist pairs configured. Run 'songbird pair' first.")
        return

    sync_manager = SyncManager()
    if sync_manager.manual_sync():
        click.echo("✅ Sync completed successfully!")
    else:
        click.echo("❌ Sync failed. Check logs for details.")


@cli.command()
def status():
    """Show sync status and last sync information"""
    from songbird.sync.pairing import PlaylistPairing

    click.echo("📊 Sync Status:")

    config = ConfigManager()
    status_info = config.get_sync_status()

    if status_info:
        click.echo(f"  Last sync: {status_info.get('last_sync', 'Never')}")
        click.echo(f"  Status: {status_info.get('status', 'Unknown')}")
        click.echo(f"  Playlist pairs: {status_info.get('pair_count', 0)}\n")

        # Show configured pairs
        pairing = PlaylistPairing()
        pairing.show_current_pairs()
    else:
        click.echo("  No sync history found")


if __name__ == '__main__':
    cli()