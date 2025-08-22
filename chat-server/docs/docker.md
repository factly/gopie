# GoPie Chat Server Documentation

Repo: https://github.com/factly/gopie

## Chat Server Docker Setup

A modular Docker Compose architecture for running the chat server with AI gateway services.

### Services

#### Core Services

- **chat-server**: port 8001
- **qdrant**: port 6333/6334

#### AI Gateways (Optional)

- **portkey-gateway**: port 8787 (profile: `portkey`)
- **litellm**: port 4000 (profile: `litellm`)

### Quick Start

#### 1. Environment Setup

Update the `.env` file with the correct values for the services.

#### 2. Basic Usage

Navigate to the main gopie directory before running docker commands:

**Start core services only:**

```bash
docker compose up -d
```

**Start with specific AI gateway:**

```bash
# With Portkey
docker compose --profile portkey up -d

# With LiteLLM
docker compose --profile litellm up -d

# With both gateways
docker compose --profile portkey --profile litellm up -d
```

#### 3. No Authentication Mode

For development or testing without authentication services, use the noauth configuration:

```bash
# Start with noauth configuration
docker compose -f docker-compose-noauth.yaml up -d

# With specific AI gateway profiles
docker compose -f docker-compose-noauth.yaml --profile portkey up -d
docker compose -f docker-compose-noauth.yaml --profile litellm up -d
```

**Note**: The noauth configuration uses `config-noauth.env` instead of `config.env` for environment variables.

### File Requirements

**For standard setup:**

- `.env` file with environment variables

**For noauth setup:**

- `config-noauth.env` file with environment variables (located in main gopie directory)

**Optional (only if using specific services):**

- `./google/service-account.json` (required only for Google services)
- `./gateways/litellm/litellm_config.yaml` (required only when using LiteLLM profile)
