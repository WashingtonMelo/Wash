from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
# from ..auth.services import get_user_by_email # Evitar importação direta de services aqui para prevenir circularidade se services importar forms
from firebase_admin import auth as firebase_auth # Usado para checar se email existe

# Perfis de usuário para o formulário de registro
# Idealmente, isso viria de uma configuração ou dos services, mas para o form é mais simples assim por agora.
USER_PROFILES_CHOICES = [
    ("consulta", "Consulta"),
    ("almoxarife", "Almoxarife"),
    ("gestor_patrimonial", "Gestor Patrimonial"),
    ("auditor", "Auditor"),
    # ("administrador", "Administrador") # Normalmente, admin não se auto-registra assim
]


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(message="Email é obrigatório."), Email(message="Email inválido.")])
    password = PasswordField('Senha', validators=[DataRequired(message="Senha é obrigatória.")])
    remember_me = BooleanField('Lembrar-me')
    submit = SubmitField('Login')


class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6, message="A senha deve ter pelo menos 6 caracteres.")])
    password2 = PasswordField(
        'Repetir Senha', validators=[DataRequired(), EqualTo('password', message="As senhas devem ser iguais.")])
    nome_completo = StringField('Nome Completo', validators=[DataRequired()])
    matricula = StringField('Matrícula', validators=[DataRequired()])
    cargo_funcao = StringField('Cargo/Função', validators=[DataRequired()])
    telefone = StringField('Telefone', validators=[DataRequired()])
    perfil = SelectField('Perfil', choices=USER_PROFILES_CHOICES, validators=[DataRequired()])
    submit = SubmitField('Registrar')

    def validate_email(self, email):
        try:
            # Verificar se o email já existe no Firebase Authentication
            firebase_auth.get_user_by_email(email.data)
            # Se não levantar exceção, o email já existe
            raise ValidationError('Este email já está cadastrado. Por favor, use um email diferente ou faça login.')
        except firebase_auth.UserNotFoundError:
            # Email não encontrado, o que é bom para um novo registro
            pass
        except Exception as e:
            # Outro erro do Firebase, tratar como falha na validação
            # print(f"Erro ao validar email no Firebase Auth: {e}")
            raise ValidationError(f'Erro ao verificar o email: {e}')


class PasswordResetRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Solicitar Redefinição de Senha')

    def validate_email(self, email):
        try:
            firebase_auth.get_user_by_email(email.data)
        except firebase_auth.UserNotFoundError:
            # Não informar ao usuário se o email existe ou não por segurança.
            # Apenas para o log ou tratamento interno, saberemos que não foi encontrado.
            # raise ValidationError('Email não encontrado. Verifique o email digitado.')
            print(f"Solicitação de reset para email não existente: {email.data}")
        except Exception as e:
            raise ValidationError(f'Erro ao verificar o email: {e}')


class PasswordResetForm(FlaskForm):
    password = PasswordField('Nova Senha', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        'Repetir Nova Senha', validators=[DataRequired(), EqualTo('password', message="As senhas devem ser iguais.")])
    submit = SubmitField('Redefinir Senha')
