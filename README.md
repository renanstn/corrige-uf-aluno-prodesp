# corrige-uf-aluno-prodesp
Atualmente, os bancos do v2 possuem por volta de 20 mil cadastros **antigos** de alunos, com RA cadastrado **sem** UF.

Para corrigir isto, este script foi desenvolvido.

Ele busca todos os alunos que **não possuem** UF cadastrada, executa a busca desses alunos na API da PRODESP de acordo com as seguintes informações:
- Nome do aluno
- Nome da mãe
- Data de nascimento

Ao encontrar o aluno, a PRODESP retorna uma série de informações, entre elas, a UF do RA.

Essa informação é então inserida no banco.

## Como utilizar
Para executar este script siga os seguintes passos:
- Inicialize um ambiente virtual python:
  - `python3 -m venv .venv`
- Ative o ambiente virtual que você acabou de criar:
  - `source .venv/bin/activate`
- Crie um arquivo `config.ini` com as seguintes informações:
  - [db]
    - server = [endereço do host]
    - user = [usuario do banco]
    - pass = [senha do banco]
    - db = [banco]
  - [api]
    - prodesp_url_rest = [url base da API da prodesp]
    - prodesp_url_auth = [endpoint que solicita o token]
    - prodesp_url_listar_alunos = [endpoint do método listar aluno]
    - prodesp_usuario_rest = [usuario da API]
    - prodesp_senha_rest = []senha da API
  - [ambiente]
    - salva_no_banco = [flag que ativa ou não a alteração no banco (1 - altera | 0 - não altera)]
- Execute o script:
  - `python main.py`

## Log
Um log, com todas as informações do que o script fez, é criado na mesma pasta do script, com o nome de `logs.log`
