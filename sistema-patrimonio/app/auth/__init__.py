from flask import Blueprint

auth_bp = Blueprint('auth', __name__, template_folder='auth', static_folder='static/auth', url_prefix='/auth')
# template_folder é relativo ao diretório 'templates' da aplicação.
# static_folder é relativo ao diretório 'static' da aplicação.
# url_prefix é definido aqui para manter tudo do auth junto.

from . import routes
