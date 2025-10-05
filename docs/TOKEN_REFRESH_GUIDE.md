# Token Refresh Implementation Guide

This document explains how automatic token refresh works in Songbird.

## Overview

Both Spotify and Apple Music require authentication tokens that expire. Songbird automatically refreshes these tokens to maintain seamless operation without user intervention.

## Spotify Token Refresh

### Token Lifecycle

1. **Initial Authentication** (`songbird auth spotify`)
   - User completes OAuth flow in browser
   - Receives: `access_token` (1 hour) + `refresh_token` (indefinite)
   - Saved to: `data/spotify_tokens.json`

2. **Token Structure**
```json
{
  "access_token": "BQC4h7...",
  "refresh_token": "AQD9x2...",
  "expires_in": 3600,
  "token_type": "Bearer",
  "scope": "playlist-read-private playlist-modify-private",
  "obtained_at": 1705334400.0
}
```

3. **Automatic Refresh Flow**
```python
# Every API call checks token validity
def get_valid_token(self):
    # Load token from file
    token_data = load_tokens()

    # Check if expired (with 5-minute buffer)
    if self._is_token_expired(token_data):
        # Refresh automatically
        new_tokens = self._refresh_access_token(refresh_token)
        self._save_tokens(new_tokens)
        return new_tokens['access_token']

    return token_data['access_token']
```

### Expiry Detection Logic

```python
def _is_token_expired(self, token_data):
    obtained_at = token_data['obtained_at']  # Unix timestamp
    expires_in = token_data['expires_in']    # Seconds (usually 3600)
    current_time = time.time()

    expires_at = obtained_at + expires_in
    buffer = 300  # 5 minutes in seconds

    # Expired if: current_time + buffer >= expires_at
    return (current_time + buffer) >= expires_at
```

**Why 5-minute buffer?** Prevents mid-request expiry during long operations.

### Refresh API Call

```python
def _refresh_access_token(self, refresh_token):
    # POST to Spotify token endpoint
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }

    # Basic Auth with client credentials
    headers = {
        'Authorization': f'Basic {base64_encoded_credentials}'
    }

    response = requests.post(
        'https://accounts.spotify.com/api/token',
        data=data,
        headers=headers
    )

    # Returns new access_token
    # May or may not include new refresh_token
```

**Important**: Spotify sometimes returns a new `refresh_token`, sometimes doesn't. Code handles both cases.

### Error Handling

```python
if refresh fails:
    print("Token refresh failed. Please re-authenticate with 'songbird auth spotify'")
    return None
```

User must manually re-authenticate if:
- Refresh token is revoked
- Network error persists
- Credentials are invalid

---

## Apple Music Token Refresh

### Token Lifecycle

1. **Initial Authentication** (`songbird auth apple`)
   - Generates JWT from private key (.p8 file)
   - Token expires in 6 hours
   - Saved to: `data/apple_tokens.json`

2. **Token Structure**
```json
{
  "token": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjRLWTdOMjY3WFgifQ...",
  "created_at": "2025-01-15T10:30:00",
  "expires_at": "2025-01-15T16:30:00"
}
```

3. **Automatic Refresh Flow**
```python
def get_valid_token(self):
    # Load token from file
    token_data = load_tokens()

    # Check if valid (with 10-minute buffer)
    if self._is_token_valid(token_data):
        return token_data['token']

    # Regenerate JWT (no API call needed!)
    new_token = self._generate_jwt_token()
    self._save_token(new_token)
    return new_token
```

### Key Difference from Spotify

**Apple Music doesn't use OAuth refresh tokens**. Instead, we regenerate JWT locally:

```python
def _generate_jwt_token(self):
    # Read private key from .p8 file
    private_key = read_p8_file()

    # Create payload
    payload = {
        'iss': team_id,           # Your Apple Team ID
        'iat': now(),             # Issued at time
        'exp': now() + 6_hours,   # Expiry time
        'aud': 'appstoreconnect-v1'
    }

    # Sign with ES256 algorithm
    token = jwt.encode(payload, private_key, algorithm='ES256')
    return token
```

**Advantages**:
- No network call needed
- Instant regeneration
- Can't be "revoked" by Apple

**Disadvantages**:
- Requires secure storage of .p8 private key
- Only works for server-to-server (not user playlists yet)

### Expiry Detection Logic

```python
def _is_token_valid(self, token_data):
    expires_at = datetime.fromisoformat(token_data['expires_at'])
    buffer = timedelta(minutes=10)

    # Valid if: current_time < expires_at - buffer
    return datetime.utcnow() < (expires_at - buffer)
```

**Why 10-minute buffer?** JWTs expire in 6 hours, so larger buffer is safe.

---

## Manual Refresh Commands

### For Debugging/Testing

Both auth classes now support manual refresh:

