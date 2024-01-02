#!/usr/bin/python

import os
import re
import logging
from flask import Flask, request
import requests

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Get the proxy instance's private IP from an environment variable
PROXY_INSTANCE_PRIVATE_IP = os.getenv('INSTANCE_PRIVATE_IP_PROXY_IP', 'default_proxy_ip')  # Replace 'default_proxy_ip' with a default value or error handling
PROXY_INSTANCE_PRIVATE_URL = f"http://{PROXY_INSTANCE_PRIVATE_IP}:80"

def is_valid_request(sql, method):
    if not re.match(r'^\s*(SELECT\s+.+?\s+FROM\s+.+?|INSERT\s+INTO\s+.+?\s+VALUES\s*\(.+?\)|UPDATE\s+.+?\s+SET\s+.+?(\s+WHERE\s+.+?)?|DELETE\s+FROM\s+.+?(\s+WHERE\s+.+?)?)\s*;?\s*$', sql):
        return False
    if method not in ['GET', 'POST', 'PUT', 'DELETE']:
        return False
    return True

@app.route('/<path>/<sql>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def forward_request(path,sql):
    try:
        method = request.method
        data = request.get_data()
        headers = {key: value for (key, value) in request.headers if key != 'Host'}

        if not is_valid_request(sql, method):
            logger.warning(f"Invalid request: {method} {sql}")
            return "Invalid Request", 400

        url = f"{PROXY_INSTANCE_PRIVATE_URL}/{path}/{sql}"
        logger.info(f"Forwarding {method} request to {url}")

        response = requests.request(method, url, headers=headers, data=data, allow_redirects=False)

        logger.info(f"Received response with status: {response.status_code}")
        return (response.content, response.status_code, response.headers.items())

    except requests.RequestException as e:
        logger.error(f"Error during request transmission: {e}")
        return "Internal Server Error", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
