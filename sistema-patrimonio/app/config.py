import os
from dotenv import load_dotenv

load_dotenv() # Carrega variáveis do arquivo .env

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'voce-nunca-vai-adivinhar'
    # Configurações do Firebase (serão usadas pelo firebase_config.py, mas podem estar aqui também)
    FIREBASE_API_KEY = os.environ.get('FIREBASE_API_KEY')
    FIREBASE_AUTH_DOMAIN = os.environ.get('FIREBASE_AUTH_DOMAIN')
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID')
    FIREBASE_STORAGE_BUCKET = os.environ.get('FIREBASE_STORAGE_BUCKET')
    FIREBASE_MESSAGING_SENDER_ID = os.environ.get('FIREBASE_MESSAGING_SENDER_ID')
    FIREBASE_APP_ID = os.environ.get('FIREBASE_APP_ID')

    # Caminho para a chave de serviço do Firebase Admin SDK
    # Este caminho será lido de uma variável de ambiente
    FIREBASE_SERVICE_ACCOUNT_KEY_PATH_ENV = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY_PATH')
    FIREBASE_DB_URL_ENV = os.environ.get('FIREBASE_DATABASE_URL') # Para Realtime DB, se usado. Firestore não precisa.

    # Adicionar outras configurações conforme necessário
    # Ex: Configurações de Email para recuperação de senha
    # MAIL_SERVER = os.environ.get('MAIL_SERVER')
    # MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    # MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    # MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    # MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    # ADMINS = ['seu_email_admin@example.com']
