#!/usr/bin/env bash
set -e -x

# Initialisation
WORKDIR=$(cd "$(dirname "$0")" && pwd)
export WORKDIR
VENV="$PWD/venv"

# Création de l'environnement virtuel si nécessaire
[[ ! -d $VENV ]] && python3 -m venv "$VENV"
source "$VENV/scripts/activate"

# Installation des dépendances
echo "Installation des dépendances"
pip3 install -r requirements.txt

# Configuration initiale
python setup_instance.py
source env_variables.txt
chmod 600 "$PRIVATE_KEY_FILE"

# Fonctions pour installer MySQL Cluster sur les instances
install_mysql_cluster_child() {
    sudo apt-get update && sudo apt-get install -y libncurses5 libclass-methodmaker-perl
    mkdir -p /opt/mysqlcluster/home && mkdir -p /var/lib/mysqlcluster
    cd /opt/mysqlcluster/home && \
        wget --progress=bar:force:noscroll https://dev.mysql.com/get/Downloads/MySQL-Cluster-7.6/mysql-cluster-community-data-node_7.6.6-1ubuntu18.04_amd64.deb && \
        dpkg -i mysql-cluster-community-data-node_7.6.6-1ubuntu18.04_amd64.deb
}

install_mysql_cluster_master() {
    sudo apt-get update && sudo apt-get install -y libncurses5 libaio1 libmecab2
    mkdir -p /opt/mysqlcluster/home && mkdir -p /var/lib/mysqlcluster
    wget --progress=bar:force:noscroll https://dev.mysql.com/get/Downloads/MySQL-Cluster-7.6/mysql-cluster-community-management-server_7.6.6-1ubuntu18.04_amd64.deb && \
    dpkg -i mysql-cluster-community-management-server_7.6.6-1ubuntu18.04_amd64.deb
    wget --progress=bar:force:noscroll http://dev.mysql.com/get/Downloads/MySQL-Cluster-7.2/mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz
    tar -xf mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz
    mv mysql-cluster-gpl-7.2.1-linux2.6-x86_64 mysqlc
    echo "alias ndb_mgm=/home/ubuntu/mysqlc/bin/ndb_mgm" >> /home/ubuntu/.profile
}

install_mysql_server() {
    wget --progress=bar:force:noscroll https://dev.mysql.com/get/Downloads/MySQL-Cluster-8.0/mysql-cluster_8.0.31-1ubuntu20.04_amd64.deb-bundle.tar
    mkdir install
    tar -xvf mysql-cluster_8.0.31-1ubuntu20.04_amd64.deb-bundle.tar -C install/
    cd install && \
        sudo dpkg -i *.deb && \
        sudo apt-get install -y -f
    sudo systemctl start mysql
    sleep 1
    sudo mysql -u root --password=mysql -e "CREATE USER 'user0'@'%' IDENTIFIED BY 'mysql';"
    sudo mysql -u root --password=mysql -e "GRANT ALL PRIVILEGES ON *.* TO 'user0'@'%' WITH GRANT OPTION;"
    sudo mysql -u root --password=mysql -e "FLUSH PRIVILEGES;"
    sleep 3 && sudo systemctl restart mysql && sleep 3
    sudo mkdir -p /opt/mysqlcluster/deploy/conf /opt/mysqlcluster/deploy/ndb_data /opt/mysqlcluster/deploy/mysqld_data /var/lib/mysqlcluster && \
                                                    sudo cp /home/ubuntu/config.ini /opt/mysqlcluster/deploy/conf/ && \
                                                    sudo ndb_mgmd -f /opt/mysqlcluster/deploy/conf/config.ini --initial --configdir=/opt/mysqlcluster/deploy/conf/ && \
    sleep 1
    sudo bash -c 'cat /home/ubuntu/server_conf.conf >> /etc/mysql/my.cnf'
    wget --progress=bar:force:noscroll https://downloads.mysql.com/docs/sakila-db.tar.gz
    tar -xvf sakila-db.tar.gz
    echo "Installing Sakila..."
    mysql -u user0 --password=mysql -e "SOURCE sakila-db/sakila-schema.sql"
    mysql -u user0 --password=mysql -e "SOURCE sakila-db/sakila-data.sql"
    systemctl status mysql
}

