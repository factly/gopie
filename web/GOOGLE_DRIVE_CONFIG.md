# Google Drive Upload Configuration

This document explains how to configure Google Drive upload functionality in the GoPie web application.

## Overview

The unified uploader component supports Google Drive file selection through the Uppy Dashboard with the Google Drive plugin. This requires proper OAuth configuration on both the client and server sides.

## Client-Side Configuration

The web application is already configured to use Google Drive through the `UnifiedUploader` component with these environment variables:

- `NEXT_PUBLIC_COMPANION_URL`: URL of the Companion server (e.g., https://companion-gopie.factly.dev/)
- `COMPANION_GOOGLE_KEY` and `COMPANION_GOOGLE_SECRET`: Available in the environment files

## Server-Side Configuration (Required)

The Google Drive integration requires server-side OAuth configuration on the Companion server. The following steps must be completed by the server administrator:

### 1. Google Cloud Console Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API for your project
4. Go to "Credentials" > "Create Credentials" > "OAuth 2.0 Client IDs"
5. Configure the OAuth consent screen if not already done
6. Set up the OAuth 2.0 client:
   - Application type: Web application
   - Name: GoPie File Uploader (or similar)
   - Authorized redirect URIs: Add your Companion server URL + `/drive/redirect`
     - Example: `https://companion-gopie.factly.dev/drive/redirect`

### 2. Environment Variables

The Companion server needs these environment variables:

```bash
COMPANION_GOOGLE_KEY=your_google_client_id
COMPANION_GOOGLE_SECRET=your_google_client_secret
```

These should match the values from your Google Cloud Console OAuth 2.0 client.

### 3. Companion Server Configuration

Ensure your Companion server is configured with Google Drive support:

```javascript
const uppy = require('@uppy/companion');

const options = {
  providerOptions: {
    googledrive: {
      key: process.env.COMPANION_GOOGLE_KEY,
      secret: process.env.COMPANION_GOOGLE_SECRET,
    },
  },
  server: {
    host: 'your-companion-server-host',
    protocol: 'https',
  },
};

app.use(uppy.app(options));
```

## Testing the Configuration

1. Navigate to the dataset upload page in the web application
2. Click on the "Google Drive" tab in the unified uploader
3. Click "Connect to Google Drive"
4. You should be redirected to Google's OAuth consent screen
5. After authorizing, you should be able to browse and select files from Google Drive

## Troubleshooting

### "Missing required parameter: client_id"

This error indicates that the Companion server doesn't have the `COMPANION_GOOGLE_KEY` environment variable properly set. Verify:

1. The environment variable is set on the Companion server
2. The server has been restarted after setting the variable
3. The client ID matches exactly what's in Google Cloud Console

### "Error 400: redirect_uri_mismatch"

This error means the redirect URI isn't properly configured:

1. Check the redirect URI in Google Cloud Console
2. Ensure it matches your Companion server URL + `/drive/redirect`
3. Make sure there are no trailing slashes or typos

### Files Not Uploading

If files can be selected but don't upload:

1. Check that the S3/storage configuration is working
2. Verify the Companion server can write to your storage backend
3. Check the browser network tab for any failed requests

## Security Considerations

1. Keep your Google OAuth credentials secure and never commit them to version control
2. Use HTTPS for both your web application and Companion server in production
3. Regularly rotate your OAuth credentials
4. Monitor Google Cloud Console for any unusual activity

## References

- [Uppy Google Drive Plugin Documentation](https://uppy.io/docs/google-drive/)
- [Uppy Companion Documentation](https://uppy.io/docs/companion/)
- [Google Drive API Documentation](https://developers.google.com/drive/api)