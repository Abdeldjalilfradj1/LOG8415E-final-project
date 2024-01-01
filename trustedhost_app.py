#!/usr/bin/python
import os

from flask import Flask, request
import requests
import re

app = Flask(__name__)

# Get the proxy instance's private IP from an environment variable
PROXY_INSTANCE_PRIVATE_IP = os.getenv('INSTANCE_PRIVATE_IP_PROXY_IP', 'default_proxy_ip')  # Replace 'default_proxy_ip' with a default value or error handling
PROXY_INSTANCE_PRIVATE_URL = f"http://{PROXY_INSTANCE_PRIVATE_IP}:80"
# Fonction pour valider la requête
def is_valid_request(path, method, data):
    # Exemple de validation simple
    # Vous pouvez étendre cette fonction selon vos besoins de sécurité
    if not re.match(r'^[a-zA-Z0-9_/-]*$', path):
        return False
    if method not in ['GET', 'POST', 'PUT', 'DELETE']:
        return False
    # Ajoutez ici des validations supplémentaires si nécessaire
    return True

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def forward_request(path):
    try:
        method = request.method
        data = request.get_data()
        headers = {key: value for (key, value) in request.headers if key != 'Host'}

        if not is_valid_request(path, method, data):
            return "Invalid Request", 400

        url = f"{PROXY_INSTANCE_PRIVATE_URL}/{path}"

        response = requests.request(method, url, headers=headers, data=data, allow_redirects=False)

        return (response.content, response.status_code, response.headers.items())
    except requests.RequestException as e:
        print(f"Erreur lors de la transmission de la requête : {e}")
        return "Internal Server Error", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
