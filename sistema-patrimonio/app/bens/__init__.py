from flask import Blueprint

bens_bp = Blueprint('bens',
                    __name__,
                    template_folder='bens',  # Procurará em app/templates/bens/
                    static_folder='static/bens',
                    url_prefix='/bens')

from . import routes # Importar rotas depois de criar o blueprint
from . import models # Se tivermos modelos específicos para bens (Pydantic, etc.)
