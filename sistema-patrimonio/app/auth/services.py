from firebase_admin import auth as firebase_auth
from firebase_admin import firestore
from datetime import datetime

# Inicializa o cliente Firestore.
# Presume-se que o Firebase Admin SDK já foi inicializado em app/__init__.py
try:
    db = firestore.client()
except Exception as e:
    print(f"Erro ao obter cliente Firestore em services.py: {e}")
    db = None

# Perfis de usuário permitidos
VALID_USER_PROFILES = ["administrador", "gestor_patrimonial", "almoxarife", "auditor", "consulta"]

def create_user_with_email_password(email, password, nome_completo, matricula, cargo_funcao, telefone, perfil="consulta"):
    """
    Cria um novo usuário no Firebase Authentication e armazena informações adicionais no Firestore.
    """
    if not db:
        raise ConnectionError("Conexão com o Firestore não estabelecida.")

    if perfil not in VALID_USER_PROFILES:
        raise ValueError(f"Perfil de usuário inválido: {perfil}. Permitidos: {VALID_USER_PROFILES}")

    try:
        # 1. Criar usuário no Firebase Authentication
        firebase_user = firebase_auth.create_user(
            email=email,
            password=password,
            display_name=nome_completo,
            disabled=False # Usuário ativo por padrão
        )

        # 2. Armazenar informações adicionais no Firestore
        user_data = {
            'uid': firebase_user.uid,
            'email': email,
            'nomeCompleto': nome_completo,
            'matricula': matricula,
            'cargoFuncao': cargo_funcao,
            'telefone': telefone,
            'perfil': perfil,
            'ativo': True,
            'dataCriacao': datetime.utcnow(),
            'ultimoLogin': None # Será atualizado no login
        }

        db.collection('usuarios').document(firebase_user.uid).set(user_data)
        log_audit_event(firebase_user.uid, "criacao_usuario", {"email": email, "perfil": perfil})
        return firebase_user, user_data

    except firebase_auth.EmailAlreadyExistsError:
        raise ValueError(f"O email '{email}' já está em uso.")
    except Exception as e:
        # Se a criação no Firestore falhar após a criação no Firebase Auth,
        # idealmente deveríamos deletar o usuário do Firebase Auth para consistência.
        # firebase_auth.delete_user(firebase_user.uid) # Adicionar lógica de rollback
        print(f"Erro ao criar usuário: {e}")
        raise

def get_user_profile(uid):
    """
    Busca o perfil de um usuário no Firestore pelo UID.
    """
    if not db:
        raise ConnectionError("Conexão com o Firestore não estabelecida.")
    try:
        user_ref = db.collection('usuarios').document(uid)
        user_doc = user_ref.get()
        if user_doc.exists:
            return user_doc.to_dict()
        else:
            return None
    except Exception as e:
        print(f"Erro ao buscar perfil do usuário {uid}: {e}")
        raise

def get_user_by_firebase_uid(uid):
    """
    Busca um usuário no Firebase Authentication pelo UID.
    """
    try:
        user = firebase_auth.get_user(uid)
        return user
    except firebase_auth.UserNotFoundError:
        return None
    except Exception as e:
        print(f"Erro ao buscar usuário no Firebase Auth {uid}: {e}")
        raise

def send_password_reset_email_service(email):
    """
    Envia um email de redefinição de senha usando Firebase Authentication.
    """
    try:
        link = firebase_auth.generate_password_reset_link(email)
        # A lógica de envio do email (usando Flask-Mail, por exemplo) seria aqui.
        # Firebase Auth apenas gera o link. O envio do email é responsabilidade do app.
        # Por enquanto, vamos apenas retornar o link (para fins de desenvolvimento/teste).
        # Em produção, você NUNCA deve expor o link diretamente.
        print(f"Link para reset de senha (NÃO ENVIAR DIRETAMENTE EM PRODUÇÃO): {link}")
        log_audit_event(None, "solicitacao_reset_senha", {"email": email, "status": "link_gerado"})
        return link # Apenas para desenvolvimento.
    except firebase_auth.UserNotFoundError:
        # Não revele se o email existe ou não por segurança.
        print(f"Tentativa de reset de senha para email não registrado (ou erro): {email}")
        # Mesmo assim, logue a tentativa.
        log_audit_event(None, "solicitacao_reset_senha_falha", {"email": email, "motivo": "usuario_nao_encontrado"})
        return None # Ou uma mensagem genérica
    except Exception as e:
        print(f"Erro ao gerar link de reset de senha para {email}: {e}")
        log_audit_event(None, "solicitacao_reset_senha_erro", {"email": email, "erro": str(e)})
        raise

def update_last_login(uid):
    """
    Atualiza o campo ultimoLogin para o usuário no Firestore.
    """
    if not db:
        print("Firestore não conectado. Não foi possível atualizar último login.")
        return
    try:
        user_ref = db.collection('usuarios').document(uid)
        user_ref.update({'ultimoLogin': datetime.utcnow()})
    except Exception as e:
        print(f"Erro ao atualizar último login para UID {uid}: {e}")
        # Não levantar exceção aqui para não quebrar o fluxo de login

def log_audit_event(user_uid, action, details=None):
    """
    Registra um evento de auditoria no Firestore.
    """
    if not db:
        print(f"AUDIT LOG (Firestore não conectado): User {user_uid}, Action: {action}, Details: {details}")
        return

    try:
        log_entry = {
            'timestamp': datetime.utcnow(),
            'user_uid': user_uid if user_uid else "sistema", # UID do usuário ou 'sistema' para ações não atreladas
            'action': action,
            'details': details if details else {}
            # 'ip_address': request.remote_addr # Se tiver acesso ao objeto request
        }
        db.collection('logs_auditoria').add(log_entry)
    except Exception as e:
        print(f"Erro ao registrar log de auditoria: {e}")

# Mais funções podem ser adicionadas aqui, como:
# - update_user_profile(uid, data)
# - deactivate_user(uid)
# - list_users_with_profiles()
# - etc.
