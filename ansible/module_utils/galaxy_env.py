"""Configuration .env commune aux rôles PostgreSQL et GeoServer."""

import re


def read_env(content):
    values = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].lstrip()
        key, separator, value = line.partition('=')
        key, value = key.strip(), value.strip()
        if not separator:
            raise ValueError('Chaque ligne du fichier .env doit être de la forme CLE=valeur.')
        if key in values:
            raise ValueError('Clé présente plusieurs fois dans .env.')
        if value.startswith(('"', "'")):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError('Les guillemets des valeurs .env doivent être fermés.')
            value = value[1:-1]
        values[key] = value
    return values


def read_configuration(content, database, username):
    values = read_env(content)
    database = values.get('POSTGRES_DB', database)
    username = values.get('POSTGRES_USER', username)
    for name in (database, username):
        if not re.fullmatch(r'[a-z_][a-z0-9_]{0,62}', name):
            raise ValueError('Les noms PostgreSQL doivent contenir 1 à 63 caractères : a-z, 0-9, underscore, sans chiffre initial.')
    if database in ('postgres', 'template0', 'template1') or username in ('postgres', 'public', 'none') or username.startswith('pg_'):
        raise ValueError('Choisir une base et un utilisateur applicatifs, hors noms réservés.')
    password = values.get('POSTGRES_PASSWORD', '')
    if not password.strip() or '\x00' in password:
        raise ValueError('Renseigner POSTGRES_PASSWORD dans le fichier .env.')
    return database, username, password
