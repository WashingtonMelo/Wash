from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from . import bens_bp
from .forms import BemForm
from .services import (
    create_bem, get_bem_by_id, list_bens, update_bem, get_bem_by_tombo
)
# from ..auth.services import log_audit_event # Para log de auditoria geral, cuidado com import circular

# Helpers para conversão de data/decimal para formulário
from datetime import date
from decimal import Decimal

def prepare_bem_data_for_form(bem_data):
    """Converte dados do Firestore para popular o formulário BemForm."""
    if not bem_data:
        return {}

    form_pop_data = {}
    form_pop_data['numero_tombo_anterior'] = bem_data.get('numeroPatrimonialAnterior')
    form_pop_data['descricao_tecnica'] = bem_data.get('descricaoTecnica')

    if bem_data.get('notaFiscal'):
        form_pop_data['nota_fiscal_numero'] = bem_data['notaFiscal'].get('numero')
        # Firestore Timestamp to Python date
        nf_date_ts = bem_data['notaFiscal'].get('data')
        if nf_date_ts and hasattr(nf_date_ts, 'strftime'): # Checa se é um objeto datetime
             form_pop_data['nota_fiscal_data'] = nf_date_ts.date() if hasattr(nf_date_ts, 'date') else nf_date_ts
        elif isinstance(nf_date_ts, str): # Se estiver como string
             form_pop_data['nota_fiscal_data'] = date.fromisoformat(nf_date_ts.split('T')[0])
        else:
            form_pop_data['nota_fiscal_data'] = None

        form_pop_data['nota_fiscal_fornecedor_cnpj'] = bem_data['notaFiscal'].get('fornecedorCNPJ')

    form_pop_data['conta_contabil'] = bem_data.get('contaContabil')
    form_pop_data['valor_aquisicao'] = Decimal(str(bem_data.get('valorAquisicao', 0)))

    # Firestore Timestamp to Python date
    aq_date_ts = bem_data.get('dataAquisicao')
    if aq_date_ts and hasattr(aq_date_ts, 'strftime'):
        form_pop_data['data_aquisicao'] = aq_date_ts.date() if hasattr(aq_date_ts, 'date') else aq_date_ts
    elif isinstance(aq_date_ts, str):
         form_pop_data['data_aquisicao'] = date.fromisoformat(aq_date_ts.split('T')[0])
    else:
        form_pop_data['data_aquisicao'] = None

    form_pop_data['taxa_depreciacao_anual'] = Decimal(str(bem_data.get('taxaDepreciacaoAnual', 0))) if bem_data.get('taxaDepreciacaoAnual') is not None else None

    if bem_data.get('localizacao'):
        form_pop_data['localizacao_unidade'] = bem_data['localizacao'].get('unidade')
        form_pop_data['localizacao_secao'] = bem_data['localizacao'].get('secao')
        form_pop_data['localizacao_setor'] = bem_data['localizacao'].get('setor')
        form_pop_data['localizacao_responsavel'] = bem_data['localizacao'].get('responsavel')

    form_pop_data['situacao_bem'] = bem_data.get('situacao')
    form_pop_data['tipo_bem'] = bem_data.get('tipoBem')
    form_pop_data['observacoes'] = bem_data.get('observacoes')

    especificacoes = bem_data.get('especificacoes', {})
    if form_pop_data['tipo_bem'] == 'movel':
        form_pop_data['movel_marca'] = especificacoes.get('marca')
        form_pop_data['movel_modelo'] = especificacoes.get('modelo')
        form_pop_data['movel_cor'] = especificacoes.get('cor')
        form_pop_data['movel_dimensoes'] = especificacoes.get('dimensoes')
    elif form_pop_data['tipo_bem'] == 'veiculo':
        form_pop_data['veiculo_placa'] = especificacoes.get('placa')
        form_pop_data['veiculo_modelo'] = especificacoes.get('modelo')
        form_pop_data['veiculo_chassi'] = especificacoes.get('chassi')
        form_pop_data['veiculo_renavam'] = especificacoes.get('renavam')
        form_pop_data['veiculo_ano_fabricacao'] = especificacoes.get('anoFabricacao')
    elif form_pop_data['tipo_bem'] == 'armamento':
        form_pop_data['armamento_tipo'] = especificacoes.get('tipoArma')
        form_pop_data['armamento_calibre'] = especificacoes.get('calibre')
        form_pop_data['armamento_numero_serie'] = especificacoes.get('numeroSerieArma')
        form_pop_data['armamento_fabricante'] = especificacoes.get('fabricanteArma')

    return form_pop_data


