# Songbird

Sync playlists between Spotify and YouTube Music.

## Environment Variables

Create a `.env` file in the project root with:

```bash
# Spotify OAuth (required)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

# S3 Storage (required)
SONGBIRD_CONFIG_BUCKET=your-s3-bucket-name

# AWS Credentials (if not using AWS CLI default profile)
# AWS_ACCESS_KEY_ID=your_aws_key
# AWS_SECRET_ACCESS_KEY=your_aws_secret
# AWS_DEFAULT_REGION=us-east-1
```

**Note:** YouTube Music uses browser cookie authentication (no OAuth keys needed).

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Authenticate with Spotify:
   ```bash
   songbird auth spotify
   ```

3. Authenticate with YouTube Music:
   ```bash
   songbird auth youtube
   ```
   Follow the prompts to copy browser cookies from YouTube Music.

## Usage

- Pair playlists: `songbird pair`
- Sync playlists: `songbird sync`
- Check status: `songbird status`
- View auth info: `songbird auth token-info`

## Notes

- YouTube Music cookies expire after ~1 year
- Spotify OAuth tokens auto-refresh
- All config stored in S3
