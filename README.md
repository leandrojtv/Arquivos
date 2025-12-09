# Sistema de cadastro de gestores e bases

Aplicação web simples construída com Flask + SQLite para registrar gestores (nome, secretaria, coordenação e e-mail) e cadastrar bases de dados com gestor titular obrigatório e até dois substitutos opcionais.

## Pré-requisitos

- Python 3.10+

## Como executar (ambiente local)

```bash
python -m venv .venv
source .venv/bin/activate  # No Windows use .venv\\Scripts\\activate
pip install -r requirements.txt
FLASK_RUN_PORT=8000 flask --app app run --debug
```

A aplicação ficará disponível em `http://localhost:8000`.

### Login obrigatório

- Usuário padrão: `admin`
- Senha padrão: `admin`
- Opcionalmente, defina credenciais via variáveis de ambiente `ADMIN_USERNAME` e `ADMIN_PASSWORD` antes de iniciar o servidor.
- Após o login, o nome do usuário aparece no canto superior direito. Clique nele para abrir o menu com **Configurações** (gestão de usuários) e **Sair**.

## Executando com Docker

1. **Construir a imagem** (executar no diretório do projeto):
   ```bash
   docker build -t cadastro-gestores:latest .
   ```
2. **Subir o contêiner** expondo a porta 8000 (ou outra via `-e PORT=<porta>`) e persistindo o banco (`data/people.db`) em um volume local:
   ```bash
   docker run --rm -it \
     -p 8000:8000 \
     -v $(pwd)/data:/app/data \
     --name cadastro-gestores \
     cadastro-gestores:latest
   ```
   - Crie a pasta `data` antes de subir o contêiner para evitar erros de permissão/caminho: `mkdir -p data`.
   - O parâmetro `-v` é opcional. Caso não seja usado, o banco será criado dentro do contêiner, sendo descartado ao removê-lo.
   - Se já possui um volume ou arquivo legado em `/app/people.db`, defina `-e DATABASE_PATH=/app/people.db` para reutilizá-lo.
3. **Acessar a aplicação** em `http://localhost:8000` (ou na porta configurada).
4. **Encerrar** com `CTRL+C` ou executando `docker stop cadastro-gestores` em outro terminal.

> Dica: para atualizar o código, pare o contêiner, execute novamente `docker build ...` e suba o contêiner com o novo build.

## Funcionalidades

- Landing page com atalho para cadastro de gestores e bases.
- Cadastro e listagem de gestores (nome, secretaria, coordenação e e-mail).
- Cadastro e listagem de bases (nome, ambiente, descrição) vinculando gestor titular obrigatório e até dois substitutos pesquisáveis e opcionais.
- Pesquisa de bases por nome, ambiente, descrição ou gestor.
- Edição e exclusão tanto de gestores (quando não vinculados) quanto de bases.
- Importação em massa de gestores via CSV ou XLSX com escolha de delimitador para CSV.
- Mensagens de feedback em todas as operações.
- Menu do usuário no topo para acessar **Configurações**, logout e abrir a modal **Novo** para escolher entre cadastrar gestor ou base.
- Página de gestão de usuários para criar, redefinir senha ou remover acessos (exceto o administrador padrão).

## Gestão de usuários

1. Faça login e clique no seu nome (canto superior direito) para abrir o menu do usuário.
2. Selecione **Configurações** para abrir a tela de gestão.
3. Para adicionar alguém, preencha o formulário "Novo usuário" e clique em **Adicionar**.
4. Para alterar a senha de um usuário existente, informe a nova senha na linha correspondente e clique em **Atualizar**.
5. Para remover um usuário, use **Remover** (o usuário padrão definido em `ADMIN_USERNAME` não pode ser excluído e você não pode remover o usuário atualmente logado).

## Importar gestores via arquivo

1. Acesse o menu **Importar** na aplicação.
2. Selecione um arquivo **CSV** ou **XLSX** contendo as colunas:
   - `Gestor` (ou `Nome`)
   - `Secretaria`
   - `Coordenação`
   - `E-mail`
3. Informe o delimitador ao usar CSV (padrão `;`). Para XLSX ele é ignorado.
4. Envie o arquivo e, ao concluir, os gestores são adicionados automaticamente à base de dados.
