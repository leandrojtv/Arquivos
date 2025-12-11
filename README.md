# Sistema de cadastro de gestores e bases

Aplicação web simples construída com Flask + SQLite para registrar gestores (nome, secretaria, coordenação e e-mail) e cadastrar bases de dados com gestor titular obrigatório e até dois substitutos opcionais.

## Pré-requisitos

- Python 3.10+
- Para uso do JDBC do Teradata, mantenha um JRE instalado (já incluído na imagem Docker sugerida) e tenha o(s) JAR(es) do drive
r disponível.

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

### Driver JDBC do Teradata

A aplicação procura automaticamente os JARs do Teradata no diretório `drivers/teradata` (ou no caminho definido pela variáve
l `TERADATA_JDBC_DIR`). Após copiar os drivers para essa pasta, basta reiniciar o servidor ou contêiner para que eles sejam us
ados no teste de conexão e na extração.

**Passo a passo (ambiente local):**

1. Crie a pasta de drivers se ainda não existir: `mkdir -p drivers/teradata`.
2. Copie o JAR do Teradata (ex.: `terajdbc4.jar`, `tdgssconfig.jar`) para dentro de `drivers/teradata`.
3. Inicie ou reinicie o Flask com `flask --app app run` (o carregamento ocorre no start).

**Passo a passo (Docker):**

1. Antes de subir o contêiner, coloque os JARs na pasta local `drivers/teradata`.
2. Monte a pasta no contêiner (somente leitura) ou inclua no build:
   ```bash
   docker run --rm -it \
     -p 8000:8000 \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/drivers/teradata:/app/drivers/teradata:ro \
     --name cadastro-gestores \
     cadastro-gestores:latest
   ```
3. Caso prefira embutir no build, mantenha os JARs em `drivers/teradata` antes do `docker build`.

Se usar outro local, defina `TERADATA_JDBC_DIR` apontando para a pasta com os JARs.

## Funcionalidades

- Landing page com atalho para cadastro de gestores e bases.
- Cadastro e listagem de gestores (nome, secretaria, coordenação e e-mail).
- Cadastro e listagem de bases (nome, ambiente opcional, descrição opcional) vinculando gestor titular obrigatório e até dois substitutos pesquisáveis e opcionais.
- Pesquisa de bases por nome, ambiente, descrição ou gestor.
- Edição e exclusão tanto de gestores (quando não vinculados) quanto de bases.
- Importação em massa de gestores via CSV ou XLSX com escolha de delimitador para CSV.
- Importação em massa de bases com mapeamento de colunas, gestor titular obrigatório e substitutos opcionais vinculados pelo nome.
  - Arquivos exportados podem ser reimportados para **atualizar** gestores ou bases existentes com base no nome, evitando duplicidades.
- Extração guiada de metadados do Teradata com montagem automática da string JDBC, teste de conexão e aplicação direta nas bases.
- Gerenciador de schedules reutilizáveis (data, hora, dias da semana, intervalo e repetição) para associar a jobs de extração ou execuções únicas.
- Download de modelos XLSX para cada tipo de importação e exportação dos resultados filtrados (bases e gestores) prontos para reimportar.
- Relatórios com gráfico de cobertura de gestores, total de gestores cadastrados e distribuição de bases por coordenação e ambiente.
- Mensagens de feedback em todas as operações.
- Menu do usuário no topo para acessar **Configurações**, logout e abrir a modal **Novo** para escolher entre cadastrar gestor ou base.
- Página de gestão de usuários para criar, redefinir senha ou remover acessos (exceto o administrador padrão).
- Monitor de jobs para reiniciar execuções, editar configurações e baixar logs das extrações.

## Gestão de usuários

1. Faça login e clique no seu nome (canto superior direito) para abrir o menu do usuário.
2. Selecione **Configurações** para abrir a tela de gestão.
3. Para adicionar alguém, preencha o formulário "Novo usuário" e clique em **Adicionar**.
4. Para alterar a senha de um usuário existente, informe a nova senha na linha correspondente e clique em **Atualizar**.
5. Para remover um usuário, use **Remover** (o usuário padrão definido em `ADMIN_USERNAME` não pode ser excluído e você não pode remover o usuário atualmente logado).

## Importar gestores via arquivo

1. Acesse o menu **Importar** e escolha **Importar gestores**.
2. Opcional: clique em **Baixar modelo XLSX** na etapa inicial para usar um template já formatado.
2. Na etapa **Arquivo**, selecione um **CSV** ou **XLSX** e informe o delimitador se estiver usando CSV (padrão `;`).
3. Na etapa **Mapeamento**, associe cada campo do gestor (`Nome`, `Secretaria`, `Coordenação`, `E-mail`) a uma coluna do arquivo — você pode escolher qualquer coluna disponível.
4. Revise o resumo e inicie a importação na etapa final. O progresso, total processado e eventuais avisos são exibidos na tela, com opção de reiniciar ou voltar aos gestores.
5. Se você reimportar um arquivo previamente exportado, os gestores existentes serão atualizados pelo **nome**, evitando registros duplicados.

## Importar bases via arquivo

