# GoPie Helm Chart Configuration

This document explains the configurable parameters for the GoPie Helm chart.

## Global Image Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Docker image repository for the main application | `""` |
| `image.pullPolicy` | Image pull policy (`Always`, `IfNotPresent`, `Never`) | `IfNotPresent` |
| `image.tag` | Image tag to use. Defaults to `appVersion` if empty | `""` |
| `imagePullSecrets` | List of Kubernetes secrets for pulling private images | `[]` |
| `nameOverride` | Override the name of the chart | `""` |
| `fullnameOverride` | Override the full resource name | `"gopie"` |

# Server Configuration
| Key                                                    | Type   | Default / Example                               | Description                                             |
| ------------------------------------------------------ | ------ | ----------------------------------------------- | ------------------------------------------------------- |
| `server.name`                                          | string | `server`                                        | Name of the server deployment                           |
| `server.replicaCount`                                  | int    | `1`                                             | Number of replicas to run                               |
| `server.extraLabels`                                   | map    | `{}`                                            | Extra labels for the Deployment                         |
| `server.extraPodLabels`                                | map    | `{}`                                            | Extra labels for the Pods                               |
| `server.annotations`                                   | map    | `{}`                                            | Annotations for the Deployment                          |
| `server.Podannotations`                                | map    | `{}`                                            | Annotations for the Pods                                |
| `server.env`                                           | list   | `[]`                                            | Environment variables for the main container            |
| `server.initContainers`                                | list   | `[{ name: gopie-migrate, image: "", env: [] }]` | Init containers to run before the main container        |
| `server.serviceAccount.create`                         | bool   | `false`                                         | Create a new service account                            |
| `server.serviceAccount.automount`                      | bool   | `true`                                          | Auto-mount API credentials                              |
| `server.serviceAccount.annotations`                    | map    | `{}`                                            | Annotations for the service account                     |
| `server.serviceAccount.name`                           | string | `""`                                            | Existing service account to use                         |
| `server.podSecurityContext`                            | map    | `{}`                                            | Pod-level security context (`fsGroup` etc.)             |
| `server.securityContext`                               | map    | `{}`                                            | Container-level security context (`runAsUser` etc.)     |
| `server.service.portName`                              | string | `http`                                          | Name of the Service port                                |
| `server.service.type`                                  | string | `ClusterIP`                                     | Service type: `ClusterIP` / `NodePort` / `LoadBalancer` |
| `server.service.portNumber`                            | int    | `8000`                                          | Port exposed by the Service                             |
| `server.resources.limits.cpu`                          | string | `200m`                                          | CPU limit                                               |
| `server.resources.limits.memory`                       | string | `1Gi`                                           | Memory limit                                            |
| `server.resources.requests.cpu`                        | string | `100m`                                          | CPU request                                             |
| `server.resources.requests.memory`                     | string | `100Mi`                                         | Memory request                                          |
| `server.autoscaling.enabled`                           | bool   | `false`                                         | Enable Horizontal Pod Autoscaler                        |
| `server.autoscaling.minReplicas`                       | int    | `5`                                             | Minimum replicas when HPA is enabled                    |
| `server.autoscaling.maxReplicas`                       | int    | `20`                                            | Maximum replicas                                        |
| `server.autoscaling.targetCPUUtilizationPercentage`    | int    | `80`                                            | Target CPU usage (%)                                    |
| `server.autoscaling.targetMemoryUtilizationPercentage` | int    | `80`                                            | Target memory usage (%)                                 |
| `server.livenessProbe`                                 | map    | *(example commented)*                           | Optional liveness probe                                 |
| `server.readinessProbe`                                | map    | *(example commented)*                           | Optional readiness probe                                |
| `server.nodeSelector`                                  | map    | `{}`                                            | Node selector for scheduling                            |
| `server.tolerations`                                   | list   | `[]`                                            | Tolerations for scheduling on tainted nodes             |
| `server.affinity`                                      | map    | `{}`                                            | Affinity / anti-affinity rules                          |
| `server.extraVolumeMounts`                             | list   | `[]`                                            | Additional volume mounts for container                  |
| `server.extraVolumes`                                  | list   | `[]`                                            | Additional volumes for the Pod                          |
| `server.persistence.type`                              | string | `pvc`                                           | Type of persistence: `pvc` or `hostPath`                |
| `server.persistence.enabled`                           | bool   | `true`                                          | Enable persistence                                      |
| `server.persistence.storageClassName`                  | string | `standard`                                      | Storage class for the PVC                               |
| `server.persistence.accessModes`                       | list   | `[ ReadWriteOnce ]`                             | Access modes                                            |
| `server.persistence.size`                              | string | `10Gi`                                          | Persistent volume size                                  |
| `server.persistence.annotations`                       | map    | `{ helm.sh/resource-policy: "keep" }`           | Annotations for the PVC                                 |
| `server.persistence.finalizers`                        | list   | `[ kubernetes.io/pvc-protection ]`              | PVC finalizers                                          |
| `server.persistence.extraPvcLabels`                    | map    | `{}`                                            | Extra labels for PVC                                    |
| `server.persistence.inMemory.enabled`                  | bool   | `false`                                         | Enable EmptyDir in-memory storage                       |
| `server.persistence.inMemory.sizeLimit`                | string | *(optional)*                                    | Size limit for EmptyDir                                 |
| `server.reIndexingJob.enabled`                         | bool   | `true`                                          | Enable the re-indexing job                              |
| `server.reIndexingJob.image.repository`                | string | `""`                                            | Docker image repository for re-indexing                 |
| `server.reIndexingJob.image.tag`                       | string | `""`                                            | Docker image tag for re-indexing                        |
| `server.reIndexingJob.env`                             | list   | `[]`                                            | Environment variables for the re-indexing job           |
| `server.reIndexingJob.volumeMounts`                    | list   | `[]`                                            | Extra volume mounts for re-indexing                     |
| `server.reIndexingJob.volumes`                         | list   | `[]`                                            | Extra volumes for re-indexing                           |


