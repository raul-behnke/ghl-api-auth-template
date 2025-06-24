import os
import requests
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configurações da API GoHighLevel ---
GHL_CLIENT_ID = os.getenv("GHL_CLIENT_ID")
GHL_CLIENT_SECRET = os.getenv("GHL_CLIENT_SECRET")
GHL_REDIRECT_URI = os.getenv("GHL_REDIRECT_URI")

# URLs dos endpoints da API GoHighLevel
TOKEN_URL = "https://services.leadconnectorhq.com/oauth/token"
API_BASE_URL = "https://services.leadconnectorhq.com"

# Caminho para o arquivo JSON de armazenamento de tokens
TOKEN_FILE_PATH = "token_storage.json"

# --- Funções de Persistência de Tokens (JSON) ---

def save_tokens(token_data: dict):
    """
    Salva os dados do token (access_token, refresh_token, expiry_timestamp) em um arquivo JSON.
    Converte o objeto datetime para string ISO formatada.
    """
    print(f"Salvando tokens em {TOKEN_FILE_PATH}...")
    # Converte o objeto datetime para string antes de salvar no JSON
    if 'expiry_timestamp' in token_data and isinstance(token_data['expiry_timestamp'], datetime):
        token_data['expiry_timestamp'] = token_data['expiry_timestamp'].isoformat()
    
    try:
        with open(TOKEN_FILE_PATH, 'w') as f:
            json.dump(token_data, f, indent=4)
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
        print("Arquivo de tokens não encontrado.")
        return None
    
    try:
        with open(TOKEN_FILE_PATH, 'r') as f:
            token_data = json.load(f)
        
        # Converte a string de timestamp de volta para objeto datetime
        if 'expiry_timestamp' in token_data and isinstance(token_data['expiry_timestamp'], str):
            token_data['expiry_timestamp'] = datetime.fromisoformat(token_data['expiry_timestamp'])
        
        print("Tokens carregados com sucesso!")
        return token_data
    except json.JSONDecodeError as e:
        print(f"Erro de decodificação JSON no arquivo de tokens: {e}. O arquivo pode estar corrompido.")
        return None
    except Exception as e:
        print(f"Erro ao carregar tokens do arquivo JSON: {e}")
        return None

# --- Funções de Autenticação (Mantidas) ---

def get_access_token(authorization_code: str):
    """
    Troca um código de autorização por um token de acesso e um token de atualização.
    """
    print("Iniciando a troca do código de autorização por tokens...")
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
        print("Tokens de acesso e atualização obtidos com sucesso!")
        return token_info
    except requests.exceptions.HTTPError as e:
        print(f"Erro HTTP ao obter token de acesso: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Erro de requisição ao obter token de acesso: {e}")
    return None

def refresh_access_token(refresh_token: str):
    """
    Renova um token de acesso usando um token de atualização.
    """
    print("Iniciando a renovação do token de acesso...")
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
        print(f"Erro de requisição ao renovar token de acesso: {e}")
    return None

