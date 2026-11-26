from collections.abc import Iterable
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle

from app.schemas.relatorio import FiltroRelatorio
from app.services.relatorio import ResumoAgenda, ResumoEventos, ResumoVisitas

MARGEM = 42
LARGURA = A4[0] - 2 * MARGEM - 12  # Padding interno do frame do Platypus.
ASSETS = Path(__file__).resolve().parents[1] / 'assets' / 'relatorios'
TEXTO = HexColor('#20201C')
TEXTO_SECUNDARIO = HexColor('#53504A')
VERMELHO = HexColor('#A22D2E')
VERDE = HexColor('#2B3F26')
LARANJA = HexColor('#884100')
BEGE = HexColor('#E8E2C9')
CREME = HexColor('#F8F7F2')
BORDA = HexColor('#DED8C5')
CORES_INDICADORES = (
    (HexColor('#F5FBF6'), VERDE),
    (HexColor('#FFF4E2'), LARANJA),
    (HexColor('#F4E6E6'), VERMELHO),
    (HexColor('#F1F0EC'), TEXTO_SECUNDARIO),
    (CREME, VERDE),
    (HexColor('#F9F4FE'), HexColor('#43177C')),
)
DIAS = ('Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo')
MENOR_PROPORCAO_EXIBIDA = 0.001
ESPACO_ENTRE_GRAFICOS = 24
LARGURA_GRAFICO = (LARGURA - ESPACO_ENTRE_GRAFICOS) / 2

TITULO = ParagraphStyle(
    'Título', fontName='Helvetica-Bold', fontSize=26, leading=30, textColor=TEXTO, spaceAfter=9,
)
SECAO = ParagraphStyle(
    'Seção',
    fontName='Helvetica-Bold',
    fontSize=17,
    leading=21,
    textColor=VERMELHO,
    spaceBefore=16,
    spaceAfter=8,
    keepWithNext=True,
)
SUBTITULO = ParagraphStyle(
    'Subtítulo',
    fontName='Helvetica-Bold',
    fontSize=11,
    leading=14,
    textColor=TEXTO,
    spaceBefore=10,
    spaceAfter=5,
    keepWithNext=True,
)
CORPO = ParagraphStyle('Corpo', fontSize=9, leading=13, textColor=TEXTO_SECUNDARIO)
PERIODO = ParagraphStyle(
    'Período', parent=CORPO, fontSize=10, leading=14, textColor=TEXTO, spaceAfter=7,
)
NUMERO = ParagraphStyle('Número', fontName='Helvetica-Bold', fontSize=18, leading=23)


def _numero(valor: int) -> str:
    return f'{valor:,}'.replace(',', '.')


def _percentual(proporcao: float) -> str:
    if 0 < proporcao < MENOR_PROPORCAO_EXIBIDA:
        return '<0,1%'
    return f'{proporcao:.1%}'.replace('.0%', '%').replace('.', ',')


def _barras(linhas: Iterable[tuple[str, int]], total: int, cor: Color) -> Drawing:
    linhas = list(linhas)
    altura_linha = 13
    inicio_barra = max(stringWidth(rotulo, 'Helvetica', 9) for rotulo, _ in linhas) + 9
    valores = [f'{_numero(valor)}  |  {_percentual(valor / total)}' for _, valor in linhas]
    largura_valores = max(stringWidth(valor, 'Helvetica', 9) for valor in valores)
    largura_barra = LARGURA_GRAFICO - inicio_barra - largura_valores - 9
    grafico = Drawing(LARGURA_GRAFICO, len(linhas) * altura_linha)
    for indice, (rotulo, valor) in enumerate(linhas):
        y = grafico.height - (indice + 1) * altura_linha + 3
        proporcao = valor / total
        grafico.add(String(0, y, rotulo, fontName='Helvetica', fontSize=9, fillColor=TEXTO))
        grafico.add(Rect(inicio_barra, y, largura_barra, 7, fillColor=BEGE, strokeColor=None))
        if valor:
            grafico.add(Rect(inicio_barra, y, largura_barra * proporcao, 7, fillColor=cor, strokeColor=None))
        grafico.add(
            String(
                LARGURA_GRAFICO,
                y,
                valores[indice],
                textAnchor='end',
                fontName='Helvetica',
                fontSize=9,
                fillColor=TEXTO,
            )
        )
    return grafico


