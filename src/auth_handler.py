import os
import requests
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Carrega as variaveis de ambiente do arquivo .env
load_dotenv()

# --- Configuracoes da API GoHighLevel ---
# Obtenha estas credenciais apos registrar seu aplicativo no Marketplace do GoHighLevel.
# NUNCA exponha estas chaves diretamente no codigo ou em repositorios publicos.
GHL_CLIENT_ID = os.getenv("GHL_CLIENT_ID")
GHL_CLIENT_SECRET = os.getenv("GHL_CLIENT_SECRET")
GHL_REDIRECT_URI = os.getenv("GHL_REDIRECT_URI")
# O ID da localizacao (sub-conta) que o seu token deve acessar.
# Obtenha este ID da URL da sua sub-conta no GoHighLevel ou via API /locations/.
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID")

# URLs dos endpoints da API GoHighLevel
TOKEN_URL = "https://services.leadconnectorhq.com/oauth/token"
API_BASE_URL = "https://services.leadconnectorhq.com"

# Caminho para o arquivo JSON de armazenamento de tokens
TOKEN_FILE_PATH = "token_storage.json"

# --- Funcoes de Persistencia de Tokens (JSON) ---

def save_tokens(token_data: dict):
    """
    Salva os dados do token (access_token, refresh_token, expiry_timestamp, scope, etc.)
    em um arquivo JSON. Converte o objeto datetime para string ISO formatada.
    """
    print(f"Salvando tokens em {TOKEN_FILE_PATH}...")
    
    # Cria uma copia para evitar modificar o dicionario original
    data_to_save = token_data.copy()

    # Converte o objeto datetime para string antes de salvar no JSON
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
    
    try:
        with open(TOKEN_FILE_PATH, 'r') as f:
            token_data = json.load(f)
        
        # Converte a string de timestamp de volta para objeto datetime
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
    Esta funcao e chamada uma unica vez para a autorizacao inicial.

    Args:
        authorization_code (str): O codigo de autorizacao recebido do GoHighLevel
                                  apos o usuario autorizar seu aplicativo.

    Returns:
        dict: Um dicionario contendo 'access_token', 'refresh_token', 'expires_in',
              e 'scope', ou None em caso de erro.
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
        response.raise_for_status() # Lanca um HTTPError para respostas de erro (4xx ou 5xx)
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
    Esta funcao deve ser chamada quando o access_token expirar.

    Args:
        refresh_token (str): O token de atualizacao previamente obtido.

    Returns:
        dict: Um dicionario contendo o novo 'access_token', 'refresh_token' (pode ser o mesmo ou novo),
              'expires_in', e 'scope', ou None em caso de erro.
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
        response.raise_for_status() # Lanca um HTTPError para respostas de erro (4xx ou 5xx)
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

    Args:
        access_token (str): O token de acesso atual.
        endpoint (str): O caminho do endpoint da API (ex: "/contacts/").
        method (str): O metodo HTTP (GET, POST, PUT, DELETE).
        json_data (dict): O corpo da requisicao para metodos POST/PUT.
        params (dict): Dicionario de parametros de query para a URL (ex: {'locationId': 'abc'}).

    Returns:
        tuple: (data: dict, status_code: int) se a requisicao for bem-sucedida,
               ou (None, status_code) em caso de erro HTTP,
               ou (None, None) em caso de erro de requisicao geral.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Version": "2021-07-28" # Versao da API, conforme o guia
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

        response.raise_for_status() # Lanca um HTTPError para respostas de erro (4xx ou 5xx)
        return (response.json() if response.content else {}, response.status_code)
    except requests.exceptions.HTTPError as e:
        print(f"Erro HTTP ao chamar a API: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 401:
            print("Token de acesso invalido ou expirado. Tente renova-lo na proxima tentativa.")
        elif e.response.status_code == 429:
            retry_after = int(e.response.headers.get("Retry-After", 1))
            print(f"Limite de taxa excedido. Aguarde {retry_after} segundos antes de re-tentar.")
            time.sleep(retry_after) # Aguarda antes de retornar o erro, para o retry externo
        return (None, e.response.status_code)
    except requests.exceptions.RequestException as e:
        print(f"Erro de requisicao ao chamar a API: {e}")
        return (None, None)

# --- Logica Principal de Exemplo ---
if __name__ == "__main__":
    if not all([GHL_CLIENT_ID, GHL_CLIENT_SECRET, GHL_REDIRECT_URI, GHL_LOCATION_ID]):
        print("Erro: As variaveis de ambiente GHL_CLIENT_ID, GHL_CLIENT_SECRET, GHL_REDIRECT_URI e GHL_LOCATION_ID devem estar definidas.")
        print("Consulte o arquivo .env.example e o README.md para mais informacoes.")
        exit(1)

    # Dicionario para armazenar os dados do token atualmente em uso
    current_token_data = None

    # Tenta carregar tokens existentes
    stored_tokens = load_tokens()

    if stored_tokens:
        current_token_data = stored_tokens.copy() # Copia para manipular
        
        # Verifica se o token de acesso expirou ao carregar
        if 'expiry_timestamp' in current_token_data and datetime.now() >= current_token_data['expiry_timestamp']:
            print("Access Token expirado ao carregar. Tentando renovar...")
            refresh_token = current_token_data.get("refresh_token")
            if refresh_token:
                new_token_info = refresh_access_token(refresh_token)
                if new_token_info:
                    current_token_data.update(new_token_info) # Atualiza com os novos dados do token
                    expires_in = current_token_data.get("expires_in", 3600)
                    current_token_data['expiry_timestamp'] = datetime.now() + timedelta(seconds=expires_in - 300) # 5 minutos de buffer
                    save_tokens(current_token_data) # Salva os novos tokens
                else:
                    print("Falha ao renovar o token expirado. Requer nova autorizacao manual.")
                    current_token_data = None # Invalida tokens para forcar nova autorizacao se necessario
            else:
                print("Refresh Token nao disponivel. Requer nova autorizacao manual.")
                current_token_data = None
        else:
            print("Tokens carregados e ainda validos.")
            print(f"Access Token: {current_token_data.get('access_token', '')[:10]}...")
            print(f"Refresh Token: {current_token_data.get('refresh_token', '')[:10]}...")
            print(f"Escopos: {current_token_data.get('scope', 'N/A')}")
            print(f"Expirara em: {current_token_data.get('expiry_timestamp').strftime('%Y-%m-%d %H:%M:%S') if current_token_data.get('expiry_timestamp') else 'N/A'}")

    # Se nao houver tokens validos apos carregar/renovar, tenta obter com o codigo de autorizacao inicial
    if not current_token_data or not current_token_data.get("access_token"):
        initial_authorization_code = os.getenv("GHL_AUTHORIZATION_CODE")
        if initial_authorization_code:
            print(f"Nenhum token valido encontrado. Tentando obter com o Codigo de Autorizacao inicial: {initial_authorization_code[:10]}...")
            token_info = get_access_token(initial_authorization_code)
            if token_info:
                current_token_data = token_info.copy() # Inicia com os dados completos da API
                expires_in = current_token_data.get("expires_in", 3600)
                current_token_data['expiry_timestamp'] = datetime.now() + timedelta(seconds=expires_in - 300) # 5 minutos de buffer
                save_tokens(current_token_data) # Salva os tokens recem-obtidos
                print(f"Access Token: {current_token_data.get('access_token', '')[:10]}...")
                print(f"Refresh Token: {current_token_data.get('refresh_token', '')[:10]}...")
                print(f"Escopos: {current_token_data.get('scope', 'N/A')}")
                print(f"Expirara em: {current_token_data.get('expiry_timestamp').strftime('%Y-%m-%d %H:%M:%S') if current_token_data.get('expiry_timestamp') else 'N/A'}")
            else:
                print("Nao foi possivel obter tokens com o codigo de autorizacao inicial. Verifique o codigo e as credenciais.")
        else:
            print("Nenhum token valido e nenhum GHL_AUTHORIZATION_CODE fornecido para a autorizacao inicial.")
            print("Por favor, obtenha um codigo de autorizacao e defina GHL_AUTHORIZATION_CODE no seu .env.")

    # --- Exemplo de como usar os tokens para fazer chamadas a API com retry ---
    if current_token_data and current_token_data.get("access_token"):
        print("\n--- Testando chamada a API de Contatos com o Access Token atual (com retry) ---")
        access_token_for_call = current_token_data["access_token"]
        contacts_endpoint = "/contacts/"
        contacts_params = {"locationId": GHL_LOCATION_ID} # PARAMETRO OBRIGATORIO

        max_api_retries = 2 # Maximo de tentativas para a chamada da API (incluindo a primeira)
        api_call_succeeded = False
        
        for attempt in range(max_api_retries):
            print(f"Tentativa {attempt + 1}/{max_api_retries} para chamar {contacts_endpoint}...")
            contact_data, status_code = make_ghl_api_call(
                access_token=access_token_for_call,
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
                break # Sai do loop se a chamada for bem-sucedida
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
                        access_token_for_call = current_token_data["access_token"] # Usa o novo token para a proxima tentativa
                        print("Token renovado com sucesso. Re-tentando a chamada a API...")
                        # Nao precisa de sleep aqui, a proxima iteracao do loop sera imediata
                    else:
                        print("Falha ao renovar token. Nao e possivel continuar com as chamadas a API sem nova autorizacao.")
                        break # Nao ha como continuar sem um novo token
                else:
                    print("Refresh Token nao disponivel. Nao e possivel renovar automaticamente.")
                    break # Nao ha como renovar
            elif status_code == 429:
                print("Limite de taxa excedido. A funcao make_ghl_api_call ja implementa um sleep. Re-tentando...")
                # O sleep ja acontece dentro de make_ghl_api_call para 429
            else:
                print(f"Chamada a API falhou com status {status_code}. Nao ha logica de retry automatica para este erro.")
                break # Para outros erros, sai do loop

        if not api_call_succeeded:
            print("Chamada a API de Contatos falhou apos todas as tentativas.")
            
    else:
        print("\nNao foi possivel fazer chamadas a API sem um Access Token valido.")