#!/usr/bin/python
"""Construire et vérifier une distribution GeoServer avec manifeste embarqué."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import zipfile

from ansible.module_utils.basic import AnsibleModule


MANIFEST = '.galaxy-bundle.json'


def checksum(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_bundle(archive, version, extensions):
    with zipfile.ZipFile(archive) as bundle:
        manifest = json.loads(bundle.read(MANIFEST))
        if manifest != dict(version=version, extensions=extensions):
            raise ValueError('Le manifeste ne correspond pas à la version et aux extensions configurées. Repréparer l’archive ou utiliser les mêmes variables.')
        if 'start.jar' not in bundle.namelist():
            raise ValueError('La distribution ne contient pas start.jar à sa racine.')
        if bundle.testzip() is not None:
            raise ValueError('Archive GeoServer corrompue.')
    return checksum(archive)


def build_bundle(source_dir, archive, version, extensions, check_mode=False):
    source = Path(source_dir)
    if not (source / 'start.jar').is_file() or not (source / 'webapps/geoserver/WEB-INF/lib').is_dir():
        raise ValueError('La source doit être une distribution GeoServer extraite avec start.jar et WEB-INF/lib.')
    fd, temporary = tempfile.mkstemp(prefix='.galaxy-bundle-', dir=Path(archive).parent)
    try:
        os.close(fd)
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(source.rglob('*')):
                if path.is_symlink():
                    raise ValueError('Lien symbolique interdit dans la distribution : ' + str(path))
                name = path.relative_to(source).as_posix()
                if name == MANIFEST:
                    continue
                if path.is_dir():
                    entry = zipfile.ZipInfo(name + '/')
                    entry.create_system = 3
                    entry.external_attr = ((stat.S_IFDIR | stat.S_IMODE(path.stat().st_mode)) << 16) | 0x10
                    bundle.writestr(entry, b'')
                    continue
                if not path.is_file():
                    raise ValueError('Fichier spécial interdit dans la distribution : ' + str(path))
                entry = zipfile.ZipInfo(name)
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.create_system = 3
                entry.external_attr = (stat.S_IFREG | stat.S_IMODE(path.stat().st_mode)) << 16
                with path.open('rb') as src, bundle.open(entry, 'w') as dest:
                    shutil.copyfileobj(src, dest)
            entry = zipfile.ZipInfo(MANIFEST)
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            bundle.writestr(entry, json.dumps(dict(version=version, extensions=extensions), sort_keys=True), compress_type=zipfile.ZIP_DEFLATED)
        digest = verify_bundle(temporary, version, extensions)
        changed = not Path(archive).is_file() or checksum(archive) != digest
        if changed and not check_mode:
            os.chmod(temporary, 0o644)
            os.replace(temporary, archive)
        return changed, digest
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    module = AnsibleModule(argument_spec=dict(
        archive=dict(type='path', required=True),
        source_dir=dict(type='path'),
        version=dict(type='str', required=True),
        extensions=dict(type='list', elements='dict', required=True),
    ), supports_check_mode=True)
    try:
        p = module.params
        if p['source_dir']:
            changed, digest = build_bundle(p['source_dir'], p['archive'], p['version'], p['extensions'], module.check_mode)
        else:
            changed, digest = False, verify_bundle(p['archive'], p['version'], p['extensions'])
        module.exit_json(changed=changed, checksum=digest)
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as error:
        module.fail_json(msg=str(error))


if __name__ == '__main__':
    main()
