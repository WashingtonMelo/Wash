from firebase_admin import firestore
from datetime import datetime
from flask_login import current_user # Para registrar quem fez a ação

# Presume-se que o Firebase Admin SDK já foi inicializado em app/__init__.py
# e que `db` é o cliente Firestore.
try:
    db = firestore.client()
except Exception as e:
    print(f"Erro ao obter cliente Firestore em bens/services.py: {e}")
    db = None

CONTADOR_TOMBO_DOC_ID = "contador_numero_tombo"
PARAMETROS_COLLECTION = "_parametros_sistema" # Coleção para contadores e outros parâmetros

def generate_numero_tombo():
    """
    Gera um novo número de tombo sequencial.
    O número de tombo será formatado como ANO-SEQUENCIAL (ex: 2023-00001).
    """
    if not db:
        raise ConnectionError("Conexão com o Firestore não estabelecida.")

    contador_ref = db.collection(PARAMETROS_COLLECTION).document(CONTADOR_TOMBO_DOC_ID)

    year = datetime.utcnow().year

    # Transação para garantir atomicidade na atualização do contador
    @firestore.transactional
    def update_in_transaction(transaction, ref):
        snapshot = ref.get(transaction=transaction)

        current_year_on_db = snapshot.get(f'ultimo_ano_gerado')
        current_seq = snapshot.get(f'ultimo_sequencial_ano_{year}')

        if not snapshot.exists or not current_seq or current_year_on_db != year:
            # Reinicia sequencial para o novo ano ou se não existir
            new_sequential = 1
            transaction.set(ref, {
                f'ultimo_sequencial_ano_{year}': new_sequential,
                'ultimo_ano_gerado': year,
                # Preserva contadores de anos anteriores se existirem
                **snapshot.to_dict() if snapshot.exists else {}
            }, merge=True)
        else:
            new_sequential = current_seq + 1
            transaction.update(ref, {
                f'ultimo_sequencial_ano_{year}': new_sequential,
                'ultimo_ano_gerado': year
            })
        return new_sequential

    try:
        new_seq_num = update_in_transaction(db.transaction(), contador_ref)
        return f"{year}-{new_seq_num:05d}" # Formato ANO-00001
    except Exception as e:
        print(f"Erro ao gerar número de tombo: {e}")
        # Fallback muito simples em caso de erro transacional extremo (raro)
        # Poderia tentar algumas vezes ou ter um mecanismo mais robusto
        timestamp_fallback = int(datetime.utcnow().timestamp() * 1000)
        return f"{year}-ERR{timestamp_fallback}"


