# !/usr/bin/python
from flask import Flask
import pymysql.cursors
import random
from sshtunnel import SSHTunnelForwarder
from pythonping import ping

# master and slaves configurations
MASTER_CONFIG = {
    "ip": "18.209.8.218",
    "port": 3306,
    "name": "MASTER"
}

SLAVE_CONFIGS = [
    {"ip": "_MASTER_HOSTNAME_", "port": 3307, "name": "SLAVE_1"},
    {"ip": "_SLAVE_1_HOSTNAME_", "port": 3308, "name": "SLAVE_2"},
    {"ip": "_SLAVE_1_HOSTNAME_", "port": 3309, "name": "SLAVE_3"},
]


# simple html template response
RESPONSE_TEMPLATE = """
<h1>{_ROUTE_TYPE_} route</h1><h2>Received from {_IP_} ({_NAME_})</h2>
<p>{_CONTENT_}</p>"""

# setup sshtunnels
servers = []
for idx, slave_config in enumerate(SLAVE_CONFIGS):
    print(f"Starting forwarding for {slave_config['ip']} -> 127.0.0.1:{slave_config['port']}")
    server = SSHTunnelForwarder(
        (slave_config["ip"], 22),
        ssh_pkey="/home/ubuntu/private_key_PROJET_KEY.pem",
        ssh_username="ubuntu",
        local_bind_address=('127.0.0.1', slave_config["port"]),
        allow_agent=False,
        remote_bind_address=(MASTER_CONFIG["ip"], MASTER_CONFIG["port"]))
    server.start()
    servers.append(server)


# simple function that pings a host and returns the average
def ping_instance(host):
    ping_result = ping(target=host, count=5, timeout=2)
    avg_ping = ping_result.rtt_avg_ms
    print(f"{host} ping : {avg_ping}ms")
    return avg_ping


# flask Application : defines our endpoints and their logic
app = Flask(__name__)


@app.route('/normal/<sql>')
def normal_endpoint(sql):
    # forward the request directly to the master
    connection = pymysql.connect(host=MASTER_CONFIG["ip"],
                                 port=MASTER_CONFIG["port"],
                                 user='user0',
                                 password='mysql',
                                 database='sakila',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)

            result = cursor.fetchall()
            print(result)

    return RESPONSE_TEMPLATE.format(_ROUTE_TYPE_="Normal",
                                    _IP_=MASTER_CONFIG['ip'],
                                    _NAME_=MASTER_CONFIG['name'],
                                    _CONTENT_=result)


@app.route('/custom/<sql>')
def custom_endpoint(sql):
    # default to master
    min_ping_config = MASTER_CONFIG
    min_ping = ping_instance(MASTER_CONFIG["ip"])

    # ping the endpoints, and forward to the right one
    for slave_config in SLAVE_CONFIGS:
        instance_ping = ping_instance(slave_config["ip"])
        if instance_ping < min_ping:
            min_ping = instance_ping
            min_ping_config = {"ip": "127.0.0.1", "port": slave_config["port"], "name": slave_config["name"]}

    print(f"Redirecting to instance: {min_ping_config}")

    connection = pymysql.connect(host=min_ping_config["ip"],
                                 port=min_ping_config["port"],
                                 user='user0',
                                 password='mysql',
                                 database='sakila',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)

            result = cursor.fetchall()
            print(result)

    return RESPONSE_TEMPLATE.format(_ROUTE_TYPE_="Custom",
                                    _IP_=min_ping_config['ip'],
                                    _NAME_=min_ping_config['name'],
                                    _CONTENT_=result)


@app.route('/random/<sql>')
def random_endpoint(sql):
    # choose a random slave
    config = random.choice(SLAVE_CONFIGS)

    # connect to the database through ssh tunnelling
    connection = pymysql.connect(host="127.0.0.1",
                                 port=config["port"],
                                 user='user0',
                                 password='mysql',
                                 database='sakila',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
            print(result)

    return RESPONSE_TEMPLATE.format(_ROUTE_TYPE_="Random",
                                    _IP_=config['ip'],
                                    _NAME_=config['name'],
                                    _CONTENT_=result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)

