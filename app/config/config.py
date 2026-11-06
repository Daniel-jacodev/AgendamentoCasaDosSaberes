from os import getenv
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / '.env')


class Settings:
    keycloak_server_url = getenv('KEYCLOAK_SERVER_URL', 'http://localhost:8080/')
    keycloak_issuer_url = getenv('KEYCLOAK_ISSUER_URL')
    keycloak_realm = getenv('KEYCLOAK_REALM', 'proj-social-ufc')
    keycloak_client_id = getenv('KEYCLOAK_CLIENT_ID', 'proj-social-backend')
    keycloak_client_secret = getenv('KEYCLOAK_CLIENT_SECRET')


settings = Settings()
