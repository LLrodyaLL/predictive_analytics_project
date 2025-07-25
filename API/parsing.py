"""
Этот модуль обрабатывает данные о товарах с API Wildbox и генерирует датасет
с различными признаками, включая видимость, время доставки и позиции товара.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from .wildbox_client import (
    get_product_details,
    get_brand_details,
    get_warehouse_positions,
    get_product_geo_visibility,
    get_all_warehouses_for_product,
    get_delivery_times,
    FO_LIST,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

REGION_LIST = '1,2,3,4,5,6,7,8,9,10'
REVENUE_THRESHOLDS = {
    'Золотой': 8709000,
    'Серебряный': 1868000,
    'Бронзовый': 382000,
    'Начальный': 50000
}


def get_average_geo_visibility(product_id: int) -> int:
    """Рассчитывает средний уровень видимости товара (0-2) на основе данных
    о доступности в регионах.

    Args:
        product_id (int): Идентификатор товара.

    Returns:
        int: Средний уровень видимости (0: недоступен, 1: частично доступен,
             2: доступен во всех регионах).
    """
    try:
        raw_data: Optional[Dict] = get_product_geo_visibility(
            product_id, REGION_LIST
        )
        if not raw_data or 'results' not in raw_data:
            return 0

        total_visibility = 0
        valid_regions = 0

        for entry in raw_data['results']:
            availabilities = entry.get('availability', [])
            total = len(availabilities)
            if total == 0:
                continue

            available = sum(
                1 for a in availabilities if a.get('is_availability') is True
            )
            total_visibility += 2 if available == total else 1 if available > 0 else 0
            valid_regions += 1

        if valid_regions == 0:
            return 0

        avg_vis = round(total_visibility / valid_regions)
        return min(max(avg_vis, 0), 2)

    except (ValueError, KeyError, TypeError) as e:
        logging.error("[%s] Ошибка расчета видимости: %s", product_id, e)
        return 0


def get_delivery_features(product_id: int, df_matrix: pd.DataFrame) -> Dict:
    """Возвращает время доставки по каждому федеральному округу (ФО)
    и среднее время доставки.

    Args:
        product_id (int): Идентификатор товара.
        df_matrix (pd.DataFrame): Логистическая матрица с временем доставки.

    Returns:
        dict: Словарь с временем доставки по ФО и средним временем доставки.
    """
    features = {f'delivery_{fo}': 0 for fo in FO_LIST}
    features['avg_delivery_time'] = 0

    try:
        if not isinstance(df_matrix, pd.DataFrame):
            raise ValueError("df_matrix должен быть DataFrame")
        delivery_times = get_delivery_times(product_id, df_matrix)
        valid_times = []

        for federal_district in FO_LIST:
            time = delivery_times.get(federal_district)
            if pd.notna(time) and time > 0:
                features[f'delivery_{federal_district}'] = int(time)
                valid_times.append(time)

        if valid_times:
            features['avg_delivery_time'] = int(np.mean(valid_times))

    except (ValueError, KeyError, TypeError) as e:
        logging.error("[%s] Ошибка расчета доставки: %s", product_id, e)

    return features


def extract_position_value(pos: Dict) -> Optional[float]:
    """Извлекает валидную позицию из словаря позиции.

    Args:
        pos (dict): Словарь с данными о позиции.

    Returns:
        Optional[float]: Числовая позиция или None, если позиция невалидна.
    """
    keys = ['expected_position', 'position', 'general_position', 'pos']
    for key in keys:
        if pos.get(key) is not None:
            try:
                pos_num = float(pos.get(key))
                if pos_num > 0:
                    return pos_num
            except (TypeError, ValueError):
                continue
    return None


def get_position_features(
    product_id: int, search_query: str
) -> Dict[str, Optional[float]]:
    """Получает данные о позициях товара в поиске.

    Args:
        product_id (int): Идентификатор товара.
        search_query (str): Поисковый запрос для складов.

    Returns:
        dict: Словарь с метриками позиций (средняя, ожидаемая, количество и т.д.).
    """
    features = {
        'avg_position': None,
        'expected_position': None,
        'positions_count': 0,
        'positions_found': 0,
        'first_valid_position': None
    }

    try:
        if not search_query or not isinstance(search_query, str):
            raise ValueError("Поисковый запрос не может быть пустым")
        positions = get_warehouse_positions(product_id, search_query)
        if not positions or not isinstance(positions, list):
            return features

        features['positions_found'] = len(positions)
        valid_positions = []

        for pos in positions:
            if not isinstance(pos, Dict):
                continue
            pos_num = extract_position_value(pos)
            if pos_num is not None:
                valid_positions.append(pos_num)
                if features['first_valid_position'] is None:
                    features['first_valid_position'] = pos_num
                if 'expected_position' in pos and pos['expected_position'] is not None:
                    features['expected_position'] = pos_num

        features['positions_count'] = len(valid_positions)
        if valid_positions:
            features['avg_position'] = round(np.mean(valid_positions), 1)
            if features['expected_position'] is None:
                features['expected_position'] = features['avg_position']

    except (ValueError, KeyError, TypeError) as e:
        logging.error("[%s] Ошибка получения позиций: %s", product_id, e)

    return features


def process_product_data(product_data: Dict) -> Dict:
    """Обрабатывает данные о товаре и возвращает соответствующие признаки.

    Args:
        product_data (dict): Данные о товаре из API.

    Returns:
        dict: Словарь с признаками товара.
    """
    revenue = product_data.get('proceeds', 0)
    features = {
        'orders': product_data.get('orders', 0),
        'revenue': revenue,
        'price': product_data.get('price', 0),
        'discount': product_data.get('discount', 0),
        'old_price': product_data.get('old_price', 0),
        'rating': product_data.get('rating', 0),
        'in_stock_percent': product_data.get('in_stock_percent', 0),
        'reviews_last_day': product_data.get(
            'reviews', product_data.get('feedbacks', 0)
        ),
        'loyalty_level': 'Нет данных'
    }

    for level, threshold in REVENUE_THRESHOLDS.items():
        if revenue >= threshold:
            features['loyalty_level'] = level
            break

    return features


def process_promos(promos: List[Dict]) -> Dict:
    """Обрабатывает данные об акциях и возвращает связанные признаки.

    Args:
        promos (list): Список акций.

    Returns:
        dict: Словарь с признаками акций.
    """
    features = {'has_promos': int(bool(promos)), 'promo_days': 0}
    promo_dates = set()

    for promo in promos:
        try:
            start = datetime.fromisoformat(promo['start_date'])
            end = datetime.fromisoformat(promo['end_date'])
            current = start
            while current <= end:
                promo_dates.add(current.date())
                current += timedelta(days=1)
        except (ValueError, KeyError):
            continue

    features['promo_days'] = len(promo_dates)
    return features


def extract_product_features(
    product_id: int, search_query: str, df_matrix: pd.DataFrame
) -> Dict:
    """Собирает все признаки товара, включая метрики по заказам, выручке,
    цене, рейтингу, акциям, бренду и логистике.

    Args:
        product_id (int): Идентификатор товара.
        search_query (str): Поисковый запрос для складов.
        df_matrix (pd.DataFrame): Логистическая матрица.

    Returns:
        dict: Словарь с признаками товара.
    """
    features = {
        'product_id': product_id,
        'query': search_query,
        'orders': 0,
        'revenue': 0,
        'price': 0,
        'discount': 0,
        'old_price': 0,
        'rating': 0,
        'in_stock_percent': 0,
        'has_promos': 0,
        'brand_rating': 0,
        'brand_reviews': 0,
        'reviews_last_day': 0,
        'promo_days': 0,
        'sum_views': 0,
        'avg_visibility': 0,
        'main_warehouse': 'Не определен',
        'avg_position': None,
        'expected_position': None,
        'positions_count': 0,
        'positions_found': 0,
        'first_valid_position': None,
        'loyalty_level': 'Нет данных'
    }

    try:
        product_data = get_product_details(product_id)
        if product_data:
            features.update(process_product_data(product_data))
            features.update(process_promos(product_data.get('promos', [])))
            if 'brand' in product_data and isinstance(product_data['brand'], Dict):
                brand_data = get_brand_details(product_data['brand'].get('id'))
                if brand_data:
                    features.update({
                        'brand_rating': brand_data.get('rating', 0),
                        'brand_reviews': brand_data.get('reviews', 0),
                    })
            dynamic_data = product_data.get('dynamic', [])
            if dynamic_data:
                features['sum_views'] = sum(
                    day.get('visibility', 0)
                    for day in dynamic_data
                    if isinstance(day, Dict)
                )

    except (ValueError, KeyError, TypeError) as e:
        logging.error("[Error] get_product_details %s: %s", product_id, e)

    features['avg_visibility'] = get_average_geo_visibility(product_id)
    features.update(get_delivery_features(product_id, df_matrix))

    try:
        warehouses = get_all_warehouses_for_product(product_id)
        if warehouses:
            features['main_warehouse'] = warehouses[0]
    except (ValueError, KeyError, TypeError) as e:
        logging.error("[%s] Ошибка получения складов: %s", product_id, e)

    features.update(get_position_features(product_id, search_query))
    return features


def create_dataset(
    product_ids: List[int], search_queries: List[str], matrix_path: str
) -> pd.DataFrame:
    """Создает датасет из данных о товарах и матрицы логистики.

    Args:
        product_ids (list): Список идентификаторов товаров.
        search_queries (list): Список поисковых запросов.
        matrix_path (str): Путь к файлу с матрицей логистики.

    Returns:
        pd.DataFrame: Датасет с признаками товаров.
    """
    if len(product_ids) != len(search_queries):
        raise ValueError(
            "Количество product_ids и search_queries должно совпадать"
        )

    try:
        df_matrix = pd.read_excel(matrix_path)
    except (FileNotFoundError, pd.errors.ParserError) as e:
        logging.error("❌ Не удалось загрузить матрицу логистики: %s", e)
        sys.exit(1)

    dataset = []
    for pid, query in zip(product_ids, search_queries):
        logging.info("▶️ Обработка артикула %s...", pid)
        try:
            row = extract_product_features(pid, query, df_matrix)
            dataset.append(row)
        except (ValueError, KeyError, TypeError) as e:
            logging.error("[Error] while processing product %s: %s", pid, e)

    return pd.DataFrame(dataset)


if __name__ == "__main__":
    products = [
        (430328428, "футболка мужская"),
    ]

    product_ids_list = [p[0] for p in products]
    queries = [p[1] for p in products]

    MATRIX_PATH = "logistics_matrix_filtered.xlsx"

    df_new = create_dataset(product_ids_list, queries, MATRIX_PATH)

    column_rename_map = {
        'product_id': 'ID товара',
        'query': 'Поисковый запрос',
        'orders': 'Заказы',
        'revenue': 'Выручка',
        'price': 'Цена',
        'discount': 'Скидка',
        'old_price': 'Старая цена',
        'rating': 'Рейтинг',
        'in_stock_percent': 'Наличие (%)',
        'has_promos': 'Участвует в акциях',
        'brand_rating': 'Рейтинг продавца',
        'brand_reviews': 'Отзывы о бренде',
        'reviews_last_day': 'Количество отзывов',
        'sum_views': 'Количество показов',
        'promo_days': 'Дней в акциях',
        'avg_visibility': 'Средняя видимость',
        'avg_delivery_time': 'Ср время доставки (ч)',
        'main_warehouse': 'Основной склад',
        'avg_position': 'Средняя позиция',
        'expected_position': 'Ожидаемая позиция',
        'positions_count': 'Количество позиций',
        'loyalty_level': 'Уровень лояльности'
    }

    for fo in FO_LIST:
        column_rename_map[f'delivery_{fo}'] = f'Доставка_{fo}_(ч)'

    df_new.rename(columns=column_rename_map, inplace=True)

    OUTPUT_PATH = "Dataset1.csv"

    if os.path.exists(OUTPUT_PATH) and os.path.getsize(OUTPUT_PATH) > 0:
        try:
            df_existing = pd.read_csv(OUTPUT_PATH, encoding='utf-8-sig')
            df_final = pd.concat(
                [df_existing, df_new]
            ).drop_duplicates(['ID товара', 'Поисковый запрос'])
        except pd.errors.EmptyDataError:
            df_final = df_new
    else:
        df_final = df_new

    final_columns = [
        'Заказы', 'Выручка', 'Цена', 'Скидка', 'Рейтинг', 'Наличие (%)',
        'Рейтинг продавца', 'Отзывы о бренде', 'Дней в акциях',
        'Средняя видимость', 'Основной склад', 'Уровень лояльности',
        'Доставка_ЮФО_(ч)', 'Доставка_ПФО_(ч)', 'Доставка_УФО_(ч)',
        'Доставка_ДФО_(ч)', 'Доставка_СФО_(ч)', 'Доставка_СЗФО_(ч)',
        'Доставка_ЦФО_(ч)', 'Ср время доставки (ч)', 'Количество показов',
        'Участвует в акциях', 'Количество отзывов'
    ]

    df_final = df_final[[col for col in final_columns if col in df_final.columns]]

    df_final.to_csv(OUTPUT_PATH, index=False, encoding='utf-8-sig')
    logging.info("✅ Датасет сохранен в %s", OUTPUT_PATH)
    