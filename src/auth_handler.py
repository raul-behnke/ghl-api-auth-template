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
# Obtenha este ID da URL da sua sub-conta no GoHighLevel.
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID")

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
    print(f"Salvando tokens em {TOKEN_FILE_PATH}...")
    
    data_to_save = token_data.copy()

    if 'expiry_timestamp' in data_to_save and isinstance(data_to_save['expiry_timestamp'], datetime):
        data_to_save['expiry_timestamp'] = data_to_save['expiry_timestamp'].isoformat()
    
    try:
        with open(TOKEN_FILE_PATH, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        print("Tokens salvos com sucesso!")
    except Exception as e:
        print(f"Erro ao salvar tokens no arquivo JSON: {e}")

def load_tokens():
    """
    Carrega os dados do token de um arquivo JSON.
    Converte a string ISO formatada de volta para um objeto datetime.
    """
    print(f"Carregando tokens de {TOKEN_FILE_PATH}...")
    if not os.path.exists(TOKEN_FILE_PATH):
        print("Arquivo de tokens nao encontrado.")
        return None
    
    if os.path.isdir(TOKEN_FILE_PATH):
        print(f"ERRO CRITICO: '{TOKEN_FILE_PATH}' eh um diretorio, nao um arquivo. Por favor, remova o diretorio manualmente para permitir a criacao do arquivo.")
        return None

    try:
        with open(TOKEN_FILE_PATH, 'r') as f:
            token_data = json.load(f)
        
        if 'expiry_timestamp' in token_data and isinstance(token_data['expiry_timestamp'], str):
            token_data['expiry_timestamp'] = datetime.fromisoformat(token_data['expiry_timestamp'])
        
        print("Tokens carregados com sucesso!")
        return token_data
    except json.JSONDecodeError as e:
        print(f"Erro de decodificacao JSON no arquivo de tokens: {e}. O arquivo pode estar corrompido.")
        return None
    except Exception as e:
        print(f"Erro ao carregar tokens do arquivo JSON: {e}")
        return None

# --- Funcoes de Autenticacao ---

def get_access_token(authorization_code: str):
    """
    Troca um codigo de autorizacao por um token de acesso e um token de atualizacao.
    Usa credenciais do ambiente local (GHL_CLIENT_ID, etc.).
    """
    print("Iniciando a troca do codigo de autorizacao por tokens...")
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
        token_info = response.json()
        print("Tokens de acesso e atualizacao obtidos com sucesso!")
        return token_info
    except requests.exceptions.HTTPError as e:
        print(f"Erro HTTP ao obter token de acesso: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Erro de requisicao ao obter token de acesso: {e}")
    return None

def refresh_access_token(refresh_token: str):
    """
    Renova um token de acesso usando um token de atualizacao.
    Usa credenciais do ambiente local (GHL_CLIENT_ID, etc.).
    """
    print("Iniciando a renovacao do token de acesso...")
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
        token_info = response.json()
        print("Token de acesso renovado com sucesso!")
        return token_info
    except requests.exceptions.HTTPError as e:
        print(f"Erro HTTP ao renovar token de acesso: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Erro de requisicao ao renovar token de acesso: {e}")
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
        response = None
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=json_data, params=params)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=json_data, params=params)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, params=params)
        else:
            raise ValueError(f"Metodo HTTP '{method}' nao suportado.")

        response.raise_for_status()
        return (response.json() if response.content else {}, response.status_code)
    except requests.exceptions.HTTPError as e:
        print(f"Erro HTTP ao chamar a API: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 401:
            print("Token de acesso invalido ou expirado. Tente renova-lo na proxima tentativa.")
        elif e.response.status_code == 429:
            retry_after = int(e.response.headers.get("Retry-After", 1))
            print(f"Limite de taxa excedido. Aguarde {retry_after} segundos antes de re-tentar.")
            time.sleep(retry_after)
        return (None, e.response.status_code)
    except requests.exceptions.RequestException as e:
        print(f"Erro de requisicao ao chamar a API: {e}")
        return (None, None)

# --- Logica Principal de Exemplo (para execucao LOCAL) ---
if __name__ == "__main__":
    if not all([GHL_CLIENT_ID, GHL_CLIENT_SECRET, GHL_REDIRECT_URI, GHL_LOCATION_ID]):
        print("Erro: As variaveis de ambiente GHL_CLIENT_ID, GHL_CLIENT_SECRET, GHL_REDIRECT_URI e GHL_LOCATION_ID devem estar definidas no seu arquivo .env.")
        print("Consulte o arquivo .env.example e o README.md para mais informacoes.")
        exit(1)

    # ** NOVO DEBUG: Imprime GHL_LOCATION_ID como lido pelo script **
    print(f"DEBUG: GHL_LOCATION_ID lido do ambiente: '{GHL_LOCATION_ID}' (comprimento: {len(GHL_LOCATION_ID) if GHL_LOCATION_ID else 0})")
    if GHL_LOCATION_ID and (GHL_LOCATION_ID.startswith(" ") or GHL_LOCATION_ID.endswith(" ")):
        print("AVISO: GHL_LOCATION_ID parece ter espacos em branco no inicio ou fim. Isso pode causar o erro 403.")


    current_token_data = None

    # Tenta carregar tokens existentes do arquivo local
    stored_tokens = load_tokens()

    if stored_tokens:
        current_token_data = stored_tokens.copy()
        
        # Verifica se o token de acesso expirou ao carregar
        if 'expiry_timestamp' in current_token_data and datetime.now() >= current_token_data['expiry_timestamp']:
            print("Access Token expirado ao carregar. Tentando renovar...")
            refresh_token = current_token_data.get("refresh_token")
            if refresh_token:
                new_token_info = refresh_access_token(refresh_token)
                if new_token_info:
                    current_token_data.update(new_token_info)
                    expires_in = current_token_data.get("expires_in", 3600)
                    current_token_data['expiry_timestamp'] = datetime.now() + timedelta(seconds=expires_in - 300)
                    save_tokens(current_token_data)
                    print("Token renovado com sucesso!")
                else:
                    print("Falha ao renovar o token expirado. Requer nova autorizacao manual.")
                    current_token_data = None
            else:
                print("Refresh Token nao disponivel. Requer nova autorizacao manual.")
                current_token_data = None
        else:
            print("Tokens carregados e ainda validos.")
        
        if current_token_data and current_token_data.get("access_token"):
            print(f"Access Token: {current_token_data.get('access_token', '')[:10]}...")
            print(f"Refresh Token: {current_token_data.get('refresh_token', '')[:10]}...")
            print(f"Escopos: {current_token_data.get('scope', 'N/A')}")
            print(f"Expirara em: {current_token_data.get('expiry_timestamp').strftime('%Y-%m-%d %H:%M:%S') if current_token_data.get('expiry_timestamp') else 'N/A'}")
        else:
            print("Nao foi possivel obter ou renovar tokens. Nao havera chamadas a API.")
            exit(1)

    # Se nao houver tokens validos apos carregar/renovar, tenta obter com o codigo de autorizacao inicial do .env
    if not current_token_data or not current_token_data.get("access_token"):
        initial_authorization_code = os.getenv("GHL_AUTHORIZATION_CODE")
        if initial_authorization_code:
            print(f"Nenhum token valido encontrado. Tentando obter com o Codigo de Autorizacao inicial do .env: {initial_authorization_code[:10]}...")
            token_info = get_access_token(initial_authorization_code)
            if token_info:
                current_token_data = token_info.copy()
                expires_in = current_token_data.get("expires_in", 3600)
                current_token_data['expiry_timestamp'] = datetime.now() + timedelta(seconds=expires_in - 300)
                save_tokens(current_token_data)
                print(f"Access Token: {current_token_data.get('access_token', '')[:10]}...")
                print(f"Refresh Token: {current_token_data.get('refresh_token', '')[:10]}...")
                print(f"Escopos: {current_token_data.get('scope', 'N/A')}")
                print(f"Expirara em: {current_token_data.get('expiry_timestamp').strftime('%Y-%m-%d %H:%M:%S') if current_token_data.get('expiry_timestamp') else 'N/A'}")
            else:
                print("Nao foi possivel obter tokens com o codigo de autorizacao inicial. Verifique o codigo e as credenciais no seu .env.")
                exit(1)
        else:
            print("Nenhum token valido e nenhum GHL_AUTHORIZATION_CODE fornecido para a autorizacao inicial no .env.")
            print("Por favor, obtenha um codigo de autorizacao e defina GHL_AUTHORIZATION_CODE no seu .env para a primeira execucao.")
            exit(1)

    # --- Testando a chamada à API de Contatos com o Access Token atual (com retry) ---
    print("\n--- Testando chamada a API de Contatos com o Access Token atual (com retry) ---")
    contacts_endpoint = "/contacts/"
    # O parametro locationId é OBRIGATORIO para /contacts/
    contacts_params = {"locationId": GHL_LOCATION_ID} 

    max_api_retries = 2
    api_call_succeeded = False
    
    for attempt in range(max_api_retries):
        print(f"Tentativa {attempt + 1}/{max_api_retries} para chamar {contacts_endpoint}...")
        contact_data, status_code = make_ghl_api_call(
            access_token=current_token_data["access_token"],
            endpoint=contacts_endpoint,
            method="GET",
            params=contacts_params
        )

        if contact_data is not None and status_code == 200:
            print("Chamada a API de Contatos bem-sucedida.")
            if 'contacts' in contact_data and len(contact_data['contacts']) > 0:
                print(f"Primeiro contato: {contact_data['contacts'][0].get('firstName')} {contact_data['contacts'][0].get('lastName')}")
            else:
                print("Nenhum contato encontrado ou estrutura de resposta inesperada.")
            api_call_succeeded = True
            break
        elif status_code == 401:
            print("Access Token expirado ou invalido durante a chamada. Tentando renovar...")
            refresh_token = current_token_data.get("refresh_token")
            if refresh_token:
                new_token_info = refresh_access_token(refresh_token)
                if new_token_info:
                    current_token_data.update(new_token_info)
                    expires_in = current_token_data.get("expires_in", 3600)
                    current_token_data['expiry_timestamp'] = datetime.now() + timedelta(seconds=expires_in - 300)
                    save_tokens(current_token_data)
                    print("Token renovado com sucesso. Re-tentando a chamada a API...")
                else:
                    print("Falha ao renovar token. Requer nova autorizacao manual.")
                    break
            else:
                print("Refresh Token nao disponivel. Requer nova autorizacao manual.")
                break
        elif status_code == 429:
            print("Limite de taxa excedido. A funcao make_ghl_api_call ja implementa um sleep. Re-tentando...")
        else:
            print(f"Chamada a API falhou com status {status_code}. Nao ha logica de retry automatica para este erro.")
            break

    if not api_call_succeeded:
        print("Chamada a API de Contatos falhou apos todas as tentativas.")
