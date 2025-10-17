# Songbird

Sync playlists between Spotify and YouTube Music with automatic and manual synchronization.

## Features

- 🎵 Spotify authentication and playlist access
- 🎬 YouTube Music API integration (in development)
- 🔗 Interactive playlist pairing
- 🔄 Manual and automatic sync
- 📊 Sync status and error reporting
- ☁️ Serverless architecture (AWS Lambda + API Gateway)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Songbird
```

2. Create and activate virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Songbird CLI:
```bash
pip install -e .
```

## Setup

### 1. Spotify Authentication

First, set up your Spotify application credentials:

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Set redirect URI to: `http://localhost:8888/callback`
4. Copy your Client ID and Client Secret

Create a `.env` file in the project root:
```env
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
```

### 2. YouTube Music (Coming Soon)

YouTube Music integration will use OAuth 2.0 authentication.

## Usage

### Authenticate with Services

```bash
# Authenticate with Spotify
songbird auth spotify

# Authenticate with YouTube Music (coming soon)
songbird auth youtube
```

### Pair Playlists

```bash
# Start interactive playlist pairing
songbird pair
```

### Sync Playlists

```bash
# Manual sync
songbird sync

# Check sync status
songbird status
```

### Help

```bash
# Show all commands
songbird --help

# Get help for specific command
songbird auth --help
```

## Development Status

### ✅ Completed
- CLI framework with Click
- Spotify OAuth 2.0 authentication
- Configuration management
- Interactive playlist pairing interface
- Song matching logic with fuzzy matching
- Local sync functionality (demo mode)

### 🚧 In Progress
- YouTube Music OAuth integration
- AWS Lambda sync function
- API Gateway manual trigger
- Error handling and logging improvements

### 📋 Planned
- Automated scheduling (EventBridge)
- S3 configuration storage
- Advanced song matching algorithms
- Web dashboard (optional)

## Architecture

```
CLI Commands:
├── songbird auth spotify    # OAuth flow
├── songbird auth youtube    # OAuth flow
├── songbird pair           # Select & pair playlists
├── songbird sync           # Manual sync
└── songbird status         # Show status

AWS:
├── Lambda Function         # Sync logic
├── API Gateway            # HTTP endpoint for manual sync
├── EventBridge           # Daily schedule
└── S3                    # Config & logs
```

## Current Limitations

1. **YouTube Music**: OAuth authentication not yet implemented
2. **Sync**: Currently runs locally, AWS Lambda integration pending
3. **Scheduling**: Manual sync only, automatic scheduling pending

## Contributing

1. Follow the existing code structure
2. Add tests for new functionality
3. Update documentation
4. Ensure CLI commands work as expected

## License

MIT License - see LICENSE file for details.