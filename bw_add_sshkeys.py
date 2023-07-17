#!/usr/bin/env python3
"""
Extracts SSH keys from Bitwarden vault
"""

import argparse
import json
import logging
import os
import subprocess
from typing import Any


def get_session(session: str) -> str:
    """
    Function to return a valid Bitwarden session
    """
    # Check for an existing, user-supplied Bitwarden session
    if not session:
        session = os.environ.get("BW_SESSION", "")
    if session:
        logging.debug("Existing Bitwarden session found")
        return session

    # Check if we're already logged in
    proc_logged = subprocess.run(["bw", "login", "--check", "--quiet"], check=False)

    if proc_logged.returncode:
        logging.debug("Not logged into Bitwarden")
        operation = "login"
    else:
        logging.debug("Bitwarden vault is locked")
        operation = "unlock"

    proc_session = subprocess.run(
        ["bw", "--raw", operation],
        stdout=subprocess.PIPE,
        universal_newlines=True,
        check=True,
    )
    session = proc_session.stdout
    logging.info(
        'To re-use this BitWarden session run: export BW_SESSION="%s"',
        session,
    )
    return session


def get_folders(session: str, foldername: str) -> str:
    """
    Function to return the ID  of the folder that matches the provided name
    """
    logging.debug("Folder name: %s", foldername)

    proc_folders = subprocess.run(
        ["bw", "list", "folders", "--search", foldername, "--session", session],
        stdout=subprocess.PIPE,
        universal_newlines=True,
        check=True,
        encoding="utf-8",
    )

    folders = json.loads(proc_folders.stdout)

    if not folders:
        logging.error('"%s" folder not found', foldername)
        return ""

    # Do we have any folders
    if len(folders) != 1:
        logging.error('%d folders with the name "%s" found', len(folders), foldername)
        return ""

    return str(folders[0]["id"])


def folder_items(session: str, folder_id: str) -> list[dict[str, Any]]:
    """
    Function to return items from a folder
    """
    logging.debug("Folder ID: %s", folder_id)

    proc_items = subprocess.run(
        ["bw", "list", "items", "--folderid", folder_id, "--session", session],
        stdout=subprocess.PIPE,
        universal_newlines=True,
        check=True,
        encoding="utf-8",
    )

    data: list[dict[str, Any]] = json.loads(proc_items.stdout)

    return data


def add_ssh_keys(
    session: str,
    items: list[dict[str, Any]],
    keyname: str,
    pwkeyname: str,
) -> None:
    """
    Function to attempt to get keys from a vault item
    """
    for item in items:
        try:
            private_key_file = [
                k["value"] for k in item["fields"] if k["name"] == keyname
            ][0]
        except IndexError:
            logging.warning('No "%s" field found for item %s', keyname, item["name"])
            continue
        except KeyError as error:
            logging.debug(
                'No key "%s" found in item %s - skipping', error.args[0], item["name"]
            )
            continue
        logging.debug("Private key file declared")

        private_key_pw = ""
        try:
            private_key_pw = [
                k["value"] for k in item["fields"] if k["name"] == pwkeyname
            ][0]
            logging.debug("Passphrase declared")
        except IndexError:
            logging.warning('No "%s" field found for item %s', pwkeyname, item["name"])
        except KeyError as error:
            logging.debug(
                'No key "%s" found in item %s - skipping', error.args[0], item["name"]
            )

        try:
            private_key_id = [
                k["id"]
                for k in item["attachments"]
                if k["fileName"] == private_key_file
            ][0]
        except IndexError:
            logging.warning(
                'No attachment called "%s" found for item %s',
                private_key_file,
                item["name"],
            )
            continue
        logging.debug("Private key ID found")

        try:
            ssh_add(session, item["id"], private_key_id, private_key_pw)
        except subprocess.SubprocessError:
            logging.warning("Could not add key to the SSH agent")


def ssh_add(session: str, item_id: str, key_id: str, key_pw: str = "") -> None:
    """
    Function to get the key contents from the Bitwarden vault
    """
    logging.debug("Item ID: %s", item_id)
    logging.debug("Key ID: %s", key_id)

    proc_attachment = subprocess.run(
        [
            "bw",
            "get",
            "attachment",
            key_id,
            "--itemid",
            item_id,
            "--raw",
            "--session",
            session,
        ],
        stdout=subprocess.PIPE,
        universal_newlines=True,
        check=True,
    )
    ssh_key = proc_attachment.stdout

    if key_pw:
        envdict = dict(
            os.environ,
            SSH_ASKPASS=os.path.realpath(__file__),
            SSH_KEY_PASSPHRASE=key_pw,
        )
    else:
        envdict = dict(os.environ, SSH_ASKPASS_REQUIRE="never")

    logging.debug("Running ssh-add")
    # CAVEAT: `ssh-add` provides no useful output, even with maximum verbosity
    subprocess.run(
        ["ssh-add", "-"],
        input=ssh_key.encode("utf-8"),
        # Works even if ssh-askpass is not installed
        env=envdict,
        universal_newlines=False,
        check=True,
    )


if __name__ == "__main__":

    def parse_args() -> argparse.Namespace:
        """
        Function to parse command line arguments
        """
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "-d",
            "--debug",
            action="store_true",
            help="show debug output",
        )
        parser.add_argument(
            "-f",
            "--foldername",
            default="ssh-agent",
            help="folder name to use to search for SSH keys",
        )
        parser.add_argument(
            "-c",
            "--customfield",
            default="private",
            help="custom field name where private key filename is stored",
        )
        parser.add_argument(
            "-p",
            "--passphrasefield",
            default="passphrase",
            help="custom field name where key passphrase is stored",
        )
        parser.add_argument(
            "-s",
            "--session",
            default="",
            help="session key of bitwarden",
        )

        return parser.parse_args()

    def main() -> None:
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
            logging.info("Getting Bitwarden session")
            session = get_session(args.session)
            logging.debug("Session = %s", session)

            logging.info("Getting folder list")
            folder_id = get_folders(session, args.foldername)

            logging.info("Getting folder items")
            items = folder_items(session, folder_id)

            logging.info("Attempting to add keys to ssh-agent")
            add_ssh_keys(session, items, args.customfield, args.passphrasefield)
        except subprocess.CalledProcessError as error:
            if error.stderr:
                logging.error('"%s" error: %s', error.cmd[0], error.stderr)
            logging.debug("Error running %s", error.cmd)

    if os.environ.get("SSH_ASKPASS") and os.environ.get(
        "SSH_ASKPASS"
    ) == os.path.realpath(__file__):
        print(os.environ.get("SSH_KEY_PASSPHRASE"))
    else:
        main()
