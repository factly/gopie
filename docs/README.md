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