```python
# Spotify
spotify_auth = SpotifyAuth()
spotify_auth.refresh_token_manually()

# Apple Music
apple_auth = AppleAuth()
apple_auth.refresh_token()
```

### Token Info Commands

Check token status without making API calls:

```python
# Spotify
info = spotify_auth.get_token_info()
print(f"Valid: {info['valid']}")
print(f"Expires at: {info['expires_at']}")
print(f"Time remaining: {info['time_remaining_minutes']} minutes")

# Apple Music
info = apple_auth.get_token_info()
print(f"Valid: {info['valid']}")
print(f"Time remaining: {info['time_remaining_hours']} hours")
```

---

## Flow Diagrams

### Spotify Token Flow
```
User runs command
    ↓
get_valid_token() called
    ↓
Check token file exists? ──No──> Return None (re-auth needed)
    ↓ Yes
Check if expired?
    ↓ No                    ↓ Yes
Return token          Call _refresh_access_token()
                           ↓
                      POST to Spotify API
                           ↓
                      Success? ──No──> Return None
                           ↓ Yes
                      Save new tokens
                           ↓
                      Return new access_token
```

### Apple Music Token Flow
```
User runs command
    ↓
get_valid_token() called
    ↓
Check token file exists? ──No──┐
    ↓ Yes                       │
Check if valid?                 │
    ↓ No                        │
    ├───────────────────────────┘
    ↓
_generate_jwt_token()
    ↓
Read .p8 private key (local file)
    ↓
Create JWT payload
    ↓
Sign with ES256
    ↓
Save token to file
    ↓
Return token
```

---

## Best Practices

### For Users

1. **Spotify**: Authenticate once, tokens auto-refresh indefinitely
2. **Apple Music**: Keep .p8 file secure, tokens regenerate automatically
3. **If errors occur**: Try `songbird auth <service>` to re-authenticate

### For Developers

1. **Always use `get_valid_token()`**: Never directly read token files
2. **Handle None returns**: Token refresh can fail, gracefully prompt re-auth
3. **Test expiry**: Manually edit `obtained_at` in token file to test refresh logic
4. **Secure storage**: In production, move tokens to AWS Secrets Manager or S3 with encryption

---

## Production Deployment

### AWS Lambda Considerations

When running in Lambda, tokens should be stored in:

1. **S3 Bucket** (recommended for Songbird)
   - Encrypted at rest
   - Versioning enabled
   - Lambda reads/writes tokens here

2. **AWS Secrets Manager** (alternative)
   - More expensive
   - Better for highly sensitive data
   - Automatic rotation support

### Example Lambda Modification

```python
def _save_tokens(self, tokens):
    # Check if running in Lambda
    if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        # Save to S3
        s3_client = boto3.client('s3')
        bucket = os.environ.get('SONGBIRD_CONFIG_BUCKET')
        s3_client.put_object(
            Bucket=bucket,
            Key='tokens/spotify_tokens.json',
            Body=json.dumps(tokens),
            ServerSideEncryption='AES256'
        )
    else:
        # Save to local file (development)
        with open('data/spotify_tokens.json', 'w') as f:
            json.dump(tokens, f)
```

---

## Troubleshooting

### "Token refresh failed"
- **Cause**: Refresh token revoked or network error
- **Solution**: Re-authenticate with `songbird auth spotify`

### "No refresh token found"
- **Cause**: Old token format or corrupted file
- **Solution**: Delete `data/spotify_tokens.json` and re-authenticate

### "Failed to generate JWT token"
- **Cause**: .p8 file not found or invalid
- **Solution**: Check `APPLE_PRIVATE_KEY_PATH` environment variable

### Tokens refreshing too frequently
- **Cause**: System clock incorrect
- **Solution**: Sync system time with NTP server

---

## Testing Token Refresh

### Manually Trigger Expiry

**Spotify**:
```python
# Edit data/spotify_tokens.json
# Change "obtained_at" to old timestamp
{
  "obtained_at": 1000000000  # Ancient timestamp
}

# Next API call will auto-refresh
```

**Apple Music**:
```python
# Edit data/apple_tokens.json
# Change "expires_at" to past time
{
  "expires_at": "2020-01-01T00:00:00"
}

# Next API call will regenerate
```

### Monitor Refresh Behavior

Add logging to see when refreshes occur:

```python
def get_valid_token(self):
    if self._is_token_expired(token_data):
        print("🔄 Token expired, refreshing...")
        new_tokens = self._refresh_access_token(refresh_token)
        print("✅ Token refreshed successfully")
```

---

## Summary

- **Spotify**: OAuth refresh tokens, 1-hour access tokens, automatic refresh via API
- **Apple Music**: JWT regeneration, 6-hour tokens, no API call needed
- **Both**: Transparent to user, automatic on every API call
- **Failure**: Gracefully prompts user to re-authenticate