def make_ghl_api_call(access_token: str, endpoint: str, method: str = "GET", payload: dict = None):
    """
    Faz uma chamada à API GoHighLevel usando o token de acesso fornecido.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Version": "2021-07-28"
    }
    url = f"{API_BASE_URL}{endpoint}"

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=payload)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=payload)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Método HTTP '{method}' não suportado.")

        response.raise_for_status()
        return response.json() if response.content else {}
    except requests.exceptions.HTTPError as e:
        print(f"Erro HTTP ao chamar a API: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 401:
            print("Token de acesso inválido ou expirado. Tente renová-lo.")
        elif e.response.status_code == 429:
            retry_after = int(e.response.headers.get("Retry-After", 1))
            print(f"Limite de taxa excedido. Tente novamente em {retry_after} segundos.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Erro de requisição ao chamar a API: {e}")
    return None

# --- Lógica Principal de Exemplo ---
if __name__ == "__main__":
    if not all([GHL_CLIENT_ID, GHL_CLIENT_SECRET, GHL_REDIRECT_URI]):
        print("Erro: As variáveis de ambiente GHL_CLIENT_ID, GHL_CLIENT_SECRET e GHL_REDIRECT_URI devem estar definidas.")
        print("Consulte o arquivo .env.example e o README.md para mais informações.")
        exit(1)

    current_access_token = None
    current_refresh_token = None
    token_expiry_timestamp = None

    # Tenta carregar tokens existentes
    stored_tokens = load_tokens()

    if stored_tokens:
        current_access_token = stored_tokens.get("access_token")
        current_refresh_token = stored_tokens.get("refresh_token")
        token_expiry_timestamp = stored_tokens.get("expiry_timestamp")

        if token_expiry_timestamp and datetime.now() >= token_expiry_timestamp:
            print("Access Token expirado ao carregar. Tentando renovar...")
            if current_refresh_token:
                new_token_info = refresh_access_token(current_refresh_token)
                if new_token_info:
                    current_access_token = new_token_info.get("access_token")
                    current_refresh_token = new_token_info.get("refresh_token")
                    expires_in = new_token_info.get("expires_in", 3600)
                    token_expiry_timestamp = datetime.now() + timedelta(seconds=expires_in - 300)
                    # Salva os novos tokens
                    save_tokens({
                        "access_token": current_access_token,
                        "refresh_token": current_refresh_token,
                        "expiry_timestamp": token_expiry_timestamp
                    })
                else:
                    print("Falha ao renovar o token expirado. Requer nova autorização manual.")
                    current_access_token = None # Invalida tokens para forçar nova autorização se necessário
            else:
                print("Refresh Token não disponível. Requer nova autorização manual.")
                current_access_token = None
        else:
            print("Tokens carregados e ainda válidos.")
            print(f"Access Token: {current_access_token[:10]}...")
            print(f"Refresh Token: {current_refresh_token[:10]}...")
            print(f"Expirará em: {token_expiry_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

    # Se não houver tokens válidos após carregar/renovar, tenta obter com o código de autorização inicial
    if not current_access_token:
        initial_authorization_code = os.getenv("GHL_AUTHORIZATION_CODE")
        if initial_authorization_code:
            print(f"Nenhum token válido encontrado. Tentando obter com o Código de Autorização inicial: {initial_authorization_code[:10]}...")
            token_info = get_access_token(initial_authorization_code)
            if token_info:
                current_access_token = token_info.get("access_token")
                current_refresh_token = token_info.get("refresh_token")
                expires_in = token_info.get("expires_in", 3600)
                token_expiry_timestamp = datetime.now() + timedelta(seconds=expires_in - 300)
                # Salva os tokens recém-obtidos
                save_tokens({
                    "access_token": current_access_token,
                    "refresh_token": current_refresh_token,
                    "expiry_timestamp": token_expiry_timestamp
                })
                print(f"Access Token: {current_access_token[:10]}...")
                print(f"Refresh Token: {current_refresh_token[:10]}...")
                print(f"Expirará em: {token_expiry_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print("Não foi possível obter tokens com o código de autorização inicial. Verifique o código e as credenciais.")
        else:
            print("Nenhum token válido e nenhum GHL_AUTHORIZATION_CODE fornecido para a autorização inicial.")
            print("Por favor, obtenha um código de autorização e defina GHL_AUTHORIZATION_CODE no seu .env.")

    # Exemplo de como usar os tokens para fazer chamadas à API
    if current_access_token:
        print("\n--- Testando chamada à API com o Access Token atual ---")
        contacts_endpoint = "/contacts/"
        contact_data = make_ghl_api_call(current_access_token, contacts_endpoint, method="GET")

        if contact_data:
            print("Chamada à API de Contatos bem-sucedida. Exemplo de dados:")
            if 'contacts' in contact_data and len(contact_data['contacts']) > 0:
                print(f"Primeiro contato: {contact_data['contacts'][0].get('firstName')} {contact_data['contacts'][0].get('lastName')}")
            else:
                print("Nenhum contato encontrado ou estrutura de resposta inesperada.")
        else:
            print("Chamada à API de Contatos falhou ou não retornou dados.")
    else:
        print("\nNão foi possível fazer chamadas à API sem um Access Token válido.")