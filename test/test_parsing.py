import pytest
import pandas as pd
from unittest.mock import patch
from datetime import datetime

from API.parsing import (
    get_average_geo_visibility,
    get_delivery_features,
    extract_position_value,
    get_position_features,
    process_product_data,
    process_promos,
    extract_product_features
)

# -------------------------------
# Test get_average_geo_visibility
# -------------------------------
@patch("API.parsing.get_product_geo_visibility")
def test_get_average_geo_visibility(mock_get_vis):
    mock_get_vis.return_value = {
        "results": [
            {"availability": [{"is_availability": True}, {"is_availability": True}]},
            {"availability": [{"is_availability": True}, {"is_availability": False}]},
            {"availability": []}
        ]
    }
    assert get_average_geo_visibility(123) == 2


# -------------------------
# Test get_delivery_features
# -------------------------
@patch("API.parsing.get_delivery_times")
def test_get_delivery_features(mock_get_times):
    df_mock = pd.DataFrame()
    mock_get_times.return_value = {
        "ЦФО": 24,
        "ПФО": 48,
        "УФО": None
    }
    result = get_delivery_features(111, df_mock)
    assert result["delivery_ЦФО"] == 24
    assert result["avg_delivery_time"] == 36


# -------------------------
# Test extract_position_value
# -------------------------
@pytest.mark.parametrize("input_dict, expected", [
    ({"position": "12"}, 12.0),
    ({"expected_position": "5"}, 5.0),
    ({"pos": None}, None),
    ({"position": "-3"}, None)
])
def test_extract_position_value(input_dict, expected):
    from API.parsing import extract_position_value
    assert extract_position_value(input_dict) == expected


# -------------------------
# Test get_position_features
# -------------------------
@patch("API.parsing.get_warehouse_positions")
def test_get_position_features(mock_positions):
    mock_positions.return_value = [
        {"expected_position": 10},
        {"position": 20},
        {"position": "30"},
        {"position": None},
    ]
    result = get_position_features(111, "test")
    assert result["positions_found"] == 4
    assert result["positions_count"] == 3
    assert result["avg_position"] == 20.0
    assert result["expected_position"] == 10.0
    assert result["first_valid_position"] == 10.0


# -------------------------
# Test process_product_data
# -------------------------
def test_process_product_data():
    input_data = {
        "orders": 10,
        "proceeds": 10000000,
        "price": 500,
        "discount": 10,
        "old_price": 600,
        "rating": 4.5,
        "in_stock_percent": 80,
        "feedbacks": 7
    }
    result = process_product_data(input_data)
    assert result["loyalty_level"] == "Золотой"
    assert result["orders"] == 10


# -------------------------
# Test process_promos
# -------------------------
def test_process_promos():
    input_promos = [
        {
            "start_date": "2024-01-01T00:00:00",
            "end_date": "2024-01-03T00:00:00"
        }
    ]
    result = process_promos(input_promos)
    assert result["has_promos"] == 1
    assert result["promo_days"] == 3


# -------------------------
# Test extract_product_features (integration test)
# -------------------------
@patch("API.parsing.get_product_details")
@patch("API.parsing.get_brand_details")
@patch("API.parsing.get_all_warehouses_for_product")
@patch("API.parsing.get_product_geo_visibility")
@patch("API.parsing.get_delivery_times")
@patch("API.parsing.get_warehouse_positions")
def test_extract_product_features(
    mock_positions, mock_delivery, mock_geo, mock_warehouses, mock_brand, mock_details
):
    mock_details.return_value = {
        "orders": 10,
        "proceeds": 500000,
        "price": 100,
        "discount": 20,
        "old_price": 125,
        "rating": 4.3,
        "feedbacks": 5,
        "promos": [],
        "dynamic": [{"visibility": 100}],
        "brand": {"id": 1}
    }
    mock_brand.return_value = {"rating": 4.5, "reviews": 200}
    mock_warehouses.return_value = ["Склад A"]
    mock_geo.return_value = {"results": [{"availability": [{"is_availability": True}]}]}
    mock_delivery.return_value = {"ЦФО": 24, "ПФО": 48}
    mock_positions.return_value = [{"expected_position": 10}]

    df_mock = pd.DataFrame()
    result = extract_product_features(101, "кроссовки", df_mock)
    assert result["product_id"] == 101
    assert result["orders"] == 10
    assert result["avg_visibility"] == 2
    assert result["main_warehouse"] == "Склад A"
    assert result["delivery_ЦФО"] == 24
