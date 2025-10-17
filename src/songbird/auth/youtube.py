"""
YouTube Music OAuth 2.0 authentication handler
"""
import boto3
import os
import json
import time
import webbrowser
from ytmusicapi import YTMusic
from ytmusicapi.auth.oauth.credentials import OAuthCredentials
from ytmusicapi.auth.oauth.token import RefreshingToken
from dotenv import load_dotenv

load_dotenv()


class YouTubeAuth:
    """Handles YouTube Music OAuth 2.0 authentication flow"""

    def __init__(self):
        self.client_id = os.getenv('YOUTUBE_CLIENT_ID')
        self.client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')

        # S3 configuration (always required)
        self.s3_bucket = os.getenv('SONGBIRD_CONFIG_BUCKET')
        if not self.s3_bucket:
            raise ValueError(
                "Missing SONGBIRD_CONFIG_BUCKET environment variable.\n"
                "Please set it to your S3 bucket name:\n"
                "  export SONGBIRD_CONFIG_BUCKET=your-bucket-name"
            )

        if not boto3:
            raise ImportError(
                "boto3 is required for S3 storage.\n"
                "Install with: pip install boto3"
            )

        self.s3_client = boto3.client('s3')

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Missing YouTube Music credentials. Please set YOUTUBE_CLIENT_ID and "
                "YOUTUBE_CLIENT_SECRET environment variables."
            )

    def authenticate(self, open_browser=True):
        """
        Perform OAuth 2.0 authentication flow for YouTube Music

        Args:
            open_browser: If True, automatically open browser with auth URL

        Returns True if successful, False otherwise
        """
        try:
            print("\n📺 YouTube Music OAuth Setup")
            print("=" * 70)
            print("\nThis will guide you through YouTube Music authentication.")

            print("\n⚠️  IMPORTANT: Google OAuth App Verification")
            print("-" * 70)
            print("Since Songbird is in development, you may see a warning that says:")
            print("  'Google hasn't verified this app'")
            print("\nTo continue:")
            print("  1. Click 'Advanced' or 'Show Advanced'")
            print("  2. Click 'Go to Songbird (unsafe)' or 'Continue'")
            print("  3. This is safe - you're authorizing YOUR OWN app")
            print("-" * 70)

            print("\nPress Enter to continue...")
            input()

            # Create OAuth credentials
            oauth_credentials = OAuthCredentials(
                client_id=self.client_id,
                client_secret=self.client_secret
            )

            # Get the device code
            print("\n🔄 Requesting authorization code from Google...")
            code_info = oauth_credentials.get_code()

            # Display the authorization information prominently
            print("\n" + "=" * 70)
            print("🔑 AUTHORIZATION CODE")
            print("=" * 70)
            print(f"\n  Code: {code_info['user_code']}")
            print(f"\n  URL:  {code_info['verification_url']}")
            print("\n" + "=" * 70)

            # Build the full URL with the code pre-filled
            full_url = f"{code_info['verification_url']}?user_code={code_info['user_code']}"

            print(f"\n📋 Full URL (code pre-filled): {full_url}")

            if open_browser:
                print("\n🌐 Opening browser...")
                webbrowser.open(full_url)

            print("\n📝 Steps to complete:")
            print("  1. Visit the URL above (should open automatically)")
            print("  2. Sign in with your Google account")
            print("  3. Click 'Advanced' → 'Go to Songbird (unsafe)' if you see a warning")
            print("  4. Grant the requested permissions")
            print("  5. Return here and press Enter when done")

            input("\n⏸️  Press Enter after completing authorization (Ctrl-C to cancel)...")

            # Exchange device code for access token
            print("\n🔄 Exchanging code for access token...")
            raw_token = oauth_credentials.token_from_code(code_info["device_code"])

            # Create refreshing token
            oauth_token = RefreshingToken(credentials=oauth_credentials, **raw_token)
            oauth_token.update(oauth_token.as_dict())

            # Get token as dictionary for YTMusic
            token_dict = oauth_token.as_dict()

            # Create YTMusic instance with the token dictionary AND oauth_credentials
            ytmusic = YTMusic(token_dict, oauth_credentials=oauth_credentials)

            # Prepare data to save to S3
            oauth_data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'token': token_dict,
                'obtained_at': time.time()
            }

            # Save OAuth configuration to S3
            self._save_oauth(oauth_data, ytmusic)

            print("\n✅ YouTube Music authentication successful!")
            print("✅ Tokens saved to S3")
            return True

        except KeyboardInterrupt:
            print("\n\n❌ Authentication cancelled by user")
            return False
        except Exception as e:
            print(f"\n❌ Authentication error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _save_oauth(self, oauth_data, ytmusic_instance):
        """Save OAuth configuration to S3"""
        try:
            # Get the headers/auth from ytmusic instance
            # ytmusicapi handles token storage internally
            auth_data = {
                'oauth_config': oauth_data,
                'created_at': time.time()
            }

            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key='tokens/youtube_oauth.json',
                Body=json.dumps(auth_data, indent=2),
                ServerSideEncryption='AES256',
                ContentType='application/json'
            )
            print(f"✅ OAuth config saved to s3://{self.s3_bucket}/tokens/youtube_oauth.json")
        except Exception as e:
            print(f"❌ Failed to save OAuth config to S3: {e}")
            raise

    def get_client(self):
        """
        Get authenticated YTMusic client
        Returns YTMusic instance or None if not authenticated
        """
        try:
            # Load OAuth config from S3
            oauth_data = self._load_oauth()

            if not oauth_data:
                return None

            # Get the nested oauth_config
            config = oauth_data.get('oauth_config')
            if not config:
                print("❌ No oauth_config found in saved data")
                return None

            # Get the saved token
            token_data = config.get('token')
            if not token_data:
                print("❌ No token found in saved OAuth data")
                return None

            # Get client credentials
            client_id = config.get('client_id')
            client_secret = config.get('client_secret')

            if not client_id or not client_secret:
                print("❌ Missing client credentials in saved data")
                return None

            # Create OAuth credentials
            oauth_credentials = OAuthCredentials(
                client_id=client_id,
                client_secret=client_secret
            )

            # Create YTMusic client with the saved token and credentials
            # ytmusicapi will handle token refresh automatically
            ytmusic = YTMusic(token_data, oauth_credentials=oauth_credentials)

            return ytmusic

        except Exception as e:
            print(f"❌ Error creating YouTube Music client: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _load_oauth(self):
        """Load OAuth configuration from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key='tokens/youtube_oauth.json'
            )
            oauth_data = json.loads(response['Body'].read())
            return oauth_data
        except self.s3_client.exceptions.NoSuchKey:
            print(f"❌ No OAuth config found in S3. Please run 'songbird auth youtube' first")
            return None
        except Exception as e:
            print(f"❌ Failed to load OAuth config from S3: {e}")
            return None

    def is_authenticated(self):
        """Check if user is authenticated with YouTube Music"""
        client = self.get_client()
        if not client:
            return False

        try:
            # Try to make a simple API call to verify authentication
            client.get_library_playlists(limit=1)
            return True
        except Exception:
            return False

    def get_token_info(self, debug=False):
        """
        Get information about current OAuth status

        Args:
            debug: If True, include detailed error information

        Returns:
            Dict with OAuth status information
        """
        oauth_data = self._load_oauth()

        if not oauth_data:
            return {
                'exists': False,
                'valid': False,
                'message': 'No OAuth config found in S3'
            }

        try:
            created_at = oauth_data.get('created_at', 0)

            # Validate token structure (no API call needed)
            config = oauth_data.get('oauth_config', {})
            token_data = config.get('token', {})

            has_required_fields = all([
                config.get('client_id'),
                config.get('client_secret'),
                token_data.get('access_token'),
                token_data.get('refresh_token')
            ])

            # Check if token structure is valid
            # ytmusicapi's RefreshingToken will handle token refresh automatically
            result = {
                'exists': True,
                'valid': has_required_fields,
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(created_at)),
                'message': 'OAuth configured - ytmusicapi handles token refresh automatically'
            }

            # Add token expiry information if available
            if 'expires_at' in token_data:
                expires_at = token_data['expires_at']
                current_time = time.time()
                is_expired = current_time >= expires_at

                result['expires_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expires_at))
                result['is_expired'] = is_expired

                if is_expired:
                    result['message'] = 'OAuth token expired but will auto-refresh on first use'
                else:
                    time_remaining = expires_at - current_time
                    result['time_remaining_minutes'] = time_remaining / 60

            if debug:
                result['debug_info'] = {
                    'has_oauth_config': 'oauth_config' in oauth_data,
                    'has_token': 'token' in config,
                    'has_client_id': bool(config.get('client_id')),
                    'has_client_secret': bool(config.get('client_secret')),
                    'has_access_token': bool(token_data.get('access_token')),
                    'has_refresh_token': bool(token_data.get('refresh_token')),
                    'token_keys': list(token_data.keys()) if token_data else [],
                    'config_keys': list(config.keys()) if config else [],
                    'oauth_data_keys': list(oauth_data.keys())
                }

            return result

        except Exception as e:
            result = {
                'exists': True,
                'valid': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'message': 'Error reading OAuth data'
            }
            if debug:
                import traceback
                result['debug_info'] = {
                    'traceback': traceback.format_exc(),
                    'oauth_data_keys': list(oauth_data.keys()) if oauth_data else None
                }
            return result

    def display_token_info(self, debug=False):
        """
        Display token information to the console

        Args:
            debug: If True, show detailed debugging information
        """
        youtube_info = self.get_token_info(debug=debug)

        if not youtube_info.get('exists'):
            print("  Status: No token found")
            print("  Run 'songbird auth youtube' to authenticate")
        elif not youtube_info.get('valid'):
            print(f"  Status: Invalid")
            print(f"  Message: {youtube_info.get('message', 'Unknown error')}")
            if 'error' in youtube_info:
                print(f"  Error: {youtube_info['error']}")
            if 'error_type' in youtube_info:
                print(f"  Error type: {youtube_info['error_type']}")
            if debug and 'debug_info' in youtube_info:
                print("\n  Debug Info:")
                print(json.dumps(youtube_info['debug_info'], indent=4))
        else:
            # Token exists and is valid
            is_expired = youtube_info.get('is_expired', False)
            print(f"  Status: {'Ready (token will auto-refresh)' if is_expired else 'Active'}")
            print(f"  Message: {youtube_info.get('message', 'Active')}")
            print(f"  Created at: {youtube_info.get('created_at', 'Unknown')}")

            if 'expires_at' in youtube_info:
                print(f"  Expires at: {youtube_info['expires_at']}")

            if not is_expired and 'time_remaining_minutes' in youtube_info:
                print(f"  Time remaining: {youtube_info['time_remaining_minutes']:.1f} minutes")

            if debug and 'debug_info' in youtube_info:
                print("\n  Debug Info:")
                print(json.dumps(youtube_info['debug_info'], indent=4))

if __name__ == "__main__":
    try:
        debugging = YouTubeAuth()
        output = debugging.get_token_info()  # Added parentheses to call the method

        print("\n=== YouTube Auth Token Info ===")
        print(json.dumps(output, indent=2))
        print("================================\n")
    except Exception as e:
        print(f"\n❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()