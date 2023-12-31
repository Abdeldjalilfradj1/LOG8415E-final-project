USER_DATA_PROXY = """#!/bin/bash
apt update && \
    apt install -y python3 python3-flask python3-pip && \
    pip install pymysql sshtunnel pythonping"""

USER_DATA_TRUSTEDHOST = """#!/bin/bash
apt update && \
    apt install -y python3 python3-flask python3-pip && \
    pip install pymysql sshtunnel pythonping"""

USER_DATA_GATEKEEPER = """#!/bin/bash
apt update && \
    apt install -y python3 python3-flask python3-pip && \
    pip install pymysql sshtunnel pythonping"""

TEMPLATE_SLAVE = """[mysql_cluster]
# Options for NDB Cluster processes:
ndb-connectstring={manager_hostname}  # location of cluster manager
"""

TEMPLATE_SQL_SERVER = """[mysqld]
# Options for mysqld process:
ndbcluster                      # run NDB storage engine

[mysql_cluster]
# Options for NDB Cluster processes:
ndb-connectstring={manager_hostname}  # location of management server"""

TEMPLATE_MASTER = """
[ndbd default]
NoOfReplicas=3	# Number of replicas

[ndb_mgmd]
# Management process options:
hostname={manager_hostname} # Hostname of the manager
datadir=/var/lib/mysqlcluster 	# Directory for the log files

[ndbd]
hostname={slave_0_hostname} # Hostname/IP of the first data node
NodeId=2			# Node ID for this data node
datadir=/opt/mysqlcluster/deploy/mysqld_data	# Remote directory for the data files

[ndbd]
hostname={slave_1_hostname} # Hostname/IP of the first data node
NodeId=3			# Node ID for this data node
datadir=/opt/mysqlcluster/deploy/mysqld_data	# Remote directory for the data files

[ndbd]
hostname={slave_2_hostname} # Hostname/IP of the second data node
NodeId=4			# Node ID for this data node
datadir=/opt/mysqlcluster/deploy/mysqld_data	# Remote directory for the data files

[mysqld]
# SQL node options:
hostname={manager_hostname}
"""