def _grafico_horarios(resumo: ResumoAgenda, cor: Color) -> Drawing:
    grafico = Drawing(LARGURA, 93)
    largura_coluna = LARGURA / 24
    escala = 54 / max(resumo.horarios.values())
    grafico.add(Line(0, 17, LARGURA, 17, strokeColor=BORDA, strokeWidth=0.75))
    for hora in range(24):
        x = (hora + 0.5) * largura_coluna
        grafico.add(
            String(
                x,
                4,
                f'{hora:02}h',
                textAnchor='middle',
                fontName='Helvetica',
                fontSize=7.5,
                fillColor=TEXTO_SECUNDARIO,
            )
        )
        quantidade = resumo.horarios[hora]
        if quantidade:
            altura = quantidade * escala
            grafico.add(Rect(x - 5, 17, 10, altura, fillColor=cor, strokeColor=None))
            grafico.add(
                String(
                    x,
                    21 + altura,
                    _percentual(quantidade / resumo.confirmados),
                    textAnchor='middle',
                    fontName='Helvetica',
                    fontSize=6.5,
                    fillColor=TEXTO,
                )
            )
    return grafico


def _indicadores(indicadores: list[tuple[str, str]]) -> Table:
    espaco = 5
    largura_cartao = (LARGURA - (len(indicadores) - 1) * espaco) / len(indicadores)
    celulas = []
    larguras = []
    estilo = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]
    for indice, (rotulo, valor) in enumerate(indicadores):
        if indice:
            celulas.append('')
            larguras.append(espaco)
        fundo, cor = CORES_INDICADORES[indice]
        coluna = len(celulas)
        celulas.append([Paragraph(valor, NUMERO.clone(f'Indicador {indice}', textColor=cor)), Paragraph(rotulo, CORPO)])
        larguras.append(largura_cartao)
        estilo.extend([
            ('BACKGROUND', (coluna, 0), (coluna, 0), fundo),
            ('LINEABOVE', (coluna, 0), (coluna, 0), 1.5, cor),
        ])
    return Table([celulas], colWidths=larguras, style=estilo)


def _ranking(resumo: ResumoEventos) -> Table | Paragraph:
    if not resumo.ranking:
        return Paragraph('Sem estimativas de público informadas para os eventos confirmados.', CORPO)
    linhas = [['Evento', 'Data de início', 'Público estimado']]
    for evento in resumo.ranking:
        linhas.append([
            Paragraph(escape(evento.titulo), CORPO),
            evento.inicio.strftime('%d/%m/%Y'),
            _numero(evento.publico_estimado),
        ])
    tabela = Table(linhas, colWidths=[LARGURA - 185, 83, 102], repeatRows=1)
    tabela.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), VERMELHO),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 1), (-1, -1), TEXTO),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [CREME, white]),
            ('LINEBELOW', (0, -1), (-1, -1), 0.75, BORDA),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ])
    )
    return tabela


def _distribuicoes(resumo: ResumoAgenda, titulo_categoria: str, categorias: list[tuple[str, int]], cor: Color) -> list:
    if resumo.confirmados == 0:
        return [Paragraph('Sem agendamentos confirmados no período.', SUBTITULO.clone('Sem dados', keepWithNext=False))]
    dias = _barras(((dia, resumo.dias[indice]) for indice, dia in enumerate(DIAS)), resumo.confirmados, cor)
    distribuicoes = Table(
        [
            [
                [Paragraph('Distribuição por dia da semana', SUBTITULO), dias],
                '',
                [Paragraph(titulo_categoria, SUBTITULO), _barras(categorias, resumo.confirmados, cor)],
            ]
        ],
        colWidths=[LARGURA_GRAFICO, ESPACO_ENTRE_GRAFICOS, LARGURA_GRAFICO],
        style=[
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ],
    )
    return [
        distribuicoes,
        Paragraph('Distribuição por hora de início', SUBTITULO),
        _grafico_horarios(resumo, cor),
    ]


def _encerrados(resumo: ResumoAgenda) -> list[tuple[str, str]]:
    return [('Negados', _numero(resumo.negados)), ('Cancelados', _numero(resumo.cancelados))]


