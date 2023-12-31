#!/usr/bin/python
from flask import Flask, request
import requests

app = Flask(__name__)

# Adresse de l'instance TrustedHost
TRUSTED_HOST_PRIVATE_URL = "http://172.31.61.244:80"

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
