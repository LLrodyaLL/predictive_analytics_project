"""
Тесты для взаимодействия с API Wildbox.
Тестируют различные функции получения данных: 
товарные детали, бренды, склады, гео-видимость и время доставки.
"""

from unittest.mock import patch, Mock  # Стандартные импорты должны быть перед сторонними
import pytest
import pandas as pd
import requests

from dataset.wildbox_client import (
    get_product_details,
    get_brand_details,
    get_warehouse_positions,
    get_product_geo_visibility,
    get_all_warehouses_for_product,
)

# Sample data for mocking responses
SAMPLE_PRODUCT_RESPONSE = {
    "results": [
        {
            "id": 123,
            "orders": 100,
            "proceeds": 50000,
            "rating": 4.5,
            "reviews": 50,
            "brand": "TestBrand",
            "seller": "TestSeller",
        }
    ]
}

SAMPLE_BRAND_RESPONSE = {
    "results": [
        {
            "id": 456,
            "rating": 4.0,
            "reviews": 200,
            "seller_rating": 4.2,
            "proceeds": 100000,
        }
    ]
}

SAMPLE_POSITIONS_RESPONSE = [
    {"warehouse": "Подольск", "position": 1},
    {"warehouse": "Казань", "position": 2},
]

SAMPLE_GEO_VISIBILITY_RESPONSE = {
    "product_id": 123,
    "geolocation_ids": "1,2",
    "availability": ["Подольск", "Казань"],
}

SAMPLE_WAREHOUSES_RESPONSE = [
    {"name": "Подольск", "quantity": 10},
    {"name": "Казань", "quantity": 5},
]

SAMPLE_DELIVERY_MATRIX = pd.DataFrame({
    "Склад": ["Подольск", "Казань", "Коледино"],
    "Федеральный округ": ["ЦФО", "ПФО", "ЦФО"],
    "Москва": [2, 5, 3],
    "Казань": [4, 1, 5],
})

@pytest.fixture
def setup_env(monkeypatch):
    """Фикстура для настройки переменных окружения для тестов."""
    monkeypatch.setenv("AUTH_TOKEN", "test_token")
    monkeypatch.setenv("COMPANY_ID", "test_company")
    monkeypatch.setenv("USER_ID", "test_user")
    monkeypatch.setenv("COOKIE_STRING", "key1=value1; key2=value2")

@pytest.fixture
def mock_requests_get():
    """Фикстура для мокирования метода requests.get."""
    with patch("requests.get") as mock_get:
        yield mock_get

def test_get_product_details_api_error(mock_requests_get):
    """Тестирование get_product_details, когда запрос к API завершился ошибкой."""
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.RequestException("API Error")
    mock_requests_get.return_value = mock_response

    result = get_product_details(123)
    assert result == {}
    mock_requests_get.assert_called_once()

def test_get_brand_details_empty_response(mock_requests_get):
    """Тестирование get_brand_details, когда API возвращает пустой результат."""
    mock_response = Mock()
    mock_response.json.return_value = {"results": []}
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()
    mock_requests_get.return_value = mock_response

    result = get_brand_details(456)
    assert result == {}
    mock_requests_get.assert_called_once()

def test_get_warehouse_positions_success(mock_requests_get):
    """Тестирование get_warehouse_positions с успешным ответом от API."""
    mock_response = Mock()
    mock_response.json.return_value = SAMPLE_POSITIONS_RESPONSE
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()
    mock_response.text = str(SAMPLE_POSITIONS_RESPONSE)
    mock_response.headers = {"Content-Type": "application/json"}
    mock_requests_get.return_value = mock_response

    result = get_warehouse_positions(123, "test query")
    assert result == SAMPLE_POSITIONS_RESPONSE
    mock_requests_get.assert_called_once()
    call_args = mock_requests_get.call_args
    assert call_args[0][0].startswith("https://wildbox.ru/api/monitoring/positions/")
    assert "product_id=123" in call_args[0][0]
    assert "phrase=test%20query" in call_args[0][0]

def test_get_product_geo_visibility_success(mock_requests_get):
    """Тестирование get_product_geo_visibility с успешным ответом от API."""
    mock_response = Mock()
    mock_response.json.return_value = SAMPLE_GEO_VISIBILITY_RESPONSE
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()
    mock_requests_get.return_value = mock_response

    result = get_product_geo_visibility(123, "1,2")
    assert result == SAMPLE_GEO_VISIBILITY_RESPONSE
    mock_requests_get.assert_called_once()
    call_args = mock_requests_get.call_args
    assert call_args[0][0] == "https://wildbox.ru/api/parsers/products/123/availability/"
    assert call_args[1]["params"]["geolocation_ids"] == "1,2"

def test_get_product_geo_visibility_error(mock_requests_get):
    """Тестирование get_product_geo_visibility, когда запрос к API завершился ошибкой."""
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.RequestException("API Error")
    mock_requests_get.return_value = mock_response

    result = get_product_geo_visibility(123, "1,2")
    assert result == {}
    mock_requests_get.assert_called_once()

def test_get_all_warehouses_for_product_error(mock_requests_get):
    """Тестирование get_all_warehouses_for_product, когда запрос к API завершился ошибкой."""
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.RequestException("API Error")
    mock_requests_get.return_value = mock_response

    result = get_all_warehouses_for_product(123)
    assert not result
    mock_requests_get.assert_called_once()
