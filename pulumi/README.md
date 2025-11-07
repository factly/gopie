# GoPie Pulumi Infrastructure

This directory contains Pulumi Infrastructure as Code (IaC) for deploying GoPie on Google Kubernetes Engine (GKE).

## Overview

This Pulumi project automates the following:
- **GKE Cluster Creation**: Provisions a Google Kubernetes Engine cluster with configurable node count and machine types
- **Kubernetes Configuration**: Generates kubeconfig for cluster access
- **Helm Chart Deployment**: Deploys the GoPie application using Helm charts with customizable values

## Architecture

The infrastructure consists of:
- **GKE Cluster**: Managed Kubernetes cluster on Google Cloud Platform
- **Node Pool**: Configurable number of nodes with specified machine types
- **GoPie Application**: Deployed via Helm chart including:
  - Server deployment (API backend)
  - Web frontend (Next.js)
  - Chat server
  - PostgreSQL database
  - MinIO object storage
  - Qdrant vector database
  - Companion service for file uploads

## Project Structure

```
pulumi/
├── __main__.py          # Main Pulumi program entry point
├── cluster.py           # GKE cluster creation and kubeconfig generation
├── config.py            # Configuration settings using Pydantic
├── helm_chart.py        # Helm chart deployment logic
├── values.yaml          # Helm chart values for GoPie application
├── requirements.txt     # Python dependencies
├── Pulumi.yaml          # Pulumi project configuration
├── .env                 # Environment variables (not in version control)
└── README.md            # This file
```

## Prerequisites

Before you begin, ensure you have the following installed:

1. **Pulumi CLI** (v3.0.0 or later)
   ```bash
   curl -fsSL https://get.pulumi.com | sh
   ```

2. **Python 3.8+**
   ```bash
   python --version
   ```

3. **Google Cloud SDK (gcloud)**
   ```bash
   # Install gcloud CLI
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   
   # Initialize and authenticate
   gcloud init
   gcloud auth application-default login
   ```

4. **kubectl** (Kubernetes CLI)
   ```bash
   gcloud components install kubectl
   ```

5. **gke-gcloud-auth-plugin**
   ```bash
   gcloud components install gke-gcloud-auth-plugin
   ```

## Setup Instructions

### Step 1: Configure Google Cloud Project

Set your GCP project and default zone:

```bash
# Set your GCP project ID
export GCP_PROJECT="your-project-id"
gcloud config set project $GCP_PROJECT

# Set default zone (optional)
gcloud config set compute/zone us-central1-a
```

### Step 2: Install Python Dependencies

Navigate to the pulumi directory and install required packages:

```bash
cd pulumi
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Create a `.env` file in the pulumi directory with your configuration:

```bash
# Optional: Override default settings
NODE_COUNT=3
NODE_MACHINE_TYPE=n1-standard-1
MASTER_VERSION=1.24.0
```

### Step 4: Configure Pulumi Stack

Initialize or select a Pulumi stack:

```bash
# Login to Pulumi (choose backend: Pulumi Cloud or local)
pulumi login

# Create a new stack (or select existing)
pulumi stack init gopie

# Set GCP project and zone
pulumi config set gcp:project $GCP_PROJECT
pulumi config set gcp:zone us-central1-a
```

### Step 5: Customize Helm Values

Edit `values.yaml` to configure your GoPie deployment:

**Required configurations:**
- `deployment.image.repository`: Your Docker image repository
- `deployment.image.tag`: Image tag to deploy
- `ingress.hosts[0].host`: Your domain name
- `deployment.env`: Environment variables (API keys, database configs, etc.)

**Example:**
```yaml
deployment:
  image:
    repository: "gcr.io/your-project/gopie"
    tag: "latest"
  env:
    - name: GOPIE_PORTKEY_APIKEY
      value: "your-api-key"
    - name: GOPIE_PORTKEY_VIRTUALKEY
      value: "your-virtual-key"

ingress:
  enabled: true
  hosts:
    - host: gopie.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
```

### Step 6: Preview Infrastructure Changes

Review what Pulumi will create:

```bash
pulumi preview
```

This command shows:
- Resources to be created
- Configuration values
- Estimated costs (if available)

### Step 7: Deploy Infrastructure

Deploy the infrastructure to GCP:

```bash
pulumi up
```

You'll be prompted to confirm. Type `yes` to proceed.

**Deployment time:** Approximately 10-15 minutes for cluster creation and application deployment.

### Step 8: Access Your Cluster

After deployment completes, export the kubeconfig:

```bash
# Export kubeconfig to a file
pulumi stack output kubeconfig > kubeconfig.yaml

# Set KUBECONFIG environment variable
export KUBECONFIG=$(pwd)/kubeconfig.yaml

# Verify cluster access
kubectl get nodes
kubectl get pods --all-namespaces
```

### Step 9: Access GoPie Application

Get the ingress IP or domain:

```bash
# Get ingress details
kubectl get ingress

# If using LoadBalancer service
kubectl get svc -n default
```

Access GoPie at the configured domain or LoadBalancer IP.

## Configuration Options

### Cluster Configuration (`config.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `NODE_COUNT` | 3 | Number of nodes in the cluster |
| `NODE_MACHINE_TYPE` | n1-standard-1 | GCP machine type for nodes |
| `MASTER_VERSION` | 1.24.0 | Kubernetes version |

