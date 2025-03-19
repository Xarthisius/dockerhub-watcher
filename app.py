import os
import requests
from flask import Flask, jsonify
from kubernetes import client, config

# Configuring Flask app
app = Flask(__name__)

# Load K8s config (if running outside K8s)
try:
    config.load_incluster_config()
except Exception:
    config.load_kube_config()


def get_docker_hub_token():
    username = os.getenv("DOCKER_USERNAME")  # Docker Hub username
    password = os.getenv("DOCKER_PASSWORD")  # Docker Hub password

    # Docker Hub API to get the token
    url = "https://hub.docker.com/v2/auth/token"

    # Sending request to Docker Hub
    response = requests.post(url, json={"identifier": username, "secret": password})

    if response.status_code != 200:
        raise Exception(
            f"Error fetching Docker Hub token: {response.status_code} - {response.text}"
        )

    data = response.json()
    return data["access_token"]


# Function to get the image used by the main container in the pod
def get_main_container_image_digest():
    v1 = client.CoreV1Api()
    pod_name = os.getenv("POD_NAME")  # Pod name should be set as environment variable
    namespace = os.getenv(
        "POD_NAMESPACE"
    )  # Namespace should be set as environment variable
    pods = v1.list_namespaced_pod(
        namespace=namespace, label_selector=f"app={pod_name}", watch=False
    )
    if not pods.items:
        raise ValueError(
            f"No pods found with label app={pod_name} in namespace {namespace}"
        )

    pod = pods.items[0]  # Assuming we are interested in the first pod
    for container in pod.status.container_statuses:
        if container.name != pod_name:
            continue
        if not container.state.running:
            raise ValueError(f"Container {pod_name} is not running: {container.state}")
        current_image = container.image_id
        if not current_image:
            raise ValueError(f"Container {pod_name} has no image ID")
        return container.image, current_image.split("@")[
            1
        ]  # Return the digest of the image


# Function to check if there is a newer version of the image in Docker Hub
def is_newer_image_available(app):

    try:
        current_image, current_digest = get_main_container_image_digest()
    except Exception as e:
        app.logger.error(f"Error: {e}")
        return False
    app.logger.info(f"Current image: {current_image}")
    app.logger.info(f"Current digest: {current_digest}")

    image_name, current_tag = current_image.split(":")
    _, ns, repo = image_name.split("/")

    headers = {
        "Authorization": f"Bearer {get_docker_hub_token()}",
    }

    # Docker Hub API to get the tags of the image
    url = f"https://registry.hub.docker.com/v2/namespaces/{ns}/repositories/{repo}/tags"

    app.logger.info(f"Fetching tags from {url}")

    # Sending request to Docker Hub
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        app.logger.error(
            f"Error fetching Docker Hub tags: {response.status_code} - {response.text}"
        )
        return False

    data = response.json()
    for tag in data["results"]:
        if tag["name"] == current_tag:
            current_tag = tag["digest"]
            break
    else:
        app.logger.error(f"Tag {current_tag} not found in {data=}")
        return False

    latest_digest = tag["digest"]
    app.logger.info(f"Latest digest: {latest_digest}")

    # Check if there is a newer image
    return latest_digest != current_digest and latest_digest is not None


# Healthcheck route that will be triggered by K8s
@app.route("/health", methods=["GET"])
def health_check():
    try:
        if is_newer_image_available(app):
            return jsonify({"status": "Newer image available, triggering restart"}), 500

        return jsonify({"status": "Up to date"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
