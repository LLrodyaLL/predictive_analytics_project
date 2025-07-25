"""
Модуль для взаимодействия с API Wildbox, включая получение данных о товарах, брендах, складах и позиции товара по регионам.
"""

import os
from datetime import datetime, timedelta
import urllib.parse
import requests
from dotenv import load_dotenv
import pandas as pd


load_dotenv()

# Получение переменных окружения
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
COMPANY_ID = os.getenv("COMPANY_ID")
USER_ID = os.getenv("USER_ID")
COOKIE_STRING = os.getenv("COOKIE_STRING")

# Проверка наличия всех переменных окружения
if not all([AUTH_TOKEN, COMPANY_ID, USER_ID, COOKIE_STRING]):
    raise ValueError("Необходимо задать все переменные окружения в .env файле (AUTH_TOKEN, COMPANY_ID, USER_ID, COOKIE_STRING)")

# Заголовки для запросов
HEADERS = {
    'Authorization': AUTH_TOKEN,
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'CompanyID': COMPANY_ID,
    'UserID': USER_ID,
    'Referer': 'https://wildbox.ru/dashboard/search-tops-analysis/formed',
    'Sec-Fetch-Dest': 'empty', 
    'Sec-Fetch-Mode': 'cors', 
    'Sec-Fetch-Site': 'same-origin',
    'Time-Zone': 'Europe/Moscow',
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
    )
}

# Преобразование строки cookie в словарь
COOKIES = {cookie.split('=')[0]: cookie.split('=')[1] for cookie in COOKIE_STRING.split('; ')}

# Даты для фильтрации
DATE_TO = datetime.now().strftime('%Y-%m-%d')
DATE_FROM = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

# Склады по умолчанию
FALLBACK_WAREHOUSES = ["Подольск", "Коледино", "Электросталь", "Казань"]

# Сопоставление гео-ID → Федеральные округа
GEO_ID_TO_FO = {
    '1': 'ЮФО',
    '2': 'ПФО',
    '3': 'УФО',
    '4': 'ДФО',
    '5': 'СФО',
    '6': 'СЗФО',
    '7': 'ЦФО'
}
FO_LIST = list(GEO_ID_TO_FO.values())


def get_product_details(product_id: int) -> dict:
    """
    Получает детальную информацию по одному товару.

    Args:
        product_id (int): Идентификатор товара.

    Returns:
        dict: Детальная информация о товаре.
    """
    url = "https://wildbox.ru/api/wb_dynamic/products/"
    extra_fields = ','.join([
        'orders', 'proceeds', 'in_stock_percent', 'quantity', 'price', 'discount',
        'old_price', 'rating', 'reviews', 'feedbacks', 'visibility_dynamic', 
        'rating_dynamic', 'expected_position', 'promos', 'sales_speed', 'brand',
        'seller', 'images'
    ])
    params = {
        'product_ids': product_id,
        'date_from': DATE_FROM,
        'date_to': DATE_TO,
        'extra_fields': extra_fields
    }
    try:
        response = requests.get(url, headers=HEADERS, cookies=COOKIES, params=params, timeout=30)
        response.raise_for_status()
        results = response.json().get('results', [])
        return results[0] if results else {}
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении деталей товара {product_id}: {e}")
        return {}


def get_brand_details(brand_id: int) -> dict:
    """
    Получает информацию по бренду.

    Args:
        brand_id (int): Идентификатор бренда.

    Returns:
        dict: Информация о бренде.
    """
    url = "https://wildbox.ru/api/wb_dynamic/brands/"
    params = {
        'brand_ids': brand_id,
        'date_from': DATE_FROM,
        'date_to': DATE_TO,
        'extra_fields': 'rating,reviews,seller_rating,proceeds'
    }
    try:
        response = requests.get(url, headers=HEADERS, cookies=COOKIES, params=params, timeout=30)
        response.raise_for_status()
        results = response.json().get('results', [])
        return results[0] if results else {}
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении данных бренда {brand_id}: {e}")
        return {}


