# Bitwarden SSH Agent

## Requirements
* You need to have the [Bitwarden CLI tool](https://github.com/bitwarden/cli) installed and available in the `$PATH` as `bw`.
* `ssh-agent` must be running in the current session.

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
5. (optional) If your key is encrypted with passphrase and you want it to decrypt automatically, save passphrase into custom field `passphrase` (field name can be overriden on the command line)
6. Repeat steps 2-5 for each subsequent key

## Command line overrides
* `--debug`/`-d` - Show debug output
* `--foldername`/`-f` - Folder name to use to search for SSH keys _(default: ssh-agent)_
* `--customfield`/`-c` - Custom field name where private key filename is stored _(default: private)_
* `--passphrasefield`/`-p` - Custom field name where passphrase for the key is stored _(default: passphrase)_
* `--session`/`-s` - session key of bitwarden
* `--lifetime`/`-t` - Maximum sshd lifetime (e.g. 60s, 30m, 2h30m) of keys; defaults to 4h