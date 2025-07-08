from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, DecimalField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Optional, Length, NumberRange, Regexp
from datetime import date

# Constantes para escolhas em SelectFields
TIPOS_BEM_CHOICES = [
    ("", "-- Selecione --"),
    ("movel", "Móvel"),
    ("veiculo", "Veículo"),
    ("armamento", "Armamento"),
    ("imovel", "Imóvel"),
    ("software", "Software/Licença"),
    ("outro", "Outro")
]

SITUACAO_BEM_CHOICES = [
    ("", "-- Selecione --"),
    ("novo", "Novo"),
    ("bom", "Bom"),
    ("regular", "Regular"),
    ("ruim", "Ruim"),
    ("inservivel", "Inservível")
]

class BemForm(FlaskForm):
    # Informações Gerais (Requisitos 3-12, 17)
    numero_tombo_anterior = StringField('Número Patrimonial Anterior (Controle Migratório)',
                                validators=[Optional(), Length(max=50)])
    descricao_tecnica = TextAreaField('Descrição Técnica e Detalhada do Bem',
                                validators=[DataRequired(message="Descrição é obrigatória."), Length(min=10, max=1000)])

    # Dados da Nota Fiscal
    nota_fiscal_numero = StringField('Número da Nota Fiscal', validators=[Optional(), Length(max=50)])
    nota_fiscal_data = DateField('Data da Nota Fiscal', validators=[Optional()], format='%Y-%m-%d')
    nota_fiscal_fornecedor_cnpj = StringField('CNPJ do Fornecedor (Nota Fiscal)',
                                        validators=[Optional(), Regexp(r'^\d{2}\.\d{3}\.\d{3}\/\d{4}\-\d{2}$',
                                                                        message="CNPJ inválido. Formato esperado: XX.XXX.XXX/XXXX-XX")])

    conta_contabil = StringField('Conta Contábil Associada', validators=[DataRequired(message="Conta contábil é obrigatória."), Length(max=100)])
    valor_aquisicao = DecimalField('Valor de Aquisição (Unitário)', places=2, validators=[DataRequired(message="Valor é obrigatório."), NumberRange(min=0)])
    # valor_total (se quantidade > 1, será calculado ou entrado em outro form de "Entrada de Lote")
    data_aquisicao = DateField('Data de Aquisição', validators=[DataRequired(message="Data de aquisição é obrigatória.")], default=date.today, format='%Y-%m-%d')

    # Depreciação - Taxa pode ser buscada da conta contábil ou informada
    taxa_depreciacao_anual = DecimalField('Taxa de Depreciação Anual (%)', places=2, validators=[Optional(), NumberRange(min=0, max=100)])

    # Localização (Simplificado por agora, pode ser mais granular com SelectFields de Unidades/Setores)
    localizacao_unidade = StringField('Unidade de Localização', validators=[DataRequired(), Length(max=100)])
    localizacao_secao = StringField('Seção/Departamento', validators=[Optional(), Length(max=100)])
    localizacao_setor = StringField('Setor Específico', validators=[Optional(), Length(max=100)])
    localizacao_responsavel = StringField('Responsável pela Lotação (Nome ou Matrícula)', validators=[Optional(), Length(max=100)])

    situacao_bem = SelectField('Situação do Bem', choices=SITUACAO_BEM_CHOICES, validators=[DataRequired(message="Situação é obrigatória.")])

    tipo_bem = SelectField('Tipo do Bem', choices=TIPOS_BEM_CHOICES, validators=[DataRequired(message="Tipo do bem é obrigatório.")])

    # Campos Específicos por Tipo de Bem (Requisito 13) - Usar Optional() e mostrar/ocultar com JS no frontend

    # Móveis (Requisito 14)
    movel_marca = StringField('Marca (Móvel)', validators=[Optional(), Length(max=100)])
    movel_modelo = StringField('Modelo (Móvel)', validators=[Optional(), Length(max=100)])
    movel_cor = StringField('Cor (Móvel)', validators=[Optional(), Length(max=50)])
    movel_dimensoes = StringField('Dimensões (Móvel - Ex: AxLxP cm)', validators=[Optional(), Length(max=100)])

    # Veículos (Requisito 15)
    veiculo_placa = StringField('Placa (Veículo)', validators=[Optional(), Length(min=7, max=8)]) # Formato antigo e Mercosul
    veiculo_modelo = StringField('Modelo (Veículo)', validators=[Optional(), Length(max=100)])
    veiculo_chassi = StringField('Chassi (Veículo)', validators=[Optional(), Length(min=17, max=17, message="Chassi deve ter 17 caracteres.")])
    veiculo_renavam = StringField('Renavam (Veículo)', validators=[Optional(), Length(min=9, max=11, message="Renavam inválido.")]) # 9 ou 11 dígitos
    veiculo_ano_fabricacao = IntegerField('Ano de Fabricação (Veículo)', validators=[Optional(), NumberRange(min=1900, max=date.today().year + 1)])

    # Armamentos (Requisito 16)
    armamento_tipo = StringField('Tipo de Armamento (Ex: Pistola, Fuzil)', validators=[Optional(), Length(max=100)])
    armamento_calibre = StringField('Calibre (Armamento)', validators=[Optional(), Length(max=50)])
    armamento_numero_serie = StringField('Número de Série (Armamento)', validators=[Optional(), Length(max=100)])
    armamento_fabricante = StringField('Fabricante (Armamento)', validators=[Optional(), Length(max=100)])

    # Outros campos específicos podem ser adicionados aqui (Software, Imóvel etc.)

    observacoes = TextAreaField('Observações Adicionais', validators=[Optional(), Length(max=1000)])

    submit = SubmitField('Salvar Bem')


    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False

        # Validações condicionais baseadas no tipo_bem
        tipo_selecionado = self.tipo_bem.data

        if tipo_selecionado == 'movel':
            if not self.movel_marca.data:
                self.movel_marca.errors.append("Marca é obrigatória para móveis.")
                return False
            if not self.movel_modelo.data:
                self.movel_modelo.errors.append("Modelo é obrigatório para móveis.")
                return False
        elif tipo_selecionado == 'veiculo':
            if not self.veiculo_placa.data:
                self.veiculo_placa.errors.append("Placa é obrigatória para veículos.")
                return False
            if not self.veiculo_chassi.data:
                self.veiculo_chassi.errors.append("Chassi é obrigatório para veículos.")
                return False
            if not self.veiculo_renavam.data:
                self.veiculo_renavam.errors.append("Renavam é obrigatório para veículos.")
                return False
            if not self.veiculo_ano_fabricacao.data:
                self.veiculo_ano_fabricacao.errors.append("Ano de fabricação é obrigatório para veículos.")
                return False
        elif tipo_selecionado == 'armamento':
            if not self.armamento_tipo.data:
                self.armamento_tipo.errors.append("Tipo é obrigatório para armamentos.")
                return False
            if not self.armamento_numero_serie.data:
                self.armamento_numero_serie.errors.append("Número de série é obrigatório para armamentos.")
                return False

        # Validar data da nota fiscal vs data de aquisição
        if self.nota_fiscal_data.data and self.data_aquisicao.data:
            if self.nota_fiscal_data.data > self.data_aquisicao.data:
                self.nota_fiscal_data.errors.append("Data da NF não pode ser posterior à data de aquisição.")
                return False
        return True
