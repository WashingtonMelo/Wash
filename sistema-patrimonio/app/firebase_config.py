import os
from dotenv import load_dotenv

load_dotenv()

# Caminho para o arquivo JSON da chave de serviço do Firebase Admin SDK
# Este arquivo deve ser baixado do console do Firebase e o caminho configurado na variável de ambiente
FIREBASE_SERVICE_ACCOUNT_KEY_PATH = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY_PATH')

# URL do Banco de Dados Firebase (Necessário se usar Realtime Database junto com Firestore, ou apenas Realtime DB)
# Para Firestore puro, o SDK geralmente descobre o projeto a partir das credenciais.
FIREBASE_DB_URL = os.environ.get('FIREBASE_DATABASE_URL')


if not FIREBASE_SERVICE_ACCOUNT_KEY_PATH:
    print("AVISO: A variável de ambiente 'FIREBASE_SERVICE_ACCOUNT_KEY_PATH' não está configurada.")
    print("O Firebase Admin SDK não será inicializado corretamente sem ela.")
    # Você pode definir um caminho padrão para desenvolvimento local se desejar,
    # mas é mais seguro usar variáveis de ambiente.
    # Ex: FIREBASE_SERVICE_ACCOUNT_KEY_PATH = "path/to/your/serviceAccountKey.json"
    # Lembre-se de adicionar o arquivo .json ao .gitignore se fizer isso.

# Outras configurações do Firebase (para o cliente web, por exemplo)
# Estas são normalmente usadas no frontend, mas podem ser úteis aqui para referência
# ou se o backend precisar interagir com APIs do Firebase como cliente.
FIREBASE_CONFIG_CLIENT = {
    "apiKey": os.environ.get("FIREBASE_API_KEY"),
    "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.environ.get("FIREBASE_PROJECT_ID"),
    "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.environ.get("FIREBASE_APP_ID"),
    "measurementId": os.environ.get("FIREBASE_MEASUREMENT_ID"), # Opcional, para Google Analytics
    "databaseURL": os.environ.get("FIREBASE_DATABASE_URL_CLIENT") # Se diferente para cliente
}

if not all(FIREBASE_CONFIG_CLIENT.values()):
    print("AVISO: Algumas variáveis de ambiente para configuração do cliente Firebase não estão definidas.")
    print("Isso pode ser necessário para funcionalidades de frontend.")

# Para usar o Firestore:
# from firebase_admin import firestore
# db = firestore.client()
#
# Para usar o Firebase Auth:
# from firebase_admin import auth
# user = auth.get_user_by_email('user@example.com')
