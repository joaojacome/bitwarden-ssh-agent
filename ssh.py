import subprocess
import os
import sys
import json
from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError

try:
    subprocess.check_output(['bw', 'logout'])
except:
    pass

try:
    session = subprocess.check_output(['bw', '--raw', 'login'])
    session = ['--session', session]
except:
    print('Couldnt login!')
    sys.exit(1)

try:
    folders = subprocess.check_output(['bw','list', 'folders', '--search', 'ssh-agent'] + session)
    folders = json.loads(folders)
    if not folders:
        raise AttributeError
    if len(folders) != 1:
        raise ValueError
except AttributeError:
    print('Couldnt find ssh-agent folder!')
    sys.exit(1)
except ValueError:
    print('More than one ssh-agent folder found!')
    sys.exit(1)
except:
    print('Error retrieving folders.')
    sys.exit(1)

folder = folders[0]['id']

try:
    items = subprocess.check_output(['bw', 'list', 'items', '--folderid', folder, 'ssh-agent'] + session)
    items = json.loads(items)
except Exception as e:
    print('Cant fint items.')
    print(e)
    sys.exit(1)

keys = []
try:
    for item in items:
        private_key_file = [k['value'] for k in item['fields'] if k['name'] == 'private' and k['type'] == 0][0]
        
        private_key_id = [k['id'] for k in item['attachments'] if k['fileName'] == private_key_file][0]

        # would be nice if there was an option to retrieve the attachment file directly to the stdout
        subprocess.check_output(['bw', 'get', 'attachment', private_key_id, '--itemid', item['id'], '--output', './private_key'] + session)
        private_key = open('private_key', 'r').read()
        os.remove('./private_key')
        keys.append({'private_key': private_key})
except:
    print('Something happened.')
    sys.exit(1)

print(';'.join([k['private_key'] for k in keys]))
