"""
Модуль тестов для backend API (FastAPI).

Тестирует основные эндпоинты:
- /region-options/
- /submit-request/
- /get-recommendation/
"""

import pytest
from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)


@pytest.mark.parametrize("region", [
    "МОСКВА - ЦФО", "САНКТ-ПЕТЕРБУРГ - СЗФО", "КРАСНОДАР - ЮФО"
])
def test_get_region_options(region):
    """
    Проверяет, что список регионов содержит указанный регион.

    Args:
        region (str): Название региона для проверки.
    """
    response = client.get("/region-options/")
    assert response.status_code == 200
    assert region in response.json()


def test_submit_request_success():
    """
    Проверяет успешную обработку запроса с корректными параметрами.

    Проверяет:
    - Статус ответа 200.
    - Наличие ключей 'product_data' и 'recommendation' в ответе.
    """
    payload = {
        "article": "393594116",
        "region": "МОСКВА - ЦФО",
        "query": "футболка мужская"
    }
    response = client.post("/submit-request/", json=payload)
    assert response.status_code == 200
    assert "product_data" in response.json()
    assert "recommendation" in response.json()


def test_submit_request_invalid_article():
    """
    Проверяет, что при передаче некорректного артикула возвращается ошибка 400.

    Проверяет сообщение об ошибке.
    """
    payload = {
        "article": "abc123",
        "region": "МОСКВА - ЦФО",
        "query": "футболка мужская"
    }
    response = client.post("/submit-request/", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Артикул должен быть числом"


def test_submit_request_invalid_region():
    """
    Проверяет, что при передач несуществующего региона возвращается ошибка 400.

    Проверяет сообщение об ошибке.
    """
    payload = {
        "article": "393594116",
        "region": "НЕСУЩЕСТВУЮЩИЙ РЕГИОН",
        "query": "футболка"
    }
    response = client.post("/submit-request/", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Неверный регион"


def test_get_recommendation_without_submit():
    """
    Проверяет, что эндпоинт get-recommendation возвращает
    статус 200 даже без предварительного запроса submit.

    Пример проверки fallback поведения.
    """
    response = client.get("/get-recommendation/")
    assert response.status_code == 200
