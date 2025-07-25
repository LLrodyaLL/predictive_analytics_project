"""
Модуль `server.py` — основной backend-компонент FastAPI-приложения для анализа товаров Wildberries.

Этот модуль реализует следующие функции:
- Обработка входных запросов от пользователей (`submit-request`).
- Получение данных о товаре по артикулу и поисковому запросу.
- Генерация признаков и подготовка данных для модели.
- Получение рекомендаций по улучшению товарной позиции (`get-recommendation`) с использованием модели CatBoost.
- Работа с пользовательскими регионами и фильтрами.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime
import pandas as pd
import subprocess
import sys
import os

from API.parsing import extract_product_features

MODEL_PATH = "WB_model.cbm"
MATRIX_PATH = "ml_model/dataset/logistics_matrix_filtered.xlsx"

REGION_MAPPING = {
    "МОСКВА - ЦФО": "Центральный",
    "САНКТ-ПЕТЕРБУРГ - СЗФО": "Северо-Западный",
    "КРАСНОДАР - ЮФО": "Южный",
    "КАЗАНЬ - ПФО": "Приволжский",
    "ЕКАТЕРИНБУРГ - УФО": "Уральский",
    "НОВОСИБИРСК - СФО": "Сибирский",
    "ХАБАРОВСК - ДФО": "Дальневосточный"
}

CITY_MAPPING = {
    "Центральный": "Москва",
    "Северо-Западный": "Санкт-Петербург",
    "Южный": "Краснодар",
    "Приволжский": "Казань",
    "Уральский": "Екатеринбург",
    "Сибирский": "Новосибирск",
    "Дальневосточный": "Хабаровск"
}

FEDERAL_DISTRICTS = list(CITY_MAPPING.keys())

app = FastAPI(title="WB Full Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserRequest(BaseModel):
    """
    Модель входного запроса от пользователя.

    Attributes:
        article (str): Артикул товара.
        region (str): Регион пользователя.
        query (str): Поисковый запрос.
    """
    article: str = Field(..., example="393594116")
    region: str = Field(..., example="МОСКВА - ЦФО")
    query: str = Field(..., example="футболка мужская")


last_product_df = None


@app.get("/region-options/")
async def get_region_options():
    """
    Получение доступных регионов для выбора на фронтенде.

    Returns:
        list[str]: Список регионов.
    """
    return list(REGION_MAPPING.keys())


@app.post("/submit-request/")
async def submit_user_request(payload: UserRequest):
    """
    Обрабатывает запрос пользователя, извлекает признаки товара,
    сохраняет их для последующей рекомендации.

    Args:
        payload (UserRequest): Данные запроса с артикулом, регионом и запросом.

    Returns:
        dict: Данные о товаре и информация для рекомендаций.
    """
    global last_product_df

    mapped_region = REGION_MAPPING.get(payload.region, payload.region)
    city = CITY_MAPPING.get(mapped_region)

    if not payload.article.isdigit():
        raise HTTPException(status_code=400,
                            detail="Артикул должен быть числом")
    if mapped_region not in FEDERAL_DISTRICTS or not city:
        raise HTTPException(status_code=400,
                            detail="Неверный регион")

    product_id = int(payload.article)

    try:
        df_matrix = pd.read_excel(MATRIX_PATH)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Не удалось загрузить логистическую матрицу"
        )

    try:
        product_data = extract_product_features(product_id,
                                                payload.query,
                                                df_matrix)

        field_mapping = {
            "orders": "Заказы",
            "revenue": "Выручка",
            "price": "Цена",
            "discount": "Скидка",
            "rating": "Рейтинг",
            "in_stock_percent": "Наличие (%)",
            "brand_rating": "Рейтинг продавца",
            "brand_reviews": "Отзывы о бренде",
            "promo_days": "Дней в акциях",
            "avg_visibility": "Средняя видимость",
            "main_warehouse": "Основной склад",
            "loyalty_level": "Уровень лояльности",
            "delivery_ЮФО": "Доставка_ЮФО_(ч)",
            "delivery_ПФО": "Доставка_ПФО_(ч)",
            "delivery_УФО": "Доставка_УФО_(ч)",
            "delivery_ДФО": "Доставка_ДФО_(ч)",
            "delivery_СФО": "Доставка_СФО_(ч)",
            "delivery_СЗФО": "Доставка_СЗФО_(ч)",
            "delivery_ЦФО": "Доставка_ЦФО_(ч)",
            "avg_delivery_time": "Ср время доставки (ч)",
            "sum_views": "Количество показов",
            "has_promos": "Участвует в акциях",
            "reviews_last_day": "Количество отзывов"
        }

        renamed_data = {
            field_mapping[k]: v
            for k, v in product_data.items()
            if k in field_mapping
        }
        last_product_df = pd.DataFrame([renamed_data])

    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Ошибка при обработке артикула: {e}")

    return {
        "datetime": datetime.now().isoformat(),
        "article": payload.article,
        "region": payload.region,
        "query": payload.query,
        "product_data": renamed_data,
        "recommendation": None
    }


@app.get("/get-recommendation/")
def get_recommendation():
    """
    Возвращает рекомендации на основе ранее отправленных данных.

    Returns:
        dict: Текст сгенерированных рекомендаций или сообщение об ошибке.
    """
    if last_product_df is None:
        raise HTTPException(
            status_code=400,
            detail="Сначала отправьте запрос через /submit-request"
        )

    try:
        temp_path = "temp_reco.csv"
        last_product_df.to_csv(temp_path, index=False, encoding="utf-8-sig")

        model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ml_model", "recomendation.py"))

        process = subprocess.Popen(
            [sys.executable, model_path, temp_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        output, error = process.communicate()

        os.remove(temp_path)

        if error:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка выполнения recomendation.py: {error}"
            )

        output = output.strip()

        return {
            "recommendation": output or "Рекомендации найдены, но текст пустой"
        }


    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
