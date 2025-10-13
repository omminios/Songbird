"""
Songbird CLI - Main entry point for all commands
"""
import click
from songbird.auth.spotify import SpotifyAuth as SPA
from songbird.auth.apple import AppleAuth as AA
from songbird.config.manager import ConfigManager
from songbird.sync.manager import SyncManager


@click.group()
@click.version_option('1.0.0')
def cli():
    """Songbird - Sync playlists between Spotify and Apple Music"""
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
def apple():
    """Authenticate with Apple Music"""
    click.echo("🍎 Starting Apple Music authentication...")
    auth_handler = AA()
    if auth_handler.authenticate():
        click.echo("✅ Apple Music authentication successful!")
    else:
        click.echo("❌ Apple Music authentication failed!")


@auth.command(name='token-info')
def token_info():
    """Show Spotify token status and expiration information"""
    click.echo("🔑 Spotify Token Information:")

    try:
        auth_handler = SPA()
        info = auth_handler.get_token_info()

        if not info.get('exists'):
            click.echo("  ❌ No token found")
            click.echo("  Run 'songbird auth spotify' to authenticate")
            return

        if not info.get('valid'):
            click.echo(f"  ❌ Token invalid: {info.get('message', 'Unknown error')}")
            if 'error' in info:
                click.echo(f"  Error: {info['error']}")
            return

        # Token exists and is valid
        click.echo("  ✅ Token is valid")
        click.echo(f"  Obtained at: {info.get('obtained_at', 'Unknown')}")
        click.echo(f"  Expires at: {info.get('expires_at', 'Unknown')}")
        click.echo(f"  Time remaining: {info.get('time_remaining_minutes', 0):.1f} minutes")
        click.echo(f"  Has refresh token: {'Yes' if info.get('has_refresh_token') else 'No'}")

    except Exception as e:
        click.echo(f"  ❌ Error retrieving token info: {e}")


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