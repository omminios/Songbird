# Parallel Processing Implementation Proposal

## Problem
Currently, searching for matches is the slowest part of sync:
- 22 tracks to match × 2 seconds each = **44 seconds**
- All searches are independent and could run simultaneously

## Solution: Parallel Search Processing

### Implementation Options

#### Option 1: ThreadPoolExecutor (Easiest)
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def find_matches_parallel(self, tracks: List[Dict], target_service: str, max_workers: int = 10):
    """Find matches for multiple tracks in parallel"""

    def search_one_track(track):
        try:
            match = self.song_matcher.find_matching_song(track, target_service)
            return (track, match, None)
        except Exception as e:
            return (track, None, str(e))

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all searches at once
        futures = {executor.submit(search_one_track, track): track
                   for track in tracks}

        # Collect results as they complete
        for future in as_completed(futures):
            results.append(future.result())

    return results
```

**Pros:**
- Easy to implement (10-15 lines of code)
- Works with existing code
- Can control concurrency (max_workers)

**Cons:**
- Still limited by API rate limits
- May hit rate limit errors if too aggressive

#### Option 2: asyncio (More Complex, More Control)
```python
import asyncio
import aiohttp

async def search_track_async(self, track: Dict, target_service: str):
    """Async search for a single track"""
    # Would need to rewrite API calls to use aiohttp
    async with aiohttp.ClientSession() as session:
        # Async API call
        result = await self._search_async(session, track)
        return result

async def find_matches_parallel(self, tracks: List[Dict], target_service: str):
    """Find matches using async/await"""
    tasks = [self.search_track_async(track, target_service)
             for track in tracks]

    # Run all searches concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

**Pros:**
- More efficient (single thread)
- Better control over rate limiting
- Can implement retry logic easily

**Cons:**
- Requires rewriting API calls
- More complex code
- Learning curve for async/await

### Recommended Approach: Hybrid

Use ThreadPoolExecutor with **controlled concurrency** and **rate limiting**:

```python
import time
from concurrent.futures import ThreadPoolExecutor
from collections import deque

class RateLimitedSearcher:
    def __init__(self, max_workers=5, requests_per_second=3):
        self.max_workers = max_workers
        self.min_interval = 1.0 / requests_per_second
        self.last_requests = deque(maxlen=requests_per_second)

    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limit"""
        now = time.time()
        if len(self.last_requests) == self.last_requests.maxlen:
            elapsed = now - self.last_requests[0]
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)
        self.last_requests.append(time.time())

    def find_matches_parallel(self, tracks, target_service):
        """Search with rate limiting"""
        def search_with_limit(track):
            self._wait_for_rate_limit()
            return self.song_matcher.find_matching_song(track, target_service)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(search_with_limit, tracks))

        return results
```

## Performance Impact

### Current Performance:
- 22 tracks × 2 seconds = **44 seconds**

### With Parallel Processing (5 workers):
- 22 tracks ÷ 5 workers × 2 seconds = **9 seconds** (5x faster!)

### With Parallel Processing (10 workers):
- 22 tracks ÷ 10 workers × 2 seconds = **5 seconds** (9x faster!)

### With Rate Limiting (3 requests/sec):
- Still faster than sequential
- Avoids API throttling
- More stable

## API Rate Limits to Consider

### Spotify:
- **Rate limit:** ~180 requests per minute
- **Recommended:** 5-10 parallel workers
- **Safe:** 3 requests/second

### YouTube Music (unofficial API):
- **Rate limit:** Unknown (uses browser cookies)
- **Recommended:** 3-5 parallel workers
- **Safe:** 1-2 requests/second (be conservative)

## Implementation Steps

1. **Add parallel search to SongMatcher**
   ```python
   # src/songbird/sync/song_matcher.py

   def batch_match_songs_parallel(self, tracks, target_service, max_workers=5):
       # Implementation here
   ```

2. **Update SyncManager to use parallel matching**
   ```python
   # src/songbird/sync/manager.py

   # In _create_sync_plan:
   if len(spotify_only) > 5:  # Only use parallel for larger batches
       matches = self.song_matcher.batch_match_songs_parallel(spotify_only, 'youtube')
   else:
       matches = self.song_matcher.batch_match_songs(spotify_only, 'youtube')
   ```

3. **Add CLI flag for concurrency control**
   ```bash
   songbird sync --parallel --workers 10
   ```

## Risks & Mitigation

### Risk 1: API Rate Limiting
- **Mitigation:** Implement rate limiter
- **Mitigation:** Start with conservative workers (3-5)
- **Mitigation:** Add exponential backoff on errors

### Risk 2: Increased API costs
- **Mitigation:** Same number of requests, just faster
- **Mitigation:** No additional costs

### Risk 3: More errors if API unstable
- **Mitigation:** Proper error handling
- **Mitigation:** Retry failed searches sequentially

## Next Steps

Would you like me to implement:
1. **Basic parallel processing** (ThreadPoolExecutor, 5 workers)
2. **Advanced with rate limiting** (Controlled concurrency)
3. **Full async implementation** (Most efficient, most work)

I recommend starting with #1 or #2 for quick wins!
