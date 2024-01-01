#!/usr/bin/python
import os

from flask import Flask, request
import requests

app = Flask(__name__)

# Get the trusted host's private IP from an environment variable
TRUSTED_HOST_PRIVATE_IP = os.getenv('INSTANCE_PRIVATE_IP_TRUSTEDHOST_IP')  # Replace 'default_private_ip' with a default or error handling
TRUSTED_HOST_PRIVATE_URL = f"http://{TRUSTED_HOST_PRIVATE_IP}:80"

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def forward_request(path):
    try:
        method = request.method
        data = request.get_data()
        headers = {key: value for (key, value) in request.headers if key != 'Host'}

        url = f"{TRUSTED_HOST_PRIVATE_URL}/{path}"

        response = requests.request(method, url, headers=headers, data=data, allow_redirects=False)

        return (response.content, response.status_code, response.headers.items())
    except requests.RequestException as e:
        print(f"Erreur lors de la transmission de la requête : {e}")
        return "Internal Server Error", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
