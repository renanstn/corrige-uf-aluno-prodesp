#!python3
import logging
import configparser
import psycopg2
import psycopg2.extras
import requests
import os
from unicodedata import normalize


def init_logger():
    '''Inicializa o logger do projeto'''
    log_file = 'logs.log'
    logging.basicConfig(filename=log_file, level=logging.INFO)


def get_config():
    '''Carrega os parâmetros do config.ini'''
    path = os.path.dirname(os.path.abspath(__file__))
    config = configparser.ConfigParser()
    config.read(path + '/config.ini')

    return config


def save_token_in_config(params, token):
    '''Recebe o token e salva ele no config.ini'''
    params['api']['token'] = token
    with open('config.ini', 'w') as configfile:
        params.write(configfile)


def db_connect(db_config):
    '''Faz a conexão com o banco, usando os parâmetros do config.ini'''
    string_conn = "dbname={db} user={user} password={passw} host={host}".format(
        db=db_config['db'],
        user=db_config['user'],
        passw=db_config['pass'],
        host=db_config['server']
    )
    pg_db = psycopg2.connect(string_conn)

    return pg_db


def get_alunos_sem_uf(conn):
    '''Busca todos os alunos sem 'aluno_ra_estcod' do banco'''
    sql = ('SELECT '
            'aluno.aluno_cod, '
            'aluno.aluno_ra AS ra, '
            'pessoa.pes_nome AS nome, '
            'pessoa.pes_nomemae AS nome_mae, '
            "TO_CHAR (pessoa.pes_dtnasc, 'DD/MM/YYYY') AS nascimento "
        'FROM edu_aluno AS aluno '
        'INNER JOIN bas_pessoa AS pessoa '
            'ON pessoa.pes_cod = aluno.aluno_pescod '
        'WHERE aluno_ra_estcod IS NULL '
    )
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(sql)

    return cursor.fetchall()


def get_uf_cods(conn):
    '''Retorna um dicionário com as siglas UF e seus respectivos códigos'''
    sql = 'SELECT est_cod, est_sigla FROM bas_estados'
    cursor = conn.cursor()
    cursor.execute(sql)
    result = cursor.fetchall()
    lista_uf = {}
    for i in result:
        lista_uf[i[1]] = i[0]

    return lista_uf


def update_uf_aluno(conn, ambiente_params, aluno_cod, uf_cod):
    '''Atualiza a tabela edu_aluno o UF cod do aluno, caso a variável salva_no_banco do config.ini seja 1'''
    logging.info('Atualizando aluno_cod {} para uf_cod {}'.format(aluno_cod, uf_cod))
    if ambiente_params['salva_no_banco'] == 1:
        sql = 'UPDATE edu_aluno SET aluno_ra_estcod = %s WHERE aluno_cod = %s'
        cursor = conn.cursor()
        cursor.execute(sql, (uf_cod, aluno_cod))
        conn.commit()


def busca_fonetica_aluno(api_params, token, aluno):
    '''Busca o aluno na prodesp usando a função REST de busca fonética'''
    url_base = api_params['prodesp_url_rest']
    endpoint = api_params['prodesp_url_listar_alunos']
    url = url_base + endpoint
    header = {'Authorization': 'Bearer ' + token}

    params = {
        'inNomeAluno': remover_acentos(aluno['nome']),
        'inNomeMae': remover_acentos(aluno['nome_mae']),
        'inDataNascimento': aluno['nascimento']
    }

    try:
        response = requests.get(url, headers=header, params=params)
    except:
        print('Houve um problema com a request:')
        logging.error(response.text)

    return response.json()


def get_token(api_params):
    '''Faz a request do token na prodesp e o retorna'''
    url_base = api_params['prodesp_url_rest']
    endpoint = api_params['prodesp_url_auth']
    user = api_params['prodesp_usuario_rest']
    passwd = api_params['prodesp_senha_rest']
    url = url_base + endpoint

    response = requests.get(url, auth=(user, passwd))
    resp_json = response.json()

    return resp_json['outAutenticacao']


def check_token_expired(data):
    '''Verifica se o token expirou a partir do json de retorno'''
    if 'outErro' in data:
        if data['outErro'] == 'Unauthorized':
            return True
    return False


def check_aluno_dados(data):
    '''Verifica se a chave 'outListaAlunos' está presente no json'''
    return True if 'outListaAlunos' in data else False


def report_aluno_erro(data, aluno):
    '''Verifica e reporta no log se há algum erro no json, por exemplo, se o aluno não foi encontrado'''
    if 'outErro' in data:
        error = 'Aluno: {}, Mãe: {}, Nascimento {}, RA {}, COD: {}, erro: {}'.format(
            aluno['nome'],
            aluno['nome_mae'],
            aluno['nascimento'],
            aluno['ra'],
            aluno['aluno_cod'],
            data['outErro']
        )
        logging.error(error)
    else:
        logging.error('Erro desconhecido')


def remover_acentos(txt):
    '''Remove acentos de uma string (necessário pois a PRODESP não aceita acentos)'''
    return normalize('NFKD', txt).encode('ASCII', 'ignore').decode('ASCII')


def main():
    init_logger()
    logging.info('--------------------- SCRIPT INICIADO ---------------------')

    config = get_config()
    params = config._sections
    conn = db_connect(params['db'])

    if params['ambiente']['salva_no_banco'] == 1:
        print('- Parâmetro de alteração de banco ATIVO')
    else:
        print('- Parâmetro de alteração de banco INATIVO')

    estados = get_uf_cods(conn)
    print('- Códigos de estados carregados')

    alunos_sem_uf = get_alunos_sem_uf(conn)
    print('- Encontrados {} alunos sem UF'.format(len(alunos_sem_uf)))
    logging.info('- Encontrados {} alunos sem UF'.format(len(alunos_sem_uf)))

    token = params['api']['token']

    print('- Iniciando buscas fonéticas dos alunos...')
    for aluno in alunos_sem_uf:
        logging.info('Buscando aluno {}'.format(aluno['nome']))
        print('- Buscando dados:\n\tAluno: {}\n\tMãe: {}\n\tNascimento: {}'.format(
            aluno['nome'],
            aluno['nome_mae'],
            aluno['nascimento']
        ))

        dados_prodesp = busca_fonetica_aluno(params['api'], token, aluno)

        token_expired = check_token_expired(dados_prodesp)
        if token_expired:
            logging.info('Token expirado, solicitando novo token')
            token = get_token(params['api'])
            save_token_in_config(config, token)
            logging.info('Token renovado: {}'.format(token))
            dados_prodesp = busca_fonetica_aluno(params['api'], token, aluno)

        aluno_ok = check_aluno_dados(dados_prodesp)
        if aluno_ok:
            uf = dados_prodesp['outListaAlunos'][0]['outSiglaUFRA']
            print('- UF do aluno: {}'.format(uf))
            logging.info('UF: {}'.format(uf))
            uf_cod = estados[uf]
            update_uf_aluno(conn, params['ambiente'], aluno['aluno_cod'], uf_cod)

        else:
            report_aluno_erro(dados_prodesp, aluno)
            print('- Houve um problema com o aluno {}'.format(aluno['nome']))
            print('- Para mais informações, consulte o log')

    conn.close()


if __name__ == "__main__":
    main()
