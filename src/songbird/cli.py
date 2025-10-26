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
    
    try:
        from songbird.auth.youtube import YouTubeAuth as YTA
        youtube_auth = YTA()
        if not youtube_auth.is_authenticated():
            click.echo("❌ Please authenticate with Youtube Music first:")
            click.echo("  songbird auth youtube")
            return
    except Exception as e:
        click.echo(f"❌ Youtube Music authentication check failed: {e}")
        return

    # Start pairing process
    pairing = PlaylistPairing()
    pairing.start_pairing_process()


@cli.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed sync progress')
@click.option('--force', '-f', is_flag=True, help='Force sync even if playlists appear unchanged')
@click.option('--dry-run', '-d', is_flag=True, help='Preview changes without actually syncing')
def sync(verbose, force, dry_run):
    """Manually trigger playlist synchronization"""
    if dry_run:
        click.echo("🔍 Dry run mode - previewing changes without syncing...")
    else:
        click.echo("🔄 Starting manual sync...")

    config = ConfigManager()
    if not config.has_playlist_pairs():
        click.echo("❌ No playlist pairs configured. Run 'songbird pair' first.")
        return

    sync_manager = SyncManager()
    if sync_manager.manual_sync(verbose=verbose, force=force, dry_run=dry_run):
        if dry_run:
            click.echo("\n✅ Dry run complete! No changes were made.")
            click.echo("   Run 'songbird sync' to apply these changes.")
        else:
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


@cli.command()
@click.argument('pair_id', type=int)
@click.confirmation_option(prompt='Are you sure you want to unpair this playlist?')
def unpair(pair_id):
    """Remove a specific playlist pair by ID"""
    config = ConfigManager()

    # Get current pairs to show what we're removing
    pairs = config.get_playlist_pairs()
    pair_to_remove = None

    for pair in pairs:
        if pair.get('id') == pair_id:
            pair_to_remove = pair
            break

    if not pair_to_remove:
        click.echo(f"❌ No playlist pair found with ID {pair_id}")
        click.echo("\nRun 'songbird status' to see available pairs")
        return

    # Show what we're removing
    click.echo(f"\n🔗 Removing pair #{pair_id}:")
    click.echo(f"  Spotify:  {pair_to_remove['spotify']['name']}")
    click.echo(f"  YouTube:  {pair_to_remove['youtube']['name']}")

    # Remove the pair
    config.remove_playlist_pair(pair_id)

    click.echo(f"\n✅ Playlist pair #{pair_id} removed successfully!")

    # Show remaining pairs
    remaining_pairs = config.get_playlist_pairs()
    if remaining_pairs:
        click.echo(f"\nRemaining pairs: {len(remaining_pairs)}")
    else:
        click.echo("\n⚠️  No playlist pairs remaining. Run 'songbird pair' to create new pairs.")


@cli.command(name='clear-errors')
@click.confirmation_option(prompt='Are you sure you want to clear all error logs?')
def clear_errors():
    """Clear all error logs from S3 config"""
    config = ConfigManager()
    config.clear_errors()
    click.echo("✅ Error logs cleared successfully!")


@cli.command(name='clear-snapshots')
def clear_snapshots():
    """Clear playlist snapshots to force re-sync"""
    config = ConfigManager()
    config.clear_snapshots()
    click.echo("✅ Snapshots cleared! Next sync will check all playlists.")


@cli.command()
@click.confirmation_option(prompt='⚠️  This will remove ALL playlist pairs and sync history. Are you sure?')
def reset():
    """Reset all configuration (pairs, history, errors)"""
    click.echo("\n🔄 Resetting configuration...")
    click.echo("=" * 70)

    config = ConfigManager()

    # Show what will be reset
    pairs = config.get_playlist_pairs()
    errors = config.get_errors(limit=1000)

    click.echo(f"\nCurrent configuration:")
    click.echo(f"  - Playlist pairs: {len(pairs)}")
    click.echo(f"  - Error logs: {len(errors)}")

    # Perform reset
    config.reset_all()

    click.echo("\n" + "=" * 70)
    click.echo("✅ Reset complete!")
    click.echo("\n⚠️  Note: This does NOT remove authentication tokens.")
    click.echo("   To re-authenticate, run:")
    click.echo("     songbird auth spotify")
    click.echo("     songbird auth youtube")


if __name__ == '__main__':
    cli()