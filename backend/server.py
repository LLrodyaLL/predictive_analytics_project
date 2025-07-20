from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import datetime
import pandas as pd
import re
import os
import joblib

MODEL_PATH = "model.pkl"
model = joblib.load(MODEL_PATH)

def predict_promotion(df: pd.DataFrame) -> pd.DataFrame:
    features = ["Рейтинг", "Заказы", "Количество отзывов на конец периода"]
    if not all(col in df.columns for col in features):
        raise ValueError("Не найдены необходимые колонки для ML-модели")

    preds = model.predict(df[features])
    df["ML_Продвигать"] = preds
    return df

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Папки
UPLOAD_DIR = "uploads"
PROCESSED_DIR = "processed"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

@app.post("/analyze-link/")
async def analyze_link(link: str = Query(..., description="Ссылка на товар")):
    try:
        # Извлекаем артикул из ссылки (например, https://www.wildberries.ru/catalog/12345678/detail.aspx)
        match = re.search(r'/catalog/(\d+)', link)
        article_id = match.group(1) if match else "Не найден"

        # Заглушка: симулированные данные товара
        fake_data = {
            "Рейтинг": 4.3,
            "Остатки": 60,
            "Время доставки": 48
        }

        df = pd.DataFrame([fake_data])
        df = predict_promotion(df)
        рекомендация = "Рекомендуется продвигать" if df["ML_Продвигать"].iloc[0] == 1 else "Не продвигать"

        return {
            "Артикул": article_id,
            "Рекомендация": рекомендация,
            "Данные": fake_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка анализа ссылки: {e}")


# Загрузка и обработка одного файла
@app.post("/upload-process/")
async def upload_and_process(file: UploadFile = File(...)):
    try:
        ext = file.filename.split(".")[-1]
        file_id = datetime.now().strftime("%Y%m%d%H%M%S")
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}.{ext}")

        with open(file_path, "wb") as f:
            f.write(await file.read())

        if ext == "csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        # Генерация рекомендаций
        df = predict_promotion(df)
        df["Рекомендация"] = df["ML_Продвигать"].apply(
            lambda x: "Рекомендуется продвигать" if x == 1 else "Не продвигать")

        processed_path = os.path.join(PROCESSED_DIR, f"processed_{file_id}.xlsx")
        df.to_excel(processed_path, index=False)

        return FileResponse(path=processed_path,
                            filename=f"processed_{file.filename}",
                            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {e}")


# Приём нескольких файлов: file_1, file_2, ..., file_5
@app.post("/merge-files/")
async def merge_custom_files(
    products: UploadFile = File(...),
    brands: UploadFile = File(...),
    suppliers: UploadFile = File(...),
    categories: UploadFile = File(...),
    trends: UploadFile = File(...),
    ads: UploadFile = File(...),
    seasonality: UploadFile = File(...),
):
    try:
        # Общие параметры чтения
        read_params = {
            'header': 4,
            'skiprows': 3
        }

        def read(file: UploadFile):
            ext = file.filename.split('.')[-1]
            if ext == 'csv':
                return pd.read_csv(file.file, **read_params)
            else:
                return pd.read_excel(file.file, **read_params)

        trends_df = read(trends)
        products_df = read(products)
        brands_df = read(brands)
        suppliers_df = read(suppliers)
        categories_df = read(categories)
        seasonality_df = read(seasonality)
        ads_df = read(ads)

        merged = products_df.merge(
            brands_df,
            on='Бренд',
            how='left',
            suffixes=('_товар', '_бренд')
        )

        merged = merged.merge(
            suppliers_df,
            on='Поставщик',
            how='left',
            suffixes=('', '_поставщик')
        )

        categories_renamed = categories_df.rename(columns={
            'Выручка': 'Выручка_категория',
            'Заказы': 'Заказы_категория',
            'Остатки на конец периода': 'Остатки_категория',
            'Средний чек': 'Средний_чек_категория',
            'Средняя цена без СПП': 'Средняя_цена_категория',
            'Упущенная выручка': 'Упущенная_выручка_категория',
            'Общая скидка без СПП': 'Общая_скидка_категория'
        })

        merged = merged.merge(
            categories_renamed,
            left_on='Предмет',
            right_on='Категория',
            how='left'
        )

        final_data = merged.merge(
            ads_df,
            on='Артикул',
            how='left',
            suffixes=('', '_реклама')
        )

        cols_to_keep = [col for col in final_data.columns if '_' not in col]
        final_data = final_data[cols_to_keep]

        final_data.dropna(axis=1, how='all', inplace=True)

        # Модель: прогноз продвижения
        final_data = predict_promotion(final_data)
        final_data["Рекомендация"] = final_data["ML_Продвигать"].apply(lambda x: "Рекомендуется продвигать" if x == 1 else "Не продвигать")

        file_id = datetime.now().strftime("%Y%m%d%H%M%S")
        out_path = os.path.join(PROCESSED_DIR, f"final_merged_{file_id}.xlsx")
        final_data.to_excel(out_path, index=False)

        return FileResponse(
            path=out_path,
            filename="Итоговая_таблица.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при объединении файлов: {e}")

