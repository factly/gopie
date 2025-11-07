"""GKE Cluster Creation Module"""
from pulumi import Output
from pulumi_gcp.config import project, zone
from pulumi_gcp.container import Cluster, ClusterNodeConfigArgs
from pulumi_kubernetes import Provider
from config import Settings

settings = Settings()


def create_gke_cluster():
    """Create a GKE cluster with the specified configuration."""
    cluster = Cluster(
        "gopie-cluster",
        initial_node_count=settings.NODE_COUNT,
        node_version=settings.MASTER_VERSION,
        min_master_version=settings.MASTER_VERSION,
        node_config=ClusterNodeConfigArgs(
            machine_type=settings.NODE_MACHINE_TYPE,
            oauth_scopes=[
                "https://www.googleapis.com/auth/compute",
                "https://www.googleapis.com/auth/devstorage.read_only",
                "https://www.googleapis.com/auth/logging.write",
                "https://www.googleapis.com/auth/monitoring",
            ],
        ),
        deletion_protection=False,
    )
    return cluster


def generate_kubeconfig(cluster):
    """Generate a kubeconfig for the GKE cluster."""
    k8s_info = Output.all(cluster.name, cluster.endpoint, cluster.master_auth)
    
    kubeconfig = k8s_info.apply(
        lambda info: """apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: {0}
    server: https://{1}
  name: {2}
contexts:
- context:
    cluster: {2}
    user: {2}
  name: {2}
current-context: {2}
kind: Config
preferences: {{}}
users:
- name: {2}
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: gke-gcloud-auth-plugin
      installHint: Install gke-gcloud-auth-plugin for use with kubectl by following
        https://cloud.google.com/blog/products/containers-kubernetes/kubectl-auth-changes-in-gke
      provideClusterInfo: true
""".format(
            info[2]["cluster_ca_certificate"],
            info[1],
            "{0}_{1}_{2}".format(project, zone, info[0]),
        )
    )
    return kubeconfig


def create_k8s_provider(kubeconfig):
    """Create a Kubernetes provider using the generated kubeconfig."""
    return Provider("gke_k8s", kubeconfig=kubeconfig)
