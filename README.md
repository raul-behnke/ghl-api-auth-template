# Projeto Padrão de Autorização GoHighLevel

Este repositório contém um template robusto para gerenciar a autenticação OAuth 2.0 com a API GoHighLevel,
projetado para ser a base de seus microserviços. Ele inclui lógica para persistência de tokens em arquivo JSON (como um passo intermediário) e renovação automática.

## Estrutura do Projeto

```
ghl-api-auth-template/
├── .env.example
├── .gitignore
├── Dockerfile
├── README.md
├── requirements.txt
├── token_storage.json (Gerado após a primeira autorização, ignorado pelo Git)
└── src/
    └── auth_handler.py
```

## Como Usar

### 1. Configuração do Ambiente

1.  **Crie um arquivo `.env`** na raiz do projeto, **baseado no `.env.example`**. Este arquivo conterá suas credenciais sensíveis e **não deve ser versionado no Git**.

    ```
    # Exemplo de conteúdo para o seu arquivo .env (com seus valores reais)
    GHL_CLIENT_ID="seu_client_id_real_aqui"
    GHL_CLIENT_SECRET="seu_client_secret_real_aqui"
    GHL_REDIRECT_URI="https://sua.url.de.redirecionamento/real"
    GHL_AUTHORIZATION_CODE="codigo_de_autorizacao_inicial_real"
    ```
    * O `GHL_AUTHORIZATION_CODE` é necessário apenas para o *primeiro* fluxo de autenticação do seu aplicativo, para obter os tokens iniciais (`access_token` e `refresh_token`). Após a primeira execução bem-sucedida, o script salvará esses tokens em `token_storage.json`, e você poderá remover ou comentar esta linha no `.env`.

2.  **Instale as Dependências (Localmente):**
    ```bash
    pip install -r requirements.txt
    ```

### 2. Fluxo de Autorização e Persistência de Tokens (Local)

1.  **Primeira Execução (Com `GHL_AUTHORIZATION_CODE`):**
    * Certifique-se de que `GHL_AUTHORIZATION_CODE` está definido no seu `.env`.
    * Execute o script:
        ```bash
        python src/auth_handler.py
        ```
    * O script tentará trocar o código de autorização por tokens, salvá-los em `token_storage.json` e fazer uma chamada de API de teste.

2.  **Execuções Posteriores (Sem `GHL_AUTHORIZATION_CODE`):**
    * Você pode remover ou comentar a linha `GHL_AUTHORIZATION_CODE` no seu `.env`.
    * Execute o script novamente:
        ```bash
        python src/auth_handler.py
        ```
    * O script tentará carregar os tokens de `token_storage.json`. Se válidos, ele os usará. Se expirados, ele tentará renová-los usando o `refresh_token` e salvará os novos tokens de volta no arquivo.

### 3. Docker

#### 3.1. Construir a Imagem

Navegue até a raiz do seu projeto no terminal e execute:

```bash
docker build -t seu-usuario-docker/ghl-auth-template .
```

Substitua `seu-usuario-docker` pelo seu nome de usuário no Docker Hub.

#### 3.2. Executar o Contêiner

Para testar o contêiner e garantir que ele possa ler suas variáveis de ambiente e persistir o `token_storage.json` (se você não o copiar na imagem, mas montá-lo via volume), use:

```bash
docker run --rm -it --env-file ./.env -v $(pwd)/token_storage.json:/app/token_storage.json seu-usuario-docker/ghl-auth-template
```
* `--rm`: Remove o contêiner automaticamente ao sair.
* `-it`: Permite interatividade (ver logs em tempo real).
* `--env-file ./.env`: Passa suas variáveis de ambiente do `.env` local para o contêiner.
* `-v $(pwd)/token_storage.json:/app/token_storage.json`: Monta o arquivo `token_storage.json` do seu host (diretório atual) dentro do contêiner. Isso permite que o contêiner leia e escreva no mesmo arquivo JSON em execuções separadas, simulando a persistência.

### 4. GitHub e Docker Hub

1.  **Para o GitHub:**
    * Inicialize seu repositório:
        ```bash
        git init
        git add .
        git commit -m "Initial commit: GoHighLevel Auth Template with JSON persistence"
        git branch -M main
        git remote add origin <URL_DO_SEU_REPOSITORIO_GITHUB>
        git push -u origin main
        ```
    * **Lembre-se:** O `.env` e o `token_storage.json` são ignorados pelo `.gitignore` e **não serão enviados para o GitHub**. Isso é essencial para a segurança das suas credenciais.

2.  **Para o Docker Hub:**
    * Faça login no Docker Hub:
        ```bash
        docker login
        ```
    * Envie sua imagem:
        ```bash
        docker push seu-usuario-docker/ghl-auth-template
        ```

## Considerações de Produção

* **Persistência de Tokens Segura:** Embora o JSON seja um passo intermediário útil, em produção, `access_token` e `refresh_token` devem ser armazenados de forma **persistente e criptografada** em um banco de dados (ex: PostgreSQL, MySQL, Firestore) ou em um serviço de gerenciamento de segredos (ex: AWS Secrets Manager, Google Secret Manager, HashiCorp Vault).
* **Gerenciamento de Segredos:** Para todas as credenciais sensíveis (`CLIENT_ID`, `CLIENT_SECRET`, etc.), é altamente recomendável usar um serviço de gerenciamento de segredos em vez de arquivos `.env` em ambientes de produção.
* **Tratamento de Erros:** A lógica de retry com backoff exponencial para `HTTP 429` e outros erros de API deve ser totalmente implementada para maior resiliência.
* **Concorrência:** Se seu microserviço tiver múltiplas instâncias ou threads acessando/modificando o `token_storage.json`, você precisará de mecanismos de travamento (locking) para evitar condições de corrida (race conditions) e corrupção de dados. Usar um banco de dados real resolve isso de forma mais robusta.

Este setup agora oferece uma solução funcional para persistir seus tokens localmente em JSON, sendo um degrau importante para a solução com banco de dados relacionais.