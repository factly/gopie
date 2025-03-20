# Gopie

### Pre-requisites

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