# Web Configuration
The web section defines configuration for deploying the web component

| Key                                                 | Type   | Default                                                                        | Description                                   |
| --------------------------------------------------- | ------ | ------------------------------------------------------------------------------ | --------------------------------------------- |
| `web.image.repository`                              | string | `""`                                                                           | Docker image repository for web               |
| `web.image.pullPolicy`                              | string | `IfNotPresent`                                                                 | Image pull policy                             |
| `web.image.tag`                                     | string | `""`                                                                           | Docker image tag                              |
| `web.replicaCount`                                  | int    | `1`                                                                            | Number of web pod replicas                    |
| `web.name`                                          | string | `web`                                                                          | Name identifier for the web Deployment        |
| `web.imagePullSecrets`                              | list   | `[]`                                                                           | Image pull secrets for private registries     |
| `web.extraLabels`                                   | map    | `{}`                                                                           | Additional labels for Deployment              |
| `web.extraPodLabels`                                | map    | `{}`                                                                           | Additional labels for pods                    |
| `web.annotations`                                   | map    | `{}`                                                                           | Annotations for Deployment                    |
| `web.Podannotations`                                | map    | `{}`                                                                           | Annotations for pods                          |
| `web.env`                                           | list   | `[]`                                                                           | Environment variables for web container       |
| `web.serviceAccount.create`                         | bool   | `false`                                                                        | Create a new ServiceAccount                   |
| `web.serviceAccount.automount`                      | bool   | `true`                                                                         | Auto-mount API credentials for ServiceAccount |
| `web.serviceAccount.annotations`                    | map    | `{}`                                                                           | Annotations for ServiceAccount                |
| `web.serviceAccount.name`                           | string | `""`                                                                           | Existing ServiceAccount name to use           |
| `web.podSecurityContext`                            | map    | `{}`                                                                           | Pod-level security context                    |
| `web.securityContext`                               | map    | `{}`                                                                           | Container-level security context              |
| `web.service.portName`                              | string | `http`                                                                         | Name of the service port                      |
| `web.service.type`                                  | string | `ClusterIP`                                                                    | Kubernetes Service type                       |
| `web.service.portNumber`                            | int    | `3000`                                                                         | Service port number                           |
| `web.resources`                                     | map    | `{limits: {cpu: 1000m, memory: 1000Mi}, requests: {cpu: 100m, memory: 128Mi}}` | Resource requests and limits                  |
| `web.autoscaling.enabled`                           | bool   | `false`                                                                        | Enable Horizontal Pod Autoscaler              |
| `web.autoscaling.minReplicas`                       | int    | `1`                                                                            | Minimum replicas if autoscaling enabled       |
| `web.autoscaling.maxReplicas`                       | int    | `10`                                                                           | Maximum replicas if autoscaling enabled       |
| `web.autoscaling.targetCPUUtilizationPercentage`    | int    | `80`                                                                           | Target average CPU utilization                |
| `web.autoscaling.targetMemoryUtilizationPercentage` | int    | `80`                                                                           | Target average Memory utilization             |
| `web.nodeSelector`                                  | map    | `{}`                                                                           | Node selector                                 |
| `web.tolerations`                                   | list   | `[]`                                                                           | Node tolerations                              |
| `web.affinity`                                      | map    | `{}`                                                                           | Pod affinity/anti-affinity                    |
| `web.extraVolumeMounts`                             | list   | `[]`                                                                           | Additional volume mounts                      |
| `web.extraVolumes`                                  | list   | `[]`                                                                           | Additional pod volumes                        |


