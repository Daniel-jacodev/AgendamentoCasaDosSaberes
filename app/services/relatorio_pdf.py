from collections.abc import Iterable
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle

from app.schemas.relatorio import FiltroRelatorio
from app.services.relatorio import ResumoAgenda, ResumoEventos, ResumoVisitas

MARGEM = 42
LARGURA = A4[0] - 2 * MARGEM - 12  # Padding interno do frame do Platypus.
TEXTO = HexColor('#192C32')
TEXTO_SECUNDARIO = HexColor('#4B646B')
DESTAQUE = HexColor('#17665A')
FUNDO = HexColor('#E9F2EF')
DIAS = ('Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo')
MENOR_PROPORCAO_EXIBIDA = 0.001
ESPACO_ENTRE_GRAFICOS = 24
LARGURA_GRAFICO = (LARGURA - ESPACO_ENTRE_GRAFICOS) / 2

TITULO = ParagraphStyle('Título', fontName='Helvetica-Bold', fontSize=26, leading=30, textColor=TEXTO)
SECAO = ParagraphStyle(
    'Seção',
    fontName='Helvetica-Bold',
    fontSize=17,
    leading=21,
    textColor=DESTAQUE,
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
NUMERO = ParagraphStyle('Número', fontName='Helvetica-Bold', fontSize=16, leading=21, textColor=DESTAQUE)


def _numero(valor: int) -> str:
    return f'{valor:,}'.replace(',', '.')


def _percentual(proporcao: float) -> str:
    if 0 < proporcao < MENOR_PROPORCAO_EXIBIDA:
        return '<0,1%'
    return f'{proporcao:.1%}'.replace('.0%', '%').replace('.', ',')


def _barras(linhas: Iterable[tuple[str, int]], total: int) -> Drawing:
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
        grafico.add(Rect(inicio_barra, y, largura_barra, 7, fillColor=FUNDO, strokeColor=None))
        if valor:
            grafico.add(Rect(inicio_barra, y, largura_barra * proporcao, 7, fillColor=DESTAQUE, strokeColor=None))
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


def _grafico_horarios(resumo: ResumoAgenda) -> Drawing:
    grafico = Drawing(LARGURA, 93)
    largura_coluna = LARGURA / 24
    escala = 54 / max(resumo.horarios.values())
    grafico.add(Line(0, 17, LARGURA, 17, strokeColor=TEXTO_SECUNDARIO, strokeWidth=0.5))
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
            grafico.add(Rect(x - 5, 17, 10, altura, fillColor=DESTAQUE, strokeColor=None))
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
    celulas = [[Paragraph(valor, NUMERO), Paragraph(rotulo, CORPO)] for rotulo, valor in indicadores]
    quadro = Table([celulas], colWidths=[LARGURA / len(indicadores)] * len(indicadores))
    quadro.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), FUNDO),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ])
    )
    return quadro


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
            ('BACKGROUND', (0, 0), (-1, 0), DESTAQUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [FUNDO, white]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ])
    )
    return tabela


def _distribuicoes(resumo: ResumoAgenda, titulo_categoria: str, categorias: list[tuple[str, int]]) -> list:
    if resumo.confirmados == 0:
        return [Paragraph('Sem agendamentos confirmados no período.', SUBTITULO.clone('Sem dados', keepWithNext=False))]
    dias = _barras(((dia, resumo.dias[indice]) for indice, dia in enumerate(DIAS)), resumo.confirmados)
    distribuicoes = Table(
        [
            [
                [Paragraph('Distribuição por dia da semana', SUBTITULO), dias],
                '',
                [Paragraph(titulo_categoria, SUBTITULO), _barras(categorias, resumo.confirmados)],
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
        _grafico_horarios(resumo),
    ]


def _secao_eventos(resumo: ResumoEventos) -> list:
    publico = _numero(resumo.publico_estimado) if resumo.eventos_com_estimativa else '—'
    conteudo = [
        Paragraph('Eventos', SECAO),
        _indicadores([
            ('Eventos confirmados', _numero(resumo.confirmados)),
            ('Solicitações pendentes', _numero(resumo.pendentes)),
            (f'Público estimado em {_numero(resumo.eventos_com_estimativa)} evento(s)', publico),
        ]),
        *_distribuicoes(resumo, 'Distribuição por pauta', resumo.pautas.most_common()),
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
            ('Pessoas previstas', _numero(resumo.pessoas_previstas)),
            ('Grupos com pessoas com deficiência', _numero(resumo.grupos_com_pcd)),
        ]),
        *_distribuicoes(resumo, 'Visitas por natureza da instituição', resumo.instituicoes.most_common()),
    ]


def gerar_pdf(filtro: FiltroRelatorio, eventos: ResumoEventos | None, visitas: ResumoVisitas | None) -> bytes:
    arquivo = BytesIO()
    periodo = f'{filtro.data_inicio:%d/%m/%Y} a {filtro.data_fim:%d/%m/%Y}'
    documento = SimpleDocTemplate(
        arquivo,
        pagesize=A4,
        leftMargin=MARGEM,
        rightMargin=MARGEM,
        topMargin=61,
        bottomMargin=49,
        title='Relatório de agendamentos',
        author='Casa de Saberes',
        lang='pt-BR',
    )

    def moldura(canvas, doc):
        largura, altura = A4
        canvas.setFillColor(DESTAQUE)
        canvas.rect(0, altura - 8, largura, 8, fill=1, stroke=0)
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawString(MARGEM + 6, altura - 41, 'Casa de Saberes')
        canvas.setFillColor(TEXTO_SECUNDARIO)
        canvas.setFont('Helvetica', 9)
        canvas.drawString(MARGEM + 6, 30, periodo)
        canvas.drawRightString(largura - MARGEM - 6, 30, f'Página {doc.page}')

    conteudo = [
        Paragraph('Relatório de agendamentos', TITULO),
        Paragraph(f'<b>{periodo}</b> (horário de Fortaleza)', CORPO),
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
