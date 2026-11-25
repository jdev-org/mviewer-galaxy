import importlib.util
from pathlib import Path
import unittest
import ansible.module_utils


MODULE_PATH = Path(__file__).parents[1] / 'roles/postgres/library/galaxy_postgres.py'
ansible.module_utils.__path__.append(str(Path(__file__).parents[1] / 'module_utils'))
spec = importlib.util.spec_from_file_location('galaxy_postgres', MODULE_PATH)
postgres = importlib.util.module_from_spec(spec)
spec.loader.exec_module(postgres)


class ConfigurationTests(unittest.TestCase):
    def test_literal_password(self):
        password = 'mot de passe $%#= avec "guillemets"'
        self.assertEqual(
            postgres.read_configuration(password, 'cartes', 'cartographe'),
            ('cartes', 'cartographe', password))

    def test_empty_and_null_passwords_are_rejected(self):
        for password in ('', '   ', 'a\x00b'):
            with self.subTest(password=password), self.assertRaises(ValueError):
                postgres.read_configuration(password, 'donneessig', 'usersig')

    def test_reserved_names_and_sql_injection_are_rejected(self):
        for database, username in (('postgres', 'usersig'), ('sig', 'postgres'),
                                   ('sig', 'pg_monitor'), ('sig', 'public'), ('sig', 'none'),
                                   ('sig', "user'; DROP ROLE postgres;--")):
            with self.subTest(database=database, username=username), self.assertRaises(ValueError):
                postgres.read_configuration('secret', database, username)


class PasswordTests(unittest.TestCase):
    def test_verifiers_are_salted_and_only_match_the_correct_password(self):
        password = "phrase $%#='avec caractères' fin"
        verifier = postgres.password_verifier(password)
        self.assertTrue(postgres.password_matches(password, verifier))
        self.assertFalse(postgres.password_matches('autre mot de passe', verifier))
        self.assertNotEqual(verifier, postgres.password_verifier(password))
        self.assertFalse(postgres.password_matches(password, None))
        self.assertFalse(postgres.password_matches(password, 'md5ancien-verificateur'))

    def test_saslprep_equivalent_password_does_not_trigger_rotation(self):
        verifier = postgres.password_verifier('pencil')
        self.assertTrue(postgres.password_matches('pen\u00adcil', verifier))
        self.assertEqual(postgres.password_bytes('\u00aa'), b'a')
        self.assertEqual(postgres.password_bytes('a\x07b'), b'a\x07b')


if __name__ == '__main__':
    unittest.main()