# Chatserver Configuration

| Key                                                        | Type   | Default                                                                        | Description                                    |
| ---------------------------------------------------------- | ------ | ------------------------------------------------------------------------------ | ---------------------------------------------- |
| `chatserver.name`                                          | string | `chatserver`                                                                   | Name identifier for the chatserver Deployment  |
| `chatserver.replicaCount`                                  | int    | `1`                                                                            | Number of chatserver pod replicas              |
| `chatserver.image.repository`                              | string | `""`                                                                           | Docker image repository for the chatserver     |
| `chatserver.image.pullPolicy`                              | string | `IfNotPresent`                                                                 | Image pull policy                              |
| `chatserver.image.tag`                                     | string | `""`                                                                           | Image tag to use                               |
| `chatserver.imagePullSecrets`                              | list   | `[]`                                                                           | Image pull secrets for private registries      |
| `chatserver.extraLabels`                                   | map    | `{}`                                                                           | Additional labels for the Deployment           |
| `chatserver.extraPodLabels`                                | map    | `{}`                                                                           | Additional labels for pods                     |
| `chatserver.annotations`                                   | map    | `{}`                                                                           | Annotations for the Deployment                 |
| `chatserver.Podannotations`                                | map    | `{}`                                                                           | Annotations for pods                           |
| `chatserver.env`                                           | list   | `[]`                                                                           | Environment variables for the chatserver       |
| `chatserver.serviceAccount.create`                         | bool   | `false`                                                                        | Whether to create a new ServiceAccount         |
| `chatserver.serviceAccount.automount`                      | bool   | `true`                                                                         | Auto-mount the ServiceAccount token in the pod |
| `chatserver.serviceAccount.annotations`                    | map    | `{}`                                                                           | Annotations for the ServiceAccount             |
| `chatserver.serviceAccount.name`                           | string | `""`                                                                           | Existing ServiceAccount name                   |
| `chatserver.podSecurityContext`                            | map    | `{}`                                                                           | Pod-level security context                     |
| `chatserver.securityContext`                               | map    | `{}`                                                                           | Container-level security context               |
| `chatserver.service.portName`                              | string | `http`                                                                         | Service port name                              |
| `chatserver.service.type`                                  | string | `ClusterIP`                                                                    | Kubernetes Service type                        |
| `chatserver.service.portNumber`                            | int    | `8000`                                                                         | Port the container listens on                  |
| `chatserver.resources`                                     | map    | `{limits: {cpu: 1000m, memory: 1000Mi}, requests: {cpu: 100m, memory: 128Mi}}` | Resource requests and limits                   |
| `chatserver.autoscaling.enabled`                           | bool   | `false`                                                                        | Enable Horizontal Pod Autoscaler               |
| `chatserver.autoscaling.minReplicas`                       | int    | `1`                                                                            | Minimum replicas if autoscaling is enabled     |
| `chatserver.autoscaling.maxReplicas`                       | int    | `100`                                                                          | Maximum replicas if autoscaling is enabled     |
| `chatserver.autoscaling.targetCPUUtilizationPercentage`    | int    | `80`                                                                           | Target average CPU utilization                 |
| `chatserver.autoscaling.targetMemoryUtilizationPercentage` | int    | `80`                                                                           | Target average Memory utilization              |
| `chatserver.nodeSelector`                                  | map    | `{}`                                                                           | Node selector rules                            |
| `chatserver.tolerations`                                   | list   | `[]`                                                                           | Node tolerations                               |
| `chatserver.affinity`                                      | map    | `{}`                                                                           | Affinity rules                                 |
| `chatserver.extraVolumeMounts`                             | list   | `[]`                                                                           | Additional volume mounts                       |
| `chatserver.extraVolumes`                                  | list   | `[]`                                                                           | Additional pod volumes                         |

