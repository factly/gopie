"""Main Pulumi program for GoPie deployment on GKE"""
from pulumi import export
from cluster import create_gke_cluster, generate_kubeconfig, create_k8s_provider
from helm_chart import deploy_gopie_chart

# Create the GKE cluster
cluster = create_gke_cluster()

# Generate kubeconfig for the cluster
kubeconfig = generate_kubeconfig(cluster)

# Create Kubernetes provider
k8s_provider = create_k8s_provider(kubeconfig)

# Deploy the GoPie Helm chart
gopie_chart = deploy_gopie_chart(k8s_provider)

# Export the kubeconfig for external access
export("kubeconfig", kubeconfig)