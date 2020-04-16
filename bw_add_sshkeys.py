#!/usr/bin/env python3
"""
Extracts SSH keys from Bitwarden vault
"""

import argparse
import getpass
import json
import logging
import os
import subprocess
import sys
import tempfile

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
    proc = subprocess.Popen(
        [
            'bw',
            '--version'
        ],
        stdout=subprocess.PIPE
    )

    (stdout, _) = proc.communicate()

    if proc.returncode:
        raise RuntimeError('Unable to fetch Bitwarden CLI version')

    return stdout.decode('utf-8')


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
    try:
        if os.environ['BW_SESSION']:
            logging.debug('Existing Bitwarden session found')
            return os.environ['BW_SESSION']
    except KeyError:
        pass

    # Check if we're already logged in
    proc = subprocess.Popen(
        [
            'bw',
            'login',
            '--check',
            '--quiet'
        ]
    )
    proc.wait()

    if proc.returncode:
        logging.debug('Not logged into Bitwarden')
        operation = 'login'
        credentials = [bytes(input('Bitwarden user: '), encoding='ascii')]
    else:
        logging.debug('Bitwarden vault is locked')
        operation = 'unlock'
        credentials = []

    # Ask for the password
    credentials.append(bytes(getpass.getpass('Bitwarden Vault password: '), encoding='ascii'))

    proc = subprocess.Popen(
        list(filter(None, [
            'bw',
            '--raw',
            (None, '--nointeraction')[cli_supports('nointeraction')],
            operation
        ] + credentials)),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    (stdout, stderr) = proc.communicate()

    if proc.returncode:
        logging.error(stderr.decode('utf-8'))
        return None

    return stdout.decode('utf-8')


def get_folders(session, foldername):
    """
    Function to return the ID  of the folder that matches the provided name
    """
    logging.debug('Folder name: %s', foldername)

    proc = subprocess.Popen(
        list(filter(None, [
            'bw',
            (None, '--nointeraction')[cli_supports('nointeraction')],
            'list',
            'folders',
            '--search', foldername,
            '--session', session
        ])),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    (stdout, stderr) = proc.communicate()

    if proc.returncode:
        logging.error(stderr.decode('utf-8'))
        return None

    folders = json.loads(stdout)

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

    proc = subprocess.Popen(
        list(filter(None, [
            'bw',
            (None, '--nointeraction')[cli_supports('nointeraction')],
            'list',
            'items',
            '--folderid', folder_id,
            '--session', session
        ])),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    (stdout, stderr) = proc.communicate()

    if proc.returncode:
        logging.error(stderr.decode('utf-8'))
        return None

    return json.loads(stdout)


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

        if not ssh_add(session, item['id'], private_key_id):
            logging.warning('Could not add key to the SSD agent')


def ssh_add(session, item_id, key_id):
    """
    Function to get the key contents from the Bitwarden vault
    """
    logging.debug('Item ID: %s', item_id)
    logging.debug('Key ID: %s', key_id)

    # TODO: avoid temporary files, if possible
    with tempfile.NamedTemporaryFile() as tmpfile:
        proc = subprocess.Popen(
            list(filter(None, [
                'bw',
                (None, '--nointeraction')[cli_supports('nointeraction')],
                '--quiet',
                'get',
                'attachment', key_id,
                '--itemid', item_id,
                '--output', tmpfile.name,
                '--session', session
            ])),
            stderr=subprocess.PIPE
        )
        (_, stderr) = proc.communicate()
        if proc.returncode:
            logging.error(stderr.decode('utf-8'))
            return False

        logging.debug("Running ssh-add")

        # CAVEAT: `ssh-add` provides no useful output, even with maximum verbosity
        proc = subprocess.Popen(['ssh-add', tmpfile.name])
        proc.wait()

        if proc.returncode:
            return False

        return True


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

        logging.info('Getting Bitwarden session')
        session = get_session()
        if not session:
            sys.exit(1)
        logging.debug('Session = %s', session)

        logging.info('Getting folder list')
        folder_id = get_folders(session, args.foldername)
        if not folder_id:
            sys.exit(2)

        logging.info('Getting folder items')
        items = folder_items(session, folder_id)
        if not items:
            sys.exit(3)

        logging.info('Attempting to add keys to ssh-agent')
        add_ssh_keys(session, items, args.customfield)

    main()
