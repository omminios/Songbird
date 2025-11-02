"""
YouTube Music Browser Cookie authentication handler
Uses browser cookies instead of OAuth for reliable YouTube Music API access
"""
import boto3
import os
import json
import time
import re
import traceback
from urllib.parse import unquote
from ytmusicapi import YTMusic
from dotenv import load_dotenv
from songbird.utils.s3_utils import validate_s3_bucket, save_json_to_s3, load_json_from_s3

load_dotenv()


class YouTubeAuth:
    """Handles YouTube Music browser cookie authentication"""

    # S3 key for storing auth data
    AUTH_KEY = 'tokens/youtube_auth.json'

    # Compiled regex patterns for cURL parsing (class-level for performance)
    HEADER_PATTERNS = [
        re.compile(r'-H\s+"([^:]+):\s*([^"]+)"', re.IGNORECASE),  # -H "header: value"
        re.compile(r"-H\s+'([^:]+):\s*([^']+)'", re.IGNORECASE),  # -H 'header: value'
        re.compile(r'--header\s+"([^:]+):\s*([^"]+)"', re.IGNORECASE),  # --header "header: value"
        re.compile(r"--header\s+'([^:]+):\s*([^']+)'", re.IGNORECASE),  # --header 'header: value'
    ]

    COOKIE_PATTERNS = [
        re.compile(r'-b\s+"([^"]+)"', re.IGNORECASE),  # -b "cookie"
        re.compile(r"-b\s+'([^']+)'", re.IGNORECASE),  # -b 'cookie'
        re.compile(r'--cookie\s+"([^"]+)"', re.IGNORECASE),  # --cookie "cookie"
        re.compile(r"--cookie\s+'([^']+)'", re.IGNORECASE),  # --cookie 'cookie'
    ]

    def __init__(self):
        # S3 configuration (always required)
        self.s3_bucket = validate_s3_bucket()
        self.s3_client = boto3.client('s3')

    def authenticate(self):
        """
        Perform browser cookie authentication for YouTube Music

        Returns True if successful, False otherwise
        """
        try:
            print("\n📺 YouTube Music Browser Authentication Setup")
            print("=" * 70)
            print("\nYouTube Music doesn't have an official OAuth API.")
            print("Instead, we'll use browser cookies from your YouTube Music session.")
            print("\nThis is a one-time setup. Cookies typically last ~1 year.")

            print("\n" + "=" * 70)
            print("STEP-BY-STEP INSTRUCTIONS")
            print("=" * 70)

            print("\n📝 Step 1: Open YouTube Music")
            print("  1. Go to: https://music.youtube.com")
            print("  2. Make sure you're logged in with your Google account")

            print("\n📝 Step 2: Open Browser Developer Tools")
            print("  - Chrome/Edge: Press F12 or Ctrl+Shift+I")
            print("  - Firefox: Press F12 or Ctrl+Shift+I")
            print("  - Safari: Enable 'Develop' menu, then press Cmd+Option+I")

            print("\n📝 Step 3: Go to Network Tab")
            print("  1. Click on the 'Network' tab in DevTools")
            print("  2. Make sure 'Preserve log' is checked")

            print("\n📝 Step 4: Trigger a Request")
            print("  1. In YouTube Music, click on your 'Library' or any playlist")
            print("  2. In the Network tab, look for a request to 'browse' or 'youtubei'")
            print("  3. Click on that request")

            print("\n📝 Step 5: Copy Request Headers")
            print("  1. In the request details, find the 'Request Headers' section")
            print("  2. Look for the full headers block (it starts with things like:")
            print("     accept: */*")
            print("     content-type: application/json")
            print("     cookie: ...")
            print("  3. Copy ALL the request headers")

            print("\n" + "=" * 70)
            print("ALTERNATIVE: Copy as cURL")
            print("=" * 70)
            print("\nIf the above is too complex, you can:")
            print("  1. Right-click on the 'browse' request in Network tab")
            print("  2. Select 'Copy' → 'Copy as cURL'")
            print("  3. Paste the entire cURL command when prompted below")

            print("\n" + "=" * 70)

            input("\n⏸️  Press Enter when you're ready to paste the headers...")

            print("\n📋 Now paste your request headers below.")
            print("Paste everything and press Ctrl+D (Linux/Mac) or Ctrl+Z then Enter (Windows) when done:")
            print("=" * 70)

            # Read multi-line input
            headers_input = []
            print("\n(Paste headers and press Ctrl+D or Ctrl+Z+Enter when done)")

            while True:
                try:
                    line = input()
                    headers_input.append(line)
                except EOFError:
                    break

            headers_text = '\n'.join(headers_input)

            # Parse headers
            auth_data = self._parse_headers(headers_text)

            if not auth_data:
                print("\n❌ Failed to parse headers. Please try again.")
                return False

            # Test the authentication
            print("\n🔄 Testing authentication...")
            ytmusic = YTMusic(auth_data)

            # Try a simple API call
            ytmusic.get_library_playlists(limit=1)
            print("✅ Authentication verified!")

            # Save to S3
            self._save_auth(auth_data)

            print("\n✅ YouTube Music authentication successful!")
            print("✅ Cookies saved to S3")
            return True

        except KeyboardInterrupt:
            print("\n\n❌ Authentication cancelled by user")
            return False
        except Exception as e:
            print(f"\n❌ Authentication error: {e}")
            traceback.print_exc()
            return False

    def _parse_headers(self, headers_text):
        """
        Parse headers from pasted text
        Supports both raw headers and cURL format
        """
        try:
            # Check if it's a cURL command
            if 'curl' in headers_text.lower() and 'music.youtube.com' in headers_text:
                return self._parse_curl(headers_text)
            else:
                return self._parse_raw_headers(headers_text)
        except Exception as e:
            print(f"❌ Error parsing headers: {e}")
            return None

    def _parse_curl(self, curl_command):
        """Parse headers from cURL command"""
        # Remove Windows line continuation characters and clean up
        curl_command = curl_command.replace('^', '').replace('\n', ' ').replace('\r', '')

        # URL decode any encoded characters
        curl_command = unquote(curl_command)

        # Extract headers from cURL using pre-compiled patterns
        headers = {}

        for pattern in self.HEADER_PATTERNS:
            matches = pattern.findall(curl_command)
            for key, value in matches:
                headers[key.lower().strip()] = value.strip()

        # Extract cookie separately using -b flag with pre-compiled patterns
        for pattern in self.COOKIE_PATTERNS:
            cookie_match = pattern.search(curl_command)
            if cookie_match:
                headers['cookie'] = cookie_match.group(1).strip()
                break

        # Convert to ytmusicapi format
        if headers:
            return self._format_headers(headers)

        return None

    def _parse_raw_headers(self, headers_text):
        """Parse raw request headers"""
        headers = {}
        lines = headers_text.strip().split('\n')

        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()

        if headers:
            return self._format_headers(headers)

        return None

    def _format_headers(self, headers):
        """Format headers for ytmusicapi"""
        # ytmusicapi expects specific headers
        formatted = {}

        # Required headers
        if 'cookie' in headers:
            formatted['cookie'] = headers['cookie']
        if 'x-goog-authuser' in headers:
            formatted['X-Goog-AuthUser'] = headers['x-goog-authuser']
        if 'authorization' in headers and 'SAPISIDHASH' in headers['authorization']:
            formatted['authorization'] = headers['authorization']
        if 'x-origin' in headers:
            formatted['X-Origin'] = headers['x-origin']

        # Must have at least cookie
        if 'cookie' not in formatted:
            raise ValueError("No cookie found in headers. Make sure to copy headers from a YouTube Music request.")

        return formatted

    def _save_auth(self, auth_data):
        """Save authentication data to S3"""
        try:
            save_data = {
                'auth_data': auth_data,
                'created_at': time.time()
            }

            save_json_to_s3(self.s3_client, self.s3_bucket, self.AUTH_KEY, save_data)
            print(f"✅ Auth data saved to s3://{self.s3_bucket}/{self.AUTH_KEY}")
        except Exception as e:
            print(f"❌ Failed to save auth data to S3: {e}")
            raise

    def get_client(self):
        """
        Get authenticated YTMusic client
        Returns YTMusic instance or None if not authenticated
        """
        try:
            # Load auth data from S3
            auth_data = self._load_auth()

            if not auth_data:
                return None

            # Get the auth headers
            headers = auth_data.get('auth_data')
            if not headers:
                print("❌ No auth headers found in saved data")
                return None

            # Create YTMusic client
            ytmusic = YTMusic(headers)

            return ytmusic

        except Exception as e:
            print(f"❌ Error creating YouTube Music client: {e}")
            traceback.print_exc()
            return None

    def _load_auth(self, silent=False):
        """Load authentication data from S3

        Args:
            silent: If True, suppress error output (useful when just checking auth info)
        """
        try:
            auth_data = load_json_from_s3(self.s3_client, self.s3_bucket, self.AUTH_KEY)
            return auth_data
        except self.s3_client.exceptions.NoSuchKey:
            if not silent:
                print(f"❌ No auth data found in S3. Please run 'songbird auth youtube' first")
            return None
        except Exception as e:
            if not silent:
                print(f"❌ Failed to load auth data from S3: {e}")
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
        Get information about current authentication status

        Args:
            debug: If True, include detailed error information

        Returns:
            Dict with authentication status information
        """
        auth_data = self._load_auth(silent=True)

        if not auth_data:
            return {
                'exists': False,
                'valid': False,
                'message': 'No authentication data found in S3'
            }

        try:
            created_at = auth_data.get('created_at', 0)

            # Check if auth data has required fields
            headers = auth_data.get('auth_data', {})
            has_cookie = 'cookie' in headers

            result = {
                'exists': True,
                'valid': has_cookie,
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(created_at)),
                'message': 'Browser authentication configured'
            }

            if debug:
                result['debug_info'] = {
                    'has_cookie': has_cookie,
                    'has_authorization': 'authorization' in headers,
                    'header_keys': list(headers.keys()) if headers else []
                }

            return result

        except Exception as e:
            result = {
                'exists': True,
                'valid': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'message': 'Error reading authentication data'
            }
            if debug:
                result['debug_info'] = {
                    'traceback': traceback.format_exc()
                }
            return result

    def display_token_info(self, debug=False):
        """
        Display authentication information to the console

        Args:
            debug: If True, show detailed debugging information
        """
        youtube_info = self.get_token_info(debug=debug)

        if not youtube_info.get('exists'):
            print("  Status: No authentication found")
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
            print(f"  Status: Active (Browser cookies)")
            print(f"  Message: {youtube_info.get('message', 'Active')}")
            print(f"  Created at: {youtube_info.get('created_at', 'Unknown')}")
            print(f"  Note: Cookies typically expire after ~1 year")

            if debug and 'debug_info' in youtube_info:
                print("\n  Debug Info:")
                print(json.dumps(youtube_info['debug_info'], indent=4))
