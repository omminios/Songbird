"""
Apple Music API authentication handler using JWT tokens
"""
import os
import json
import time
import jwt
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()


class AppleAuth:
    """Handles Apple Music API authentication using JWT tokens"""

    def __init__(self):
        self.team_id = os.getenv('APPLE_TEAM_ID')
        self.key_id = os.getenv('APPLE_KEY_ID')
        self.private_key_path = os.getenv('APPLE_PRIVATE_KEY_PATH')

        if not all([self.team_id, self.key_id, self.private_key_path]):
            raise ValueError(
                "Missing Apple Music credentials. Please set:\n"
                "- APPLE_TEAM_ID\n"
                "- APPLE_KEY_ID\n"
                "- APPLE_PRIVATE_KEY_PATH (path to .p8 file)"
            )

    def authenticate(self):
        """
        Generate and validate JWT token for Apple Music API
        Returns True if successful, False otherwise
        """
        try:
            # Generate JWT token
            token = self._generate_jwt_token()
            if not token:
                return False

            # Validate token by making a test API call
            if self._validate_token(token):
                self._save_token(token)
                return True
            else:
                return False

        except Exception as e:
            print(f"Apple Music authentication error: {e}")
            return False

    def _generate_jwt_token(self):
        """Generate JWT token for Apple Music API"""
        try:
            # Read private key
            with open(self.private_key_path, 'r') as f:
                private_key = f.read()

            # JWT payload
            now = datetime.now(timezone.utc)
            payload = {
                'iss': self.team_id,
                'iat': int(now.timestamp()),
                'exp': int((now + timedelta(hours=6)).timestamp()),  # Token expires in 6 hours
                'aud': 'appstoreconnect-v1'
            }

            # JWT headers
            headers = {
                'kid': self.key_id,
                'alg': 'ES256'
            }

            # Generate token
            token = jwt.encode(
                payload,
                private_key,
                algorithm='ES256',
                headers=headers
            )

            return token

        except Exception as e:
            print(f"Failed to generate JWT token: {e}")
            return None

    def _validate_token(self, token):
        """Validate token by making a test API call"""
        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Music-User-Token': ''  # Will be empty for server-to-server calls
            }

            # Make a simple API call to validate token
            response = requests.get(
                'https://api.music.apple.com/v1/catalog/us/songs/203709340',  # Test song
                headers=headers
            )

            return response.status_code == 200

        except Exception as e:
            print(f"Token validation failed: {e}")
            return False

    def _save_token(self, token):
        """Save JWT token to secure storage"""
        token_data = {
            'token': token,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'expires_at': (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
        }

        tokens_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'apple_tokens.json')
        os.makedirs(os.path.dirname(tokens_file), exist_ok=True)

        with open(tokens_file, 'w') as f:
            json.dump(token_data, f, indent=2)

        print(f"Apple Music token saved to {tokens_file}")

    def get_valid_token(self):
        """Get a valid JWT token, regenerating if necessary"""
        tokens_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'apple_tokens.json')

        # Check if token file exists and is still valid
        if os.path.exists(tokens_file):
            try:
                with open(tokens_file, 'r') as f:
                    token_data = json.load(f)

                # Check if token is still valid (not expired)
                if self._is_token_valid(token_data):
                    return token_data['token']

            except Exception as e:
                print(f"Error reading token file: {e}")

        # Token doesn't exist or is expired, generate new one
        new_token = self._generate_jwt_token()
        if new_token:
            self._save_token(new_token)
            return new_token

        return None

    def _is_token_valid(self, token_data):
        """
        Check if JWT token is still valid

        Args:
            token_data: Token data dict with 'expires_at' field

        Returns:
            True if token is valid, False otherwise
        """
        try:
            if 'expires_at' not in token_data:
                return False

            expires_at = datetime.fromisoformat(token_data['expires_at'])
            buffer = timedelta(minutes=10)  # 10 minute buffer before expiry

            # Token is valid if current time + buffer < expiry time
            return datetime.now(timezone.utc) < (expires_at - buffer)

        except Exception as e:
            print(f"Error checking token validity: {e}")
            return False

    def refresh_token(self):
        """
        Manually refresh the JWT token
        Useful for testing or forcing a refresh

        Returns:
            New token or None if generation failed
        """
        new_token = self._generate_jwt_token()
        if new_token:
            self._save_token(new_token)
            print("Apple Music token refreshed successfully")
            return new_token
        else:
            print("Failed to refresh Apple Music token")
            return None

    def get_token_info(self):
        """
        Get information about current token status

        Returns:
            Dict with token status information
        """
        tokens_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'apple_tokens.json')

        if not os.path.exists(tokens_file):
            return {
                'exists': False,
                'valid': False,
                'message': 'No token file found'
            }

        try:
            with open(tokens_file, 'r') as f:
                token_data = json.load(f)

            expires_at = datetime.fromisoformat(token_data['expires_at'])
            created_at = datetime.fromisoformat(token_data['created_at'])
            now = datetime.now(timezone.utc)

            is_valid = self._is_token_valid(token_data)
            time_remaining = (expires_at - now).total_seconds()

            return {
                'exists': True,
                'valid': is_valid,
                'created_at': created_at.isoformat(),
                'expires_at': expires_at.isoformat(),
                'time_remaining_seconds': max(0, time_remaining),
                'time_remaining_hours': max(0, time_remaining / 3600)
            }

        except Exception as e:
            return {
                'exists': True,
                'valid': False,
                'error': str(e),
                'message': 'Error reading token data'
            }

    def is_authenticated(self):
        """Check if we can generate valid tokens"""
        try:
            token = self.get_valid_token()
            return token is not None
        except Exception:
            return False

    def get_user_token_instructions(self):
        """
        Return instructions for getting user token
        Note: Apple Music requires user tokens for playlist access
        """
        return """
        To access Apple Music playlists, you need a Music User Token:

        1. Set up MusicKit JS in a web page
        2. User must authorize your app
        3. Get the user token from MusicKit.getInstance().musicUserToken

        For development, you can use Apple's MusicKit JS documentation:
        https://developer.apple.com/documentation/musickit/getting_keys_and_creating_tokens
        """