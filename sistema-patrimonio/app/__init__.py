from flask import Flask
from flask_login import LoginManager
from .config import Config
import firebase_admin
from firebase_admin import credentials, firestore
from .firebase_config import FIREBASE_SERVICE_ACCOUNT_KEY_PATH, FIREBASE_DB_URL

# Inicializar LoginManager
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # Rota para redirecionar se o usuário não estiver logado
login_manager.login_message = "Por favor, faça login para acessar esta página."
login_manager.login_message_category = "info"

# Inicializar Firebase Admin SDK e Firestore client
db = None
try:
    if FIREBASE_SERVICE_ACCOUNT_KEY_PATH:
        cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_KEY_PATH)
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_DB_URL
        })
        db = firestore.client()
        print("Firebase Admin SDK inicializado com sucesso e cliente Firestore conectado.")
    else:
        print("AVISO: FIREBASE_SERVICE_ACCOUNT_KEY_PATH não configurado. Firebase Admin SDK não inicializado.")
except Exception as e:
    print(f"Erro ao inicializar Firebase Admin SDK: {e}")

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    login_manager.init_app(app)

    # Registrar Blueprints aqui
    from .auth.routes import auth_bp # auth_bp já tem url_prefix='/auth'
    app.register_blueprint(auth_bp)

    from .bens.routes import bens_bp # Definiremos o url_prefix no init do blueprint de bens
    app.register_blueprint(bens_bp)

    # Rota de teste
    @app.route('/hello')
    def hello():
        return "Olá, Sistema de Patrimônio!"

    return app

# O user_loader callback é usado para recarregar o objeto do usuário
# a partir do ID de usuário armazenado na sessão.
@login_manager.user_loader
def load_user(user_id):
    # Não podemos importar services no nível superior devido a importações circulares
    # com `db` e `login_manager` sendo inicializados aqui.
    # Importamos aqui ou movemos a classe User e o load_user para auth.models.
    from .auth.models import User
    if not db: # Se o Firebase não estiver conectado, não podemos carregar usuários.
        return None
    return User.get(user_id, db)