# Dependencies Configuration

| Key                               | Description                                        |
| --------------------------------- | -------------------------------------------------- |
| `postgresql.enabled`              | Enable or disable the bundled PostgreSQL chart     |
| `postgresql.auth.username`        | Database username for PostgreSQL                   |
| `postgresql.auth.database`        | Default database name                              |
| `minio.enabled`                   | Enable or disable the bundled MinIO chart          |
| `minio.defaultBuckets`            | Comma-separated list of default buckets to create  |
| `companion.enabled`               | Enable or disable the Companion service            |
| `companion.env`                   | Environment variables for Companion                |
| `companion.ingress.enabled`       | Enable or disable Ingress for Companion            |
| `qdrant.enabled`                  | Enable or disable the Qdrant vector database chart |
| `zitadel.enabled`                 | Enable or disable the ZITADEL identity provider    |
| `zitadel.zitadel.masterkey`       | Master encryption key for ZITADEL                  |
| `zitadel.zitadel.configmapConfig` | Configuration for ZITADEL deployment               |
| `zitadel.env`                     | Additional ZITADEL environment variables           |
| `zitadel.ingress.enabled`         | Enable or disable Ingress for ZITADEL              |
| `zitadel.ingress.className`       | Ingress class name                                 |
| `zitadel.ingress.annotations`     | Ingress annotations                                |
| `zitadel.ingress.hosts`           | Ingress host and paths                             |
| `zitadel.ingress.tls`             | TLS configuration for Ingress                      |


# **Gopie Configuration: Environment Variables**

This document provides a complete reference for all environment variables required to configure and run the Gopie application. All configuration is handled through environment variables, which can also be placed in a config.env file in the application's root directory.

### **General Configuration**

These variables control core application behavior.

| Variable | Required | Default | Description |
| :---- | :---- | :---- | :---- |
| **GOPIE\_ENCRYPTION\_KEY** | **Yes** | \- | A secret key used for all data encryption and decryption. **Must be 32 characters long.** |
| **GOPIE\_ENABLE\_ZITADEL** | No | false | A boolean (true/false) to enable or disable Zitadel authentication. |

### **Server Configuration**

Settings for the main public-facing server.

| Variable | Required | Default | Description |
| :---- | :---- | :---- | :---- |
| **GOPIE\_SERVER\_HOST** | No | localhost | The hostname or IP address the main server will listen on. |
| **GOPIE\_SERVER\_PORT** | No | 8000 | The port the main server will listen on. |

### **Internal Server Configuration**

Settings for the internal-only server.

| Variable | Required | Default | Description |
| :---- | :---- | :---- | :---- |
| **GOPIE\_INTERNAL\_SERVER\_HOST** | No | localhost | The hostname or IP address the internal server will listen on. |
| **GOPIE\_INTERNAL\_SERVER\_PORT** | No | 8001 | The port the internal server will listen on. |

### **Postgres Configuration**

Connection details for the PostgreSQL database.

| Variable | Required | Default | Description |
| :---- | :---- | :---- | :---- |
| **GOPIE\_POSTGRES\_HOST** | **Yes** | \- | Hostname of the PostgreSQL server. |
| **GOPIE\_POSTGRES\_PORT** | **Yes** | \- | Port of the PostgreSQL server. |
| **GOPIE\_POSTGRES\_DB** | **Yes** | \- | The name of the database to connect to. |
| **GOPIE\_POSTGRES\_USER** | **Yes** | \- | The username for the database connection. |
| **GOPIE\_POSTGRES\_PASSWORD** | **Yes** | \- | The password for the database connection. |

### **S3 Configuration**

Credentials for an S3-compatible object storage service. **These are required for dataset operations.**

| Variable | Required | Default | Description |
| :---- | :---- | :---- | :---- |
| **GOPIE\_S3\_ACCESS\_KEY** | **Yes** | \- | Access key for your S3-compatible service. |
| **GOPIE\_S3\_SECRET\_KEY** | **Yes** | \- | Secret key for your S3-compatible service. |
| **GOPIE\_S3\_ENDPOINT** | **Yes** | \- | Custom endpoint URL for the S3 service (e.g., for MinIO). |
| **GOPIE\_S3\_REGION** | No | us-east-1 | The AWS region for the S3 bucket. |
| **GOPIE\_S3\_SSL** | No | false | Use SSL (true/false) for the S3 connection. |

