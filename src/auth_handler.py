# src/auth_handler.py
import os
import requests
import json
import time
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Carrega as variaveis de ambiente do arquivo .env
load_dotenv()

# --- Configuracoes da API GoHighLevel ---
GHL_CLIENT_ID = os.getenv("GHL_CLIENT_ID")
GHL_CLIENT_SECRET = os.getenv("GHL_CLIENT_SECRET")
GHL_REDIRECT_URI = os.getenv("GHL_REDIRECT_URI")
# O ID da localizacao (sub-conta) que o seu token deve acessar.
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID")

# IDs e Nomes para a funcionalidade de Health Check por Tag
# O ID do contato especifico que recebera a tag de health check.
GHL_HEALTH_CHECK_CONTACT_ID = os.getenv("GHL_HEALTH_CHECK_CONTACT_ID")
# O nome da tag que sera adicionada ao contato para sinalizar o health check.
GHL_HEALTH_CHECK_TAG_NAME = os.getenv("GHL_HEALTH_CHECK_TAG_NAME")
# Removido: GHL_NOTIFICATION_WORKFLOW_ID, pois o trigger sera a tag

# URLs dos endpoints da API GoHighLevel
TOKEN_URL = "https://services.leadconnectorhq.com/oauth/token"
API_BASE_URL = "https://services.leadconnectorhq.com"

# Caminho para o arquivo JSON de armazenamento de tokens
TOKEN_FILE_PATH = "ghl_tokens.json"

# --- Funcoes de Persistencia de Tokens (JSON) ---

def save_tokens(token_data: dict):
    """
    Salva os dados do token em um arquivo JSON.
    Converte o objeto datetime para string ISO formatada.
    """
    try:
        with open(TOKEN_FILE_PATH, 'w') as f:
            json.dump(token_data, f, indent=4)
        print("Tokens salvos.")
    except Exception as e:
        print(f"Erro ao salvar tokens: {e}")

def load_tokens():
    """
    Carrega os dados do token de um arquivo JSON.
    Converte a string ISO formatada de volta para um objeto datetime.
    """
    if not os.path.exists(TOKEN_FILE_PATH):
        return None
    
    if os.path.isdir(TOKEN_FILE_PATH):
        print(f"Erro: '{TOKEN_FILE_PATH}' é um diretório, não um arquivo. Remova-o manualmente.")
        return None

    try:
        with open(TOKEN_FILE_PATH, 'r') as f:
            token_data = json.load(f)
        
        if 'expiry_timestamp' in token_data and isinstance(token_data['expiry_timestamp'], str):
            token_data['expiry_timestamp'] = datetime.fromisoformat(token_data['expiry_timestamp'])
        
        return token_data
    except json.JSONDecodeError as e:
        print(f"Erro de decodificação JSON no arquivo de tokens: {e}. O arquivo pode estar corrompido.")
        return None
    except Exception as e:
        print(f"Erro ao carregar tokens: {e}")
        return None

# --- Funcoes de Autenticacao ---

def get_access_token(authorization_code: str):
    """
    Troca um codigo de autorizacao por um token de acesso e um token de atualizacao.
    """
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "client_id": GHL_CLIENT_ID,
        "client_secret": GHL_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": GHL_REDIRECT_URI
    }

    try:
        response = requests.post(TOKEN_URL, headers=headers, data=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"Erro HTTP ao obter token: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Erro de requisição ao obter token: {e}")
    return None

def refresh_access_token(refresh_token: str):
    """
    Renova um token de acesso usando um token de atualizacao.
    """
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "client_id": GHL_CLIENT_ID,
        "client_secret": GHL_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    try:
        response = requests.post(TOKEN_URL, headers=headers, data=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"Erro HTTP ao renovar token: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Erro de requisição ao renovar token: {e}")
    return None

