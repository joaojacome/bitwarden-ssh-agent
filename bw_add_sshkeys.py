#!/usr/bin/env python3
"""
Extracts SSH keys from Bitwarden vault
"""

import argparse
import json
import logging
import os
import subprocess

from pkg_resources import parse_version


def memoize(func):
    """
    Decorator function to cache the results of another function call
    """
    cache = dict()

    def memoized_func(*args):
        if args in cache:
            return cache[args]
        result = func(*args)
        cache[args] = result
        return result

    return memoized_func


@memoize
def bwcli_version():
    """
    Function to return the version of the Bitwarden CLI
    """
    proc_version = subprocess.run(
        ['bw', '--version'],
        stdout=subprocess.PIPE,
        universal_newlines=True,
        check=True,
    )
    return proc_version.stdout


@memoize
def cli_supports(feature):
    """
    Function to return whether the current Bitwarden CLI supports a particular
    feature
    """
    version = parse_version(bwcli_version())

    if feature == 'nointeraction' and version >= parse_version('1.9.0'):
        return True
    return False


def get_session():
    """
    Function to return a valid Bitwarden session
    """
    # Check for an existing, user-supplied Bitwarden session
    session = os.environ.get('BW_SESSION')
    if session is not None:
        logging.debug('Existing Bitwarden session found')
        return session

    # Check if we're already logged in
    proc_logged = subprocess.run(['bw', 'login', '--check', '--quiet'])

    if proc_logged.returncode:
        logging.debug('Not logged into Bitwarden')
        operation = 'login'
    else:
        logging.debug('Bitwarden vault is locked')
        operation = 'unlock'

    proc_session = subprocess.run(
        ['bw', '--raw', operation],
        stdout=subprocess.PIPE,
        universal_newlines=True,
        check=True,
    )
    return proc_session.stdout


def get_folders(session, foldername):
    """
    Function to return the ID  of the folder that matches the provided name
    """
    logging.debug('Folder name: %s', foldername)

    proc_folders = subprocess.run(
        ['bw', 'list', 'folders', '--search', foldername, '--session', session],
        stdout=subprocess.PIPE,
        universal_newlines=True,
        check=True,
    )

    folders = json.loads(proc_folders.stdout)

    if not folders:
        logging.error('"%s" folder not found', foldername)
        return None

    # Do we have any folders
    if len(folders) != 1:
        logging.error('%d folders with the name "%s" found', len(folders), foldername)
        return None

    return folders[0]['id']


def folder_items(session, folder_id):
    """
    Function to return items from a folder
    """
    logging.debug('Folder ID: %s', folder_id)

    proc_items = subprocess.run(
        [ 'bw', 'list', 'items', '--folderid', folder_id, '--session', session],
        stdout=subprocess.PIPE,
        universal_newlines=True,
        check=True,
    )
    return json.loads(proc_items.stdout)


def add_ssh_keys(session, items, keyname):
    """
    Function to attempt to get keys from a vault item
    """
    for item in items:
        try:
            private_key_file = [k['value'] for k in item['fields']
                                if k['name'] == keyname and k['type'] == 0][0]
        except IndexError:
            logging.warning('No "%s" field found for item %s', keyname, item['name'])
            continue
        except KeyError as e:
            logging.debug('No key "%s" found in item %s - skipping', e.args[0], item['name'])
            continue
        logging.debug('Private key file declared')

        try:
            private_key_id = [k['id'] for k in item['attachments']
                              if k['fileName'] == private_key_file][0]
        except IndexError:
            logging.warning(
                'No attachment called "%s" found for item %s',
                private_key_file,
                item['name']
            )
            continue
        logging.debug('Private key ID found')

        try:
            ssh_add(session, item['id'], private_key_id)
        except subprocess.SubprocessError:
            logging.warning('Could not add key to the SSH agent')


def ssh_add(session, item_id, key_id):
    """
    Function to get the key contents from the Bitwarden vault
    """
    logging.debug('Item ID: %s', item_id)
    logging.debug('Key ID: %s', key_id)

    proc_attachment = subprocess.run([
            'bw',
            'get',
            'attachment', key_id,
            '--itemid', item_id,
            '--raw',
            '--session', session
        ],
        stdout=subprocess.PIPE,
        universal_newlines=True,
        check=True,
    )
    ssh_key = proc_attachment.stdout

    logging.debug("Running ssh-add")

    # CAVEAT: `ssh-add` provides no useful output, even with maximum verbosity
    subprocess.run(
        ['ssh-add', '-'],
        input=ssh_key,
        # Works even if ssh-askpass is not installed
        env=dict(os.environ, SSH_ASKPASS_REQUIRE="never"),
        universal_newlines=True,
        check=True,
    )


if __name__ == '__main__':
    def parse_args():
        """
        Function to parse command line arguments
        """
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '-d', '--debug',
            action='store_true',
            help='show debug output',
        )
        parser.add_argument(
            '-f', '--foldername',
            default='ssh-agent',
            help='folder name to use to search for SSH keys',
        )
        parser.add_argument(
            '-c', '--customfield',
            default='private',
            help='custom field name where private key filename is stored',
        )

        return parser.parse_args()


    def main():
        """
        Main program logic
        """

        args = parse_args()

        if args.debug:
            loglevel = logging.DEBUG
        else:
            loglevel = logging.INFO

        logging.basicConfig(level=loglevel)

        try:
            logging.info('Getting Bitwarden session')
            session = get_session()
            logging.debug('Session = %s', session)

            logging.info('Getting folder list')
            folder_id = get_folders(session, args.foldername)

            logging.info('Getting folder items')
            items = folder_items(session, folder_id)

            logging.info('Attempting to add keys to ssh-agent')
            add_ssh_keys(session, items, args.customfield)
        except subprocess.CalledProcessError as e:
            if e.stderr:
                logging.error('`%s` error: %s', e.cmd[0], e.stderr)
            logging.debug('Error running %s', e.cmd)

    main()
