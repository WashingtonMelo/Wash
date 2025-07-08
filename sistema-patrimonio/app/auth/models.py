from flask_login import UserMixin
# from firebase_admin import firestore # Evitar import aqui se db é passado como argumento

class User(UserMixin):
    def __init__(self, uid, email, nome_completo, matricula, perfil, ativo=True, cargo_funcao=None, telefone=None, ultimo_login=None, data_criacao=None):
        self.id = uid  # Flask-Login espera que o ID do usuário seja chamado 'id'
        self.uid = uid
        self.email = email
        self.nome_completo = nome_completo
        self.matricula = matricula
        self.perfil = perfil
        self.ativo = ativo
        self.cargo_funcao = cargo_funcao
        self.telefone = telefone
        self.ultimo_login = ultimo_login
        self.data_criacao = data_criacao

    def __repr__(self):
        return f"<User {self.email} (UID: {self.uid}, Perfil: {self.perfil})>"

    @staticmethod
    def get(user_id, db_client):
        """
        Retorna um objeto User a partir do UID, buscando dados no Firestore.
        `db_client` é a instância do cliente Firestore.
        """
        if not db_client:
            print("models.User.get: Cliente Firestore não fornecido ou não inicializado.")
            return None
        try:
            user_doc_ref = db_client.collection('usuarios').document(user_id)
            user_doc = user_doc_ref.get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                return User(
                    uid=user_data.get('uid'),
                    email=user_data.get('email'),
                    nome_completo=user_data.get('nomeCompleto'),
                    matricula=user_data.get('matricula'),
                    perfil=user_data.get('perfil'),
                    ativo=user_data.get('ativo', True),
                    cargo_funcao=user_data.get('cargoFuncao'),
                    telefone=user_data.get('telefone'),
                    ultimo_login=user_data.get('ultimoLogin'),
                    data_criacao=user_data.get('dataCriacao')
                )
            return None
        except Exception as e:
            print(f"Erro ao buscar usuário {user_id} em models.User.get: {e}")
            return None

    # Flask-Login requer estas propriedades/métodos se não herdados de UserMixin com defaults
    # No entanto, UserMixin já os fornece com valores padrão (True/True/True/id).
    # @property
    # def is_active(self):
    # return self.ativo

    # @property
    # def is_authenticated(self):
    #     # Todos os usuários carregados devem ser autenticados
    #     return True

    # @property
    # def is_anonymous(self):
    #     return False

    # def get_id(self):
    # return str(self.uid) # Deve retornar uma string

    # Métodos de verificação de perfil/permissão podem ser adicionados aqui
    def has_role(self, role_name):
        return self.perfil == role_name

    def is_admin(self):
        return self.perfil == "administrador"

    def can_manage_patrimonio(self):
        return self.perfil in ["administrador", "gestor_patrimonial", "almoxarife"]
