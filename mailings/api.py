import requests
from typing import Optional, List, Dict, Any
from django.conf import settings

AUTH_URL = getattr(settings, 'AUTH_URL', '')                
AUTH_KEY = getattr(settings, 'AUTH_KEY', '')
AUTH_PROVIDER = getattr(settings, 'AUTH_PROVIDER', '')
AUTH_PASSWORD = getattr(settings, 'AUTH_PASSWORD', '')

def auth_request() -> str:
    """
    POST запрос для авторизации
        
    Returns:
        str: token из ответа сервера
    """
    headers = {
        "Content-Type": "application/json",
        "fingerprint": "tg_bot"
    }
    
    payload = {
        "key": AUTH_KEY,
        "password": AUTH_PASSWORD,
        "provider": AUTH_PROVIDER
    }
    
    try:
        response = requests.post(
            url=f"{AUTH_URL}/auth/login",
            json=payload,
            headers=headers
        )
        
        if response.status_code in [200, 201]:
            return response.json().get('accessToken')
            
        error_data = response.json()
        raise Exception(f"Ошибка авторизации: {error_data}")
                
    except Exception as e:
        print(f"Ошибка при выполнении запроса на авторизацию: {str(e)}")
        raise

def get_available_filters() -> List[Dict[str, Any]]:
    """
    GET запрос для получения доступных фильтров
    
    Returns:
        List[Dict]: Список фильтров в формате:
        {
            "name": str,
            "label": str,
            "type": str,
            "choices": List[str]
        }
    """
    token = auth_request()
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            url=f"{AUTH_URL}/users/available-filters",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
            
        error_data = response.json()
        raise Exception(f"Ошибка получения фильтров: {error_data}")
            
    except Exception as e:
        print(f"Ошибка при выполнении запроса фильтров: {str(e)}")
        raise

def get_filtered_users(filters: Dict[str, Any], page: int = 1, limit: int = 100) -> Dict[str, Any]:
    token = auth_request()
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "page": page,
        "limit": limit
    }
    
    request_data = {
        "additionalProperties": filters
    }
    
    try:
        response = requests.post(
            url=f"{AUTH_URL}/users/filter",
            json=request_data,
            params=params,
            headers=headers
        )
        
        if response.status_code == 201:
            return response.json()
        elif response.status_code == 400:
            error_data = response.json()
            raise Exception(f"Неверные параметры запроса: {error_data}")
            
        error_data = response.json()
        raise Exception(f"Ошибка получения пользователей: {error_data}")
            
    except Exception as e:
        print(f"Ошибка при выполнении запроса пользователей: {str(e)}")
        raise