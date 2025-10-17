"""
Spotify OAuth 2.0 authentication handler
"""
import boto3
import os
import webbrowser
import base64
import json
from urllib.parse import urlencode, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import requests
from dotenv import load_dotenv

load_dotenv()


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP server to handle OAuth callback"""

    def do_GET(self):
        if self.path.startswith('/callback'):
            # Extract authorization code from callback URL
            query = self.path.split('?', 1)[1] if '?' in self.path else ''
            params = parse_qs(query)

            if 'code' in params:
                self.server.auth_code = params['code'][0]
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'''
                    <html><body>
                    <h1>Authentication Successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                    </body></html>
                ''')
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'''
                    <html><body>
                    <h1>Authentication Failed</h1>
                    <p>No authorization code received.</p>
                    </body></html>
                ''')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress server logs
        pass


class SpotifyAuth:
    """Handles Spotify OAuth 2.0 authentication flow"""

    def __init__(self):
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = 'http://127.0.0.1:8888/callback'
        self.scope = 'playlist-read-private playlist-modify-private playlist-modify-public'

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
                "Missing Spotify credentials. Please set SPOTIFY_CLIENT_ID and "
                "SPOTIFY_CLIENT_SECRET environment variables."
            )

    def authenticate(self):
        """
        Perform OAuth 2.0 authentication flow
        Runs locally with browser interaction, saves tokens directly to S3
        Returns True if successful, False otherwise
        """
        try:
            # Step 1: Get authorization code
            auth_code = self._get_authorization_code()
            if not auth_code:
                return False

            # Step 2: Exchange code for tokens
            tokens = self._exchange_code_for_tokens(auth_code)
            if not tokens:
                return False

            # Step 3: Save tokens to S3
            self._save_tokens(tokens)
            return True

        except Exception as e:
            print(f"Authentication error: {e}")
            return False

    def _get_authorization_code(self):
        """Start OAuth flow and get authorization code"""
        # Build authorization URL
        auth_params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': self.scope,
            'show_dialog': 'true'
        }

        auth_url = f"https://accounts.spotify.com/authorize?{urlencode(auth_params)}"

        # Start local server for callback
        server = HTTPServer(('127.0.0.1', 8888), CallbackHandler)
        server.auth_code = None
        server.timeout = 120  # 2 minute timeout

        # Start server in separate thread
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        print(f"Opening browser for Spotify authentication...")
        print(f"If browser doesn't open, visit: {auth_url}")

        # Open browser
        webbrowser.open(auth_url)

        # Wait for callback
        start_time = time.time()
        while server.auth_code is None and (time.time() - start_time) < 120:
            time.sleep(1)

        server.shutdown()
        server.server_close()

        return server.auth_code

    def _exchange_code_for_tokens(self, auth_code):
        """Exchange authorization code for access and refresh tokens"""
        # Prepare token request
        token_data = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': self.redirect_uri
        }

        # Create authorization header
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        # Make token request
        response = requests.post(
            'https://accounts.spotify.com/api/token',
            data=token_data,
            headers=headers
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Token exchange failed: {response.status_code} - {response.text}")
            return None

    def _save_tokens(self, tokens):
        """Save tokens to S3 with timestamp"""
        # Add timestamp for expiry tracking
        token_data = {
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'expires_in': tokens['expires_in'],  # Seconds until expiry (usually 3600)
            'token_type': tokens.get('token_type', 'Bearer'),
            'scope': tokens.get('scope', self.scope),
            'obtained_at': time.time()  # Unix timestamp when token was obtained
        }

        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key='tokens/spotify_tokens.json',
                Body=json.dumps(token_data, indent=2),
                ServerSideEncryption='AES256',
                ContentType='application/json'
            )
            print(f"✅ Tokens saved to s3://{self.s3_bucket}/tokens/spotify_tokens.json")
        except Exception as e:
            print(f"❌ Failed to save tokens to S3: {e}")
            raise

    def get_valid_token(self):
        """Get a valid access token, refreshing if necessary"""
        # Load tokens from S3
        token_data = self._load_tokens()

        if not token_data:
            return None

        # Check if token is expired
        if self._is_token_expired(token_data):
            # Token expired, refresh it
            new_tokens = self._refresh_access_token(token_data['refresh_token'])
            if new_tokens:
                self._save_tokens(new_tokens)
                return new_tokens['access_token']
            else:
                # Refresh failed, user needs to re-authenticate
                print("Token refresh failed. Please re-authenticate with 'songbird auth spotify'")
                return None

        return token_data.get('access_token')

    def _load_tokens(self):
        """Load tokens from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key='tokens/spotify_tokens.json'
            )
            token_data = json.loads(response['Body'].read())
            return token_data
        except self.s3_client.exceptions.NoSuchKey:
            print(f"❌ No tokens found in S3. Please run 'songbird auth spotify' first")
            return None
        except Exception as e:
            print(f"❌ Failed to load tokens from S3: {e}")
            return None

    def _is_token_expired(self, token_data):
        """Check if access token is expired or will expire soon"""
        if 'obtained_at' not in token_data or 'expires_in' not in token_data:
            # Old token format, assume expired
            return True

        obtained_at = token_data['obtained_at']
        expires_in = token_data['expires_in']
        current_time = time.time()

        # Calculate when token expires
        expires_at = obtained_at + expires_in

        # Add 5 minute buffer (refresh if expiring in next 5 minutes)
        buffer_seconds = 300

        return (current_time + buffer_seconds) >= expires_at

    def _refresh_access_token(self, refresh_token):
        """
        Refresh the access token using refresh token

        Args:
            refresh_token: The refresh token from initial authentication

        Returns:
            New token data or None if refresh failed
        """
        # Prepare refresh request
        token_data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }

        # Create authorization header
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        try:
            # Make refresh request
            response = requests.post(
                'https://accounts.spotify.com/api/token',
                data=token_data,
                headers=headers
            )

            if response.status_code == 200:
                new_tokens = response.json()

                # Spotify doesn't always return a new refresh token
                # If not included, keep the old one
                if 'refresh_token' not in new_tokens:
                    new_tokens['refresh_token'] = refresh_token

                return new_tokens
            else:
                print(f"Token refresh failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"Token refresh error: {e}")
            return None


    def get_token_info(self, debug=False):
        """
        Get information about current token status

        Args:
            debug: If True, include detailed error information

        Returns:
            Dict with token status information
        """
        token_data = self._load_tokens()

        if not token_data:
            return {
                'exists': False,
                'valid': False,
                'message': 'No tokens found in S3'
            }

        try:
            if 'obtained_at' not in token_data or 'expires_in' not in token_data:
                result = {
                    'exists': True,
                    'valid': False,
                    'message': 'Old token format - please re-authenticate'
                }
                if debug:
                    result['debug_info'] = {
                        'has_obtained_at': 'obtained_at' in token_data,
                        'has_expires_in': 'expires_in' in token_data,
                        'token_keys': list(token_data.keys())
                    }
                return result

            obtained_at = token_data['obtained_at']
            expires_in = token_data['expires_in']
            expires_at = obtained_at + expires_in
            current_time = time.time()

            is_expired = self._is_token_expired(token_data)
            has_refresh_token = 'refresh_token' in token_data
            time_remaining = max(0, expires_at - current_time)

            # Token is considered "valid" if it has a refresh token (even if access token expired)
            # The system will auto-refresh when needed
            result = {
                'exists': True,
                'valid': has_refresh_token,  # Valid if we can refresh
                'obtained_at': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(obtained_at)),
                'expires_at': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expires_at)),
                'time_remaining_seconds': time_remaining,
                'time_remaining_minutes': time_remaining / 60,
                'has_refresh_token': has_refresh_token,
                'is_expired': is_expired
            }

            # Add helpful message based on state
            if not has_refresh_token:
                result['message'] = 'No refresh token - please re-authenticate'
            elif is_expired:
                result['message'] = 'Access token expired but will auto-refresh on first use'
            else:
                result['message'] = 'Token is active'

            if debug:
                result['debug_info'] = {
                    'current_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time)),
                    'is_expired': is_expired,
                    'buffer_seconds': 300,
                    'raw_obtained_at': obtained_at,
                    'raw_expires_in': expires_in
                }

            return result

        except Exception as e:
            result = {
                'exists': True,
                'valid': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'message': 'Error reading token data'
            }
            if debug:
                import traceback
                result['debug_info'] = {
                    'traceback': traceback.format_exc(),
                    'token_data_keys': list(token_data.keys()) if token_data else None
                }
            return result

    def is_authenticated(self):
        """Check if user is authenticated"""
        return self.get_valid_token() is not None

    def display_token_info(self, debug=False):
        """
        Display token information to the console

        Args:
            debug: If True, show detailed debugging information
        """
        import json

        spotify_info = self.get_token_info(debug=debug)

        if not spotify_info.get('exists'):
            print("  Status: No token found")
            print("  Run 'songbird auth spotify' to authenticate")
        elif not spotify_info.get('valid'):
            print(f"  Status: Invalid")
            print(f"  Message: {spotify_info.get('message', 'Unknown error')}")
            if 'error' in spotify_info:
                print(f"  Error: {spotify_info['error']}")
            if 'error_type' in spotify_info:
                print(f"  Error type: {spotify_info['error_type']}")
            if debug and 'debug_info' in spotify_info:
                print("\n  Debug Info:")
                print(json.dumps(spotify_info['debug_info'], indent=4))
        else:
            # Token exists and is valid
            is_expired = spotify_info.get('is_expired', False)
            print(f"  Status: {'Ready (token will auto-refresh)' if is_expired else 'Active'}")
            print(f"  Message: {spotify_info.get('message', 'Token is active')}")
            print(f"  Obtained at: {spotify_info.get('obtained_at', 'Unknown')}")
            print(f"  Expires at: {spotify_info.get('expires_at', 'Unknown')}")

            if not is_expired:
                print(f"  Time remaining: {spotify_info.get('time_remaining_minutes', 0):.1f} minutes")

            print(f"  Has refresh token: {'Yes' if spotify_info.get('has_refresh_token') else 'No'}")

            if debug and 'debug_info' in spotify_info:
                print("\n  Debug Info:")
                print(json.dumps(spotify_info['debug_info'], indent=4))