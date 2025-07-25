from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime
import os
import sys
import json
import pandas as pd
import catboost
import subprocess
from pathlib import Path


from parsing import extract_product_features

# --- Константы ---
MODEL_PATH = "WB_model.cbm"
MATRIX_PATH = "logistics_matrix_filtered.xlsx"
HISTORY_DIR = "history"
os.makedirs(HISTORY_DIR, exist_ok=True)

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

# --- Инициализация приложения ---
app = FastAPI(title="WB Full Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic модели ---
class UserRequest(BaseModel):
    article: str = Field(..., example="393594116")
    region: str = Field(..., example="МОСКВА - ЦФО")
    query: str = Field(..., example="футболка мужская")


class RecommendationRequest(BaseModel):
    article: str
    region: str
    query: str
    product_data: dict


# --- Вспомогательные функции ---
def save_to_individual_history(payload: dict):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    filename = f"history_{timestamp}.json"
    path = os.path.join(HISTORY_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def load_all_history():
    history = []
    for file in os.listdir(HISTORY_DIR):
        if file.endswith(".json"):
            path = os.path.join(HISTORY_DIR, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    history.append(json.load(f))
            except Exception:
                continue
    return history


# --- Эндпоинты ---
@app.get("/region-options/")
async def get_region_options():
    return list(REGION_MAPPING.keys())


@app.post("/submit-request/")
async def submit_user_request(payload: UserRequest):
    mapped_region = REGION_MAPPING.get(payload.region, payload.region)
    city = CITY_MAPPING.get(mapped_region)

    if not payload.article.isdigit():
        raise HTTPException(status_code=400, detail="Артикул должен быть числом")
    if mapped_region not in FEDERAL_DISTRICTS or not city:
        raise HTTPException(status_code=400, detail="Неверный регион")

    product_id = int(payload.article)

    try:
        df_matrix = pd.read_excel(MATRIX_PATH)
    except Exception:
        raise HTTPException(status_code=500, detail="Не удалось загрузить логистическую матрицу")

    try:
        product_data = extract_product_features(product_id, payload.query, df_matrix)

        # Фильтрация нужных полей
        desired_fields = [
            "orders", "revenue", "price", "discount", "rating", "in_stock_percent",
            "brand_rating", "brand_reviews", "promo_days", "avg_visibility",
            "main_warehouse", "loyalty_level", "delivery_ЮФО", "delivery_ПФО",
            "delivery_УФО", "delivery_ДФО", "delivery_СФО", "delivery_СЗФО",
            "delivery_ЦФО", "avg_delivery_time", "sum_views", "has_promos", "reviews_last_day"
        ]

        product_data = {k: v for k, v in product_data.items() if k in desired_fields}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке артикула: {e}")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    record = {
        "datetime": datetime.now().isoformat(),
        "article": payload.article,
        "region": payload.region,
        "query": payload.query,
        "product_data": product_data,
        "recommendation": None
    }
    save_to_individual_history(record)

    # --- Дополнительно сохраняем в CSV для get-recommendation ---
    csv_fields_order = [
        "Заказы", "Выручка", "Цена", "Скидка", "Рейтинг", "Наличие (%)",
        "Рейтинг продавца", "Отзывы о бренде", "Дней в акциях", "Средняя видимость",
        "Основной склад", "Уровень лояльности", "Доставка_ЮФО_(ч)", "Доставка_ПФО_(ч)",
        "Доставка_УФО_(ч)", "Доставка_ДФО_(ч)", "Доставка_СФО_(ч)", "Доставка_СЗФО_(ч)",
        "Доставка_ЦФО_(ч)", "Ср время доставки (ч)", "Количество показов",
        "Участвует в акциях", "Количество отзывов"
    ]

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

    renamed_data = {field_mapping[k]: v for k, v in product_data.items() if k in field_mapping}
    df_row = pd.DataFrame([renamed_data])
    csv_path = os.path.join(HISTORY_DIR, f"history_{timestamp}.csv")

    try:
        df_row = df_row[[col for col in csv_fields_order if col in df_row.columns]]
        df_row.to_csv(csv_path, index=False, encoding="utf-8-sig")
    except Exception as e:
        print(f"[Ошибка сохранения CSV] {e}")

    return record


@app.get("/get-recommendation/")
def get_recommendation():
    try:
        # Найдём последний созданный CSV в history/
        csv_files = sorted(Path("history").glob("*.csv"), key=os.path.getmtime, reverse=True)
        if not csv_files:
            raise HTTPException(status_code=404, detail="Нет CSV-файлов в папке history")

        csv_path = str(csv_files[0])

        # Запускаем recomendation.py как subprocess
        process = subprocess.Popen(
            [sys.executable, "recomendation.py", csv_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        output, error = process.communicate()

        if error:
            raise HTTPException(status_code=500, detail=f"Ошибка выполнения recomendation.py: {error}")

        # Извлечём блок "Рекомендуемый план действий" и всё, что после
        recommendation_lines = []
        capture = False
        for line in output.splitlines():
            if "Рекомендуемый план действий" in line:
                capture = True
                recommendation_lines.append(line.strip())
                continue
            if capture:
                if line.strip() == "":
                    continue
                recommendation_lines.append(line.strip())

        recommendation_text = "\n".join(recommendation_lines)
        return {"recommendation": recommendation_text or "Рекомендации найдены, но текст пустой"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