def make_ghl_api_call(access_token: str, endpoint: str, method: str = "GET", json_data: dict = None, params: dict = None):
    """
    Faz uma chamada a API GoHighLevel usando o token de acesso fornecido.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Version": "2021-07-28"
    }
    url = f"{API_BASE_URL}{endpoint}"

    try:
        response = requests.request(method.upper(), url, headers=headers, json=json_data, params=params)
        response.raise_for_status()
        return (response.json() if response.content else {}, response.status_code)
    except requests.exceptions.HTTPError as e:
        print(f"Erro na API {endpoint}: {e.response.status_code} - {e.response.text.strip()[:100]}...")
        if e.response.status_code == 429:
            retry_after = int(e.response.headers.get("Retry-After", 1))
            time.sleep(retry_after)
        return (None, e.response.status_code)
    except requests.exceptions.RequestException as e:
        print(f"Erro de requisição na API {endpoint}: {e}")
        return (None, None)

def add_tag_to_contact_by_id(access_token: str, contact_id: str, tag_name: str):
    """
    Adiciona uma tag a um contato específico no GoHighLevel.
    """
    print(f"Adicionando tag '{tag_name}' ao contato ID '{contact_id}'...")
    endpoint = f"/contacts/{contact_id}/tags"
    payload = {"tags": [tag_name]}
    # Para adicionar uma tag, é um POST para /contacts/{contactId}/tags
    return make_ghl_api_call(access_token, endpoint, method="POST", json_data=payload)

# --- Logica Principal de Exemplo ---
if __name__ == "__main__":
    if not all([GHL_CLIENT_ID, GHL_CLIENT_SECRET, GHL_REDIRECT_URI, GHL_LOCATION_ID,
                GHL_HEALTH_CHECK_CONTACT_ID, GHL_HEALTH_CHECK_TAG_NAME]):
        print("Erro: Variáveis de ambiente essenciais para autenticação ou health check ausentes no .env.")
        sys.exit(1)

    current_token_data = None

    # Tenta carregar tokens existentes
    stored_tokens = load_tokens()

    if stored_tokens:
        current_token_data = stored_tokens.copy()
        
        # Verifica se o token de acesso expirou
        if 'expiry_timestamp' in current_token_data and datetime.now() >= current_token_data['expiry_timestamp']:
            print("Access Token expirado. Renovando...")
            refresh_token = current_token_data.get("refresh_token")
            if refresh_token:
                new_token_info = refresh_access_token(refresh_token)
                if new_token_info:
                    current_token_data.update(new_token_info)
                    expires_in = current_token_data.get("expires_in", 3600)
                    current_token_data['expiry_timestamp'] = datetime.now() + timedelta(seconds=expires_in - 300)
                    save_tokens(current_token_data)
                    print("Token renovado e salvo.")
                else:
                    print("Falha ao renovar token. Requer nova autorização manual.")
                    current_token_data = None
            else:
                print("Refresh Token não disponível. Requer nova autorização manual.")
                current_token_data = None
        else:
            print("Tokens carregados e válidos.")
        
        if current_token_data and current_token_data.get("access_token"):
            print(f"Access Token (parcial): {current_token_data.get('access_token', '')[:10]}...")
            print(f"Refresh Token (parcial): {current_token_data.get('refresh_token', '')[:10]}...")
            # Removido: escopos completos e expiração para tornar a saída mais concisa
        else:
            print("Não foi possível obter ou renovar tokens para continuar.")
            sys.exit(1)

    # Se ainda não houver tokens válidos, tenta obter com o código de autorização inicial do .env
    if not current_token_data or not current_token_data.get("access_token"):
        initial_authorization_code = os.getenv("GHL_AUTHORIZATION_CODE")
        if initial_authorization_code:
            print("Tentando obter token com Código de Autorização inicial...")
            token_info = get_access_token(initial_authorization_code)
            if token_info:
                current_token_data = token_info.copy()
                expires_in = current_token_data.get("expires_in", 3600)
                current_token_data['expiry_timestamp'] = datetime.now() + timedelta(seconds=expires_in - 300)
                save_tokens(current_token_data)
                print("Token inicial obtido e salvo.")
                print(f"Access Token (parcial): {current_token_data.get('access_token', '')[:10]}...")
                print(f"Refresh Token (parcial): {current_token_data.get('refresh_token', '')[:10]}...")
            else:
                print("Falha ao obter token inicial. Verifique código e credenciais no .env.")
                sys.exit(1)
        else:
            print("Nenhum token válido e GHL_AUTHORIZATION_CODE ausente no .env para autorização inicial.")
            sys.exit(1)

    # --- Realizar Health Check adicionando uma tag ao contato ---
    print("\nExecutando Health Check (adicionando tag ao contato GoHighLevel)...")
    health_check_succeeded = False
    
    # Para adicionar tags, o endpoint é /contacts/{contactId}/tags e o locationId é um parâmetro de query
    add_tag_response, add_tag_status = add_tag_to_contact_by_id(
        access_token=current_token_data["access_token"],
        contact_id=GHL_HEALTH_CHECK_CONTACT_ID,
        tag_name=GHL_HEALTH_CHECK_TAG_NAME
    )

    if add_tag_response is not None and (add_tag_status == 200 or add_tag_status == 201):
        print(f"Tag '{GHL_HEALTH_CHECK_TAG_NAME}' adicionada ao contato '{GHL_HEALTH_CHECK_CONTACT_ID}' com sucesso!")
        health_check_succeeded = True
    else:
        print(f"Falha ao adicionar tag '{GHL_HEALTH_CHECK_TAG_NAME}' ao contato '{GHL_HEALTH_CHECK_CONTACT_ID}'. Status: {add_tag_status}")

    if health_check_succeeded:
        print("Microserviço operacional. Notificação de saúde disparada via tag.")
    else:
        print("Health Check falhou. Microserviço pode não estar operacional ou há um problema de permissão/ID.")
        sys.exit(1) # Sair com erro se o health check falhar