@bens_bp.route('/', methods=['GET'])
@login_required
def listar_os_bens(): # Renomeado para evitar conflito com 'list_bens' do service
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 10) # Definir no config.py

    # TODO: Adicionar filtros do request.args
    filtros_req = {
        'tipoBem': request.args.get('tipoBem', None),
        'situacao': request.args.get('situacao', None)
        # Adicionar mais filtros conforme necessário
    }
    filtros_ativos = {k: v for k, v in filtros_req.items() if v}

    bens, total_bens, total_pages = list_bens(page=page, per_page=per_page, filtros=filtros_ativos)

    return render_template('listar_bens.html',
                           bens=bens,
                           title="Listagem de Bens",
                           page=page,
                           per_page=per_page,
                           total_bens=total_bens,
                           total_pages=total_pages,
                           filtros_aplicados=filtros_ativos)


@bens_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def cadastrar_bem():
    # TODO: Verificar permissão do usuário (ex: current_user.can_manage_patrimonio())
    form = BemForm()
    if form.validate_on_submit():
        try:
            # Passar form.data que é um MultiDict do WTForms
            # O service create_bem irá extrair os campos
            bem_id, numero_tombo, _ = create_bem(form.data)
            flash(f'Bem cadastrado com sucesso! Número de Tombo: {numero_tombo}', 'success')
            # log_audit_event(current_user.uid, "cadastro_bem_sucesso", {"bemId": bem_id, "numeroTombo": numero_tombo})
            return redirect(url_for('bens.detalhar_bem_por_id', bem_id=bem_id))
        except Exception as e:
            flash(f'Erro ao cadastrar bem: {e}', 'danger')
            current_app.logger.error(f"Erro ao cadastrar bem: {e}", exc_info=True)
            # log_audit_event(current_user.uid, "cadastro_bem_falha", {"erro": str(e)})
    else:
        if request.method == 'POST':
            flash('Formulário contém erros. Por favor, corrija-os.', 'warning')

    return render_template('cadastrar_bem.html', title='Cadastrar Novo Bem', form=form)


@bens_bp.route('/<string:bem_id>', methods=['GET'])
@login_required
def detalhar_bem_por_id(bem_id): # Renomeado para clareza
    bem = get_bem_by_id(bem_id)
    if not bem:
        flash('Bem não encontrado.', 'danger')
        return redirect(url_for('bens.listar_os_bens'))

    # Gerar dados para QR Code (exemplo simples)
    # Em um caso real, você pode querer mais dados ou uma URL para o bem
    qr_code_data = f"Tombo: {bem.get('numeroTombo')}\nDescrição: {bem.get('descricaoTecnica', '')[:50]}..."

    return render_template('detalhar_bem.html', title=f"Detalhes do Bem: {bem.get('numeroTombo')}", bem=bem, qr_code_data=qr_code_data)

@bens_bp.route('/tombo/<path:numero_tombo>', methods=['GET']) # path permite '/' no numero_tombo
@login_required
def detalhar_bem_por_tombo(numero_tombo):
    bem = get_bem_by_tombo(numero_tombo)
    if not bem:
        flash(f'Bem com tombo {numero_tombo} não encontrado.', 'danger')
        return redirect(url_for('bens.listar_os_bens'))
    # Reutiliza o mesmo template de detalhe por ID
    qr_code_data = f"Tombo: {bem.get('numeroTombo')}\nDescrição: {bem.get('descricaoTecnica', '')[:50]}..."
    return render_template('detalhar_bem.html', title=f"Detalhes do Bem: {bem.get('numeroTombo')}", bem=bem, qr_code_data=qr_code_data)


