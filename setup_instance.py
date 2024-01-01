import boto3
from botocore.exceptions import ClientError
from os import path
import constants


EC2_RESOURCE = boto3.resource('ec2')
EC2_CLIENT = boto3.client('ec2')


def create_ec2(instance_type, sg_id, key_name, user_data, instance_name):
    """
        Crée une instance EC2 avec les paramètres spécifiés.

        Args:
            instance_type (str): Type de l'instance (par exemple, m4.large).
            sg_id (str): ID du groupe de sécurité.
            key_name (str): Nom de la clé SSH.
            user_data (str): Données utilisateur pour l'initialisation de l'instance.
            instance_name (str): Nom de l'instance.

        Returns:
            Instance EC2 créée.
        """
    instance = EC2_RESOURCE.create_instances(
        ImageId='ami-0149b2da6ceec4bb0',
        MinCount=1,
        MaxCount=1,
        UserData=user_data,
        InstanceType=instance_type,
        Monitoring={'Enabled': True},
        SecurityGroupIds=[sg_id],
        KeyName=key_name,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': instance_name
                    },
                ]
            },
        ]
    )[0]
    print(f'{instance} is starting')
    return instance


def create_security_group(sg_name):
    """
    Crée un groupe de sécurité avec des règles personnalisées.

    Args:
        sg_name (str): Nom du groupe de sécurité.

    Returns:
        ID du groupe de sécurité créé.
    """
    security_group_id = None
    try:
        response = EC2_CLIENT.create_security_group(
            GroupName=sg_name,
            Description=f'Security group for {sg_name}'
        )
        security_group_id = response['GroupId']
        print(f'Successfully created security group {security_group_id}')

        # Define the security group rules based on the sg_name
        if sg_name == 'proxy-sg':
            sec_group_rules = [
                {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 1186, 'ToPort': 1186, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ]
        elif sg_name == 'gatekeeper-sg':
            sec_group_rules = [
                {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ]
        elif sg_name == 'trustedhost-sg':
            sec_group_rules = []
        else:
            raise ValueError("Unknown security group")

        data = EC2_CLIENT.authorize_security_group_ingress(GroupId=security_group_id, IpPermissions=sec_group_rules)
        print(f'Successfully updated security group {sg_name} rules with: {sec_group_rules}')
        return security_group_id
    except ClientError as e:
        try:  # if security group exists already, find the security group id
            response = EC2_CLIENT.describe_security_groups(
                Filters=[
                    dict(Name='group-name', Values=[sg_name])
                ])
            security_group_id = response['SecurityGroups'][0]['GroupId']
            print(f'Security group already exists with id {security_group_id}.')
            return security_group_id
        except ClientError as e:
            print(e)
            exit(1)

def update_security_group(sg_id, ip_protocol, from_port, to_port, cidr_ip):
    """
    Met à jour un groupe de sécurité avec une nouvelle règle entrante.

    Args:
        sg_id (str): ID du groupe de sécurité.
        ip_protocol (str): Protocole (par exemple, 'tcp').
        from_port (int): Port de début.
        to_port (int): Port de fin.
        cidr_ip (str): CIDR IP pour la source (par exemple, '203.0.113.0/24').
    """
    try:
        EC2_CLIENT.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {
                    'IpProtocol': ip_protocol,
                    'FromPort': from_port,
                    'ToPort': to_port,
                    'IpRanges': [{'CidrIp': cidr_ip}]
                }
            ]
        )
        print(f'Successfully updated security group {sg_id} with new rule: {cidr_ip}')
    except ClientError as e:
        print(f'Error updating security group {sg_id}: {e}')


def create_private_key_filename(key_name):
    """
    Génère un nom de fichier pour sauvegarder la paire de clés.

    Args:
        key_name (str): Nom de la clé.

    Returns:
        Nom de fichier pour la clé privée.
    """
    return f'./private_key_{key_name}.pem'


def create_key_pair(key_name, private_key_filename):
    """
    Génère une paire de clés pour accéder à l'instance.

    Args:
        key_name (str): Nom de la clé.
        private_key_filename (str): Nom de fichier pour sauvegarder la clé privée.
    """
    response = EC2_CLIENT.describe_key_pairs()
    kp = [kp for kp in response['KeyPairs'] if kp['KeyName'] == key_name]
    if len(kp) > 0 and not path.exists(private_key_filename):
        print(f'{key_name} already exists distantly, but the private key file has not been downloaded. Either delete the remote key or download the associate private key as {private_key_filename}.')
        exit(1)

    print(f'Creating {private_key_filename}')
    if path.exists(private_key_filename):
        print(f'Private key {private_key_filename} already exists, using this file.')
        return

    response = EC2_CLIENT.create_key_pair(KeyName=key_name)
    with open(private_key_filename, 'w+') as f:
        f.write(response['KeyMaterial'])
    print(f'{private_key_filename} written.')


