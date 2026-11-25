#!/usr/bin/python
"""Installer les JAR vérifiés des extensions sans réécrire les bibliothèques identiques."""

import fnmatch
import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile
import zipfile

from ansible.module_utils.basic import AnsibleModule


def library_plan(extensions, cache_dir, lib_dir, allow_missing=False):
    """Valider toutes les archives et collisions avant toute modification du service."""
    libraries = {}
    missing = []
    for extension in extensions:
        name = extension['name']
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', name):
            raise ValueError('Nom d’extension invalide.')
        checksum = extension['checksum']
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', checksum):
            raise ValueError('Une empreinte SHA-256 est obligatoire pour chaque extension.')
        path = Path(cache_dir) / (name + '.zip')
        if not path.exists() and allow_missing:
            missing.append(name)
            continue
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != checksum.split(':', 1)[1]:
            raise ValueError('Empreinte incorrecte pour l’extension ' + name)
        count = 0
        with zipfile.ZipFile(path) as archive:
            for entry in archive.infolist():
                if entry.is_dir() or not entry.filename.endswith('.jar'):
                    continue
                if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+\-]*\.jar', entry.filename):
                    raise ValueError('Chemin de bibliothèque invalide dans l’extension ' + name)
                if any(fnmatch.fnmatchcase(entry.filename, pattern)
                       for pattern in extension.get('exclude_jars', [])):
                    continue
                data = archive.read(entry)
                if entry.filename in libraries and libraries[entry.filename] != data:
                    raise ValueError('Bibliothèque partagée incompatible : ' + entry.filename)
                libraries[entry.filename] = data
                count += 1
        if not count:
            raise ValueError('Aucune bibliothèque JAR dans l’extension ' + name)
    changed = {}
    for name, data in libraries.items():
        target = Path(lib_dir) / name
        if (target.is_symlink() or not target.is_file()
                or target.read_bytes() != data
                or stat.S_IMODE(target.stat().st_mode) != 0o644):
            changed[name] = data
    return changed, missing


def install_libraries(changes, lib_dir):
    """Remplacer chaque JAR atomiquement, après arrêt du service par le rôle."""
    for name, data in changes.items():
        fd, temporary = tempfile.mkstemp(prefix='.ansible-extension-', dir=lib_dir)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
                os.fchmod(stream.fileno(), 0o644)
            os.replace(temporary, Path(lib_dir) / name)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            extensions=dict(type='list', elements='dict', required=True,
                            options=dict(name=dict(type='str', required=True),
                                         url=dict(type='str', required=True),
                                         checksum=dict(type='str', required=True),
                                         exclude_jars=dict(type='list', elements='str', default=[]))),
            cache_dir=dict(type='path', required=True),
            lib_dir=dict(type='path', required=True),
            allow_missing=dict(type='bool', default=False),
        ), supports_check_mode=True)
    try:
        if not Path(module.params['lib_dir']).is_dir():
            raise ValueError('Le répertoire WEB-INF/lib de GeoServer doit déjà exister.')
        if module.params['allow_missing'] and not module.check_mode:
            raise ValueError('allow_missing est réservé au mode simulation.')
        changes, missing = library_plan(
            module.params['extensions'], module.params['cache_dir'],
            module.params['lib_dir'], module.params['allow_missing'])
        if not module.check_mode:
            install_libraries(changes, module.params['lib_dir'])
        module.exit_json(changed=bool(changes or missing), libraries=sorted(changes),
                         missing_archives=missing)
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        module.fail_json(msg=str(error))


if __name__ == '__main__':
    main()
