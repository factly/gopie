# Gopie

## Pre-requisites to run GoPie using Docker Compose
- Add `zitadel/key.json`
- Add `.env` in the root directory based on `.env.example`

### Things to Note
- Currently it doesn't support hot reload when starting using Docker Compose
- It creates a directory named `volumes` in the root directory to persist the data for services like Postgres, Redis etc

--- Following setup with running Zitadel locally is not working as expected currently ---

# Zitadel Setup Guide

Set GOPIE_ZITADEL_DOMAIN = gopie.xyz.com (for production server env), REACT_APP_ZITADEL_AUTHORITY = https://gopie.xyz.com (for production env).

## Instance Setup

1. Add organization name, user email, and password for the first user in the provided file (zitadel/init-steps.yml).
2. Use these credentials to log into the Zitadel console.
3. Complete the project setup and obtain necessary secrets.

## Project Configuration

Access the Zitadel console and create a project named "Gopie" (or a name of your choice). Navigate to the project detail page. Then add project id to REACT_APP_ZITADEL_PROJECT_ID (for gopie web env) and GOPIE_ZITADEL_PROJECT_ID (for gopie server env).

**Note:** Do not delete or update the "zitadel" project.

### 1. project general Settings

- **Brand settings**: Choose any option of your preference (adjust brand settings accordingly)
- **Assert Roles on Authentication**: Checked
- **Check authorization on Authentication**: Checked
- **Check for Project on Authentication**: Checked

### 2. Applications

Create following applications in project:

#### 2.1 Server

1. Create application
   - Name: Admin Server (or your preferred name)
   - Application Type: API
   - Authentication Method: Private Key JWT
   - Copy the client id and set it in REACT_APP_ZITADEL_CLIENT_ID (for web env)
2. Configuration
   - Navigate to the configuration tab and generate a key
   - Store the generated file as `zitadel_key.json` in the server root folder. While using gopie-installation scripts store it as zitadel-secret.json in the root folder.

#### 2.2 Studio

1. Create application
   - Name: Studio (or your preferred name)
   - Application Type: Web
   - Authentication Method: PKCE
   - Redirect settings:
     - Select development mode while in development
     - Add redirect URIs: (on entering link in the input then click on add icon and save settings)
       - Local: `http://localhost:3000/redirect`
       - Production: `https://gopie.xyz.com/redirect`
     - Add post-logout URIs:
       - Local: `http://localhost:3000`
       - Production: `https://gopie.xyz.com`
2. Configuration
   - Store the client ID in `REACT_APP_ZITADEL_CLIENT_ID` in gopie web env

### 3. Roles

Create the following roles in project:

1. Admin

   - Key: admin
   - Display Name: Administrator
   - Group: Administrator

2. Member
   - Key: member
   - Display Name: Member
   - Group: Member

### 4. Service Account

1. From the Users page, select the Service tab
2. Create a new service account:
   - User Name: Service account (or your preferred name)
   - Name: Service account (or your preferred name)
   - Access Token Type: Bearer
3. Open the user detail page, select the Personal Access Tokens tab
4. Create a new token and set this value in the `gopie_zitadel_personal_access_token` in gopie server environment variables.

## Adding Users

To add other users, select the Users tab at the top and add users from that page.

## Important Post-User Addition Steps

1. Go to the Authorizations page (select Authorizations tab from the top)
2. Select the user and project, then assign the created role (either admin or member)
3. Navigate to the Organizations detail page by clicking the Organization tab in the top bar
4. Click the plus icon in the top right to add membership
   - For users assigned as members, provide the `Org User Self Manager` grant
   - For service user account, provide the `Org User Self Manager` grant
   - For admins, provide the `Org User Manager` grant

# Sentry Error Tracking Setup

Sentry is integrated into the web application for error tracking and performance monitoring.

## Prerequisites

1. Create a Sentry account at [sentry.io](https://sentry.io)
2. Create a new project for your web application
3. Obtain the following from your Sentry project:
   - DSN (Data Source Name)
   - Organization slug
   - Project slug
   - Auth token (for source maps and releases)

## Environment Configuration

Add the following environment variables to `web/.env.local`:

```env
# Sentry Configuration
NEXT_PUBLIC_SENTRY_DSN=your_sentry_dsn_here
SENTRY_ORG=your_organization_slug
SENTRY_PROJECT_WEB=your_project_slug
SENTRY_AUTH_TOKEN=your_auth_token_here
```

**Note:** The `NEXT_PUBLIC_SENTRY_DSN` must be prefixed with `NEXT_PUBLIC_` to be available in the browser.

## Features Enabled

- **Error Tracking**: Automatic capture of JavaScript errors and unhandled promise rejections
- **Performance Monitoring**: Transaction tracing for API calls and page loads
- **Session Replay**: Records user sessions for debugging (enabled in development and on errors in production)
- **Source Maps**: Uploaded automatically for better error stack traces
- **Release Tracking**: Integrates with your deployment process

## Testing the Integration

1. Start the development server:
   ```bash
   cd web
   bun run dev
   ```

2. Navigate to `/sentry-debug` in your browser

3. Test different error scenarios:
   - **Client-side errors**: Click "Test Client Error" button
   - **Server-side errors**: Click "Test Server Error" button
   - **Custom messages**: Click "Capture Message" button
   - **Context data**: Click "Test with Context" button

4. Check your Sentry dashboard to verify errors are being captured

## Configuration Details

- **Environment**: Automatically set based on `NODE_ENV`
- **Sample Rates**: 
  - Production: 10% for performance traces
  - Development: 100% for all traces
- **Debug Mode**: Enabled in development for troubleshooting
- **Error Filtering**: Common browser extension and network errors are filtered out

## Production Considerations

- Source maps are automatically uploaded and hidden in production
- Performance monitoring sample rate is reduced to 10% in production
- Session replay is limited to 10% of sessions and 100% of error sessions
- Debug logging is disabled in production