def retrieve_instance_ip_dns(instance_id):
    """
    Récupère l'IP publique, l'IP privée et le DNS privé d'une instance.

    Args:
        instance_id (str): ID de l'instance.

    Returns:
        Tuple contenant l'IP publique, l'IP privée et le DNS privé de l'instance.
    """
    print(f'Retrieving instance {instance_id} public and private IP...')
    instance_config = EC2_CLIENT.describe_instances(InstanceIds=[instance_id])
    instance_data = instance_config["Reservations"][0]['Instances'][0]
    instance_public_ip = instance_data['PublicIpAddress']
    instance_private_ip = instance_data['PrivateIpAddress']
    instance_dns_name = instance_data['PrivateDnsName']
    print(f'Public IP: {instance_public_ip}, Private IP: {instance_private_ip}, Private DNS: {instance_dns_name}')
    return instance_public_ip, instance_private_ip, instance_dns_name




def start_instance(instance_type, sg_id, user_data, instance_name):
    """
    Démarre une instance avec la configuration spécifiée.

    Args:
        instance_type (str): Type de l'instance.
        sg_id (str): ID du groupe de sécurité.
        user_data (str): Données utilisateur pour l'instance.
        instance_name (str): Nom de l'instance.
    """
    # Create the instance with the key pair
    key_name = 'PROJET_KEY'  # Assurez-vous que cette clé est correctement définie
    instance = create_ec2(instance_type, sg_id, key_name, user_data, instance_name)
    print(f'Waiting for instance {instance.id} to be running...')
    instance.wait_until_running()
    # Get the instance's IP and DNS name
    instance_ip, instance_private_ip, instance_dns_name = retrieve_instance_ip_dns(instance.id)
    print(f'Instance {instance.id} started. Access it with \'ssh -i {private_key_filename} ubuntu@{instance_ip}\'')

    return instance_ip, instance_private_ip, instance_dns_name, instance_name


def generate_cluster_config_file(instance_infos):
    """
    Génère les fichiers de configuration nécessaires pour le cluster.

    Args:
        instance_infos (list of dict): Informations de configuration des instances.
    """
    template_master = constants.TEMPLATE_MASTER

    template_slave = constants.TEMPLATE_SLAVE

    template_sql_server = constants.TEMPLATE_SQL_SERVER

    with open('master_node/config.ini', 'w+') as f:
        f.write(template_master.format(manager_hostname=instance_infos[0]['dns'],
                                slave_0_hostname=instance_infos[1]['dns'],
                                slave_1_hostname=instance_infos[2]['dns'],
                                slave_2_hostname=instance_infos[3]['dns']))
    with open('master_node/my.cnf', 'w+') as f:
        f.write(template_slave.format(manager_hostname=instance_infos[0]['dns']))
    with open('master_node/server_conf.conf', 'w+') as f:
        f.write(template_sql_server.format(manager_hostname=instance_infos[0]['dns']))

def generate_proxy_py(instance_infos):
    """
    Génère le fichier Python pour le proxy utilisé dans le modèle de cloud proxy.

    Args:
        instance_infos (list of dicts): Informations de configuration des instances.
    """
    with open('proxy_app_temp.py', 'r') as f:
        lines = f.read()
    formatted_lines = lines.replace('_MASTER_HOSTNAME_', instance_infos[0]['ip']) \
                            .replace("_SLAVE_1_HOSTNAME_", instance_infos[1]['ip']) \
                            .replace("_SLAVE_2_HOSTNAME_", instance_infos[2]['ip']) \
                            .replace("_SLAVE_3_HOSTNAME_", instance_infos[3]['ip'])
    with open('proxy_app.py', 'w+') as f_api:
        f_api.write(formatted_lines)


