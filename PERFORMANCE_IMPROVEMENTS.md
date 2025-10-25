# Songbird Performance Improvements

## Overview

The sync performance has been significantly improved with smart change detection and optimized matching logic.

## Features Implemented

### 1. Smart Change Detection (Fast Skip)

**How it works:**
- After each sync, saves a "snapshot" of playlist track counts to S3
- On next sync, quickly checks if track counts changed
- If counts match → Skip sync (saves minutes!)
- If counts differ → Run full sync

**Performance Impact:**
- **No changes:** ~2-5 seconds (just API calls to get counts)
- **With changes:** Full sync as before

**Example:**
```bash
# First sync (full)
songbird sync
📋 Syncing: Playlist A ↔ Playlist B
  Spotify: 100 tracks
  YouTube: 100 tracks
  [Full sync runs...]
✅ Sync completed

# Second sync (no changes)
songbird sync
📋 Syncing: Playlist A ↔ Playlist B
  ⏩ Skipped (no changes detected)
⏩ Skipped 1 playlist(s) with no changes
✅ Sync completed in 3 seconds!
```

### 2. Optimized Matching Logic

**Before:**
- Matched ALL tracks from both playlists
- 77 Spotify + 111 YouTube = 188 API searches
- ~3-9 minutes per playlist pair

**After:**
- Only matches tracks that are MISSING
- Example: If 150 tracks already match, only search for 38 missing
- ~1-3 minutes per playlist pair (when changes exist)

### 3. Deduplication

- Removes duplicate tracks before comparison
- Prevents duplicate syncing bugs
- Faster comparisons with cleaner data

## CLI Usage

### Normal Sync (with smart skip)
```bash
songbird sync
```
- Skips playlists with no changes
- Fast when nothing changed

### Verbose Sync
```bash
songbird sync --verbose
# or
songbird sync -v
```
- Shows detailed progress
- See which tracks are being processed
- Debug matching issues

### Force Sync (skip detection disabled)
```bash
songbird sync --force
# or
songbird sync -f
```
- Forces full sync even if no changes detected
- Useful if:
  - Tracks were manually edited
  - You suspect the snapshot is wrong
  - Previous sync failed partway

### Combined Options
```bash
songbird sync --verbose --force
songbird sync -vf
```

## Performance Comparison

### Scenario 1: No Changes (Common)
- **Before:** 3-9 minutes (full sync every time)
- **After:** 2-5 seconds (smart skip)
- **Improvement:** ~100x faster!

### Scenario 2: Small Changes (10-20 new tracks)
- **Before:** 3-9 minutes (matches all 188 tracks)
- **After:** 30-90 seconds (matches only 10-20 tracks)
- **Improvement:** ~5x faster

### Scenario 3: First Sync or Major Changes
- **Before:** 3-9 minutes
- **After:** 3-9 minutes (same, but with better progress reporting)
- **Improvement:** Same speed, better UX

## Future Optimizations (Not Yet Implemented)

### Parallel Pair Processing
```python
# Sync multiple pairs simultaneously
# Would require async/threading
for pair in pairs:
    sync_in_parallel(pair)
```
**Benefit:** 15 pairs could sync in ~same time as 1 pair

### Batch API Calls
- Group multiple searches into one request
- Requires API support (Spotify supports this, YouTube Music limited)

### Incremental Sync
- Track individual song additions/removals
- Only sync the delta, not full comparison
- Would require more complex state management

## Tips for Best Performance

1. **Run sync regularly** - Smaller changes = faster syncs
2. **Use `--force` sparingly** - Let smart skip work for you
3. **Clean duplicates** - Run `remove_duplicates.py` occasionally
4. **Monitor with `--verbose`** - See what's taking time

## Troubleshooting

### "Skipped but I added songs!"
- Track count might not have changed if you added AND removed
- Use `songbird sync --force` to override

### "Still slow with small changes"
- YouTube Music API is inherently slower (browser cookies)
- Consider running sync less frequently
- API rate limits can't be avoided

### "Snapshot seems wrong"
- Run `songbird reset` to clear all data
- Or `songbird sync --force` to rebuild snapshot