def create_bem(form_data):
    """
    Cria um novo bem patrimonial no Firestore.
    `form_data` é um dicionário com os dados validados do formulário.
    """
    if not db:
        raise ConnectionError("Conexão com o Firestore não estabelecida.")

    numero_tombo = generate_numero_tombo()

    # Coleta dados do formulário e estrutura para o Firestore
    data_bem = {
        "numeroTombo": numero_tombo,
        "numeroPatrimonialAnterior": form_data.get("numero_tombo_anterior"),
        "descricaoTecnica": form_data.get("descricao_tecnica"),
        "notaFiscal": {
            "numero": form_data.get("nota_fiscal_numero"),
            "data": form_data.get("nota_fiscal_data"), # Já deve ser objeto date
            "fornecedorCNPJ": form_data.get("nota_fiscal_fornecedor_cnpj")
        },
        "contaContabil": form_data.get("conta_contabil"),
        "valorAquisicao": float(form_data.get("valor_aquisicao")), # WTForms DecimalField -> float
        "dataAquisicao": form_data.get("data_aquisicao"), # Já deve ser objeto date
        "taxaDepreciacaoAnual": float(form_data.get("taxa_depreciacao_anual")) if form_data.get("taxa_depreciacao_anual") is not None else None,
        "localizacao": {
            "unidade": form_data.get("localizacao_unidade"),
            "secao": form_data.get("localizacao_secao"),
            "setor": form_data.get("localizacao_setor"),
            "responsavel": form_data.get("localizacao_responsavel")
        },
        "situacao": form_data.get("situacao_bem"),
        "tipoBem": form_data.get("tipo_bem"),
        "especificacoes": {}, # Preencher de acordo com o tipo_bem
        "observacoes": form_data.get("observacoes"),
        "dataCadastro": datetime.utcnow(),
        "usuarioCadastroUID": current_user.uid if current_user.is_authenticated else None,
        "ativo": True, # Bem ativo por padrão ao ser cadastrado
        "historico": [
            {
                "timestamp": datetime.utcnow(),
                "usuarioUID": current_user.uid if current_user.is_authenticated else "sistema",
                "acao": "criacao",
                "detalhes": f"Bem cadastrado com número de tombo {numero_tombo}."
            }
        ]
    }

    # Preencher especificações de acordo com o tipo de bem
    tipo_bem = data_bem["tipoBem"]
    if tipo_bem == "movel":
        data_bem["especificacoes"] = {
            "marca": form_data.get("movel_marca"),
            "modelo": form_data.get("movel_modelo"),
            "cor": form_data.get("movel_cor"),
            "dimensoes": form_data.get("movel_dimensoes"),
        }
    elif tipo_bem == "veiculo":
        data_bem["especificacoes"] = {
            "placa": form_data.get("veiculo_placa"),
            "modelo": form_data.get("veiculo_modelo"),
            "chassi": form_data.get("veiculo_chassi"),
            "renavam": form_data.get("veiculo_renavam"),
            "anoFabricacao": form_data.get("veiculo_ano_fabricacao"),
        }
    elif tipo_bem == "armamento":
        data_bem["especificacoes"] = {
            "tipoArma": form_data.get("armamento_tipo"), # Nome do campo no Firestore
            "calibre": form_data.get("armamento_calibre"),
            "numeroSerieArma": form_data.get("armamento_numero_serie"), # Nome do campo no Firestore
            "fabricanteArma": form_data.get("armamento_fabricante"), # Nome do campo no Firestore
        }
    # Adicionar outros tipos conforme necessário

    try:
        # O ID do documento no Firestore pode ser o próprio número de tombo
        # ou um UUID gerado automaticamente, com o número de tombo sendo um campo indexado.
        # Usar número de tombo como ID pode ser simples para busca direta, mas UUIDs são mais robustos para distribuição.
        # Vamos usar um ID automático do Firestore por enquanto.
        doc_ref = db.collection('bens').document()
        data_bem['id'] = doc_ref.id # Armazena o ID gerado pelo Firestore no próprio documento

        doc_ref.set(data_bem)

        # Log de auditoria geral (já coberto pelo histórico do bem, mas pode ser adicional)
        # from ..auth.services import log_audit_event (cuidado com import circular)
        # log_audit_event(current_user.uid, "cadastro_bem", {"numeroTombo": numero_tombo, "bemId": doc_ref.id})

        return doc_ref.id, numero_tombo, data_bem
    except Exception as e:
        print(f"Erro ao criar bem no Firestore: {e}")
        raise

def get_bem_by_id(bem_id):
    """Busca um bem pelo seu ID de documento no Firestore."""
    if not db:
        raise ConnectionError("Conexão com o Firestore não estabelecida.")
    try:
        doc_ref = db.collection('bens').document(bem_id)
        bem = doc_ref.get()
        if bem.exists:
            return bem.to_dict()
        return None
    except Exception as e:
        print(f"Erro ao buscar bem por ID {bem_id}: {e}")
        raise

def get_bem_by_tombo(numero_tombo):
    """Busca um bem pelo seu número de tombo."""
    if not db:
        raise ConnectionError("Conexão com o Firestore não estabelecida.")
    try:
        bens_ref = db.collection('bens').where('numeroTombo', '==', numero_tombo).limit(1)
        results = bens_ref.stream()
        for bem_doc in results:
            return bem_doc.to_dict()
        return None
    except Exception as e:
        print(f"Erro ao buscar bem por número de tombo {numero_tombo}: {e}")
        raise

