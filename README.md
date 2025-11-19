# Sistema de cadastro de gestores

Aplicação web simples construída com Flask + SQLite para cadastro de pessoas, contendo nome, área/coordenação e banco de dados que gerem.

## Pré-requisitos

- Python 3.10+

## Como executar (ambiente local)

```bash
python -m venv .venv
source .venv/bin/activate  # No Windows use .venv\\Scripts\\activate
pip install -r requirements.txt
flask --app app run --debug
```

A aplicação ficará disponível em `http://localhost:5000`.

## Executando com Docker

1. **Construir a imagem** (executar no diretório do projeto):
   ```bash
   docker build -t cadastro-gestores:latest .
   ```
2. **Subir o contêiner** expondo a porta 5000 e persistindo o banco (`people.db`) em um volume local:
   ```bash
   docker run --rm -it \
     -p 5000:5000 \
     -v $(pwd)/people.db:/app/people.db \
     --name cadastro-gestores \
     cadastro-gestores:latest
   ```
   - O parâmetro `-v` é opcional. Caso não seja usado, o banco será criado dentro do contêiner, sendo descartado ao removê-lo.
3. **Acessar a aplicação** em `http://localhost:5000`.
4. **Encerrar** com `CTRL+C` ou executando `docker stop cadastro-gestores` em outro terminal.

> Dica: para atualizar o código, pare o contêiner, execute novamente `docker build ...` e suba o contêiner com o novo build.

## Funcionalidades

- Landing page inicial com atalhos para as ações principais.
- Listagem de cadastros existentes.
- Criação de novos registros em uma tela dedicada.
- Pesquisa por nome, área/coordenação ou banco de dados.
- Edição e exclusão de registros.
- Mensagens de feedback em todas as operações.
