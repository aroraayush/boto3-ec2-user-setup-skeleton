#! /bin/bash

USERNAME=$1;
PUBLIC_KEY=$2" "$3;

echo $USERNAME;
echo $PUBLIC_KEY;
echo "$USER"

sudo adduser $USERNAME
sudo -H -u $USERNAME bash -c 'echo "Logged in as $USER"' 
sudo -H -u $USERNAME bash -c 'rm -rf ~/.ssh' 
sudo -H -u $USERNAME bash -c 'mkdir ~/.ssh' 
sudo -H -u $USERNAME bash -c 'chmod 700 ~/.ssh' 
sudo -H -u $USERNAME bash -c 'cd ~/.ssh && touch authorized_keys' 
sudo -H -u $USERNAME bash -c 'echo "$PUBLIC_KEY" > ~/.ssh/authorized_keys'
sudo -H -u $USERNAME bash -c 'chmod 600 ~/.ssh/authorized_keys' 
sudo -H -u $USERNAME bash -c 'echo "Logging out as $USER"' 

