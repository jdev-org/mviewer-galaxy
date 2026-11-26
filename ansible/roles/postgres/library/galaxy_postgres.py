#!/usr/bin/python
"""Provisionner la base SIG avec psql et la bibliothèque standard Python."""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import stringprep
from unicodedata import ucd_3_2_0

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.galaxy_database import read_configuration


def password_bytes(password):
    """SASLprep RFC 4013, avec le repli UTF-8 utilisé par PostgreSQL."""
    mapped = ''.join(' ' if stringprep.in_table_c12(c) else c
                     for c in password if not stringprep.in_table_b1(c))
    prepared = ucd_3_2_0.normalize('NFKC', mapped)
    prohibited = (stringprep.in_table_a1, stringprep.in_table_c12,
                  stringprep.in_table_c21, stringprep.in_table_c22,
                  stringprep.in_table_c3, stringprep.in_table_c4,
                  stringprep.in_table_c5, stringprep.in_table_c6,
                  stringprep.in_table_c7, stringprep.in_table_c8, stringprep.in_table_c9)
    if any(test(c) for c in prepared for test in prohibited):
        return password.encode('utf-8')
    if any(stringprep.in_table_d1(c) for c in prepared):
        if (any(stringprep.in_table_d2(c) for c in prepared)
                or not stringprep.in_table_d1(prepared[0])
                or not stringprep.in_table_d1(prepared[-1])):
            return password.encode('utf-8')
    return prepared.encode('utf-8')


def scram_keys(password, salt, iterations):
    salted = hashlib.pbkdf2_hmac('sha256', password_bytes(password), salt, iterations)
    client = hmac.digest(salted, b'Client Key', 'sha256')
    return hashlib.sha256(client).digest(), hmac.digest(salted, b'Server Key', 'sha256')


def password_matches(password, verifier):
    try:
        mechanism, parameters, keys = verifier.split('$')
        if mechanism != 'SCRAM-SHA-256':
            return False
        iterations, salt = parameters.split(':')
        stored, server = keys.split(':')
        actual_stored, actual_server = scram_keys(password, base64.b64decode(salt), int(iterations))
        return (hmac.compare_digest(actual_stored, base64.b64decode(stored))
                and hmac.compare_digest(actual_server, base64.b64decode(server)))
    except (ValueError, TypeError, AttributeError):
        return False


def password_verifier(password):
    salt = secrets.token_bytes(16)
    stored, server = scram_keys(password, salt, 4096)
    encode = lambda value: base64.b64encode(value).decode('ascii')
    return 'SCRAM-SHA-256$4096:{}${}:{}'.format(encode(salt), encode(stored), encode(server))


def inspect_database(query, database, minimum_version, minimum_postgis_version):
    """Vérifier les versions et l'existence de la base avant toute écriture SQL."""
    version_number = int(query('SHOW server_version_num;'))
    version = query('SHOW server_version;')
    if version_number < minimum_version * 10000:
        raise ValueError('PostgreSQL ' + version + ' est inférieur à la version minimale ' + str(minimum_version) + '. Aucune migration automatique n’est effectuée.')
    owner = query("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = '" + database + "';")
    postgis_version = query("SELECT extversion FROM pg_extension WHERE extname = 'postgis';", database) if owner else ''
    available_postgis_version = postgis_version or query("SELECT default_version FROM pg_available_extensions WHERE name = 'postgis';")
    if not available_postgis_version:
        raise ValueError('PostGIS n’est pas disponible pour ce serveur PostgreSQL. Installer les paquets correspondant à sa version majeure.')
    major = re.match(r'^(\d+)(?:\.|$)', available_postgis_version)
    if not major or int(major.group(1)) < minimum_postgis_version:
        raise ValueError('PostGIS ' + available_postgis_version + ' est incompatible avec la version minimale ' + str(minimum_postgis_version) + '. Aucune mise à niveau automatique n’est effectuée.')
    return owner, version, postgis_version


