"""Helm Chart Deployment Module"""
import yaml
from pulumi import ResourceOptions
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts


def deploy_gopie_chart(k8s_provider, values_file="values.yaml"):
    """Deploy the GoPie Helm chart to the cluster."""
    # Load values from YAML file
    with open(values_file) as f:
        values = yaml.safe_load(f)
    
    # Deploy the Helm chart
    chart = Chart(
        "gopie",
        ChartOpts(
            chart="gopie",
            version="0.1.3",
            fetch_opts=FetchOpts(
                repo="https://factly.github.io/gopie/",
            ),
            values=values,
        ),
        opts=ResourceOptions(provider=k8s_provider),
    )
    
    return chart
