"""
Аналитический скрипт для оценки позиции товара на маркетплейсе Wildberries
и генерации рекомендаций по улучшению на основе предсказаний модели CatBoost.

Функциональность:
- Загрузка модели и данных по товару
- Предсказание текущей позиции
- Оценка метрик и рекомендаций
- Определение слабых мест по регионам доставки
- Итоговый отчет

Формат входных данных: CSV с одним товаром.
"""

from catboost import CatBoostRegressor, Pool
import pandas as pd
import sys
from pathlib import Path


# === Настройки ===
MODEL_PATH = Path(__file__).parent / "WB_model.cbm"
DATA_PATH = sys.argv[1] if len(sys.argv) > 1 else "Dataset1.csv"
# DATA_PATH = "product3.csv"  # Путь к входным данным
CAT_FEATURES = ["Основной склад",
                "Уровень лояльности"]  # Категориальные признаки

# Параметры для настройки
TUNABLE_FEATURES = {
    "Цена": {"delta": -100, "min": 0, "max": None},
    "Скидка": {"delta": 5, "min": 0, "max": 70},
    "Рейтинг": {"delta": 0.1, "min": 0, "max": 5},
    "Наличие (%)": {"delta": 5, "min": 0, "max": 100},
    "Дней в акциях": {"delta": 5, "min": 0, "max": 31},
    "Средняя видимость": {"delta": 0.05, "min": 0, "max": 1},
    "Количество отзывов": {"delta": 10, "min": 0, "max": None},
    "Ср время доставки (ч)": {"delta": -1, "min": 20, "max": None},
    "Доставка_ЮФО_(ч)": {"delta": -2, "min": 20, "max": None},
    "Доставка_ПФО_(ч)": {"delta": -2, "min": 20, "max": None},
    "Доставка_ЦФО_(ч)": {"delta": -2, "min": 20, "max": None}
}

# Названия параметров для отображения
FEATURE_NAMES = {
    "Цена": "Цена товара",
    "Скидка": "Размер скидки",
    "Рейтинг": "Рейтинг товара",
    "Наличие (%)": "Уровень наличия",
    "Дней в акциях": "Дни в акциях",
    "Средняя видимость": "Видимость товара",
    "Количество отзывов": "Количество отзывов",
    "Ср время доставки (ч)": "Среднее время доставки",
    "Доставка_ЮФО_(ч)": "Доставка в ЮФО",
    "Доставка_ПФО_(ч)": "Доставка в ПФО",
    "Доставка_ЦФО_(ч)": "Доставка в ЦФО"
}

# === Загрузка данных и модели ===
model = CatBoostRegressor()
model.load_model(MODEL_PATH)
df = pd.read_csv(DATA_PATH)

if len(df) != 1:
    print("Ошибка: В данных должен быть ровно один товар")
    exit()

# Предсказание позиции
current_position = model.predict(Pool(df, cat_features=CAT_FEATURES))[0]
print(f"Текущая позиция товара: {int(current_position)}\n")

# === Анализ показателей ===
print("--- Анализ текущих показателей ---")


def get_status(value, good, bad):
    """
    Возвращает статус метрики товара по заданным порогам.

    Args:
        value (float): Значение метрики
        good (float): Порог, выше которого считается хорошим
        bad (float): Порог, ниже которого требуется улучшение

    Returns:
        str: Оценка метрики ("Хорошо", "Норма", "Требует улучшения")
    """
    if value >= good:
        return "Хорошо"
    if value <= bad:
        return "Требует улучшения"
    return "Норма"


metrics = [
    ("Рейтинг", 4.5, 3.5),
    ("Наличие (%)", 95, 70),
    ("Скидка", 30, 10),
    ("Количество отзывов", 1000, 100),
    ("Ср время доставки (ч)", 48, 72),
    ("Дней в акциях", 15, 5)
]

for metric in metrics:
    if metric[0] in df.columns:
        value = df.at[0, metric[0]]
        status = get_status(value, metric[1], metric[2])
        print(f"{FEATURE_NAMES.get(metric[0], metric[0])}: {value} ({status})")

# === Генерация рекомендаций ===
print("\n--- Рекомендации по улучшению ---")

df_copy = df.copy()
recommendations = []

for feature, params in TUNABLE_FEATURES.items():
    if feature not in df.columns:
        continue

    original = df.at[0, feature]
    delta = params["delta"]
    new_value = original + delta

    if params["min"] is not None and new_value < params["min"]:
        new_value = params["min"]
    if params["max"] is not None and new_value > params["max"]:
        new_value = params["max"]

    if new_value == original:
        continue

    df_copy[feature] = df_copy[feature].astype(float)
    df_copy.at[0, feature] = new_value

    new_pos = model.predict(Pool(df_copy, cat_features=CAT_FEATURES))[0]
    improvement = current_position - new_pos

    if improvement > 0:
        recommendations.append({
            "feature": feature,
            "original": original,
            "new": new_value,
            "improvement": improvement
        })

    df_copy.at[0, feature] = original

recommendations.sort(key=lambda x: -x["improvement"])

for i, rec in enumerate(recommendations[:5], 1):
    feature_name = FEATURE_NAMES.get(rec["feature"], rec["feature"])
    print(f"\nРекомендация {i}: {feature_name}")
    print(f"Текущее значение: {rec['original']}")
    print(f"Рекомендуемое значение: {rec['new']}")
    print(f"Ожидаемый прирост позиции: +{int(rec['improvement'])} пунктов")

# === Анализ доставки ===
print("\n--- Анализ времени доставки ---")
delivery_cols = [c for c in df.columns
                 if c.startswith("Доставка_") and c.endswith("(ч)")]
if delivery_cols:
    regions = []
    for col in delivery_cols:
        region = col.split("_")[1]
        hours = df.at[0, col]
        regions.append((region, hours))

    regions.sort(key=lambda x: -x[1])

    print("Время доставки по регионам:")
    for region, hours in regions:
        print(f"- {region}: {hours} часов")

    worst = regions[0]
    print(f"\nНаибольшие проблемы с доставкой в {worst[0]} ({worst[1]} часов)")
    print("Рекомендации:")
    print(f"- Оптимизировать логистику в {worst[0]}")
    print(f"- Рассмотреть дополнительные склады в {worst[0]}")
    print(f"- Целевой показатель: {worst[1] - 5} часов")

# === Итоговый отчет ===
print("\n--- Итоговый отчет ---")
print(f"Текущая позиция: {int(current_position)}")
print("Лучшие возможности для улучшения:")

top_3 = recommendations[:3]
total_improvement = sum(r["improvement"] for r in top_3)

for i, rec in enumerate(top_3, 1):
    feature_name = FEATURE_NAMES.get(rec["feature"], rec["feature"])
    print(f"{i}. {feature_name}: +{int(rec['improvement'])} пунктов")

print(f"\nСуммарный потенциальный прирост: +{int(total_improvement)} пунктов")

if total_improvement >= 1000:
    print("\nВывод: Значительное улучшение позиции возможно")
else:
    print("\nВывод: Для большего эффекта требуются дополнительные меры")

print("\nРекомендуемый план действий:")
print("1. Оптимизировать участие в акциях")
print("2. Настроить ценовую политику")
print("3. Улучшить логистику в проблемных регионах")
print("4. Запустить кампанию по сбору отзывов")