def main():
    module = AnsibleModule(
        argument_spec=dict(
            password=dict(type='str', required=True, no_log=True),
            database=dict(type='str', default='donneessig'),
            username=dict(type='str', default='usersig'),
            port=dict(type='int', default=5432),
            socket_dir=dict(type='path', default='/var/run/postgresql'),
            validate_only=dict(type='bool', default=False),
            inspect_only=dict(type='bool', default=False),
            minimum_version=dict(type='int', default=14),
            minimum_postgis_version=dict(type='int', default=3),
        ),
        supports_check_mode=True,
    )
    try:
        if module.params['minimum_version'] < 1 or module.params['minimum_postgis_version'] < 1:
            raise ValueError('Les versions minimales doivent être des entiers positifs.')
        database, username, password = read_configuration(
            module.params['password'], module.params['database'], module.params['username'])
    except ValueError as error:
        module.fail_json(msg=str(error))
    module.no_log_values.add(password)
    if module.params['validate_only']:
        module.exit_json(changed=False, database=database, username=username)

    psql = module.get_bin_path('psql', required=True)
    if os.geteuid() == 0:
        prefix = [module.get_bin_path('runuser', required=True), '-u', 'postgres', '--']
    else:
        # L'authentification locale doit fournir l'administrateur postgres.
        prefix = []

    def query(sql, target='postgres'):
        argv = prefix + [psql, '--no-psqlrc', '--no-password', '--quiet',
                         '--tuples-only', '--no-align', '--set=ON_ERROR_STOP=1',
                         '--username=postgres', '--host=' + module.params['socket_dir'],
                         '--port=' + str(module.params['port']), '--dbname=' + target]
        rc, stdout, stderr = module.run_command(
            argv, data=sql, environ_update={'PGOPTIONS': '-c standard_conforming_strings=on'})
        if rc:
            # Le serveur peut citer la requête (et son vérificateur) dans l'erreur.
            module.fail_json(msg='Échec de la requête PostgreSQL. Vérifier le service, le port et les journaux PostgreSQL.')
        return stdout.strip()

    try:
        owner, server_version, postgis_version = inspect_database(
            query, database, module.params['minimum_version'], module.params['minimum_postgis_version'])
    except ValueError as error:
        module.fail_json(msg=str(error))
    database_reused = bool(owner)
    if module.params['inspect_only']:
        module.exit_json(changed=False, database=database, database_reused=database_reused,
                         server_version=server_version, postgis_version=postgis_version)

    # Les identifiants sont validés ci-dessus et les secrets transmis par stdin.
    role_json = query("SELECT row_to_json(r) FROM (SELECT rolpassword, rolcanlogin, "
                      "rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls "
                      "FROM pg_authid WHERE rolname = '" + username + "') r;")
    role = json.loads(role_json) if role_json else None
    changes = []
    password_changed = not role or not password_matches(password, role['rolpassword'])
    permissions_changed = not role or not role['rolcanlogin'] or any(
        role[key] for key in ('rolsuper', 'rolcreatedb', 'rolcreaterole', 'rolreplication', 'rolbypassrls'))
    if password_changed or permissions_changed:
        changes.append('role')
        if not module.check_mode:
            sql = ('ALTER' if role else 'CREATE') + ' ROLE "' + username + '" WITH LOGIN'
            sql += ' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS'
            if password_changed:
                sql += " PASSWORD '" + password_verifier(password) + "'"
            query(sql + ';')

    if owner != username:
        changes.append('database')
        if not module.check_mode:
            if owner:
                query('ALTER DATABASE "' + database + '" OWNER TO "' + username + '";')
            else:
                query('CREATE DATABASE "' + database + '" OWNER "' + username + '";')

    if not postgis_version:
        changes.append('postgis')
        if not module.check_mode:
            query('CREATE EXTENSION IF NOT EXISTS postgis;', database)
            postgis_version = query("SELECT extversion FROM pg_extension WHERE extname = 'postgis';", database)
    if owner or not module.check_mode:
        schema_owner = query("SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname = 'public';", database)
        if schema_owner != username:
            changes.append('schema_owner')
            if not module.check_mode:
                if schema_owner:
                    query('ALTER SCHEMA public OWNER TO "' + username + '";', database)
                else:
                    query('CREATE SCHEMA public AUTHORIZATION "' + username + '";', database)
    module.exit_json(changed=bool(changes), changes=changes, database=database, username=username,
                     database_reused=database_reused, server_version=server_version, postgis_version=postgis_version,
                     hba_file=query('SHOW hba_file;'), config_file=query('SHOW config_file;'))


if __name__ == '__main__':
    main()
