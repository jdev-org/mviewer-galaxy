#!/usr/bin/python
"""Configurer le workspace et l'entrepôt PostGIS par l'API REST GeoServer."""

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.galaxy_env import read_configuration


def main():
    module = AnsibleModule(
        argument_spec=dict(
            env_content=dict(type='str', required=True, no_log=True),
            database=dict(type='str', default='donneessig'),
            username=dict(type='str', default='usersig'),
            host=dict(type='str', default='127.0.0.1'),
            port=dict(type='int', default=5432),
            workspace=dict(type='str', default='donnessig'),
            datastore=dict(type='str', default='postgis'),
            url=dict(type='str', default='http://127.0.0.1:8080/geoserver'),
            admin_username=dict(type='str', default='admin'),
            admin_password=dict(type='str', required=True, no_log=True),
            state_file=dict(type='path', required=True),
        ), supports_check_mode=True)
    try:
        database, username, password = read_configuration(
            module.params['env_content'], module.params['database'], module.params['username'])
    except ValueError as error:
        module.fail_json(msg=str(error))
    module.no_log_values.add(password)
    workspace, datastore = module.params['workspace'], module.params['datastore']
    if not all(re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_-]{0,62}', name) for name in (workspace, datastore)):
        module.fail_json(msg='Noms de workspace et d’entrepôt invalides.')
    authorization = base64.b64encode(
        (module.params['admin_username'] + ':' + module.params['admin_password']).encode()).decode('ascii')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    base_url = module.params['url'].rstrip('/') + '/rest/'

    def request(path, method='GET', root=None, allow_missing=False):
        body = ET.tostring(root, encoding='utf-8') if root is not None else None
        req = urllib.request.Request(base_url + path, data=body, method=method,
                                     headers={'Authorization': 'Basic ' + authorization,
                                              'Accept': 'application/xml', 'Content-Type': 'application/xml'})
        try:
            with opener.open(req, timeout=5) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code == 404 and allow_missing:
                return None
            raise

    try:
        deadline = time.monotonic() + 60
        while True:
            try:
                request('about/version.xml')
                break
            except (urllib.error.URLError, TimeoutError) as error:
                if isinstance(error, urllib.error.HTTPError) and error.code in (401, 403):
                    raise
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)

        changes = []
        ws_path = 'workspaces/' + urllib.parse.quote(workspace, safe='')
        ws = ET.Element('workspace')
        ET.SubElement(ws, 'name').text = workspace
        if request(ws_path + '.xml', allow_missing=True) is None:
            changes.append('workspace')
            if not module.check_mode:
                request('workspaces', 'POST', ws)
        default = request('workspaces/default.xml', allow_missing=True)
        if default is None or ET.fromstring(default).findtext('name') != workspace:
            changes.append('default_workspace')
            if not module.check_mode:
                request('workspaces/default.xml', 'PUT', ws)

        desired = {'dbtype': 'postgis', 'host': module.params['host'],
                   'port': str(module.params['port']), 'database': database,
                   'schema': 'public', 'user': username, 'passwd': password}
        state_path = Path(module.params['state_file'])
        try:
            state = json.loads(state_path.read_text())
            salt = bytes.fromhex(state['salt'])
        except (OSError, ValueError, KeyError, TypeError):
            state, salt = {}, secrets.token_bytes(32)
        fingerprint_data = json.dumps([base_url, workspace, datastore, desired], sort_keys=True).encode()
        fingerprint = hmac.new(salt, fingerprint_data, hashlib.sha256).hexdigest()
        store_path = ws_path + '/datastores/' + urllib.parse.quote(datastore, safe='')
        store_xml = request(store_path + '.xml', allow_missing=True)
        store = ET.fromstring(store_xml) if store_xml else None
        current = ({entry.attrib['key']: entry.text or ''
                    for entry in store.findall('./connectionParameters/entry')} if store is not None else {})
        needs_update = (store is None or store.findtext('enabled') != 'true'
                        or any(current.get(key) != value for key, value in desired.items() if key != 'passwd')
                        or state.get('fingerprint') != fingerprint)
        if needs_update:
            changes.append('datastore')
            if not module.check_mode:
                # Une écriture REST suivie d'un échec de connexion doit pouvoir
                # être corrigée au passage suivant, même avec l'ancien mot de passe.
                state_path.unlink(missing_ok=True)
                state = {}
                payload = ET.Element('dataStore')
                ET.SubElement(payload, 'name').text = datastore
                ET.SubElement(payload, 'enabled').text = 'true'
                parameters = ET.SubElement(payload, 'connectionParameters')
                for key, value in desired.items():
                    ET.SubElement(parameters, 'entry', key=key).text = value
                if store is None:
                    request(ws_path + '/datastores', 'POST', payload)
                else:
                    request(store_path + '.xml', 'PUT', payload)
        if not module.check_mode:
            # Ce GET ouvre réellement la connexion PostGIS sans publier de couche.
            request(store_path + '/featuretypes.xml?list=available')
            if state.get('fingerprint') != fingerprint:
                # Le mot de passe REST est chiffré par GeoServer. Une empreinte
                # locale permet de détecter sa rotation sans réécriture à chaque passage.
                state_path.parent.mkdir(parents=True, exist_ok=True)
                temporary_path = None
                try:
                    with tempfile.NamedTemporaryFile(mode='w', dir=state_path.parent, delete=False) as handle:
                        temporary_path = handle.name
                        json.dump({'salt': salt.hex(), 'fingerprint': fingerprint}, handle)
                    os.chmod(temporary_path, 0o600)
                    os.replace(temporary_path, state_path)
                finally:
                    if temporary_path and os.path.exists(temporary_path):
                        os.unlink(temporary_path)
    except urllib.error.HTTPError as error:
        module.fail_json(msg='Erreur REST GeoServer HTTP {}. Vérifier les identifiants administrateur, la connexion PostGIS et les journaux.'.format(error.code))
    except (OSError, ValueError, ET.ParseError):
        module.fail_json(msg='Impossible de configurer GeoServer. Vérifier le service, les fichiers et les journaux.')
    module.exit_json(changed=bool(changes), changes=changes, workspace=workspace, datastore=datastore)


if __name__ == '__main__':
    main()