# Fonction pour vérifier la disponibilité SSH
wait_for_ssh() {
    while ! nc -vzw 1 "$1" 22; do
        echo "En attente de SSH sur $1"
        sleep 3
    done
    echo "SSH disponible sur $1"
}

# Installation sur les instances
install_on_instance() {
    INSTANCE_IP=$1
    SCRIPT=$2
    wait_for_ssh "$INSTANCE_IP"
    scp -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" "$SCRIPT" ubuntu@"$INSTANCE_IP":~
    ssh -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" ubuntu@"$INSTANCE_IP" "chmod +x ~/$SCRIPT && sudo ~/$SCRIPT"
}

# Installation sur le maître et les enfants
install_on_instance "$INSTANCE_IP_MASTER_IP" install_mysql_cluster_master
for ip in $INSTANCE_IP_CHILD_IP_0 $INSTANCE_IP_CHILD_IP_1 $INSTANCE_IP_CHILD_IP_2; do
    install_on_instance "$ip" install_mysql_cluster_child
done

# Configuration supplémentaire sur les nœuds enfants
for ip in $INSTANCE_IP_CHILD_IP_0 $INSTANCE_IP_CHILD_IP_1 $INSTANCE_IP_CHILD_IP_2; do
    scp -i "$PRIVATE_KEY_FILE" systemd/ndbd.service master_node/my.cnf ubuntu@"$ip":~
    ssh -i "$PRIVATE_KEY_FILE" ubuntu@"$ip" 'sudo mkdir -p /opt/mysqlcluster/deploy/mysqld_data && \
                                        sudo cp ndbd.service /etc/systemd/system/ && \
                                        sudo systemctl daemon-reload'
done

# Démarrage des services
start_services() {
    for ip in $INSTANCE_IP_CHILD_IP_0 $INSTANCE_IP_CHILD_IP_1 $INSTANCE_IP_CHILD_IP_2; do
        ssh -i "$PRIVATE_KEY_FILE" ubuntu@"$ip" 'sudo systemctl start ndbd.service && sudo systemctl status ndbd.service'
    done
}

install_on_instance "$INSTANCE_IP_MASTER_IP" install_mysql_server
start_services

# Vérification du cluster
ssh -i "$PRIVATE_KEY_FILE" ubuntu@"$INSTANCE_IP_MASTER_IP" 'sudo systemctl restart mysql && ndb_mgm -e show'

# Déploiement de l'application proxy_app.py sur le serveur proxy
scp -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" proxy_app.py ubuntu@"$INSTANCE_IP_PROXY_IP":~
ssh -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" ubuntu@"$INSTANCE_IP_PROXY_IP" 'chmod 755 proxy_app.py && export FLASK_APP=proxy_app.py && sudo flask run --host 0.0.0.0 --port 80'

# Deploy gatekeeper.py to the Gatekeeper instance
echo "Successfully setup cluster !"
echo "Deploying gatekeeper.py to Gatekeeper instance..."
scp -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" gatekeeper.py ubuntu@"$INSTANCE_IP_GATEKEEPER_IP":~

# Start the Flask application on the Gatekeeper instance with the environment variable
echo "Starting gatekeeper Flask app on Gatekeeper instance..."
ssh -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" ubuntu@"$INSTANCE_IP_GATEKEEPER_IP" "export INSTANCE_PRIVATE_IP_TRUSTEDHOST_IP=$INSTANCE_PRIVATE_IP_TRUSTEDHOST_IP && nohup python3 gatekeeper.py > gatekeeper.log 2>&1 &"

# Deploy trustedhost.py to the TrustedHost instance
echo "Deploying trustedhost.py to TrustedHost instance..."
scp -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" trustedhost.py ubuntu@"$INSTANCE_IP_TRUSTEDHOST_IP":~

# Start the Flask application on the TrustedHost instance with the environment variable
echo "Starting trustedhost Flask app on TrustedHost instance..."
ssh -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" ubuntu@"$INSTANCE_IP_TRUSTEDHOST_IP" "export INSTANCE_PRIVATE_IP_PROXY_IP=$INSTANCE_PRIVATE_IP_PROXY_IP && nohup python3 trustedhost.py > trustedhost.log 2>&1 &"
echo "Installation terminée"