### **OLAP Database Configuration**

This section configures the OLAP database. You must choose between duckdb and motherduck.

| Variable | Required | Default | Description |
| :---- | :---- | :---- | :---- |
| **GOPIE\_OLAPDB\_DBTYPE** | **Yes** | \- | The OLAP database to use. Must be duckdb or motherduck. |
| **GOPIE\_OLAPDB\_ACCESS\_MODE** | No | read\_write | The database access mode (e.g., read\_only, read\_write). |

#### **DuckDB Settings**

*These variables are used if GOPIE\_OLAPDB\_DBTYPE="duckdb".*

| Variable | Required | Default | Description |
| :---- | :---- | :---- | :---- |
| **GOPIE\_DUCKDB\_PATH** | **Yes** | ./duckdb/gopie.db | The file path for the local DuckDB database file. |
| **GOPIE\_DUCKDB\_CPU** | No | 1 | Number of CPU cores allocated to DuckDB. Must be \> 0\. |
| **GOPIE\_DUCKDB\_MEMORY\_LIMIT** | No | 1024 | Memory limit in MB for DuckDB. Must be \> 0\. |
| **GOPIE\_DUCKDB\_STORAGE\_LIMIT** | No | 1024 | Storage limit in MB for DuckDB. Must be \> 0\. |

#### **MotherDuck Settings**

*These variables are used if GOPIE\_OLAPDB\_DBTYPE="motherduck".*

| Variable | Required | Default | Description |
| :---- | :---- | :---- | :---- |
| **GOPIE\_MOTHERDUCK\_DB\_NAME** | **Yes** | \- | The name of your database in MotherDuck. |
| **GOPIE\_MOTHERDUCK\_TOKEN** | **Yes** | \- | Your MotherDuck service token for authentication. |
| **GOPIE\_MOTHERDUCK\_HELPER\_DB\_DIR\_PATH** | No | ./motherduck | Directory path for MotherDuck's local helper files. |

### **AI Provider Configuration (PortKey / OpenAI)**

Configuration for the AI provider. The application uses the OpenAI SDK internally, so these variables can accept values for either PortKey or a standard OpenAI-compatible service.

| Variable | Required | Description |
| :---- | :---- | :---- |
| **GOPIE\_PORTKEY\_BASEURL** | **Yes** | The base URL for the API. This can be the PortKey URL or a standard OPENAI\_API\_BASE URL. |
| **GOPIE\_PORTKEY\_APIKEY** | **Yes** | The API key for the service. This can be a PortKey API key or a standard OPENAI\_API\_KEY. |
| **GOPIE\_PORTKEY\_MODEL** | **Yes** | The specific AI model to use (e.g., gpt-4). |
| **GOPIE\_PORTKEY\_VIRTUALKEY** | **Yes** | The virtual key for your PortKey configuration. **Note:** This is specific to PortKey and should be set even if using OpenAI values in other variables. |

### **Zitadel Configuration**

*These variables are required if GOPIE\_ENABLE\_ZITADEL="true".*

| Variable | Required | Default | Description |
| :---- | :---- | :---- | :---- |
| **GOPIE\_ZITADEL\_PROTOCOL** | **Yes** | \- | The protocol for Zitadel (http or https). |
| **GOPIE\_ZITADEL\_DOMAIN** | **Yes** | \- | The domain of your Zitadel instance. |
| **GOPIE\_ZITADEL\_PROJECT\_ID** | **Yes** | \- | The project ID within your Zitadel instance. |
| **GOPIE\_ZITADEL\_INSECURE\_PORT** | **Conditional** | \- | Required only if GOPIE\_ZITADEL\_PROTOCOL is not https. |

### **AI Agent Configuration**

| Variable | Required | Default | Description |
| :---- | :---- | :---- | :---- |
| **GOPIE\_AIAGENT\_URL** | **Yes** | \- | The URL endpoint for the AI Agent service. |

### **Logger Configuration**

| Variable | Required | Default | Description |
| :---- | :---- | :---- | :---- |
| **GOPIE\_LOGGER\_LEVEL** | No | info | Logging level (e.g., debug, info, warn, error). |
| **GOPIE\_LOGGER\_FILE** | No | gopie.log | The path to the log file. |
| **GOPIE\_LOGGER\_MODE** | No | dev | Logger mode (dev for human-readable, prod for JSON). |