def list_bens(page=1, per_page=10, filtros=None):
    """
    Lista bens com paginação e filtros.
    `filtros` é um dicionário opcional, ex: {'tipoBem': 'veiculo', 'situacao': 'novo'}
    Retorna uma tupla: (lista de bens, total de bens para os filtros, total de páginas)
    A implementação de paginação eficiente com Firestore e múltiplos filtros `where`
    e `orderBy` pode ser complexa. Firestore tem limitações em queries (ex: não pode
    usar `!=` ou `not-in` facilmente, e range filters em múltiplos campos são restritos).

    Esta é uma implementação básica. Para paginação real com start_after,
    você precisaria do último documento da página anterior.
    """
    if not db:
        raise ConnectionError("Conexão com o Firestore não estabelecida.")

    query = db.collection('bens')

    if filtros:
        for campo, valor in filtros.items():
            if valor: # Apenas aplica filtro se houver valor
                query = query.where(campo, '==', valor)

    # Para contar o total com filtros, precisamos executar a query sem paginação
    # Isso pode ser ineficiente para grandes datasets.
    # Uma alternativa é manter contadores agregados ou usar Cloud Functions.
    # Por simplicidade, vamos buscar todos os IDs e contar.
    # total_bens_snapshot = query.select([]).stream() # Pega apenas IDs
    # total_bens = sum(1 for _ in total_bens_snapshot)
    # Se for muito lento, precisaremos de outra estratégia para contagem total.
    # Para uma contagem aproximada ou para datasets menores:
    all_matching_docs = query.stream()
    temp_list = [doc.to_dict() for doc in all_matching_docs]
    total_bens = len(temp_list)


    # Aplicar ordenação e paginação
    # Firestore requer um índice para cada combinação de where + orderBy.
    query = query.order_by("dataCadastro", direction=firestore.Query.DESCENDING) # Exemplo de ordenação

    # Paginação baseada em offset (menos eficiente no Firestore, mas mais simples de implementar inicialmente)
    # Para paginação baseada em cursor (start_after), você precisaria passar o último documento da página anterior.
    offset = (page - 1) * per_page

    # query_page = query.limit(per_page).offset(offset).stream() # Offset não é ideal
    # Vamos simular offset buscando mais e fatiando, ou usando start_after se possível

    # Simulação de paginação por offset (não ideal para performance no Firestore)
    # Se for usar start_after, a lógica muda significativamente.
    # Esta é uma forma simplificada que busca todos os resultados e fatia na memória:
    # all_docs = query.stream() # Re-executa a query ordenada
    # bens_list = [doc.to_dict() for doc in all_docs]
    # paginated_bens = bens_list[offset : offset + per_page]

    # Uma abordagem um pouco melhor para paginação simples sem `start_after` para este exemplo:
    # Buscar `page * per_page` e pegar os últimos `per_page` (se ordenado ASC)
    # ou os primeiros `per_page` de um slice (se ordenado DESC e buscado até `page * per_page`)

    # Para simplificar este exemplo inicial, vamos usar a lista já obtida para contagem (temp_list)
    # e aplicar a paginação nela. ISSO NÃO É EFICIENTE PARA GRANDES DATASETS.
    # Em um sistema real, a paginação com Firestore deve usar cursores (start_after).

    if page < 1: page = 1
    start_index = (page - 1) * per_page
    end_index = start_index + per_page

    # Reordenar temp_list se a ordenação padrão for diferente da desejada para exibição
    # Supondo que temp_list já está ordenada por dataCadastro DESC
    paginated_bens = temp_list[start_index:end_index]

    total_pages = (total_bens + per_page - 1) // per_page if per_page > 0 else 0

    return paginated_bens, total_bens, total_pages