def get_warehouse_positions(product_id, search_query):
    """
    Получает позиции товара по городам по конкретному запросу.

    Args:
        product_id (int): Идентификатор товара.
        search_query (str): Запрос для поиска товара.

    Returns:
        list: Список позиций товара.
    """
    print(f"[API Client] Запрос позиций по складам для товара ID: {product_id}")
    url = "https://wildbox.ru/api/monitoring/positions/"

    encoded_phrase = urllib.parse.quote(search_query, safe='')

    params = {'product_id': product_id, 'phrase': search_query, 'pages_max': 30}

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Authorization': AUTH_TOKEN,
        'CompanyID': COMPANY_ID,
        'Connection': 'keep-alive',
        'Referer': f'https://wildbox.ru/dashboard/position/formed?product_id={product_id}&phrase={encoded_phrase}',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Time-Zone': 'Europe/Moscow',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'UserID': USER_ID,
        'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"'
    }

    try:
        encoded_params = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        full_url = f"{url}?{encoded_params}"

        print(f"[API Client] Полный URL: {full_url}")
        print(f"[API Client] Заголовки: {headers}")

        response = requests.get(full_url, headers=headers, cookies=COOKIES, timeout=45)

        print(f"[API Client] Статус ответа: {response.status_code}")
        print(f"[API Client] Заголовки ответа: {dict(response.headers)}")
        print(f"[API Client] Текст ответа (первые 500 символов): {response.text[:500]}")

        if response.status_code == 404:
            print("  -> Внимание: Эндпоинт позиций вернул ошибку 404 (Not Found).")
            return []

        if response.status_code == 403:
            print("  -> Ошибка авторизации 403. Проверьте токен и права доступа.")
            return []

        response.raise_for_status()

        try:
            data = response.json()
        except ValueError as e:
            print(f"  -> Ошибка парсинга JSON: {e}")
            print(f"  -> Полный текст ответа: {response.text}")
            return []

        print(f"[API Client] Тип данных: {type(data)}")
        print(f"[API Client] Получено записей: {len(data) if isinstance(data, list) else 'не список'}")
        print(f"[API Client] Данные: {data}")

        if isinstance(data, dict) and data.get('detail'):
            print(f"  -> API вернул деталь: {data['detail']}")
            return []

        return data

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе позиций по складам {product_id}: {e}")
        return []


def get_product_geo_visibility(product_id: int, geolocation_ids: str) -> dict:
    """
    Получает информацию о гео-видимости товара.

    Args:
        product_id (int): Идентификатор товара.
        geolocation_ids (str): Идентификаторы геолокаций.

    Returns:
        dict: Информация о гео-видимости.
    """
    url = f"https://wildbox.ru/api/parsers/products/{product_id}/availability/"
    params = {
        'product_id': product_id,
        'geolocation_ids': geolocation_ids,
        'limit': 10,
        'offset': 0
    }
    try:
        response = requests.get(url, headers=HEADERS, cookies=COOKIES, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе по гео-видимости товара ID {product_id}: {e}")
        return {}


def get_all_warehouses_for_product(product_id: int) -> list:
    """
    Получает все склады для товара.

    Args:
        product_id (int): Идентификатор товара.

    Returns:
        list: Список складов.
    """
    url = "https://wildbox.ru/api/wb_dynamic/warehouses/"
    params = {
        'product_ids': product_id,
        'date_from': DATE_FROM,
        'date_to': DATE_TO,
        'extra_fields': 'name,quantity',
        'limit': 1000
    }
    try:
        r = requests.get(url, headers=HEADERS, cookies=COOKIES, params=params, timeout=30)
        r.raise_for_status()
        return list({w.get("name") for w in r.json() if w.get("name")})
    except requests.exceptions.RequestException as e:
        print(f"[{product_id}] Ошибка складов:", e)
        return []


def get_delivery_times(product_id: int, df_matrix: pd.DataFrame) -> dict:
    """
    Получает время доставки для товара.

    Args:
        product_id (int): Идентификатор товара.
        df_matrix (pd.DataFrame): Данные о складах и времени доставки.

    Returns:
        dict: Время доставки.
    """
    warehouses = get_all_warehouses_for_product(product_id)
    filtered = df_matrix[df_matrix['Склад'].isin(warehouses)]
    if filtered.empty:
        filtered = df_matrix[df_matrix['Склад'].isin(FALLBACK_WAREHOUSES)]
    cleaned = filtered.drop(columns=['Федеральный округ'])
    numeric = cleaned.drop(columns=['Склад']).map(lambda x: x if x > 1 else None)
    return numeric.min().to_dict()
