import yaml, os, base64
from pip._internal import main

class Utils:
    def __init__(self) -> None:
        pass
    
    def import_or_install(self,package):
        try:
            return __import__(package)
        except ImportError:
            main(['install', package])
            return __import__(package)

class InfraSetup(Utils):

    def __init__(self, filename):
        self.config_filename = filename

        # Importing/Installing boto3
        self.boto3 = super().import_or_install("boto3")
        
        # Importing/Installing paramiko for ssh access to create users in ec2 instances
        self.paramiko = super().import_or_install("paramiko")

        self.user_session = self.boto3.session.Session()
        self.client = self.boto3.client('ec2')
        self.ec2_client = self.user_session.resource('ec2')
        self.user_region = self.user_session.region_name

    def get_images_list(self, server_cfg):
        """
        Fetches the meta data for EC2 machine types from Amazon Servers
        based on the filters proivded by user in server_cfg.
        """
        user_filters = list()
        
        if 'architecture' in server_cfg:
            user_filters.append({'Name': 'architecture', 'Values': [server_cfg['architecture']]})

        if 'root_device_type' in server_cfg:
            user_filters.append({'Name': 'root-device-type', 'Values': [server_cfg['root_device_type']]})

        if 'ami_type' in server_cfg:
            user_filters.append({'Name': 'name', 'Values': [server_cfg['ami_type']+"*"]})
        
        response = self.client.describe_images(Filters=user_filters)

        if response is None or 'Images' not in response or len(response['Images']) == 0:
            raise Exception("No instances found as per the config. Try changing the configuration")

        return response['Images'][0]['ImageId']
    
    def instantiate_instances(self, server_cfg, selected_image_id, key_name, sg_group_name):
        '''
        Instantiates custom ec2 instances based on the configuration provided by the user.
        We add a custom security group with inbound rules for SSH.
        Currently, the inbound is opened for any IP (0.0.0.0) for submission, else
        would have changed for only specific IPs.

        Returns the Ids of instances generated from the AWS. As public IP in not immediately 
        generated, that will be extracted later on.     
        
        General Creation State:
        'State': 'creating'|'available'|'in-use'|'deleting'|'deleted'|'error'   
        '''

        max_count = server_cfg['max_count'] if "max_count" in server_cfg else 1
        min_count = server_cfg['min_count'] if "min_count" in server_cfg else 1
        instance_type = server_cfg['instance_type'] if "instance_type" in server_cfg else 't2.micro'
        
        response = self.ec2_client.create_instances(
            ImageId = selected_image_id, 
            MinCount = min_count, 
            MaxCount = max_count,
            InstanceType = instance_type,
            KeyName = key_name,
            SecurityGroups = [ sg_group_name ]
        )
        
        instance_ids = []
        for instance in response:
            instance_ids.append(instance.instance_id)
        
        return instance_ids
    
    def generate_key_pair(self):
        """
        For generating key value pairs for which the 2 users can login to the machines.
        """
        keyname = "ec2-keypair"
        reqd_permission = '400'
        
        try:
            
            # calling the boto ec2 function to create a key pair
            key_pair = self.client.create_key_pair(KeyName = keyname)

            # creating a file to store the key locally
            outfile = open(keyname + '.pem','w')
            
            # capturing the key and store it in a file
            KeyPairOut = str(key_pair['KeyMaterial'])
            
            outfile.write(KeyPairOut)

            # Output key path
            key_path = os.path.join(os.getcwd(), keyname + ".pem")
            
            # Changing file permissions for key
            os.chmod(key_path, int(reqd_permission, base=8))

            # If the above doesn't work, new for Python 3
            # os.chmod(key_path , '0o400')
            
        except Exception as e:
            # If the same key already existing, we are ignoring it. Might not be the case for production env.
            if e.response['Error']['Code'] == "InvalidKeyPair.Duplicate":
                pass
            else:
                print("Error while generating Key pair ", e)
        finally:
            return keyname
    
    def create_security_group(self):
        """
        Creating custom security group with added support for SSH access for Inbound access.
        """
        group_name = 'SECURITY_GROUP_EC2_SSH'
        try:
            response = self.client.describe_vpcs()
            vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')

            response = self.client.create_security_group(GroupName = group_name,
                                                Description = 'This security group allows SSH access to EC2 instances to which this SG will assigned to',
                                                VpcId = vpc_id)
            security_group_id = response['GroupId']
            print('Security Group Created %s in vpc %s.' % (security_group_id, vpc_id))

            data = self.client.authorize_security_group_ingress(
                GroupId = security_group_id,
                IpPermissions = [
                    {'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                ])
            print('Ingress Successfully Set for Security Group')
            if data['ResponseMetadata']['HTTPStatusCode'] == 200:
                return group_name
            else:
                raise Exception("Unable to create Security Group")

        except Exception as e:
            if e.response['Error']['Code'] == 'InvalidGroup.Duplicate':
                return group_name
            print(e) 

    def fetch_sg_id(self, group_name):
        response = self.client.describe_security_groups(
                    Filters=[
                        dict(Name='group-name', Values=[group_name])
                    ]
                )
        group_id = response['SecurityGroups'][0]['GroupId']
        return group_id
    

    def add_users(self, server_ids, key_name, users_cfg):
        """
        Adding new users to instances [server_ids] and attaching Key Pair [key_name]
        """
        for server_id in server_ids:
            server_host = self.get_host(server_id)
            self.add_user(server_host, key_name, users_cfg)
            
    def get_host(self, server_id):
        """
            Obtaining the public dns name for SSH connection
        """
        instances = self.ec2_client.instances.filter(
            Filters=[{'Name': 'instance-id', 'Values': [server_id]}])

        for instance in instances:
            return instance.public_dns_name
        
        raise Exception("Error : Public IP for instance id : ",server_id," not generated yet")

    def add_user(self, server_host, key_name, users_cfg):
        """
        Creating an SSH client to add users.
        Obtaining the public key for the PEM file using the ssh-keygen of macOS
        """
        ssh = self.paramiko.SSHClient()
        key_path = os.path.join(os.getcwd(), key_name + ".pem")
        
        # Early exit to improve the code flow
        if not os.path.exists(key_path):
            raise Exception("Invalid File Path :",key_path)
        
        private_key = self.paramiko.RSAKey.from_private_key_file(key_path)

        # Extracting the public key from private key
        # Will be added to .ssh directory for different users, to allow SSH login
        stream = os.popen("ssh-keygen -y -f "+ key_path)
        public_key = stream.read()[:-1]
        
        ssh.set_missing_host_key_policy(self.paramiko.AutoAddPolicy())
        ssh.connect(hostname = server_host, username = "ec2-user", pkey = private_key)

        # Copying SSH file to Instance for User creation.
        # sftp = ssh.open_sftp()
        # shell_path = os.path.join(os.getcwd(),"shell_script.sh")
        # sftp.put(shell_path, "/home/ec2-user/shell_script.sh")

        for user_cfg in users_cfg:
            username = user_cfg['login']
            
            # Adding new user
            _, _, ssh_stderr = ssh.exec_command("sudo adduser " + username)
            
            # Adding required files and folders to add public key data
            _, _, ssh_stderr = ssh.exec_command("sudo -H -u "+username+" bash -c 'mkdir ~/.ssh ; chmod 700 ~/.ssh; cd ~/.ssh && touch authorized_keys; chmod 600 ~/.ssh/authorized_keys;'")
            err = ssh_stderr.readlines()
            if err:
                print("Error while creating ~/.ssh or authorized_keys file for user ", username," : " , err)
            
            
            # Encoding the public key as it contains a whitespace character.
            # The echo command considers it 2 different strings. This leads to issues while writing into the file.
            _, _, ssh_stderr = ssh.exec_command("sudo -H -u "+username+" bash -c 'echo -n "+str(base64.b64encode(public_key.encode('ascii')))[2:-1]+" | base64 --decode >> ~/.ssh/authorized_keys'")
            err = ssh_stderr.readlines()
            if err:
                print("Error while writing in the ~/.ssh/authorized_keys for user ", username," : " , err)

    def create_and_attach_volume(self, volumes_cfg, instance_ids, DryRunFlag):
        
        try:
            for volume_cfg in volumes_cfg:
            
                size_gb = volume_cfg['size_gb'] if 'size_gb' in volume_cfg else 10
                vol_type = volume_cfg['vol_type'] if 'vol_type' in volume_cfg else 'gp2'
                device = volume_cfg['device'] if 'device' in volume_cfg else '/dev/xvda'
                
                response = self.client.create_volume(
                    AvailabilityZone = self.user_region + "b",
                    Encrypted = False,
                    Size = size_gb,
                    VolumeType = vol_type,
                    DryRun = DryRunFlag
                )

                if response['ResponseMetadata']['HTTPStatusCode']== 200:
                    volume_id = response['VolumeId']
                    print('***volume:', volume_id)

                    self.client.get_waiter('volume_available').wait(
                        VolumeIds = [volume_id],
                        DryRun = DryRunFlag
                        )
                    print('***Success!! volume:', volume_id, 'created...')

                    
                    # for instance_id in instance_ids:
                    instance_id = "i-00b77133a8956043d"
                    VolumeId = "VolumeId"
                    print(instance_id)
                    attach_response = self.client.attach_volume(
                        Device = device,
                        InstanceId = instance_id,
                        VolumeId = volume_id,
                        DryRun = DryRunFlag
                    )
                    print(attach_response)

        except Exception as e:
                print('***Failed to create the volume...')
                print(type(e), ':', e)
                volumes = self.client.volumes.all()
                for volume in volumes:
                    print('Deleting volume {0}'.format(volume.id))
                    volume.delete()

    def setup(self):
        with open(self.config_filename, 'r') as stream:
            try:
                config = yaml.safe_load(stream)
                server_cfg = config['server']
                volume_cfg = server_cfg['volumes']
                users_cfg = server_cfg['users']

                # Creating new security group.
                # Could have used authorize_security_group_ingress() as well after creating instance.
                sg_group_name = self.create_security_group()

                # Obtaining specific Instance Type, AMI based on requirement.
                selected_image_id = self.get_images_list(server_cfg)

                # Generated Key Value Pairs
                key_name = self.generate_key_pair()
                
                # New servers started.
                server_ids = self.instantiate_instances(server_cfg, selected_image_id,key_name, sg_group_name)

                # Adding users and attaching them to the public key.
                self.add_users(server_ids, key_name, users_cfg)
                
                # self.create_and_attach_volume(volume_cfg, server_ids, DryRunFlag = False)

            except yaml.YAMLError as exc:
                print(exc)


infra = InfraSetup("config.yml")
infra.setup()