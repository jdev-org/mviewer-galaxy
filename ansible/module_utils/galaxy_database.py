"""Validation des variables PostgreSQL communes aux rôles PostgreSQL et GeoServer."""

import re


def read_configuration(password, database, username):
    for name in (database, username):
        if not re.fullmatch(r'[a-z_][a-z0-9_]{0,62}', name):
            raise ValueError('Les noms PostgreSQL doivent contenir 1 à 63 caractères : a-z, 0-9, underscore, sans chiffre initial.')
    if database in ('postgres', 'template0', 'template1') or username in ('postgres', 'public', 'none') or username.startswith('pg_'):
        raise ValueError('Choisir une base et un utilisateur applicatifs, hors noms réservés.')
    if not password.strip() or '\x00' in password:
        raise ValueError('Renseigner postgres_password dans le fichier Ansible Vault.')
    return database, username, password