def update_bem(bem_id, form_data):
    """
    Atualiza um bem existente no Firestore.
    `form_data` é um dicionário com os dados validados do formulário.
    """
    if not db:
        raise ConnectionError("Conexão com o Firestore não estabelecida.")

    doc_ref = db.collection('bens').document(bem_id)
    if not doc_ref.get().exists:
        raise FileNotFoundError(f"Bem com ID {bem_id} não encontrado.")

    # Estrutura os dados para atualização
    # Similar ao create_bem, mas sem gerar número de tombo ou dataCadastro inicial
    data_update = {
        "numeroPatrimonialAnterior": form_data.get("numero_tombo_anterior"),
        "descricaoTecnica": form_data.get("descricao_tecnica"),
        "notaFiscal": {
            "numero": form_data.get("nota_fiscal_numero"),
            "data": form_data.get("nota_fiscal_data"),
            "fornecedorCNPJ": form_data.get("nota_fiscal_fornecedor_cnpj")
        },
        "contaContabil": form_data.get("conta_contabil"),
        "valorAquisicao": float(form_data.get("valor_aquisicao")),
        "dataAquisicao": form_data.get("data_aquisicao"),
        "taxaDepreciacaoAnual": float(form_data.get("taxa_depreciacao_anual")) if form_data.get("taxa_depreciacao_anual") is not None else None,
        "localizacao": {
            "unidade": form_data.get("localizacao_unidade"),
            "secao": form_data.get("localizacao_secao"),
            "setor": form_data.get("localizacao_setor"),
            "responsavel": form_data.get("localizacao_responsavel")
        },
        "situacao": form_data.get("situacao_bem"),
        "tipoBem": form_data.get("tipo_bem"),
        "especificacoes": {},
        "observacoes": form_data.get("observacoes"),
        "dataUltimaModificacao": datetime.utcnow(),
        "usuarioUltimaModificacaoUID": current_user.uid if current_user.is_authenticated else None,
    }

    # Preencher especificações
    tipo_bem = data_update["tipoBem"]
    if tipo_bem == "movel":
        data_update["especificacoes"] = {
            "marca": form_data.get("movel_marca"),
            "modelo": form_data.get("movel_modelo"),
            "cor": form_data.get("movel_cor"),
            "dimensoes": form_data.get("movel_dimensoes"),
        }
    # Adicionar outros tipos conforme necessário (veiculo, armamento)
    elif tipo_bem == "veiculo":
        data_update["especificacoes"] = {
            "placa": form_data.get("veiculo_placa"),
            "modelo": form_data.get("veiculo_modelo"),
            "chassi": form_data.get("veiculo_chassi"),
            "renavam": form_data.get("veiculo_renavam"),
            "anoFabricacao": form_data.get("veiculo_ano_fabricacao"),
        }
    elif tipo_bem == "armamento":
        data_update["especificacoes"] = {
            "tipoArma": form_data.get("armamento_tipo"),
            "calibre": form_data.get("armamento_calibre"),
            "numeroSerieArma": form_data.get("armamento_numero_serie"),
            "fabricanteArma": form_data.get("armamento_fabricante"),
        }

    try:
        doc_ref.update(data_update)
        # Adicionar ao histórico do bem
        add_log_bem(bem_id,
                    current_user.uid if current_user.is_authenticated else "sistema",
                    "edicao",
                    "Dados do bem atualizados.")
        return data_update
    except Exception as e:
        print(f"Erro ao atualizar bem {bem_id}: {e}")
        raise

def add_log_bem(bem_id, user_uid, acao, detalhes):
    """Adiciona uma entrada de log ao histórico de um bem."""
    if not db:
        print("Firestore não conectado. Log do bem não adicionado.")
        return

    log_entry = {
        "timestamp": datetime.utcnow(),
        "usuarioUID": user_uid,
        "acao": acao,
        "detalhes": detalhes
    }
    try:
        bem_ref = db.collection('bens').document(bem_id)
        bem_ref.update({
            "historico": firestore.ArrayUnion([log_entry])
        })
    except Exception as e:
        print(f"Erro ao adicionar log ao bem {bem_id}: {e}")
        # Não levantar exceção para não quebrar a operação principal

# TODO: Implementar delete_bem (geralmente uma baixa lógica, alterando o campo 'ativo' ou 'situacao')
# def delete_bem_logico(bem_id): ...
# def delete_bem_fisico(bem_id): ... (menos comum para patrimônio)
