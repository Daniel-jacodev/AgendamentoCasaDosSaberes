def test_get_evento_empty(client):
    response = client.get('/eventos')

    assert response.json() == {'eventos': []}


def test_get_evento_populated(client, evento):
    response = client.get(
        '/eventos',
    )

    assert response.json() == {'eventos': [
        {
           'titulo': 'Oficina de Flauta Doce',
           'descricao': 'Uma oficina prática focada no ensino de respiração, dedilhado e '
           'ornamentações básicas.',
           'data_inicio': '2026-10-25T14:00:00',
           'data_fim': '2026-10-25T16:00:00',
           'classificacao_indicativa': 'Livre',
           'espaco_id': 1,
           'responsavel': 'Coordenação Educativa',
           'publico_estimado': 25,
           'id': 1,
       },
    ]}
