from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models.conteudo_visita import Exposicao, FormularioVisita
from app.schemas.conteudo_visita import ExposicaoResponse, ExposicaoSalvar, FormularioVisitaSchema

FORMULARIO_ID = 1
FORMULARIO_PADRAO = FormularioVisitaSchema.model_validate_json(
    Path(__file__).with_name('formulario_visita_padrao.json').read_text(encoding='utf-8')
)


def listar_exposicoes(db: Session, *, incluir_pausadas: bool = False):
    consulta = select(Exposicao).order_by(Exposicao.sala_id)
    if not incluir_pausadas:
        consulta = consulta.where(Exposicao.pausada.is_(False))
    return db.scalars(consulta).all()


def salvar_exposicao(db: Session, sala_id: int, conteudo: ExposicaoSalvar) -> ExposicaoResponse:
    campos = conteudo.model_dump()
    if 'pausada' not in conteudo.model_fields_set:
        del campos['pausada']

    insert = sqlite_insert if db.get_bind().dialect.name == 'sqlite' else pg_insert
    comando = (
        insert(Exposicao)
        .values(sala_id=sala_id, **campos)
        .on_conflict_do_update(index_elements=[Exposicao.sala_id], set_=campos)
        .returning(Exposicao)
    )
    exposicao = ExposicaoResponse.model_validate(db.scalars(comando).one())
    db.commit()
    return exposicao


def alterar_status_exposicao(db: Session, sala_id: int, pausada: bool) -> ExposicaoResponse | None:
    comando = update(Exposicao).where(Exposicao.sala_id == sala_id).values(pausada=pausada).returning(Exposicao)
    registro = db.scalars(comando).one_or_none()
    exposicao = ExposicaoResponse.model_validate(registro) if registro is not None else None
    db.commit()
    return exposicao


def consultar_formulario(db: Session) -> FormularioVisitaSchema:
    formulario = db.get(FormularioVisita, FORMULARIO_ID)
    if formulario is None:
        return FORMULARIO_PADRAO
    return FormularioVisitaSchema(campos=formulario.campos)


def salvar_formulario(db: Session, formulario: FormularioVisitaSchema) -> FormularioVisitaSchema:
    campos = formulario.model_dump(mode='json', exclude_defaults=True)['campos']
    insert = sqlite_insert if db.get_bind().dialect.name == 'sqlite' else pg_insert
    comando = (
        insert(FormularioVisita)
        .values(id=FORMULARIO_ID, campos=campos)
        .on_conflict_do_update(index_elements=[FormularioVisita.id], set_={'campos': campos})
    )
    db.execute(comando)
    db.commit()
    return formulario
