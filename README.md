Projeto Padrão de Autenticação GoHighLevel
Este repositório contém um template robusto e replicável para gerenciar a autenticação OAuth 2.0 com a API GoHighLevel. Ele é projetado como um microserviço autônomo que pode ser implantado em um servidor (como uma VPS) para operar periodicamente, garantindo que a conexão com a API GoHighLevel esteja sempre ativa e reportando seu status.

Propósito do Projeto
O objetivo principal deste projeto é fornecer uma base de autenticação padronizada e monitorável para qualquer aplicação ou microserviço que precise interagir com a API GoHighLevel. Ele resolve os desafios de:

Autenticação OAuth 2.0: Obtendo e renovando access_token e refresh_token.

Persistência de Tokens: Armazenando os tokens de forma segura e persistente para evitar reautenticações manuais constantes.

Controle de Saúde do Serviço (Health Check): Verificando periodicamente a conectividade e as permissões com a API GoHighLevel.

Notificações Proativas: Disparando automações no GoHighLevel (como SMS ou e-mail) para alertar sobre o status operacional do microserviço.

Dockerização: Empacotando a aplicação para fácil implantação e portabilidade entre ambientes.

Agendamento Flexível: Permitindo a configuração do intervalo de execução diretamente via variáveis de ambiente.

Este projeto é ideal como um componente fundamental em uma arquitetura de microserviços GoHighLevel.

Estrutura do Projeto
ghl-api-auth-template/
├── .env.example                 # Exemplo de variáveis de ambiente para configuração.
├── .gitignore                   # Regras para ignorar arquivos no Git (tokens, envs, logs).
├── Dockerfile                   # Definição da imagem Docker do microserviço.
├── README.md                    # Este arquivo.
├── requirements.txt             # Dependências Python do projeto.
├── ghl_tokens.json              # Arquivo JSON onde os tokens são persistidos (criado localmente, montado no Docker).
├── src/                         # Código-fonte principal do microserviço.
│   └── auth_handler.py          # Lógica de autenticação, API calls e health check.
└── run_ghl_check.sh             # Script Shell para executar o Docker via Cron.
└── setup_cron.sh                # Script Shell auxiliar para configurar o Cron job na VPS.

Como Usar: Configuração Local e Primeira Autorização
Esta seção guia você na configuração inicial do projeto em seu ambiente local. O objetivo é realizar a primeira autenticação OAuth e gerar o arquivo ghl_tokens.json que será usado posteriormente no Docker.

1. Pré-requisitos
Python 3.9+

pip (gerenciador de pacotes Python)

Docker Desktop (ou engine Docker no Linux)

Conta de Desenvolvedor GoHighLevel (para Client ID, Secret, Redirect URI)

Acesso a uma sub-conta (Location) no GoHighLevel com permissões para criar contatos/tags e disparar workflows.

2. Clonar o Repositório
git clone https://github.com/seu-usuario/ghl-api-auth-template.git
cd ghl-api-auth-template

(Substitua seu-usuario pelo seu usuário GitHub.)

3. Configurar Variáveis de Ambiente (.env)
Crie um arquivo chamado .env na raiz do seu projeto, baseado no .env.example. Este arquivo conterá suas credenciais sensíveis e NÃO DEVE SER VERSIONADO NO GIT (ele já está no .gitignore).

cp .env.example .env
# Agora, edite o arquivo .env

Abra o arquivo .env e preencha com seus valores reais:

# .env
# Credenciais do seu aplicativo GoHighLevel (Geradas no Marketplace do GoHighLevel)
GHL_CLIENT_ID="SEU_CLIENT_ID_AQUI"
GHL_CLIENT_SECRET="SEU_CLIENT_SECRET_AQUI"
GHL_REDIRECT_URI="https://sua.url.de.redirecionamento/aqui" # Ex: https://google.com/

# O ID da localizacao (sub-conta) que o seu token deve acessar.
# Obtenha este ID diretamente da UI do GoHighLevel (Settings -> Company Profile -> Location ID).
GHL_LOCATION_ID="O_ID_DA_SUA_LOCALIZACAO_GHL_AQUI"

