# Bitwarden SSH Agent

## Requirements
* You need to have the [Bitwarden CLI tool](https://bitwarden.com/help/cli/) installed and available in the `$PATH` as `bw`. See below for detailed instructions.
* `ssh-agent` must be running in the current session.

## Installation
Just save the file `bw_add_sshkeys.py` in a folder where it can by found when calling it from the command line. On linux you can see these folders by running `echo $PATH` from the command line. To install for a single user, you can - for example - save the script under `~/.local/bin/` and make it executable by running `chmod +x ~/.local/bin/bw_add_sshkeys.py`.

## What does it do?
Fetches SSH keys stored in Bitwarden vault and adds them to `ssh-agent`.

##  How to use it
1. Run,
   ```shell
   ./bw_add_sshkeys.py
   ```
2. Enter your Bitwarden credentials, if a Bitwarden vault session is not already set.
3. (optional) Enter your SSH keys' passphrases if they're not stored in your Bitwarden.

## Storing the keys in BitWarden
1. Create a folder called `ssh-agent` (can be overridden on the command line).
2. Add an new secure note to that folder.
3. Upload the private key as an attachment.
4. Add the custom field `private` (can be overridden on the command line), containing the file name of the private key attachment.
5. (optional) If your key is encrypted with passphrase and you want it to decrypt automatically, save passphrase into custom field `passphrase` (field name can be overriden on the command line). You can create this field as `hidden` if you don't want the passphrase be displayed by default.
6. Repeat steps 2-5 for each subsequent key

## Command line overrides
* `--debug`/`-d` - Show debug output
* `--foldername`/`-f` - Folder name to use to search for SSH keys _(default: ssh-agent)_
* `--customfield`/`-c` - Custom field name where private key filename is stored _(default: private)_
* `--passphrasefield`/`-p` - Custom field name where passphrase for the key is stored _(default: passphrase)_
* `--session`/`-s` - session key of bitwarden

## Setting up the Bitwarden CLI tool
Download the [Bitwarden CLI](https://bitwarden.com/help/cli/), extract the binary from the zip file, make it executable and add it to your path so that it can be found on the command line.

On linux you will likely want to move the executable to `~/.local/bin` and make it executable `chmod +x ~/.local/bin/bw`. `~/.local/bin` is likely already set as a path. You can confirm that by running `which bw`, which should return the path to the executable. You can use the same approach to turn `bw_add_sshkeys.py` into an executable.

If you want to build the Bitwarden CLI by yourself, see [these instructions on the bitwarden github page](https://contributing.bitwarden.com/getting-started/clients/cli).