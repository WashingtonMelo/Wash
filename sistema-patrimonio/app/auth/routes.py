from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from . import auth_bp
from .forms import LoginForm, RegistrationForm, PasswordResetRequestForm, PasswordResetForm
from .services import create_user_with_email_password, get_user_profile, \
                      send_password_reset_email_service, log_audit_event, \
                      update_last_login, get_user_by_firebase_uid
from .models import User
from firebase_admin import auth as firebase_auth
from werkzeug.urls import url_parse

# No __init__.py do app, db é inicializado. Se precisar dele diretamente aqui:
# from app import db # Supondo que db foi inicializado no app/__init__.py globalmente
# Ou, se você passou db para o blueprint:
# db = auth_bp.db

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('hello')) # Ou uma rota de dashboard

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        remember = form.remember_me.data
        try:
            # Tentar autenticar com Firebase Auth (isso não cria sessão por si só)
            # Usamos um custom token ou verificação de id token para logar de forma segura
            # Para simplificar aqui, vamos assumir que se o signInWithPassword funcionar (o que faríamos no frontend),
            # o usuário existe e a senha está correta.
            # No backend puro, verificaríamos a senha de outra forma ou usaríamos ID tokens do cliente.

            # Solução mais simples para backend puro sem cliente Firebase JS:
            # 1. Buscar usuário pelo email para pegar o UID.
            firebase_user = firebase_auth.get_user_by_email(email)
            # 2. (Importante) Aqui é onde a verificação real da senha deveria acontecer.
            # O Admin SDK NÃO TEM um método `signInWithPassword`. Essa verificação
            # normalmente é feita pelo SDK cliente (web/mobile) que então envia um ID Token
            # para o backend. O backend verifica o ID Token.
            # Para um formulário web tradicional servido pelo Flask, isso é um desafio.
            # Opções:
            #    a) Usar Firebase UI Web no frontend e enviar ID token para uma rota de API no Flask.
            #    b) Implementar um endpoint que aceite email/senha, chame uma Firebase Function
            #       (que pode usar o SDK cliente) para verificar a senha e retornar um custom token.
            #    c) Para este exemplo, vamos simular um login bem-sucedido se o usuário existir
            #       e **PULAR A VERIFICAÇÃO DE SENHA NO BACKEND**, o que é INSEGURO para produção.
            #       Em um cenário real, você PRECISARIA verificar a senha.
            #       Uma forma seria usar a API REST de identidade do Firebase:
            #       https://firebase.google.com/docs/reference/rest/auth#section-sign-in-email-password
            #       Isso requer a API Key do projeto.

            # >>> INÍCIO DA SIMULAÇÃO INSEGURA (NÃO FAÇA ISSO EM PRODUÇÃO) <<<
            # Em um sistema real, você usaria a API REST ou um ID token do cliente.
            # Este bloco apenas verifica se o usuário existe, não a senha.
            if firebase_user: # Se o usuário existe (senha não verificada aqui!)
                user_profile_data = get_user_profile(firebase_user.uid)
                if user_profile_data and user_profile_data.get('ativo'):
                    user = User(
                        uid=user_profile_data.get('uid'),
                        email=user_profile_data.get('email'),
                        nome_completo=user_profile_data.get('nomeCompleto'),
                        matricula=user_profile_data.get('matricula'),
                        perfil=user_profile_data.get('perfil'),
                        ativo=user_profile_data.get('ativo')
                    )
                    login_user(user, remember=remember)
                    update_last_login(firebase_user.uid)
                    log_audit_event(firebase_user.uid, "login_sucesso")

                    next_page = request.args.get('next')
                    if not next_page or url_parse(next_page).netloc != '':
                        next_page = url_for('hello') # Rota principal após login
                    return redirect(next_page)
                else:
                    flash('Conta desativada ou perfil não encontrado.', 'danger')
                    log_audit_event(firebase_user.uid if firebase_user else None, "login_falha", {"email": email, "motivo": "conta_desativada_ou_perfil_incompleto"})
            else: # Isso não deveria acontecer se get_user_by_email não lançou exceção
                flash('Usuário não encontrado.', 'danger')
                log_audit_event(None, "login_falha", {"email": email, "motivo": "usuario_nao_encontrado_inesperado"})

            # >>> FIM DA SIMULAÇÃO INSEGURA <<<

        except firebase_auth.UserNotFoundError:
            flash('Login inválido. Verifique email e senha.', 'warning')
            log_audit_event(None, "login_falha", {"email": email, "motivo": "usuario_nao_encontrado"})
        except firebase_auth.FirebaseError as e:
            flash(f'Erro de autenticação: {e}', 'danger')
            log_audit_event(None, "login_falha", {"email": email, "erro": str(e)})
        except Exception as e:
            flash(f'Ocorreu um erro: {e}', 'danger')
            log_audit_event(None, "login_falha", {"email": email, "erro": str(e)})

    return render_template('login.html', title='Login', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('hello'))
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            _, user_data = create_user_with_email_password(
                email=form.email.data,
                password=form.password.data,
                nome_completo=form.nome_completo.data,
                matricula=form.matricula.data,
                cargo_funcao=form.cargo_funcao.data,
                telefone=form.telefone.data,
                perfil=form.perfil.data
            )
            flash('Cadastro realizado com sucesso! Você já pode fazer login.', 'success')
            # log_audit_event é chamado dentro de create_user_with_email_password
            return redirect(url_for('auth.login'))
        except ValueError as e: # Erros como email já existe ou perfil inválido
            flash(str(e), 'danger')
            log_audit_event(None, "registro_falha", {"email": form.email.data, "erro": str(e)})
        except Exception as e:
            flash(f'Ocorreu um erro durante o registro: {e}', 'danger')
            log_audit_event(None, "registro_falha", {"email": form.email.data, "erro_inesperado": str(e)})

    return render_template('register.html', title='Registrar', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    user_uid = current_user.uid if current_user else "desconhecido"
    logout_user()
    flash('Você foi desconectado.', 'info')
    log_audit_event(user_uid, "logout")
    return redirect(url_for('auth.login'))


@auth_bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('hello'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        email = form.email.data
        try:
            # O serviço já lida com log e UserNotFoundError de forma segura
            reset_link = send_password_reset_email_service(email)
            if reset_link:
                # EM PRODUÇÃO: Envie o email aqui com o `reset_link`
                # Ex: send_email_utility(subject="Redefinição de Senha", recipients=[email], body=f"Clique aqui para redefinir: {reset_link}")
                flash('Um email foi enviado com instruções para redefinir sua senha (se o email estiver cadastrado). Verifique sua caixa de entrada e spam.', 'info')
                print(f"DEV_NOTE: Link de reset para {email}: {reset_link}")
            else:
                # Mensagem genérica mesmo se o email não existir, para não vazar informação.
                 flash('Se o seu email estiver cadastrado em nosso sistema, você receberá um link para redefinir a senha. Verifique sua caixa de entrada e spam.', 'info')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f'Erro ao solicitar redefinição de senha: {e}', 'danger')
            log_audit_event(None, "reset_senha_solicitacao_erro_inesperado", {"email": email, "erro": str(e)})

    return render_template('reset_password_request.html', title='Solicitar Redefinição de Senha', form=form)


# A rota real de reset de senha (para onde o link do email aponta)
# geralmente é tratada pelo Firebase diretamente ou por uma página hospedada pelo Firebase.
# Se você quiser uma página customizada DENTRO do seu app Flask para o reset:
# 1. O link gerado pelo `generate_password_reset_link` direciona para uma URL do Firebase.
# 2. Essa URL do Firebase pode ser configurada no console Firebase (Authentication > Templates > Password reset)
#    para redirecionar para uma URL do seu app, passando o `oobCode` (o token) como parâmetro.
#    Ex: https://meuapp.com/auth/reset_password?mode=resetPassword&oobCode=CODIGO_AQUI&apiKey=SUA_API_KEY
#
# A rota abaixo simula o recebimento desse oobCode.

@auth_bp.route('/reset_password_action', methods=['GET', 'POST']) # Nome alterado para refletir ação
def reset_password_action():
    if current_user.is_authenticated:
        return redirect(url_for('hello'))

    oob_code = request.args.get('oobCode')
    if not oob_code:
        flash('Link de redefinição inválido ou expirado. (Código ausente)', 'danger')
        return redirect(url_for('auth.login'))

    form = PasswordResetForm()
    if request.method == 'GET':
        # Apenas para verificar se o código é válido antes de mostrar o formulário
        try:
            email_verified = firebase_auth.check_password_reset_code(oob_code)
            session['reset_oob_code'] = oob_code # Salva o código na sessão para usar no POST
            session['reset_email'] = email_verified # Salva o email verificado
            flash(f'Redefinindo senha para {email_verified}. Por favor, insira sua nova senha.', 'info')
        except firebase_auth.FirebaseError as e:
            flash(f'Link de redefinição inválido ou expirado: {e}', 'danger')
            log_audit_event(None, "reset_senha_link_invalido", {"oob_code": oob_code, "erro": str(e)})
            return redirect(url_for('auth.login'))

    if form.validate_on_submit():
        saved_oob_code = session.get('reset_oob_code')
        saved_email = session.get('reset_email')

        if not saved_oob_code or saved_oob_code != oob_code: # Checagem extra
            flash('Sessão de redefinição inválida ou expirada. Tente novamente.', 'danger')
            return redirect(url_for('auth.reset_password_request'))

        new_password = form.password.data
        try:
            firebase_auth.confirm_password_reset(saved_oob_code, new_password)
            flash('Sua senha foi redefinida com sucesso! Você já pode fazer login com a nova senha.', 'success')
            log_audit_event(None, "reset_senha_sucesso", {"email": saved_email}) # Idealmente pegar o UID aqui se possível
            session.pop('reset_oob_code', None)
            session.pop('reset_email', None)
            return redirect(url_for('auth.login'))
        except firebase_auth.FirebaseError as e:
            flash(f'Erro ao redefinir senha: {e}', 'danger')
            log_audit_event(None, "reset_senha_falha_confirmacao", {"email": saved_email, "erro": str(e)})
        except Exception as e:
            flash(f'Erro inesperado ao redefinir senha: {e}', 'danger')
            log_audit_event(None, "reset_senha_falha_inesperada", {"email": saved_email, "erro": str(e)})

    return render_template('reset_password_form.html', title='Redefinir Senha', form=form, oobCode=oob_code)


# Exemplo de rota protegida
@auth_bp.route('/profile')
@login_required
def profile():
    # current_user já é o objeto User carregado pelo Flask-Login
    return render_template('profile.html', title='Perfil', user=current_user)
