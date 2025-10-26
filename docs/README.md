# Songbird - Quick Start Guide

**Bidirectional Playlist Sync between Spotify and YouTube Music**

## Overview

Songbird is a Python CLI tool that automatically syncs playlists between Spotify and YouTube Music. Set up multiple playlist pairs and keep them in sync effortlessly.

**Key Features:**
- 🎵 Bidirectional sync (Spotify ↔ YouTube Music)
- ⚡ Smart change detection (100x faster when unchanged)
- 🔄 Parallel processing for fast matching
- 🎯 Fuzzy song matching across services
- 🚫 Automatic duplicate prevention
- 👁️ Dry-run mode to preview changes
- ☁️ Secure S3 storage for config and tokens

---

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/songbird.git
cd Songbird

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup

Create a `.env` file in the project root:

```env
# Spotify OAuth (required)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

# S3 Storage (required)
SONGBIRD_CONFIG_BUCKET=your-s3-bucket-name

# AWS Credentials (if not using AWS CLI)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_DEFAULT_REGION=us-east-1
```

**Get Spotify Credentials:**
1. Visit [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create an app with redirect URI: `http://localhost:8888/callback`
3. Copy Client ID and Secret to `.env`

**Setup S3 Bucket:**
```bash
aws s3 mb s3://your-songbird-bucket
```

### 3. Authenticate

```bash
# Authenticate with Spotify
songbird auth spotify

# Authenticate with YouTube Music
songbird auth youtube

# Verify authentication
songbird auth token-info
```

### 4. Pair Playlists

```bash
songbird pair
```
Follow the interactive prompts to select and pair playlists.

### 5. Sync

```bash
# Normal sync
songbird sync

# Preview changes first (dry-run)
songbird sync --dry-run

# Verbose output
songbird sync --verbose

# Force sync (skip change detection)
songbird sync --force
```

---

## Common Commands

### Authentication
```bash
songbird auth spotify              # Authenticate Spotify
songbird auth youtube              # Authenticate YouTube Music
songbird auth token-info           # Show token status
songbird auth token-info --debug   # Detailed debug info
```

### Playlist Management
```bash
songbird pair                      # Create new playlist pair
songbird unpair <pair_id>          # Remove playlist pair
songbird status                    # Show all pairs and sync status
```

### Sync
```bash
songbird sync                      # Normal sync
songbird sync -v                   # Verbose (detailed progress)
songbird sync -f                   # Force sync
songbird sync -d                   # Dry-run (preview only)
songbird sync -vf                  # Verbose + force
```

### Utility
```bash
songbird clear-errors              # Clear error logs
songbird clear-snapshots           # Clear cached snapshots
songbird reset                     # Reset all config (keeps auth)
```

---

## How It Works

### Smart Change Detection
After each sync, Songbird saves track counts to S3. On next sync:
- If counts match → Skip sync (2-5 seconds)
- If counts differ → Run full sync (30-90 seconds)

**Result:** 100x faster for unchanged playlists!

### Parallel Processing
For batches > 5 tracks:
- Uses ThreadPoolExecutor with 5 workers
- Rate limiting: 3 req/sec (Spotify), 2 req/sec (YouTube)
- 5x faster track matching

### Fuzzy Matching
Songs are matched using:
- Normalized track/artist names
- 70% title weight, 30% artist weight
- Duration comparison (±5 seconds)
- 80% similarity threshold

---

## Troubleshooting

### "Spotify authentication failed"
- Check `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in `.env`
- Verify redirect URI: `http://localhost:8888/callback`
- Ensure port 8888 is available

### "YouTube Music authentication failed"
- Ensure browser is logged into YouTube Music
- Copy cookies exactly as prompted
- Try a different browser if issues persist

### "Sync is slow"
- First sync: 3-9 minutes (normal)
- Subsequent syncs: 2-5 seconds with smart skip
- Use `--verbose` to see detailed progress

### "Duplicates appearing"
- Should be fixed in v1.0 with two-layer deduplication
- If persisting, report as bug

### "Changes not detected"
- Track counts might be same (added + removed = 0 change)
- Use `songbird sync --force` to override
- Or `songbird clear-snapshots` and re-sync

---

## Performance

| Scenario | Before | After | Improvement |
|----------|--------|-------|-------------|
| No changes | 3-9 min | 2-5 sec | 100x faster |
| Small changes | 3-9 min | 30-90 sec | 5x faster |
| First sync | 3-9 min | 3-9 min | Same |

---

## Documentation

- **[Songbird PRD](./Songbird%20PRD.md)** - Comprehensive product requirements and technical documentation
- **[Google OAuth Setup](./GOOGLE_OAUTH_SETUP.md)** - YouTube Music authentication guide

---

## Architecture

```
CLI → SyncManager → Spotify API / YouTube Music API → S3 Storage
```

**Components:**
- **CLI Layer:** Command parsing (Click)
- **Auth Layer:** OAuth 2.0 (Spotify), Cookie auth (YouTube)
- **Sync Layer:** Orchestration, matching, playlist management
- **Config Layer:** S3 storage for config, tokens, snapshots

---

## Requirements

- **Python:** 3.8+
- **AWS:** S3 bucket with read/write access
- **Spotify:** Developer account with OAuth credentials
- **YouTube Music:** Account with cookie authentication

---

## Security

- ✅ All credentials stored in environment variables
- ✅ S3 server-side encryption (AES256)
- ✅ OAuth 2.0 best practices
- ✅ `.env` file in `.gitignore`
- ✅ No hardcoded secrets

---

## Future Features

- ⏰ Scheduled sync (AWS Lambda + EventBridge)
- 📧 Webhook notifications
- 📊 Web dashboard
- 🔄 Incremental sync
- 💾 Search result caching

---

## Contributing

Pull requests welcome! Please read the [Songbird PRD](./Songbird%20PRD.md) for detailed technical information.

---

## License

MIT License

---

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

**Version:** 1.0
**Last Updated:** 2025-10-26
