# boto3-ec2-user-setup-skeleton

This project reads a YAML configuration file and set ups ec2 instances with EBS volumes and users to ssh into the machines

---
#### Prerequisites:
- Python 3
- AWS CLI (natively installed or via docker)
- An IAM user with programmatic access for usage with CLI or SDK and permission - `EC2FullAccess`.
- Keys for the before mentioned IAM user.
- `config.yml` should be in the same directory as `program.py`
- No need to install any python package. Auto installation handled by the program
---
- Most of the failing exceptions have already been handled, but will be printed for developer convinience. You might not get issue if above prereq matches.
---

### Setup

- To start, install aws-cli, or use docker

- Setup in `.bachrc` or `.zshrc`
```
alias aws='docker run --rm -ti -v ~/.aws:/root/.aws -v $(pwd):/aws amazon/aws-cli'
```
- Get the latest cli image
```
docker pull amazon/aws-cli
```
- Next, run `aws configure`
```
aws configure
```
- Fill in your credentials to store in ~/.aws folder. Test by running
```
cat ~/.aws/credentials 
```
- Next store the default region in `~/.aws/config` file. For Example
```
[default]
region = us-west-1
```
- Next, run the program by
```
python3 -m program.py
```
---
### You will get output like
---
```
Creating custom security group SECURITY_GROUP_EC2_SSH ....
Security group created!
Fetching the meta data for EC2 machine types based on user filter..
Instances type selected based on user filter !
Generating Key Value Pairs with Key name : ec2-keypair
Key Value Pairs with Key name  ec2-keypair generated sucecesfully~
Creating instances....
instance is in state  {'Code': 0, 'Name': 'pending'}
instance is in state  {'Code': 0, 'Name': 'pending'}
instance is in state  {'Code': 0, 'Name': 'pending'}
Instances created succesfully!!!
Adding 2 users to server i-0ee3032dacc909010
        Obtaining the public IP address for server  i-0ee3032dacc909010 ......
        Public IP address for server  i-0ee3032dacc909010  obtained !!
User creation for server started...
Connecting to instance via root access..
Formating and mounting the file systems
sudo mkfs -t ext4 /dev/xvda && sudo mkdir / && sudo mount /dev/xvda /
Error while mounting disk  ['mke2fs 1.42.9 (28-Dec-2013)\n', '/dev/xvda is apparently in use by the system; will not make a filesystem here!\n']
sudo mkfs -t xfs /dev/xvdf && sudo mkdir /data && sudo mount /dev/xvdf /data
Creating user  user1 on server...
User  user1 created sucessfully!. SSH with Keyfile  /Users/ayush/Downloads/boto3-ec2-user-setup-skeleton/ec2-keypair.pem

Usage > ssh -i "/Users/ayush/Downloads/boto3-ec2-user-setup-skeleton/ec2-keypair.pem" user1@ec2-54-183-31-51.us-west-1.compute.amazonaws.com 


Creating user  user2 on server...
User  user2 created sucessfully!. SSH with Keyfile  /Users/ayush/Downloads/boto3-ec2-user-setup-skeleton/ec2-keypair.pem

Usage > ssh -i "/Users/ayush/Downloads/boto3-ec2-user-setup-skeleton/ec2-keypair.pem" user2@ec2-54-183-31-51.us-west-1.compute.amazonaws.com 
```
- SSH by using the commands generated at the end of the program

Usage >  `ssh -i "/Users/ayush/Downloads/boto3-ec2-user-setup-skeleton/ec2-keypair.pem" user1@ec2-54-183-31-51.us-west-1.compute.amazonaws.com`