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

### File Requirements

- `.env` file with environment variables
- `./google/service-account.json` (for Google services)
- `./gateways/litellm/litellm_config.yaml` (for LiteLLM)