if __name__ == "__main__":
    # Create a key pair
    key_name = 'PROJET_KEY'
    private_key_filename = create_private_key_filename(key_name)
    create_key_pair(key_name, private_key_filename)

    # Create a security group
    proxy_sg_id = create_security_group('proxy-sg')
    gatekeeper_sg_id = create_security_group('gatekeeper-sg')
    trustedhost_sg_id = create_security_group('trustedhost-sg')

    # create the cluster
    instance_infos = []

    # Define instance roles and their corresponding types
    instance_configurations = {
        "Master": "t2.micro",
        "Child_1": "t2.micro",
        "Child_2": "t2.micro",
        "Child_3": "t2.micro",
        "Proxy": "t2.large",
        "Standalone": "t2.micro",
        "Trustedhost": "t2.large",
        "Gatekeeper": "t2.large"
    }

    child_counter = 0  # Counter for child instances

    gatekeeper_private_ip = None
    trustedhost_private_ip = None

    for role, instance_type in instance_configurations.items():
        if role == "Proxy":
            sg_id = proxy_sg_id
            user_data = constants.USER_DATA_PROXY
        elif role == "Gatekeeper":
            sg_id = gatekeeper_sg_id
            user_data = constants.USER_DATA_GATEKEEPER
        elif role == "Trustedhost":
            sg_id = trustedhost_sg_id
            user_data = constants.USER_DATA_TRUSTEDHOST
        else:
            sg_id = proxy_sg_id  # Define a default security group for other roles
            user_data = ""
        instance_ip, instance_private_ip, instance_dns_name, instance_name = start_instance(instance_type, sg_id, user_data, role)
        if role == 'Gatekeeper':
            gatekeeper_private_ip = instance_private_ip
        elif role == 'Trustedhost':
            trustedhost_private_ip = instance_private_ip
        if 'Child' in role:
            # This is a child instance
            instance_infos.append(
                {'public_ip': instance_ip, 'private_ip': instance_private_ip, 'dns': instance_dns_name, 'name': instance_name, 'child_idx': child_counter})
            child_counter += 1
        else:
            # Other instances
            instance_infos.append({'public_ip': instance_ip, 'private_ip': instance_private_ip, 'dns': instance_dns_name, 'name': instance_name})

    # save the instances information to env_variables.txt to use them in the sh part
    with open('env_variables.txt', 'w+') as f:
        for instance_info in instance_infos:
            instance_role = instance_info['name'].split('-')[-1]  # Extrait le rôle à partir du nom
            if instance_role == "Master":
                f.write(f'INSTANCE_IP_MASTER_IP={instance_info["public_ip"]}\n')
                f.write(f'INSTANCE_PRIVATE_IP_MASTER_IP={instance_info["private_ip"]}\n')
                f.write(f'INSTANCE_IP_MASTER_DNS={instance_info["dns"]}\n')
            elif instance_role == "Proxy":
                f.write(f'INSTANCE_IP_PROXY_IP={instance_info["ip"]}\n')
                f.write(f'INSTANCE_PRIVATE_IP_PROXY_IP={instance_info["private_ip"]}\n')
                f.write(f'INSTANCE_IP_PROXY_DNS={instance_info["dns"]}\n')
            elif instance_role == "Standalone":
                f.write(f'INSTANCE_IP_STANDALONE_IP={instance_info["ip"]}\n')
                f.write(f'INSTANCE_PRIVATE_IP_STANDALONE_IP={instance_info["private_ip"]}\n')
                f.write(f'INSTANCE_IP_STANDALONE_DNS={instance_info["dns"]}\n')
            elif instance_role == "Trustedhost":
                f.write(f'INSTANCE_IP_TRUSTEDHOST_IP={instance_info["ip"]}\n')
                f.write(f'INSTANCE_PRIVATE_IP_TRUSTEDHOST_IP={instance_info["private_ip"]}\n')
                f.write(f'INSTANCE_IP_TRUSTEDHOST_DNS={instance_info["dns"]}\n')
            elif instance_role == "Gatekeeper":
                f.write(f'INSTANCE_IP_GATEKEEPER_IP={instance_info["ip"]}\n')
                f.write(f'INSTANCE_PRIVATE_IP_GATEKEEPER_IP={instance_info["private_ip"]}\n')
                f.write(f'INSTANCE_IP_GATEKEEPER_DNS={instance_info["dns"]}\n')
            elif 'child_idx' in instance_info:
                f.write(f'INSTANCE_IP_CHILD_IP_{instance_info["child_idx"]}={instance_info["ip"]}\n')
                f.write(f'INSTANCE_PRIVATE_IP_CHILD_IP_{instance_info["child_idx"]}={instance_info["private_ip"]}\n')
                f.write(f'INSTANCE_IP_CHILD_DNS_{instance_info["child_idx"]}={instance_info["dns"]}\n')
        f.write(f'PRIVATE_KEY_FILE={private_key_filename}\n')
    print('Wrote instance\'s IP and private key filename to env_variables.txt')

    if gatekeeper_private_ip:
        update_security_group(trustedhost_sg_id, 'tcp', 80, 80, f'{gatekeeper_private_ip}/32')

    if trustedhost_private_ip:
        update_security_group(proxy_sg_id, 'tcp', 80, 80, f'{trustedhost_private_ip}/32')

    # generate the various configuration files for the cluster : my.cnf, config.ini, server_conf.conf
    generate_cluster_config_file(instance_infos)
    # generate the proxy python file (flask API) : app.py
    generate_proxy_py(instance_infos)
