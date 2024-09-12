# Kueue Lifecycle Watcher

This is a simple watcher that listens to Kubernetes events and sends notifications when a Kueue workload enters a certain lifecycle state.

## Workload Annotations

Only workloads annotated with appropriate Kubernetes annotations will be watched.

-   `x-jobby.io/notify-channel`: The channel to use for notifications (currently, `slack` and `webhook` are supported)
-   `x-jobby.io/slack-channel-ids`: Comma-separated list of Slack channel IDs to send notifications to
-   `x-jobby.io/webhook-urls`: Comma-separated list of URLs to send notifications to

## Running the Watcher

To run the watcher, you need to provide the following environment variables:

-   `WATCHER_SLACK_API_TOKEN`: The Slack API token to use for sending Slack notifications

The watcher will attempt to load Kubernetes configuration from either a local Kubeconfig file (`~/.kube/
config` or `$KUBECONFIG`) or from the in-cluster configuration.

To run the watcher, run the following command:

```bash
$ export WATCHER_SLACK_API_TOKEN="<your-slack-api-token>"
$ go run main.go
# or, if you have compiled the binary already:
$ ./watcher
```

## Building the Watcher

### Locally

To build the watcher from source, run the following command:

```bash
$ go build -o watcher
```

### Container Images

This project uses [ko](https://github.com/google/ko) to build container images. To build the container image, run the following command:

```bash
$ ko build -L
```

This will build the container image and load it into the local Docker daemon.

You can then run the container using the following command:

```bash
$ docker run -it --rm \
    -e WATCHER_SLACK_API_TOKEN="<your-slack-api-token>" \
    -e KUBECONFIG="/kubeconfig" \
    -v ~/.kube/config:/kubeconfig:ro \
    --network=host \
    <image-id>
```

Replace `<image-id>` with the ID of the image you built.
