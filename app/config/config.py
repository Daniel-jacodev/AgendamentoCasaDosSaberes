from os import getenv
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / '.env')


class Settings:
    cors_origins = [
        origin.strip().rstrip('/')
        for origin in getenv('CORS_ORIGINS', 'http://127.0.0.1:3000,http://localhost:3000').split(',')
        if origin.strip()
    ]
    db_host = getenv('DB_HOST', 'localhost')
    db_port = int(getenv('DB_PORT', '5432'))
    db_name = getenv('DB_NAME', 'agendamento')
    db_user = getenv('DB_USER', 'agendamento')
    db_password = getenv('DB_PASSWORD')
    keycloak_server_url = getenv('KEYCLOAK_SERVER_URL', 'http://localhost:8080/')
    keycloak_issuer_url = getenv('KEYCLOAK_ISSUER_URL')
    keycloak_realm = getenv('KEYCLOAK_REALM', 'proj-social-ufc')
    keycloak_client_id = getenv('KEYCLOAK_CLIENT_ID', 'proj-social-backend')
    keycloak_client_secret = getenv('KEYCLOAK_CLIENT_SECRET')


settings = Settings()
