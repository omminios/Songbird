# Google OAuth Setup for YouTube Music

This guide explains how to set up and handle Google OAuth authentication for Songbird, including dealing with the "unverified app" warning.

## Understanding the "Unverified App" Warning

When you authenticate with YouTube Music, you'll see a warning from Google that says:

> **"Google hasn't verified this app"**

This is completely normal and expected for apps in development. Here's why:

### Why This Happens

1. **Your App is in Development**: Songbird uses your own Google OAuth credentials
2. **Not Publicly Published**: The app hasn't been submitted to Google for verification
3. **Personal Use**: You're the developer and the user - it's YOUR app
4. **OAuth Scopes**: The app requests access to your YouTube Music data

### Is This Safe?

**Yes, it's completely safe** because:
- You created the OAuth credentials yourself in Google Cloud Console
- The app is running locally on your machine
- You're authorizing YOUR OWN application
- The credentials are under YOUR control
- No third party has access to your credentials

## How to Bypass the Warning

When you see the "Google hasn't verified this app" screen:

### Step 1: Click "Advanced"
Look for a small "Advanced" link at the bottom of the warning page. It might also say "Show Advanced".

### Step 2: Click "Go to Songbird (unsafe)"
After clicking Advanced, you'll see a link that says:
- "Go to Songbird (unsafe)" or
- "Continue to Songbird (unsafe)"

Click this link to proceed.

### Step 3: Grant Permissions
After bypassing the warning, you'll see the standard OAuth consent screen asking for permissions. Click "Allow" or "Grant Access".

## Making the App "Verified" (Optional)

If you want to remove the warning permanently, you have two options:

### Option 1: Add Test Users (Easiest)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** → **OAuth consent screen**
3. Scroll down to **Test users**
4. Click **ADD USERS**
5. Add your Google email address
6. Click **SAVE**

Now when you authenticate with that email, you won't see the warning.

### Option 2: Publish the App (For Production)

If you want to share Songbird with others or use it publicly:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** → **OAuth consent screen**
3. Fill out all required information:
   - App name
   - User support email
   - Developer contact information
   - Privacy policy (if required)
   - Terms of service (if required)
4. Click **SUBMIT FOR VERIFICATION**
5. Wait for Google to review your app (can take several days to weeks)

**Note**: For personal use, publishing is NOT necessary. Just use the "Advanced" bypass.

## OAuth Credentials Setup

### 1. Create OAuth Client ID

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Enable **YouTube Data API v3**:
   - Go to **APIs & Services** → **Library**
   - Search for "YouTube Data API v3"
   - Click **ENABLE**
4. Create OAuth credentials:
   - Go to **APIs & Services** → **Credentials**
   - Click **CREATE CREDENTIALS** → **OAuth client ID**
   - Select **TVs and Limited Input devices**
   - Name it "Songbird"
   - Click **CREATE**
5. Copy the **Client ID** and **Client Secret**

### 2. Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Choose **External** (unless you have a Google Workspace)
3. Fill in required fields:
   - App name: "Songbird"
   - User support email: Your email
   - Developer contact: Your email
4. Add scopes:
   - Click **ADD OR REMOVE SCOPES**
   - Add `https://www.googleapis.com/auth/youtube`
   - Click **UPDATE**
5. Click **SAVE AND CONTINUE**

### 3. Add to .env File

Add your credentials to `.env`:

```env
YOUTUBE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=your-client-secret-here
```

## Troubleshooting

### "Access blocked: This app's request is invalid"

**Solution**: Make sure you selected "TVs and Limited Input devices" when creating the OAuth client ID, not "Desktop app" or "Web application".

### "The OAuth client was not found"

**Solution**: Double-check your `YOUTUBE_CLIENT_ID` and `YOUTUBE_CLIENT_SECRET` in the `.env` file.

### "This app isn't verified" with no "Advanced" option

**Solution**:
1. Try a different browser
2. Make sure you're signed in to Google
3. Add yourself as a test user in Google Cloud Console

### Token expires quickly

**Solution**: This is normal. ytmusicapi automatically refreshes tokens using the refresh token. You only need to authenticate once.

## Security Best Practices

1. **Never commit credentials**: Keep `.env` in `.gitignore`
2. **Use environment variables**: Don't hardcode credentials in code
3. **Restrict OAuth scopes**: Only request permissions you need
4. **Store tokens securely**: Songbird uses AWS S3 with encryption
5. **Regenerate if compromised**: If credentials leak, regenerate them in Google Cloud Console

## Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [YouTube Data API v3](https://developers.google.com/youtube/v3)
- [ytmusicapi Documentation](https://ytmusicapi.readthedocs.io/)