def _secao_eventos(resumo: ResumoEventos) -> list:
    publico = _numero(resumo.publico_estimado) if resumo.eventos_com_estimativa else '—'
    conteudo = [
        Paragraph('Eventos', SECAO),
        _indicadores([
            ('Eventos confirmados', _numero(resumo.confirmados)),
            ('Solicitações pendentes', _numero(resumo.pendentes)),
            *_encerrados(resumo),
            (f'Público estimado em {_numero(resumo.eventos_com_estimativa)} evento(s)', publico),
        ]),
        *_distribuicoes(resumo, 'Pautas dos eventos confirmados', resumo.pautas.most_common(), VERMELHO),
    ]
    if resumo.confirmados:
        conteudo.extend([
            Paragraph('Principais eventos por público estimado', SUBTITULO),
            _ranking(resumo),
        ])
    return conteudo


def _secao_visitas(resumo: ResumoVisitas) -> list:
    return [
        Paragraph('Visitas mediadas', SECAO),
        _indicadores([
            ('Visitas confirmadas', _numero(resumo.confirmados)),
            ('Solicitações pendentes', _numero(resumo.pendentes)),
            *_encerrados(resumo),
            ('Pessoas previstas', _numero(resumo.pessoas_previstas)),
            ('Grupos com pessoas com deficiência', _numero(resumo.grupos_com_pcd)),
        ]),
        *_distribuicoes(resumo, 'Visitas por natureza da instituição', resumo.instituicoes.most_common(), VERDE),
    ]


def gerar_pdf(filtro: FiltroRelatorio, eventos: ResumoEventos | None, visitas: ResumoVisitas | None) -> bytes:
    arquivo = BytesIO()
    periodo = f'{filtro.data_inicio:%d/%m/%Y} a {filtro.data_fim:%d/%m/%Y}'
    status = {
        'todos': 'Todos',
        'aceito': 'Confirmados',
        'pendente': 'Pendentes',
        'negado': 'Negados',
        'cancelado': 'Cancelados',
    }[filtro.status]
    documento = SimpleDocTemplate(
        arquivo,
        pagesize=A4,
        leftMargin=MARGEM,
        rightMargin=MARGEM,
        topMargin=99,
        bottomMargin=49,
        title='Relatório de agendamentos',
        author='Casa dos Saberes',
        lang='pt-BR',
    )

    marca = ImageReader(str(ASSETS / 'csca-gov.png'))
    faixa = ImageReader(str(ASSETS / 'faixa.png'))

    def moldura(canvas, doc):
        largura, altura = A4
        canvas.saveState()
        canvas.setFillColor(BEGE)
        canvas.rect(0, altura - 60, largura, 60, fill=1, stroke=0)
        marca_largura, marca_altura = marca.getSize()
        canvas.drawImage(marca, MARGEM + 6, altura - 46, 208, 208 * marca_altura / marca_largura, mask='auto')
        faixa_largura, faixa_altura = faixa.getSize()
        altura_faixa = 15
        largura_faixa = altura_faixa * faixa_largura / faixa_altura
        recorte = canvas.beginPath()
        recorte.rect(0, altura - 75, largura, altura_faixa)
        canvas.clipPath(recorte, stroke=0, fill=0)
        for indice in range(int(largura / largura_faixa) + 1):
            canvas.drawImage(faixa, indice * largura_faixa, altura - 75, largura_faixa, altura_faixa, mask='auto')
        canvas.restoreState()
        canvas.setStrokeColor(BORDA)
        canvas.line(MARGEM + 6, 42, largura - MARGEM - 6, 42)
        canvas.setFillColor(TEXTO_SECUNDARIO)
        canvas.setFont('Helvetica', 9)
        canvas.drawString(MARGEM + 6, 30, periodo)
        canvas.drawRightString(largura - MARGEM - 6, 30, f'Página {doc.page}')

    conteudo = [
        Paragraph('Relatório de agendamentos', TITULO),
        Paragraph(f'<b>{periodo}</b> (horário de Fortaleza) · Status: {status}', PERIODO),
        Paragraph(
            'O período considera a data de início do agendamento. Os gráficos mostram a participação '
            'no total confirmado de cada tipo. Os dados de público refletem as previsões informadas no cadastro.',
            CORPO,
        ),
    ]
    if eventos is not None:
        conteudo.extend(_secao_eventos(eventos))
    if visitas is not None:
        if eventos is not None:
            conteudo.append(PageBreak())
        conteudo.extend(_secao_visitas(visitas))
    documento.build(conteudo, onFirstPage=moldura, onLaterPages=moldura)
    return arquivo.getvalue()
