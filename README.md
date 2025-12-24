# GoPie

Look up for the documentation on the product site: https://gopie.ai/docs

## Getting Started

### Setup

**1. Prepare Environment Variables**

Copy the example configuration files:

```bash
cp config-auth.env.example config-auth.env
cp config-noauth.env.example config-noauth.env
```

**2. Start the Application**

**With Authentication:**

**1. Configure Host**

Add the following entry to your `/etc/hosts` file (required for local development):
```
127.0.0.1 127.0.0.1.zitadel.local
```

**2. Start the Application**
```bash
docker-compose --env-file config-auth.env -f docker-compose-auth.yaml up
```

**3. Zitadel Configuration**

After starting the application for the first time, you need to configure Zitadel.
*   **Login:** Access the Zitadel Console (e.g., `http://127.0.0.1.zitadel.local:80/ui/console`). Use the credentials defined in `config-auth.env` (Initial user details: `ZITADEL_FIRSTINSTANCE_...`) and reset the password.
*   **Note:** Do not modify or delete the initial Zitadel project.

**Step A: Create Project**
1.  Create a new Project.
2.  Copy the **Project ID** and update `GOPIE_ZITADEL_PROJECT_ID` and `ZITADEL_PROJECT_ID` in your `config-auth.env`.

**Step B: Create Applications**
Open the new project and add two applications:

*   **Server (API):**
    1.  Create an application of type **API**.
    2.  Select authentication method: **Private Key JWT**.
    3.  Once created, generate a new **JSON** key file.
    4.  Save this file as `zitadel_key.json` in the `server` root directory.

*   **Web (Frontend):**
    1.  Create an application of type **Web**.
    2.  Select authentication method: **PKCE**.
    3.  Add Redirect URI: `http://localhost:3000/api/oauth/callback`
    4.  Copy the **Client ID** and update `ZITADEL_CLIENT_ID` in your `config-auth.env`.

**Step C: Service User & Permissions**
1.  **Create Service User:**
    *   Go to the **Users** page and select the **Service Users** tab.
    *   Create a user with **Access Token Type** set to **Bearer**.
2.  **Generate PAT:**
    *   On the user detail page, generate a **Personal Access Token**.
    *   Update `ZITADEL_PAT` in your `config-auth.env`.
3.  **Grant Permissions:**
    *   Open **Default Settings** (Instance Settings) from the top right corner.
    *   Click the **+** icon (top right) to add a manager.
    *   Select the **Service User** created above.
    *   Add the manager role **IAM OWNER** (or "I AM LOGIN CLIENT").

*Restart the application after updating the configuration.*

**Without Authentication:**
```bash
docker-compose --env-file config-noauth.env -f docker-compose-noauth.yaml up
```