1. Acesse o menu **Importar** e escolha **Importar bases**.
2. Opcional: baixe o **modelo XLSX** na etapa inicial para preencher rapidamente com as colunas padrão.
2. Na etapa **Arquivo**, selecione um **CSV** ou **XLSX** e informe o delimitador se estiver usando CSV (padrão `;`).
3. Na etapa **Mapeamento**, associe colunas do arquivo aos campos da base (`Base`, `Gestor`) e, se desejar, informe também `Ambiente`, `Descrição` e as colunas de **1º** e **2º substitutos**.
4. Na etapa final, confirme a importação. O sistema procura os gestores pelo nome para vincular o titular e substitutos (quando informados), mostrando progresso, totais e eventuais avisos caso algum nome não seja encontrado.
5. Reimportar um XLSX/CSV exportado aplica **atualizações** nas bases existentes (busca por nome da base) em vez de duplicar registros.

## Vincular bases a gestores via arquivo

Use este fluxo quando as bases já estiverem cadastradas (por exemplo, via extração) e você só precisar atualizar o titular e os substitutos:

1. Acesse o menu **Importar** e escolha **Vincular bases e gestores**.
2. Opcional: baixe o **modelo XLSX** na etapa inicial para preencher rapidamente os nomes de base e gestores.
2. Envie um **CSV** ou **XLSX** e informe o delimitador se estiver usando CSV (padrão `;`).
3. Mapeie as colunas obrigatórias **Base** (nome da base) e **Gestor** (nome do titular). As colunas de **1º substituto** e **2º substituto** são opcionais.
4. Revise o resumo e inicie a atualização. O sistema localiza bases e gestores pelo nome, aplica as alterações e exibe progresso, totais processados e avisos se algum nome não for encontrado.

## Exportar resultados filtrados

- Em **Gestores**, use o botão **Exportar resultados** (respeita a busca digitada) para baixar um XLSX já no formato do importador de gestores.
- Em **Pesquisa de bases**, após preencher os filtros e/ou a busca, clique em **Exportar resultados** para baixar um XLSX compatível com a importação de bases/vínculos.

## Extração de metadados (Teradata)

1. Abra o menu **Extração** para ver a lista de **resources** já configurados. Cada resource guarda a conexão e o modo de extração e pode gerar várias execuções (jobs).
2. Clique em **Novo resource** ou em **Editar** para abrir o fluxo do conector **Teradata**.
3. Na etapa **Conexão**, informe **Nome do resource**, host, banco, tipo (TD2/LDAP), usuário e senha ou cole a string JDBC completa. É possível adicionar parâmetros extras (ex.: `DBS_PORT=1025`) e escolher o **nível de log** (Error, Warn, Info, Debug ou Verbose) para filtrar o que será registrado nos jobs, semelhante ao log4j.
4. Utilize **Testar conexão** para validar rapidamente a string. Caso o driver JDBC não esteja disponível no ambiente, o teste retornará o motivo. Se a conexão falhar, nenhum dado de exemplo é aplicado e o job ficará com status de erro.
5. Avance para **Tipo** e escolha o modo **Incremental** (atualiza/aplica apenas diferenças) ou **Completa** (remove bases importadas anteriormente do Teradata antes de recarregar). O tipo atual disponível é **Metadados**, que executa a consulta `select d.DatabaseName, d.CommentString from DBC.DatabasesV where DBKind='D'`.
6. Em **Agenda**, selecione **Execução única** ou associe um **schedule** existente (criado no menu do usuário) para reaproveitar a programação em outros resources.
7. Em **Extração**, revise o resumo e clique em **Salvar** para apenas gravar/atualizar o resource (sem criar job) ou **Salvar e executar** para gerar um job imediato vinculado ao resource. As bases são vinculadas automaticamente ao gestor padrão de metadados.

> Um gestor padrão (`Gestor Padrão (Metadados)`) é criado automaticamente para garantir o vínculo obrigatório nas extrações diretas. Para cadastros manuais ou importações via arquivo, o usuário continua escolhendo o gestor titular normalmente.

## Gerenciar schedules

1. No menu do usuário (canto superior direito), clique em **Schedules** para abrir o gerenciador.
2. Preencha **Nome**, data/hora de início, selecione os **dias da semana** e, se desejar, informe um **intervalo em minutos** e marque **Repetir indefinidamente**.
3. Salve o schedule para reutilizar em diferentes resources. Você pode editar ou excluir agendas existentes na mesma tela.
4. Na etapa **Agenda** do fluxo de extração, escolha **Execução única** ou selecione um dos schedules criados para programar execuções recorrentes. Resources com schedule terão seu **próximo run** calculado automaticamente e gerarão um novo job a cada disparo.

## Monitorar jobs e logs

- No menu suspenso do usuário, acesse **Jobs de extração** para ver histórico, progresso e status de cada execução, incluindo o último erro (quando houver) e o nível de log aplicado.
- Cada execução aparece associada ao **resource** que a originou. Use **Restart** para reprocessar com o mesmo snapshot ou **Editar** para ajustar o resource antes de criar um novo job.
- Clique em **Logs** para baixar o log de execução (carimbo horário + nível) e investigar eventuais falhas respeitando o filtro configurado no resource.

## Relatórios

- Acesse o menu **Relatórios** para ver um painel com:
  - Quantidade total de bases e gestores cadastrados.
  - Gráfico de pizza com bases que possuem gestor vinculado e bases sem gestor.
  - Gráfico de barras com a distribuição de bases por coordenação (do gestor titular).
  - Gráfico de barras com a distribuição de bases por ambiente (produção, homologação, desenvolvimento, DataLab ou vazio).
