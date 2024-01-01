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
install_on_instance "$INSTANCE_IP_MASTER_IP" install_mysql_cluster_master.sh
for ip in $INSTANCE_IP_CHILD_IP_0 $INSTANCE_IP_CHILD_IP_1 $INSTANCE_IP_CHILD_IP_2; do
    install_on_instance "$ip" install_mysql_cluster_child.sh
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

install_on_instance "$INSTANCE_IP_MASTER_IP" install_mysql_server.sh
start_services

# Vérification du cluster
ssh -i "$PRIVATE_KEY_FILE" ubuntu@"$INSTANCE_IP_MASTER_IP" 'sudo systemctl restart mysql && ndb_mgm -e show'

# Déploiement de l'application proxy_app.py sur le serveur proxy
scp -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" proxy_app.py ubuntu@"$INSTANCE_IP_PROXY_IP":~
ssh -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" ubuntu@"$INSTANCE_IP_PROXY_IP" 'chmod 755 proxy_app.py && export FLASK_APP=proxy_app.py && sudo flask run --host 0.0.0.0 --port 80'

# Déploiement de l'application Gatekeeper
scp -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" gatekeeper_app.py ubuntu@"$INSTANCE_IP_GATEKEEPER":~
ssh -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" ubuntu@"$INSTANCE_IP_GATEKEEPER" 'chmod 755 gatekeeper_app.py && export FLASK_APP=gatekeeper_app.py && sudo flask run --host 0.0.0.0 --port 80'

# Déploiement de l'application TrustedHost
scp -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" trustedhost_app.py ubuntu@"$INSTANCE_IP_TRUSTEDHOST":~
ssh -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" ubuntu@"$INSTANCE_IP_TRUSTEDHOST" 'chmod 755 trustedhost_app.py && export FLASK_APP=trustedhost_app.py && sudo flask run --host 0.0.0.0 --port 80'

echo "Installation terminée"
