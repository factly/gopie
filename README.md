# GoPie

Look up for the documentation on the product site: [https://gopie.ai/docs](https://gopie.ai/docs)

## Installation

[Helm](https://helm.sh) must be installed to use the charts.
Please refer to Helm's [documentation](https://helm.sh/docs/) to get started.

Once Helm is set up properly, add the repo as follows:

```console
helm repo add gopie https://factly.github.io/gopie/
helm repo update
```

```console
helm install gopie gopie/gopie
```
For more information on installing the chart, see the [configuration](https://github.com/factly/gopie/blob/main/helm/gopie/README.md).

## License

[MIT License](https://github.com/factly/gopie/blob/main/LICENSE).
