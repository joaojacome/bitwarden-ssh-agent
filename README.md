# Bitwarden SSH Agent

## Requirements

* You need to have the bitwarden cli `bw` installed
* ssh-agent must be running in the current session

## What it does?

* connects to bitwarden using the bitwarden cli
* looks for a folder called `ssh-agent`
* loads the ssh key for each item in that folder

##  How to use it

`$ ./start.sh`

Fill in you login information 


## Storing the keys in BitWarden

1. Create a folder called 'ssh-agent'
2. Add an new secure note to that folder
3. Upload the private_key as an attachment
4. add the custom field `private`, containing the private key filename


## Improvements to be made

* Find a way to extract the attachment from bitwarden in memory, instead of creating a file for it
