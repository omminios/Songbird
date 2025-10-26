# Songbird - Product Requirements Document (PRD)

**Version:** 1.0
**Last Updated:** 2025-10-26
**Status:** Active Development

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Functional Requirements](#functional-requirements)
3. [Non-Functional Requirements](#non-functional-requirements)
4. [Architecture](#architecture)
5. [Technology Stack](#technology-stack)
6. [Authentication Setup](#authentication-setup)
7. [CLI Commands Reference](#cli-commands-reference)
8. [Performance Optimizations](#performance-optimizations)
9. [Implementation Details](#implementation-details)
10. [Recent Changes & Updates](#recent-changes--updates)
11. [Future Enhancements](#future-enhancements)

---

## Project Overview

### Project Name
**Songbird** - Bidirectional Playlist Synchronization Tool

### Target Users
Two individuals sharing playlists across different music streaming platforms:
- One Spotify user
- One YouTube Music user

### Core Problem
Manually updating shared playlists across two different music streaming services is tedious, error-prone, and fails to account for deletions or modifications.

### Solution
A serverless CLI application that performs bidirectional, state-based synchronization between multiple playlist pairs on a schedule or on-demand.

### Key Features
- ✅ OAuth 2.0 authentication for Spotify and YouTube Music
- ✅ Multiple playlist pair support
- ✅ Bidirectional sync (both directions)
- ✅ Smart change detection (skips unchanged playlists)
- ✅ Parallel processing for faster matching
- ✅ Fuzzy song matching across services
- ✅ Duplicate prevention
- ✅ Manual and automated sync triggers
- ✅ Comprehensive error logging
- ✅ Dry-run mode for previewing changes

---

## Functional Requirements

### 1. Authentication
**Requirement:** The application must securely authenticate with both Spotify and YouTube Music using industry-standard protocols.

**Implementation:**
- **Spotify:** OAuth 2.0 with automatic token refresh
- **YouTube Music:** Browser cookie authentication via ytmusicapi
- **Token Storage:** AWS S3 with server-side encryption (AES256)
- **Security:** All credentials stored as environment variables, never committed to code

### 2. Playlist Synchronization
**Requirement:** Support multiple playlist pairs with bidirectional synchronization ensuring both playlists become identical.

**Implementation:**
- Configuration of unlimited playlist pairs
- Set-based comparison for efficient diff calculation
- Handles additions from both services
- Deduplication logic prevents duplicate tracks
- Real-time duplicate checking before adding tracks
- Smart skip for playlists with no changes (100x faster)

### 3. Manual Sync
**Requirement:** Users must be able to trigger sync manually via CLI command.

**Implementation:**
```bash
songbird sync              # Normal sync with smart skip
songbird sync --verbose    # Detailed progress output
songbird sync --force      # Force sync, ignore change detection
songbird sync --dry-run    # Preview changes without syncing
```

### 4. Song Matching
**Requirement:** Accurately match songs between services despite variations in metadata.

**Implementation:**
- Fuzzy string matching using SequenceMatcher
- Normalized track/artist names (removes parentheses, brackets, "feat", etc.)
- Weighted scoring: 70% title, 30% artist
- Duration comparison for additional validation (±5 seconds)
- 80% similarity threshold for automatic matches
- Parallel processing (5 workers) for batches > 5 tracks
- Rate limiting: 3 req/sec for Spotify, 2 req/sec for YouTube

### 5. Configuration Management
**Requirement:** Interactive CLI for setup, playlist pairing, and configuration.

**Implementation:**
- Guided authentication flow
- Interactive playlist selection with search
- Playlist pair management (add, remove, view)
- Configuration stored in S3 (config.json)
- Snapshot caching for change detection

### 6. Error Handling and Reporting
**Requirement:** Capture unmatched songs and errors in persistent logs for review.

**Implementation:**
- Structured error logging to S3
- Unmatched tracks logged with details
- Error log management commands
- Graceful degradation on API failures

---

## Non-Functional Requirements

### Security
- ✅ OAuth 2.0 best practices
- ✅ Environment variables for all secrets
- ✅ S3 server-side encryption (AES256)
- ✅ `.env` file in `.gitignore`
- ✅ No credentials in code or commits

### Cost
- ✅ Serverless architecture (AWS Lambda ready)
- ✅ S3 free tier usage
- ✅ Minimal API costs (within free tiers)
- ✅ Efficient change detection reduces unnecessary API calls

### Reliability
- ✅ Retry logic for API failures (planned)
- ✅ Graceful error handling
- ✅ Duplicate prevention mechanisms
- ✅ Snapshot-based change detection
- ✅ Rate limiting to avoid throttling

### Performance
- ✅ Smart skip: 2-5 seconds when no changes (vs 3-9 minutes)
- ✅ Parallel processing: 5x faster matching for batches
- ✅ Optimized matching: Only searches for missing tracks
- ✅ Deduplication reduces comparison overhead

### Scalability
- ✅ Supports unlimited playlist pairs
- ✅ Handles large playlists (100+ tracks)
- ✅ Modular architecture for future expansion

---

## Architecture

### High-Level Design
Serverless, event-driven model with dual-trigger mechanism.

```
┌─────────────────┐         ┌──────────────────┐
│  Manual Trigger │         │  Scheduled Cron  │
│  (CLI Command)  │         │   (AWS Lambda)   │
└────────┬────────┘         └────────┬─────────┘
         │                           │
         └───────────┬───────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   Sync Manager        │
         │   (Core Logic)        │
         └───────────┬───────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌────────────────┐      ┌────────────────┐
│  Spotify API   │      │ YouTube Music  │
│  (OAuth 2.0)   │      │  (ytmusicapi)  │
└────────────────┘      └────────────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  AWS S3 Storage       │
         │  - config.json        │
         │  - tokens/            │
         │  - snapshots/         │
         └───────────────────────┘
```

### Component Architecture

#### 1. CLI Layer (`cli.py`)
- Command parsing (Click framework)
- User interaction
- Command routing

#### 2. Authentication Layer
- **Spotify Auth** (`auth/spotify.py`): OAuth 2.0 flow
- **YouTube Auth** (`auth/youtube.py`): Browser cookie authentication
- Token management and refresh

#### 3. Sync Layer
- **Sync Manager** (`sync/manager.py`): Orchestrates sync process
- **Song Matcher** (`sync/song_matcher.py`): Fuzzy matching logic
- **Playlist Manager** (`sync/playlist_manager.py`): API interactions
- **Pairing** (`sync/pairing.py`): Interactive playlist selection

#### 4. Configuration Layer
- **Config Manager** (`config/manager.py`): S3 storage interface
- Playlist pairs management
- Snapshot caching
- Error logging

---

## Technology Stack

### Programming Language
**Python 3.8+**

### Cloud Provider
**AWS (Amazon Web Services)**
- AWS Lambda (planned for scheduled sync)
- S3 (configuration and token storage)
- CloudWatch (logging, planned)

### APIs & Libraries
- **Spotify:** `spotipy` (Spotify Web API wrapper)
- **YouTube Music:** `ytmusicapi` (unofficial YouTube Music API)
- **CLI Framework:** `click`
- **HTTP:** `requests`
- **Data Validation:** `pydantic`
- **Cloud Storage:** `boto3` (AWS SDK)
- **Environment:** `python-dotenv`

### Development Tools
- **Version Control:** Git
- **Package Management:** pip, requirements.txt
- **Virtual Environment:** venv

---

## Authentication Setup

### Spotify OAuth Setup

#### 1. Create Spotify App
1. Visit [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click "Create an App"
3. Fill in app details:
   - **App name:** Songbird
   - **App description:** Playlist sync tool
   - **Redirect URI:** `http://localhost:8888/callback`
4. Copy **Client ID** and **Client Secret**

#### 2. Add to .env File
```env
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
```

#### 3. Authenticate
```bash
songbird auth spotify
```
- Opens browser for OAuth flow
- Redirects to localhost:8888/callback
- Tokens saved to S3 automatically

### YouTube Music Cookie Authentication

#### 1. Understanding the "Unverified App" Warning

When authenticating with YouTube Music via Google OAuth, you'll see:
> **"Google hasn't verified this app"**

This is **completely normal** and expected because:
- Your app is in development mode
- Not publicly published to Google
- Personal use only
- YOU are the developer and the user

#### 2. Bypassing the Warning

**Step 1:** Click "Advanced" at the bottom of the warning page

**Step 2:** Click "Go to Songbird (unsafe)" or "Continue to Songbird (unsafe)"

**Step 3:** Click "Allow" on the consent screen

#### 3. Google OAuth Setup (Optional but Recommended)

**Create OAuth Client ID:**
1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project: "Songbird"
3. Enable **YouTube Data API v3**:
   - Go to **APIs & Services** → **Library**
   - Search "YouTube Data API v3"
   - Click **ENABLE**
4. Create OAuth credentials:
   - Go to **APIs & Services** → **Credentials**
   - Click **CREATE CREDENTIALS** → **OAuth client ID**
   - Select **TVs and Limited Input devices** (important!)
   - Name: "Songbird"
   - Click **CREATE**
5. Copy **Client ID** and **Client Secret**

**Configure OAuth Consent Screen:**
1. Go to **APIs & Services** → **OAuth consent screen**
2. Choose **External**
3. Fill required fields:
   - App name: "Songbird"
   - User support email: your email
   - Developer contact: your email
4. Add scopes: `https://www.googleapis.com/auth/youtube`
5. Click **SAVE AND CONTINUE**

**Add Test User (removes warning):**
1. In OAuth consent screen
2. Scroll to **Test users**
3. Click **ADD USERS**
4. Add your Google email
5. Click **SAVE**

#### 4. Add to .env (if using OAuth)
```env
YOUTUBE_CLIENT_ID=your-client-id.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=your-client-secret
```

#### 5. Authenticate
```bash
songbird auth youtube
```
- Follow prompts to copy browser cookies
- Tokens saved to S3 automatically

### AWS S3 Setup

#### 1. Create S3 Bucket
```bash
aws s3 mb s3://your-songbird-bucket
```

#### 2. Configure AWS Credentials
Option A: AWS CLI (recommended)
```bash
aws configure
```

Option B: Environment variables
```env
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1
```

#### 3. Add Bucket Name to .env
```env
SONGBIRD_CONFIG_BUCKET=your-songbird-bucket
```

---

## CLI Commands Reference

### Authentication Commands

#### `songbird auth spotify`
Authenticate with Spotify using OAuth 2.0.

**Usage:**
```bash
songbird auth spotify
```

**Flow:**
1. Opens browser for authorization
2. Redirects to localhost:8888/callback
3. Saves access token and refresh token to S3

---

#### `songbird auth youtube`
Authenticate with YouTube Music using browser cookies.

**Usage:**
```bash
songbird auth youtube
```

**Flow:**
1. Prompts for browser cookie authentication
2. Validates credentials with YouTube Music API
3. Saves authentication headers to S3

---

#### `songbird auth token-info`
Display authentication status and token information.

**Usage:**
```bash
songbird auth token-info           # Show basic info
songbird auth token-info --debug   # Show detailed debug info
```

**Output:**
- Token validity status
- Expiration time (if applicable)
- Last refresh time
- Scopes/permissions

---

### Playlist Management Commands

#### `songbird pair`
Interactively select and pair playlists between Spotify and YouTube Music.

**Usage:**
```bash
songbird pair
```

**Flow:**
1. Fetches all Spotify playlists
2. Fetches all YouTube Music playlists
3. Interactive selection interface
4. Saves pair to S3 config

**Prerequisites:**
- Must be authenticated with both services

---

#### `songbird unpair <pair_id>`
Remove a specific playlist pair by ID.

**Usage:**
```bash
songbird unpair 1          # With confirmation prompt
songbird unpair 2 --yes    # Skip confirmation
```

**Example:**
```bash
$ songbird unpair 1

🔗 Removing pair #1:
  Spotify:  My Favorite Songs
  YouTube:  Best Music Ever

Are you sure you want to unpair this playlist? [y/N]: y

✅ Playlist pair #1 removed successfully!

Remaining pairs: 2
```

---

#### `songbird status`
Show sync status and configured playlist pairs.

**Usage:**
```bash
songbird status
```

**Output:**
- Last sync timestamp
- Number of configured pairs
- List of all playlist pairs with:
  - Pair ID
  - Spotify playlist name
  - YouTube playlist name
  - Last sync status

**Example:**
```bash
📊 Sync Status:
  Last sync: 2025-10-26 14:32:15
  Status: configured
  Playlist pairs: 3

Configured Playlist Pairs:
  #1: "Workout Mix" ↔ "Gym Playlist"
  #2: "Chill Vibes" ↔ "Relaxing Music"
  #3: "Road Trip" ↔ "Travel Songs"
```

---

### Sync Commands

#### `songbird sync`
Manually trigger playlist synchronization.

**Usage:**
```bash
songbird sync                 # Normal sync with smart skip
songbird sync --verbose       # Show detailed progress
songbird sync --force         # Force sync, ignore change detection
songbird sync --dry-run       # Preview changes without syncing
songbird sync -vf             # Verbose + force (combined)
songbird sync -d -v           # Dry-run + verbose
```

**Flags:**
- `-v, --verbose`: Show detailed track-by-track progress
- `-f, --force`: Force full sync even if no changes detected
- `-d, --dry-run`: Preview what would change without making modifications

**Normal Sync Output:**
```bash
🔄 Starting manual sync...
🔄 Starting local sync...

📋 Syncing: Workout Mix ↔ Gym Playlist
  ⏩ Skipped (no changes detected)

📋 Syncing: Chill Vibes ↔ Relaxing Music
  Spotify: 45 tracks
  YouTube Music: 43 tracks
  ➕ Adding 2 tracks to YouTube Music
  [Parallel processing with 5 workers...]
  ✅ Matched 2 tracks
✅ Sync completed for pair 2

⏩ Skipped 1 playlist(s) with no changes
✅ Sync completed successfully!
```

**Dry-Run Output:**
```bash
🔍 Dry run mode - previewing changes without syncing...
🔍 Analyzing playlists (dry run - no changes will be made)...

📋 Analyzing: Chill Vibes ↔ Relaxing Music
  Spotify: 45 tracks
  YouTube Music: 43 tracks

  📋 Sync Plan Preview:
  ============================================================

  ➕ Would add 2 tracks to YouTube Music:
     1. Midnight City - M83
     2. Electric Feel - MGMT

  ✓ No tracks to add to Spotify

  ============================================================
  📊 Total changes: 2 tracks would be added

✅ Dry run complete! No changes were made.
   Run 'songbird sync' to apply these changes.
```

---

### Utility Commands

#### `songbird clear-errors`
Clear all error logs from S3.

**Usage:**
```bash
songbird clear-errors
```

**Confirmation:** Prompts for confirmation before clearing.

---

#### `songbird clear-snapshots`
Clear playlist snapshots to force re-sync on next run.

**Usage:**
```bash
songbird clear-snapshots
```

**Use Cases:**
- Snapshot data appears incorrect
- Want to force fresh comparison
- Manual edits not being detected

**Note:** Next sync will compare full playlists instead of using cached counts.

---

#### `songbird reset`
Reset all configuration (pairs, history, errors).

**Usage:**
```bash
songbird reset
```

**Confirmation:** Requires explicit confirmation.

**Removes:**
- All playlist pairs
- Sync history
- Error logs
- Playlist snapshots

**Preserves:**
- Authentication tokens (Spotify and YouTube)

**Note:** To re-authenticate, run:
```bash
songbird auth spotify
songbird auth youtube
```

---

## Performance Optimizations

### 1. Smart Change Detection (Snapshot-Based Skip)

**Problem:** Running full sync every time, even when playlists haven't changed, wastes time and API calls.

**Solution:** After each sync, save a "snapshot" of track counts to S3. On next sync, quickly check if counts changed.

**Implementation:**
- Stores: `spotify_count`, `youtube_count`, `updated_at`
- Comparison: O(1) count check vs O(n) full track fetch
- Bypass: Use `--force` flag to skip detection

**Performance Impact:**
```
No changes:     2-5 seconds    (vs 3-9 minutes before)
Small changes:  30-90 seconds  (vs 3-9 minutes before)
First sync:     3-9 minutes    (same as before)

Improvement: ~100x faster for unchanged playlists
```

**Code Location:** `src/songbird/sync/manager.py:94-146`

---

### 2. Parallel Processing for Song Matching

**Problem:** Sequential API calls for matching tracks is slow (2 seconds per track).

**Solution:** Use `ThreadPoolExecutor` to search for multiple tracks concurrently with rate limiting.

**Implementation:**
- 5 parallel workers for batches > 5 tracks
- Rate limiting: 3 req/sec (Spotify), 2 req/sec (YouTube)
- Automatic fallback to sequential for small batches
- Thread-safe request tracking with `deque`

**Performance Impact:**
```
22 tracks sequential: 44 seconds
22 tracks parallel:   ~9 seconds (5x faster!)
```

**Code Location:** `src/songbird/sync/song_matcher.py:87-172`

---

### 3. Optimized Matching Logic

**Problem:** Previously matched ALL tracks from both playlists (188 searches for 77+111 tracks).

**Solution:** Set-based comparison to find only MISSING tracks, then search for those.

**Implementation:**
- Normalize track names for comparison
- Use Python sets for O(1) lookup
- Only match tracks in `spotify_only` and `youtube_only` sets
- Deduplicate before comparison

**Performance Impact:**
```
Before: 188 API searches (all tracks)
After:  38 API searches (only missing tracks)

Improvement: ~5x fewer API calls
```

**Code Location:** `src/songbird/sync/manager.py:148-345`

---

### 4. Duplicate Prevention

**Problem:** Duplicate tracks were being added on subsequent syncs.

**Solution:** Two-layer deduplication:
1. Remove pre-existing duplicates before comparison
2. Check playlist contents before adding tracks

**Implementation:**
```python
# Layer 1: Deduplication in sync plan
seen_spotify = set()
deduplicated_spotify = []
for track in spotify_tracks:
    norm = normalize_track(track)
    if norm not in seen_spotify:
        seen_spotify.add(norm)
        deduplicated_spotify.append(track)

# Layer 2: Real-time duplicate checking
existing_tracks = self.spotify_manager.get_playlist_tracks(playlist_id)
existing_uris = {track['uri'] for track in existing_tracks}

if match['uri'] not in existing_uris:
    spotify_uris.append(match['uri'])
```

**Code Location:**
- Layer 1: `src/songbird/sync/manager.py:217-248`
- Layer 2: `src/songbird/sync/manager.py:423-470`

---

### Performance Comparison Table

| Scenario | Before | After | Improvement |
|----------|--------|-------|-------------|
| No changes (common) | 3-9 min | 2-5 sec | 100x faster |
| Small changes (10-20 tracks) | 3-9 min | 30-90 sec | 5x faster |
| First sync / major changes | 3-9 min | 3-9 min | Same (better UX) |
| 22 track matching | 44 sec | 9 sec | 5x faster |

---

## Implementation Details

### Song Matching Algorithm

**Normalization Process:**
1. Remove parentheses content: `(Remastered)`, `(feat. Artist)`
2. Remove bracket content: `[Radio Edit]`
3. Remove text after dash: `Song - Remix`
4. Remove common words: `feat`, `featuring`, `ft`, `remix`, `remaster`
5. Trim whitespace
6. Convert to lowercase

**Scoring System:**
```python
# Weighted scoring
title_score = SequenceMatcher(None, track1_title, track2_title).ratio()
artist_score = SequenceMatcher(None, track1_artist, track2_artist).ratio()
combined_score = (title_score * 0.7) + (artist_score * 0.3)

# Bonuses
if exact_artist_match: combined_score += 0.1
if exact_title_match: combined_score += 0.1

# Duration validation (±5 seconds)
if duration_diff <= 5000ms:
    duration_score = 1.0 - (diff / 5000)
    combined_score = (combined_score * 0.9) + (duration_score * 0.1)

# Threshold
if combined_score >= 0.8:
    return match
```

**Code Location:** `src/songbird/sync/song_matcher.py:220-287`

---

### S3 Storage Structure

```
s3://your-songbird-bucket/
├── config.json                      # Main configuration
│   ├── playlist_pairs[]             # Array of paired playlists
│   │   ├── id                       # Unique pair ID
│   │   ├── spotify{}                # Spotify playlist info
│   │   │   ├── id
│   │   │   ├── name
│   │   │   └── uri
│   │   ├── youtube{}                # YouTube playlist info
│   │   │   ├── id
│   │   │   └── name
│   │   ├── snapshot{}               # Cached track counts
│   │   │   ├── spotify_count
│   │   │   ├── youtube_count
│   │   │   └── updated_at
│   │   ├── last_sync                # ISO timestamp
│   │   └── last_sync_status         # success/failed
│   ├── sync_settings{}
│   │   ├── schedule                 # daily/hourly/etc
│   │   ├── last_sync                # Global last sync time
│   │   └── sync_deletions           # true/false
│   └── error_log[]                  # Last 100 errors
│       ├── timestamp
│       ├── type
│       ├── message
│       └── details{}
│
└── tokens/
    ├── spotify_tokens.json          # Spotify OAuth tokens
    │   ├── access_token
    │   ├── refresh_token
    │   ├── expires_at
    │   └── scope
    └── youtube_headers.json         # YouTube auth headers
        ├── cookie
        ├── user-agent
        └── x-goog-authuser
```

---

### Data Flow Diagram

```
User runs: songbird sync
         │
         ▼
    ┌────────────────┐
    │  CLI Layer     │  Parse command, validate flags
    └────────┬───────┘
             │
             ▼
    ┌────────────────┐
    │ ConfigManager  │  Load playlist pairs from S3
    └────────┬───────┘
             │
             ▼
    ┌────────────────┐
    │  SyncManager   │  For each pair:
    └────────┬───────┘
             │
             ├─► Check snapshot (smart skip)
             │   └─► If no changes → Skip pair
             │
             ├─► Fetch Spotify tracks
             │   └─► SpotifyPlaylistManager → Spotify API
             │
             ├─► Fetch YouTube tracks
             │   └─► YouTubePlaylistManager → ytmusicapi
             │
             ├─► Create sync plan
             │   ├─► Normalize tracks
             │   ├─► Deduplicate
             │   ├─► Set comparison (find missing)
             │   └─► Determine add_to_spotify, add_to_youtube
             │
             ├─► Execute sync plan (or preview if dry-run)
             │   ├─► Match missing tracks (parallel if >5)
             │   │   └─► SongMatcher.batch_match_songs_parallel()
             │   │       ├─► ThreadPoolExecutor (5 workers)
             │   │       ├─► Rate limiting (2-3 req/sec)
             │   │       └─► Fuzzy matching
             │   │
             │   ├─► Add tracks to Spotify
             │   │   ├─► Check for duplicates
             │   │   └─► Spotify API batch add
             │   │
             │   └─► Add tracks to YouTube
             │       ├─► Check for duplicates
             │       └─► ytmusicapi batch add
             │
             └─► Update snapshot
                 └─► Save new track counts to S3
```

---

## Recent Changes & Updates

### v1.0 - October 2025

#### New CLI Commands

**1. Unpair Command**
- Added `songbird unpair <pair_id>` to remove specific playlist pairs
- Includes confirmation prompt (bypassable with `--yes`)
- Shows playlist details before removal
- Displays remaining pairs count

**2. Dry-Run Mode**
- Added `--dry-run` flag to `songbird sync`
- Previews all changes without making modifications
- Shows first 5 tracks that would be added
- Displays unmatched tracks
- Provides change summary

#### Performance Improvements

**1. Smart Skip (Snapshot-Based Change Detection)**
- Caches track counts after each sync
- 100x faster when no changes (2-5 sec vs 3-9 min)
- Bypassable with `--force` flag

**2. Parallel Processing**
- ThreadPoolExecutor with 5 workers
- Rate limiting: 3 req/sec (Spotify), 2 req/sec (YouTube)
- 5x faster track matching
- Automatic for batches > 5 tracks

**3. Optimized Matching**
- Set-based comparison for O(1) lookups
- Only searches for missing tracks
- 5x fewer API calls

#### Bug Fixes

**1. Duplicate Prevention**
- Two-layer deduplication system
- Pre-sync deduplication of existing duplicates
- Real-time duplicate checking before adding
- Fixes recurring duplicate issue

**2. YouTube Music Search Errors**
- Added null checks for API responses
- Type validation for search results
- Graceful handling of empty results

**3. Datetime Compatibility**
- Fixed `datetime.UTC` compatibility (Python 3.11+ only)
- Changed to `timezone.utc` (Python 3.2+)

#### Configuration Management

**1. Snapshot Management**
- `songbird clear-snapshots` command
- Stores: track counts, snapshot IDs, updated_at
- Automatic updates after successful sync

**2. Error Log Management**
- `songbird clear-errors` command
- Keeps last 100 errors in S3
- Structured error format with timestamps

**3. Reset Functionality**
- `songbird reset` command
- Clears pairs, history, errors
- Preserves authentication tokens

---

## Future Enhancements

### Planned Features

#### 1. Scheduled Sync (AWS Lambda)
**Status:** Architecture ready, not yet implemented

**Implementation Plan:**
- Deploy to AWS Lambda
- EventBridge scheduled trigger (hourly/daily)
- CloudWatch logging
- SNS notifications on failure

**Estimated Effort:** 2-3 days

---

#### 2. Incremental Sync
**Status:** Proposed

**Description:** Track individual song additions/removals instead of full playlist comparison.

**Benefits:**
- Faster syncs (only process delta)
- Better handling of playlist edits
- Lower API usage

**Challenges:**
- Requires more complex state management
- Need to track "last seen" state per track
- Harder to recover from errors

**Estimated Effort:** 1 week

---

#### 3. Webhook Notifications
**Status:** Proposed

**Description:** Send notifications when sync completes or fails.

**Implementation Options:**
- Email (AWS SES)
- Slack webhook
- Discord webhook
- SMS (AWS SNS)

**Estimated Effort:** 1-2 days

---

#### 4. Multi-User Support
**Status:** Future consideration

**Description:** Support multiple user accounts and cross-user sharing.

**Challenges:**
- Authentication complexity
- Permission management
- Cost implications

**Estimated Effort:** 2-3 weeks

---

#### 5. Web Dashboard
**Status:** Long-term

**Description:** Web UI for configuration and monitoring.

**Features:**
- View sync history
- Configure playlist pairs
- Trigger manual sync
- View error logs
- Statistics and analytics

**Tech Stack:** React + AWS API Gateway + Lambda

**Estimated Effort:** 4-6 weeks

---

### Performance Improvements (Future)

#### 1. Async/Await Implementation
Replace ThreadPoolExecutor with asyncio for better resource efficiency.

**Benefits:**
- Single-threaded (lower overhead)
- Better rate limit control
- Easier retry logic

**Challenges:**
- Requires rewriting API calls
- More complex code
- Learning curve

**Estimated Effort:** 1 week

---

#### 2. Search Result Caching
Cache search results to avoid re-searching the same tracks.

**Implementation:**
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def find_matching_song(track_name, artist, target_service):
    # Search logic
```

**Benefits:**
- Faster repeated searches
- Lower API usage
- Better for large libraries

**Estimated Effort:** 1 day

---

#### 3. Batch API Calls
Group multiple operations into single API requests.

**Status:** Limited by API support
- Spotify: Supports batch adds (already implemented)
- YouTube Music: Limited batch support

**Estimated Effort:** 2-3 days

---

## Appendix

### Troubleshooting Guide

#### "Spotify authentication failed"
**Solutions:**
1. Check `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in `.env`
2. Verify redirect URI is `http://localhost:8888/callback`
3. Check port 8888 is not in use
4. Re-run `songbird auth spotify`

#### "YouTube Music authentication failed"
**Solutions:**
1. Ensure browser is logged into YouTube Music
2. Copy cookies exactly as shown
3. Check cookie hasn't expired
4. Try different browser

#### "Access denied: invalid token"
**Solutions:**
1. Tokens may have expired
2. Re-authenticate: `songbird auth spotify` / `songbird auth youtube`
3. Check S3 bucket access

#### "Sync is slow"
**Solutions:**
1. Normal for first sync (3-9 min)
2. Subsequent syncs should use smart skip (2-5 sec)
3. Use `--verbose` to see what's taking time
4. YouTube Music API is inherently slower

#### "Duplicates appearing"
**Solutions:**
1. Should be fixed in v1.0 with two-layer deduplication
2. If still occurring, report as bug
3. Temporary fix: manually remove duplicates

#### "Changes not detected"
**Solutions:**
1. Track counts might be same (added + removed)
2. Use `songbird sync --force` to override
3. Clear snapshots: `songbird clear-snapshots`

---

### API Rate Limits

#### Spotify
- **Rate Limit:** ~180 requests per minute
- **Recommended:** 3 requests/second
- **Batch Add:** Up to 100 tracks per request

#### YouTube Music (ytmusicapi)
- **Rate Limit:** Unknown (unofficial API)
- **Recommended:** 2 requests/second (conservative)
- **Batch Add:** Up to 100 tracks per request

---

### Environment Variables Reference

```env
# Required: Spotify OAuth
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

# Required: S3 Storage
SONGBIRD_CONFIG_BUCKET=your-s3-bucket-name

# Optional: AWS Credentials (if not using AWS CLI)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_DEFAULT_REGION=us-east-1

# Optional: YouTube Music OAuth (alternative to cookies)
YOUTUBE_CLIENT_ID=your-client-id.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=your-client-secret
```

---

### File Structure

```
Songbird/
├── src/
│   └── songbird/
│       ├── __init__.py
│       ├── __main__.py              # Entry point
│       ├── cli.py                   # CLI commands
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── spotify.py           # Spotify OAuth
│       │   └── youtube.py           # YouTube auth
│       ├── config/
│       │   ├── __init__.py
│       │   └── manager.py           # S3 config management
│       ├── sync/
│       │   ├── __init__.py
│       │   ├── manager.py           # Sync orchestration
│       │   ├── song_matcher.py      # Matching logic
│       │   ├── playlist_manager.py  # API interactions
│       │   └── pairing.py           # Interactive pairing
│       └── utils/
│           └── __init__.py
├── docs/
│   ├── Songbird PRD.md              # This file
│   ├── README.md                    # Quick start guide
│   └── GOOGLE_OAUTH_SETUP.md        # OAuth setup (archived)
├── tests/                           # (Future)
├── .env                             # Environment variables (gitignored)
├── .gitignore
├── requirements.txt
└── README.md                        # Project overview
```

---

### Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1 | Oct 2025 | Initial implementation: auth, pairing, basic sync |
| 0.2 | Oct 2025 | Added smart skip, parallel processing |
| 0.3 | Oct 2025 | Duplicate prevention, error handling |
| 1.0 | Oct 2025 | Dry-run mode, unpair command, comprehensive docs |

---

**Document Maintained By:** Development Team
**Last Review:** 2025-10-26
**Next Review:** As needed for major changes