# --- Configuracoes para o Health Check por Tag ---
# O ID do contato no GoHighLevel que sera usado para o health check (adicione uma tag a ele).
# Crie um contato de teste no GHL (pode ser seu proprio contato) e obtenha o ID dele na URL.
GHL_HEALTH_CHECK_CONTACT_ID="O_ID_DO_CONTATO_DE_HEALTH_CHECK_AQUI"
# O nome da tag que sera adicionada e entao removida pelo workflow do GoHighLevel.
GHL_HEALTH_CHECK_TAG_NAME="Status:Online-AuthService" # Sugestao de nome

# Nome do microservico para personalizacao da notificacao (Opcional)
MICROSERVICE_NAME="AuthServicePadrao" # Ex: JARDINS-IMOB para sua notificacao

# --- Configuracao do Agendamento (para Cron Job na VPS) ---
# Define o intervalo de execucao do script em horas.
# Usado pelo setup_cron.sh. Ex: 12 para 12 em 12 horas; 24 para 24 em 24 horas.
RUN_INTERVAL_HOURS=12

# NOTA: GHL_AUTHORIZATION_CODE (o codigo de uso unico) sera adicionado TEMPORARIAMENTE
# no proximo passo, apenas para a PRIMEIRA execucao local.

4. Instalar Dependências
pip install -r requirements.txt

5. Realizar a Primeira Autorização (Gerar ghl_tokens.json)
Este é um passo CRÍTICO. Você precisa obter um código de autorização "virgem" e usá-lo rapidamente.

Limpeza Inicial: Para garantir um início limpo, remova quaisquer arquivos de token antigos que possam ter sido criados:

Remove-Item -Path ".\token_storage.json" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path ".\ghl_tokens.json" -Recurse -Force -ErrorAction SilentlyContinue

Verifique visualmente na raiz do seu projeto se ghl_tokens.json (e token_storage.json) não existem.

Obter um NOVO e VIRGEM authorization_code:

Vá para a UI do GoHighLevel.

Refaça o processo de autorização OAuth para o seu aplicativo (geralmente, o administrador da agência/sub-conta visita a URL de autorização do seu aplicativo).

