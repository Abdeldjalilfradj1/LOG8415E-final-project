#!/usr/bin/python
from flask import Flask, request
import requests
import re
import json

app = Flask(__name__)

PROXY_INSTANCE_PRIVATE_URL = "http://172.31.53.93:80"

def extract_sql_query(method, data):
    try:
        if method == 'GET':
            return request.args.get('query')
        else:
            json_data = json.loads(data)
            return json_data.get('query')
    except json.JSONDecodeError as e:
        app.logger.error(f"JSON decoding error: {e}")
        return None

def is_valid_sql_query(sql_query):
    return sql_query and sql_query.strip().upper().startswith("SELECT")

def is_valid_request(path, method, data):
    if not re.match(r'^[a-zA-Z0-9_/-]*$', path):
        return False
    if method not in ['GET', 'POST', 'PUT', 'DELETE']:
        return False

    sql_query = extract_sql_query(method, data)
    return is_valid_sql_query(sql_query)

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def forward_request(path):
    method = request.method
    data = request.get_data(as_text=True)

    if not is_valid_request(path, method, data):
        return "Invalid Request", 400

    url = f"{PROXY_INSTANCE_PRIVATE_URL}/{path}"
    headers = {key: value for (key, value) in request.headers if key != 'Host'}

    # Transmettre la requête au proxy
    response = requests.request(method, url, headers=headers, data=data, allow_redirects=False)

    return (response.content, response.status_code, response.headers.items())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