### Helm Chart Configuration (`values.yaml`)

Key sections to configure:

#### 1. **Deployment Settings**
```yaml
deployment:
  replicaCount: 1
  image:
    repository: "your-registry/gopie"
    tag: "latest"
```

#### 2. **Environment Variables**
```yaml
deployment:
  env:
    - name: GOPIE_API_SERVER_PORT
      value: "8000"
    - name: GOPIE_PORTKEY_APIKEY
      value: "your-api-key"
```

#### 3. **Ingress Configuration**
```yaml
ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: gopie.example.com
      paths:
        - path: /
          pathType: Prefix
```

#### 4. **Database Configuration**
```yaml
postgresql:
  enabled: true
  auth:
    username: default
    database: gopie
```

#### 5. **Storage Configuration**
```yaml
stateful:
  persistence:
    enabled: true
    size: 10Gi
    storageClassName: standard
```

## Common Operations

### Update Infrastructure

After modifying configuration:

```bash
pulumi up
```

### View Stack Outputs

```bash
pulumi stack output
pulumi stack output kubeconfig
```

### Destroy Infrastructure

**Warning:** This will delete all resources including data!

```bash
pulumi destroy
```

### Switch Between Stacks

```bash
# List stacks
pulumi stack ls

# Select a stack
pulumi stack select <stack-name>
```

### View Resource Details

```bash
# List all resources in the stack
pulumi stack --show-urns

# Export stack state
pulumi stack export > stack-state.json
```

## Troubleshooting

### Issue: Authentication Errors

```bash
# Re-authenticate with GCP
gcloud auth application-default login
gcloud auth login
```

### Issue: Cluster Creation Fails

Check GCP quotas and permissions:
```bash
gcloud compute project-info describe --project=$GCP_PROJECT
```

Ensure you have the following IAM roles:
- `roles/container.admin` (Kubernetes Engine Admin)
- `roles/compute.admin` (Compute Admin)
- `roles/iam.serviceAccountUser` (Service Account User)

### Issue: Helm Chart Deployment Fails

Check Kubernetes events:
```bash
kubectl get events --sort-by='.lastTimestamp'
kubectl describe pod <pod-name>
```

### Issue: Cannot Access Application

1. Check ingress status:
   ```bash
   kubectl get ingress
   kubectl describe ingress gopie
   ```

2. Check service endpoints:
   ```bash
   kubectl get svc
   kubectl get endpoints
   ```

3. Check pod logs:
   ```bash
   kubectl logs -l app=gopie
   ```

### Issue: Pulumi State Conflicts

```bash
# Cancel ongoing operations
pulumi cancel

# Refresh state
pulumi refresh
```

## Monitoring and Logs

### View Application Logs

```bash
# Server logs
kubectl logs -l app.kubernetes.io/name=gopie -c server

# Web logs
kubectl logs -l app.kubernetes.io/name=gopie -c web

# Follow logs
kubectl logs -f deployment/gopie-server
```

### Monitor Resources

```bash
# Resource usage
kubectl top nodes
kubectl top pods

# Cluster info
kubectl cluster-info
kubectl get all --all-namespaces
```

## Updating the Application

### Update Docker Image

1. Update `values.yaml`:
   ```yaml
   deployment:
     image:
       tag: "v1.2.3"
   ```

2. Apply changes:
   ```bash
   pulumi up
   ```

### Update Helm Chart Version

1. Modify `helm_chart.py`:
   ```python
   version="0.1.4"  # New version
   ```

2. Deploy:
   ```bash
   pulumi up
   ```

## Security Best Practices

1. **Secrets Management**: Use Pulumi secrets for sensitive data:
   ```bash
   pulumi config set --secret apiKey your-secret-key
   ```

2. **Network Policies**: Configure Kubernetes network policies in `values.yaml`

3. **RBAC**: Enable and configure Role-Based Access Control

4. **TLS/SSL**: Configure TLS certificates in ingress:
   ```yaml
   ingress:
     tls:
       - secretName: gopie-tls
         hosts:
           - gopie.example.com
   ```

5. **Image Security**: Use private registries and image pull secrets:
   ```yaml
   imagePullSecrets:
     - name: regcred
   ```

## Cost Optimization

1. **Right-size nodes**: Adjust `NODE_MACHINE_TYPE` based on workload
2. **Enable autoscaling**: Configure HPA in `values.yaml`
3. **Use preemptible nodes**: For non-production environments
4. **Set resource limits**: Define CPU/memory limits in `values.yaml`

## Support and Resources

- **Pulumi Documentation**: https://www.pulumi.com/docs/
- **GKE Documentation**: https://cloud.google.com/kubernetes-engine/docs
- **Kubernetes Documentation**: https://kubernetes.io/docs/
- **GoPie Helm Chart**: https://factly.github.io/gopie/

## Contributing

When making changes to the infrastructure:

1. Test in a separate stack first
2. Document configuration changes
3. Update this README if adding new features
4. Use `pulumi preview` before applying changes

## License

[MIT License](https://github.com/factly/gopie/blob/main/LICENSE).
