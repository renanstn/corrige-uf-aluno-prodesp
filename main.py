#!python3
import logging
import configparser
import psycopg2
import psycopg2.extras
import requests
import os
from unicodedata import normalize


def init_logger():
    log_file = 'logs.log'
    logging.basicConfig(filename=log_file, level=logging.INFO)


def get_config():
    path = os.path.dirname(os.path.abspath(__file__))
    config = configparser.ConfigParser()
    config.read(path + '/config.ini')

    return config


def save_token_in_config(params, token):
    params['api']['token'] = token
    with open('config.ini', 'w') as configfile:
        params.write(configfile)


def db_connect(db_config):
    string_conn = "dbname={db} user={user} password={passw} host={host}".format(
        db=db_config['db'],
        user=db_config['user'],
        passw=db_config['pass'],
        host=db_config['server']
    )
    pg_db = psycopg2.connect(string_conn)

    return pg_db


def get_alunos_sem_uf(conn):
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


def get_uf_cods():
    pass


def save_uf_aluno(conn, aluno_cod, uf_cod):
    cursor = conn.cursor()
    cursor.execute('INSERT INTO edu_aluno (aluno_ra_estcod) VALUES (%s) WHERE aluno_cod = %s', (uf_cod, aluno_cod))
    conn.commit()


def busca_fonetica_aluno(api_params, token, aluno):
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
    url_base = api_params['prodesp_url_rest']
    endpoint = api_params['prodesp_url_auth']
    user = api_params['prodesp_usuario_rest']
    passwd = api_params['prodesp_senha_rest']
    url = url_base + endpoint

    response = requests.get(url, auth=(user, passwd))
    resp_json = response.json()

    return resp_json['outAutenticacao']


def check_token_expired(data):
    if 'outErro' in data:
        if data['outErro'] == 'Unauthorized':
            return True
    return False


def check_aluno_dados(data):
    return True if 'outListaAlunos' in data else False


def report_aluno_erro(data, aluno):
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


def remover_acentos(txt):
    return normalize('NFKD', txt).encode('ASCII', 'ignore').decode('ASCII')


def main():
    init_logger()
    logging.info('--------------------- SCRIPT INICIADO ---------------------')
    config = get_config()
    params = config._sections
    conn = db_connect(params['db'])
    alunos_sem_uf = get_alunos_sem_uf(conn)
    print('- Encontrados {} alunos sem UF'.format(len(alunos_sem_uf)))

    token = params['api']['token']
    # Buscar os UF cods e armazenar num dicionário

    print('- Iniciando buscas fonéticas dos alunos...')
    for aluno in alunos_sem_uf:
        print('- Buscando dados:\n\tAluno: {}\n\tMãe: {}\n\tNascimento: {}'.format(
            aluno['nome'],
            aluno['nome_mae'],
            aluno['nascimento']
        ))

        logging.info('Buscando aluno {}'.format(aluno['nome']))
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

        else:
            erro = report_aluno_erro(dados_prodesp, aluno)
            print('- Houve um problema com o aluno {}'.format(aluno['nome']))
            print('- Para mais informações, consulte o log')

    conn.close()


if __name__ == "__main__":
    main()
