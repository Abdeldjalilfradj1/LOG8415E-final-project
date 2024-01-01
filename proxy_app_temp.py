#!/usr/bin/python
from flask import Flask
import pymysql.cursors
import random
from sshtunnel import SSHTunnelForwarder
from pythonping import ping

# Combined configuration for master and slaves
DB_CONFIGS = {
    "MASTER": {"ip": "_MASTER_HOSTNAME_", "port": 3306},
    "SLAVE_1": {"ip": "_SLAVE_1_HOSTNAME_", "port": 3307},
    "SLAVE_2": {"ip": "_SLAVE_2_HOSTNAME_", "port": 3308},
    "SLAVE_3": {"ip": "_SLAVE_3_HOSTNAME_", "port": 3309},
}

SQL_QUERY = "SELECT * FROM film LIMIT 5;"
RESPONSE_TEMPLATE = "<h1>{route} route</h1><h2>Received from {ip} ({name})</h2><p>{content}</p>"

# Setup SSH tunnels for slaves
servers = []
def setup_ssh_tunnels():
    for name, config in DB_CONFIGS.items():
        if 'SLAVE' in name:
            server = SSHTunnelForwarder(
                (config["ip"], 22),
                ssh_pkey="/home/ubuntu/private_key_PROJET_KEY.pem",
                ssh_username="ubuntu",
                local_bind_address=('127.0.0.1', config["port"]),
                allow_agent=False,
                remote_bind_address=(DB_CONFIGS["MASTER"]["ip"], DB_CONFIGS["MASTER"]["port"]))
            server.start()
            servers.append(server)
            print(f"SSH tunnel setup for {name} at 127.0.0.1:{config['port']}")

setup_ssh_tunnels()

def ping_instance(host):
    return ping(target=host, count=5, timeout=2).rtt_avg_ms

def db_connection(config):
    return pymysql.connect(host="127.0.0.1" if 'SLAVE' in config else config["ip"],
                           port=config["port"],
                           user='user0',
                           password='mysql',
                           database='sakila',
                           charset='utf8mb4',
                           cursorclass=pymysql.cursors.DictCursor)

app = Flask(__name__)

@app.route('/normal')
def normal_endpoint():
    with db_connection(DB_CONFIGS["MASTER"]) as conn:
        with conn.cursor() as cursor:
            cursor.execute(SQL_QUERY)
            result = cursor.fetchone()
    return RESPONSE_TEMPLATE.format(route="Normal", ip=DB_CONFIGS["MASTER"]['ip'], name="MASTER", content=result)

@app.route('/custom')
def custom_endpoint():
    selected_config = min(DB_CONFIGS.items(), key=lambda x: ping_instance(x[1]['ip']))[1]
    with db_connection(selected_config) as conn:
        with conn.cursor() as cursor:
            cursor.execute(SQL_QUERY)
            result = cursor.fetchone()
    return RESPONSE_TEMPLATE.format(route="Custom", ip=selected_config['ip'], name=selected_config['name'], content=result)

@app.route('/random')
def random_endpoint():
    config = random.choice(list(DB_CONFIGS.values()))
    with db_connection(config) as conn:
        with conn.cursor() as cursor:
            cursor.execute(SQL_QUERY)
            result = cursor.fetchone()
    return RESPONSE_TEMPLATE.format(route="Random", ip=config['ip'], name=config['name'], content=result)

if __name__ == '__main__':
    app.run()