Quando for redirecionado para a GHL_REDIRECT_URI (ex: https://google.com/?code=SEU_CODIGO_AQUI), COPIE IMEDIATAMENTE o valor do parâmetro code da URL. Este código é de uso único e expira em poucos segundos.

Atualize seu .env com o GHL_AUTHORIZATION_CODE:

Abra seu arquivo .env novamente.

Adicione (ou atualize) a linha GHL_AUTHORIZATION_CODE com o código que você acabou de copiar:

GHL_AUTHORIZATION_CODE="COLE_AQUI_O_CODIGO_RECEM_COPIADO"

SALVE O ARQUIVO .env RAPIDAMENTE.

Execute o script Python localmente:

python src/auth_handler.py

Saída Esperada:
Você verá mensagens indicando a busca de tokens, a troca do código de autorização, e finalmente:

Tokens salvos.
Access Token (parcial): eyJhbGciOi...
Refresh Token (parcial): eyJhbGciOi...
Escopos: [Seus escopos completos aqui]
Expira em: YYYY-MM-DD HH:MM:SS

Testando chamada à API de Contatos...
Tentativa 1/2...
Chamada à API de Contatos bem-sucedida.
Tag 'Status:Online-AuthService' adicionada ao contato 'O_ID_DO_CONTATO_DE_HEALTH_CHECK_AQUI' com sucesso!
Microserviço operacional. Notificação de saúde disparada via tag.

VERIFIQUE: Um arquivo ghl_tokens.json deve ter sido criado na raiz do seu projeto local.

VERIFIQUE NO GoHighLevel: A tag configurada deve ter aparecido no contato especificado, e seu workflow deve ter sido disparado (e a tag removida, se você configurou o workflow para isso).

Dockerização do Projeto
Após o sucesso da configuração local, vamos empacotar e testar o microserviço com Docker.

1. Construir a Imagem Docker
docker build -t raulbehnke/ghl-auth-template .

Esta imagem contém o ambiente Python, as dependências e o código, mas não o ghl_tokens.json ou o .env diretamente (eles serão montados em runtime).

2. Preparar .env para o Docker Runtime
Após a primeira execução local bem-sucedida (passo 5), você pode remover ou comentar a linha GHL_AUTHORIZATION_CODE no seu arquivo .env, pois os tokens já estão persistidos em ghl_tokens.json. As outras variáveis são necessárias para a operação contínua.

3. Testar o Contêiner Docker Localmente (com Persistência)
Execute o contêiner, montando o arquivo ghl_tokens.json que foi gerado no seu host:

docker run --rm -it --env-file ./.env -v "${PWD}/ghl_tokens.json:/app/ghl_tokens.json" raulbehnke/ghl-auth-template

Saída Esperada:
Similar à execução local, mostrando o carregamento de tokens, a adição da tag e o sucesso do health check.

Publicar no Docker Hub
Para que seu servidor VPS possa acessar a imagem do seu microserviço, você precisa publicá-la em um registro de contêineres como o Docker Hub.

Faça login no Docker Hub:

docker login

Envie sua imagem:

docker push raulbehnke/ghl-auth-template

Implantação e Agendamento em um Servidor VPS
Esta seção detalha como implantar o microserviço em sua VPS e agendá-lo para execução periódica usando cron.

1. Pré-requisitos na VPS
Acesso SSH à sua VPS.

Docker Engine instalado e funcionando na VPS.

Conexão de rede da VPS com a internet para acessar o Docker Hub e a API GoHighLevel.

2. Configuração Inicial na VPS
Conecte-se ao seu VPS via SSH:

ssh seu_usuario@seu_ip_do_vps

Criar o diretório do projeto:

sudo mkdir -p /opt/ghl-auth-microservice
sudo chown $(whoami):$(whoami) /opt/ghl-auth-microservice
cd /opt/ghl-auth-microservice

Copiar .env e ghl_tokens.json para a VPS:

Você precisará copiar esses dois arquivos do seu computador local para /opt/ghl-auth-microservice/ na sua VPS.

No seu TERMINAL LOCAL (não no VPS), execute os comandos scp:

scp "C:\Users\WEB\OneDrive\Área de Trabalho\ghl-api-auth-template\.env" seu_usuario@seu_ip_do_vps:/opt/ghl-auth-microservice/
scp "C:\Users\WEB\OneDrive\Área de Trabalho\ghl-api-auth-template\ghl_tokens.json" seu_usuario@seu_ip_do_vps:/opt/ghl-auth-microservice/

(Ajuste os caminhos e credenciais SSH.)

Puxar a imagem Docker:

docker pull raulbehnke/ghl-auth-template

3. Criar Scripts de Execução e Agendamento na VPS
Estes scripts serão criados diretamente na sua VPS, no diretório /opt/ghl-auth-microservice/.

Criar run_ghl_check.sh:

nano run_ghl_check.sh

Cole o conteúdo abaixo:

#!/bin/bash
# run_ghl_check.sh
# Script para executar o microservico de autenticacao GoHighLevel via Docker.

# Carrega as variaveis de ambiente do arquivo .env
if [ -f "$(dirname "$0")/.env" ]; then
    set -a
    source "$(dirname "$0")/.env"
    set +a
else
    echo "$(date): Erro: Arquivo .env nao encontrado no diretorio do script. Saindo." >> /var/log/ghl_auth_check.log 2>&1
    exit 1
fi

cd "$(dirname "$0")"

echo "$(date): Iniciando execucao do microservico de autenticacao." >> /var/log/ghl_auth_check.log 2>&1

docker run --rm --env-file ./.env \
    -v "$(pwd)/ghl_tokens.json:/app/ghl_tokens.json" \
    raulbehnke/ghl-auth-template >> /var/log/ghl_auth_check.log 2>&1

echo "$(date): Execucao do microservico de autenticacao finalizada." >> /var/log/ghl_auth_check.log 2>&1

Salve e saia (Ctrl+X, Y, Enter).

Tornar run_ghl_check.sh executável:

chmod +x run_ghl_check.sh

Criar setup_cron.sh:

nano setup_cron.sh

Cole o conteúdo abaixo:

#!/bin/bash
# setup_cron.sh
# Script para configurar ou atualizar o cron job para o microservico de autenticacao GoHighLevel.

cd "$(dirname "$0")"

if [ -f ./.env ]; then
    set -a
    source ./.env
    set +a
else
    echo "Erro: Arquivo .env nao encontrado. Nao foi possivel configurar o cron."
    exit 1
fi

if [ -z "$RUN_INTERVAL_HOURS" ]; then
    echo "Erro: RUN_INTERVAL_HOURS nao definido no .env. Por favor, defina um valor (ex: 12) em seu .env."
    exit 1
fi

if [ "$RUN_INTERVAL_HOURS" -eq 24 ]; then
    CRON_SCHEDULE="0 0 * * *"
elif [ "$RUN_INTERVAL_HOURS" -gt 0 ] && [ $((24 % RUN_INTERVAL_HOURS)) -eq 0 ]; then
    CRON_SCHEDULE="0 */$RUN_INTERVAL_HOURS * * *"
else
    echo "Erro: RUN_INTERVAL_HOURS '$RUN_INTERVAL_HOURS' invalido para agendamento simples de cron."
    echo "Por favor, use um divisor de 24 (ex: 1, 2, 3, 4, 6, 8, 12, 24)."
    exit 1
fi

SCRIPT_PATH="$(pwd)/run_ghl_check.sh"
LOG_PATH="/var/log/ghl_auth_check.log"

CRON_JOB="$CRON_SCHEDULE $SCRIPT_PATH >> $LOG_PATH 2>&1"

echo "Configurando cron job para rodar a cada $RUN_INTERVAL_HOURS horas."
echo "Linha do cron gerada: '$CRON_JOB'"

(crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH" ; echo "$CRON_JOB") | crontab -

echo "Cron job configurado com sucesso!"
echo "Para verificar, digite: crontab -l"
echo "Para ver os logs, digite: tail -f $LOG_PATH"

Salve e saia (Ctrl+X, Y, Enter).

Tornar setup_cron.sh executável:

chmod +x setup_cron.sh

4. Configurar o Workflow de Notificação no GoHighLevel
Este workflow é essencial para receber as notificações de saúde do seu microserviço via GoHighLevel (SMS/Email).

Crie um Contato de "Health Check": Se ainda não o fez, crie um contato no GoHighLevel que você usará para os testes (pode ser seu próprio contato). Obtenha o ID desse contato (na URL quando visualiza o contato) e use-o em GHL_HEALTH_CHECK_CONTACT_ID no seu .env.

Crie uma Tag de "Health Check": Crie a tag com o nome definido em GHL_HEALTH_CHECK_TAG_NAME (ex: Status:Online-AuthService).

Crie um Novo Workflow no GoHighLevel:

Vá para "Automation" (Automação) > "Workflows".

Trigger (Acionador): Escolha "Contact Tag" (Tag de Contato), selecione o trigger "Tag Added" (Tag Adicionada) e escolha a tag que você criou (Status:Online-AuthService).

Ações do Workflow:

1. Enviar Notificação (SMS/Email): Adicione uma ação "Send SMS" ou "Send Email" com sua mensagem personalizada. Ex: O microserviço {{ contact.custom_field_microservice_name | default:"AuthServicePadrao" }} executou sua verificacao agora {{ contact.last_activity_date | date: "%H:%M" }}. (Você precisaria de um campo personalizado microservice_name no contato ou usar o nome padrão, e o horário seria o da última atividade do contato).

2. Remover Tag (MUITO IMPORTANTE!): Adicione uma ação "Remove Tag" e selecione a mesma tag que você adicionou (Status:Online-AuthService). Isso é crucial para que a tag possa ser adicionada novamente na próxima execução do script e o trigger funcione.

5. Configurar o Agendamento Periódico no VPS
Execute o setup_cron.sh:

./setup_cron.sh

Este comando lerá RUN_INTERVAL_HOURS do seu .env e adicionará a linha correspondente ao cron. Você pode verificar a lista de cron jobs com crontab -l.

Teste a Execução Manual (Opcional, mas recomendado):
Execute o script uma vez para confirmar que tudo está funcionando:

./run_ghl_check.sh

E verifique o log para a saída:

tail -f /var/log/ghl_auth_check.log

Agora seu microserviço está totalmente configurado, implantado e agendado para rodar periodicamente em sua VPS. A cada 12 (ou X) horas, ele verificará a conexão com a API GoHighLevel e enviará uma notificação de status através da adição de uma tag.