@bens_bp.route('/<string:bem_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_bem(bem_id):
    # TODO: Verificar permissão
    bem_data = get_bem_by_id(bem_id)
    if not bem_data:
        flash('Bem não encontrado.', 'danger')
        return redirect(url_for('bens.listar_os_bens'))

    # Popula o formulário com os dados existentes
    form_data_for_population = prepare_bem_data_for_form(bem_data)
    form = BemForm(data=form_data_for_population)

    # Para garantir que o tipo de bem não seja alterado para um que invalide campos já preenchidos
    # ou para simplificar, podemos desabilitar a alteração do tipo de bem após o cadastro.
    # form.tipo_bem.render_kw = {'disabled': 'disabled'} # Exemplo para desabilitar

    if form.validate_on_submit():
        try:
            # Se o tipo_bem foi desabilitado, precisamos pegar o valor original
            # updated_data = form.data.copy()
            # if 'tipo_bem' not in updated_data or not updated_data['tipo_bem']:
            # updated_data['tipo_bem'] = bem_data.get('tipoBem')

            update_bem(bem_id, form.data) # Passa o form.data
            flash('Bem atualizado com sucesso!', 'success')
            # log_audit_event(current_user.uid, "edicao_bem_sucesso", {"bemId": bem_id})
            return redirect(url_for('bens.detalhar_bem_por_id', bem_id=bem_id))
        except FileNotFoundError:
            flash('Erro: Bem não encontrado para atualização.', 'danger')
            return redirect(url_for('bens.listar_os_bens'))
        except Exception as e:
            flash(f'Erro ao atualizar bem: {e}', 'danger')
            current_app.logger.error(f"Erro ao editar bem {bem_id}: {e}", exc_info=True)
            # log_audit_event(current_user.uid, "edicao_bem_falha", {"bemId": bem_id, "erro": str(e)})
    else:
        if request.method == 'POST':
             flash('Formulário contém erros. Por favor, corrija-os.', 'warning')
             # Para depuração, mostrar erros do formulário:
             # for field, errors in form.errors.items():
             #     for error in errors:
             #         flash(f"Erro no campo '{getattr(form, field).label.text}': {error}", 'danger')


    return render_template('editar_bem.html', title=f"Editar Bem: {bem_data.get('numeroTombo')}", form=form, bem_id=bem_id, numero_tombo=bem_data.get('numeroTombo'))


# Rota para gerar QR Code (exemplo)
@bens_bp.route('/<string:bem_id>/qrcode', methods=['GET'])
@login_required
def gerar_qr_code_bem(bem_id):
    bem = get_bem_by_id(bem_id)
    if not bem:
        return jsonify({"error": "Bem não encontrado"}), 404

    try:
        import qrcode
        import io
        from flask import send_file

        # Dados para o QR Code (pode ser uma URL para a página de detalhes do bem)
        # data_qr = url_for('bens.detalhar_bem_por_id', bem_id=bem_id, _external=True)
        # Ou dados mais simples:
        data_qr = f"ID: {bem_id}\nTombo: {bem.get('numeroTombo', 'N/A')}\nDesc: {bem.get('descricaoTecnica', '')[:30]}"

        img = qrcode.make(data_qr)
        buf = io.BytesIO()
        img.save(buf, 'PNG')
        buf.seek(0)
        return send_file(buf, mimetype='image/png')

    except ImportError:
        flash("Biblioteca 'qrcode' não instalada. Não é possível gerar QR Code.", 'warning')
        return redirect(url_for('bens.detalhar_bem_por_id', bem_id=bem_id))
    except Exception as e:
        flash(f"Erro ao gerar QR Code: {e}", 'danger')
        return redirect(url_for('bens.detalhar_bem_por_id', bem_id=bem_id))


# TODO: Implementar rota de exclusão (baixa lógica)
# @bens_bp.route('/<string:bem_id>/baixar', methods=['POST'])
# @login_required
# def baixar_bem(bem_id):
#     # Lógica para baixa (mudar status para 'inservivel' ou 'baixado')
#     pass
