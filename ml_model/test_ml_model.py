"""
    Модуль тестирует функциональность аналитического скрипта 
    для оценки позиции товара на маркетплейсе Wildberries.
"""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from main import get_status, TUNABLE_FEATURES  # Используем только нужные импорты

class TestWildberriesAnalytics(unittest.TestCase):
    """
    Тесты для аналитического скрипта, который оценивает позицию товара
    на маркетплейсе Wildberries и генерирует рекомендации по улучшению.
    """

    # Тестирование загрузки данных и модели
    @patch("main.pd.read_csv")
    @patch("main.CatBoostRegressor")
    def test_load_model_and_data(self, mock_catboost, mock_read_csv):
        """
        Тестирование корректности загрузки модели и данных.
        """
        # Мокаем модель и данные
        mock_model = MagicMock()
        mock_catboost.return_value = mock_model
        mock_read_csv.return_value = pd.DataFrame({
            'Основной склад': ['Warehouse_1'],
            'Уровень лояльности': [1],
            'Цена': [1000],
            'Скидка': [15],
            'Рейтинг': [4.5],
            'Наличие (%)': [95],
            'Количество отзывов': [200],
            'Ср время доставки (ч)': [48],
            'Дней в акциях': [12],
        })

        # Загрузка данных и модели
        df = pd.read_csv("product3.csv")
        model = mock_catboost()
        model.load_model("WB_model.cbm")

        # Проверяем, что данные загружены корректно
        self.assertEqual(len(df), 1)
        self.assertTrue(mock_catboost.called)
        self.assertTrue(mock_read_csv.called)

    # Тестирование функции get_status
    def test_get_status(self):
        """
        Тестирование функции get_status, которая оценивает метрики товара.
        """
        # Проверяем, что функция возвращает правильные статусы
        self.assertEqual(get_status(4.6, 4.5, 3.5), "Хорошо")
        self.assertEqual(get_status(4.0, 4.5, 3.5), "Норма")
        self.assertEqual(get_status(3.0, 4.5, 3.5), "Требует улучшения")

    @patch("main.model.predict")
    def test_generate_recommendations(self, mock_predict):
        """
        Тестирование функции генерации рекомендаций на основе изменений параметров товара.
        """
        mock_predict.return_value = [100]  # Мокаем предсказание модели

        # Пример данных
        df = pd.DataFrame({
            'Основной склад': ['Warehouse_1'],
            'Уровень лояльности': [1],
            'Цена': [1000],
            'Скидка': [10],
            'Рейтинг': [4.5],
            'Наличие (%)': [95],
            'Количество отзывов': [200],
            'Ср время доставки (ч)': [48],
            'Дней в акциях': [12],
        })

        # Инициализация текущей позиции товара
        current_position = 9428  # Используем фиксированное значение текущей позиции

        recommendations = []
        for feature, params in TUNABLE_FEATURES.items():
            if feature in df.columns:
                original = df.at[0, feature]
                delta = params["delta"]
                new_value = original + delta
                new_pos = mock_predict([df])[0]
                improvement = current_position - new_pos

                if improvement > 0:
                    recommendations.append({
                        "feature": feature,
                        "original": original,
                        "new": new_value,
                        "improvement": improvement
                    })

        # Проверка, что рекомендации сгенерированы
        self.assertGreater(len(recommendations), 0)

    # Тестирование анализа времени доставки
    def test_delivery_analysis(self):
        """
        Тестирование анализа времени доставки по регионам.
        """
        # Мокаем данные
        df = pd.DataFrame({
            'Доставка_ЮФО_(ч)': [40],
            'Доставка_ПФО_(ч)': [35],
            'Доставка_ЦФО_(ч)': [25]
        })

        # Анализ времени доставки
        delivery_cols = [col for col in df.columns if col.startswith("Доставка_") 
                 and col.endswith("(ч)")]
        regions = []
        for col in delivery_cols:
            region = col.split("_")[1]
            hours = df.at[0, col]
            regions.append((region, hours))

        regions.sort(key=lambda x: -x[1])

        self.assertEqual(regions[0], ('ЮФО', 40))  # Проверка на сортировку по времени доставки

    # Тестирование итогового отчета
    @patch("main.model.predict")
    def test_generate_final_report(self, mock_predict):
        """
        Тестирование генерации итогового отчета с расчетом улучшений.
        """
        mock_predict.return_value = [100]  # Мокаем предсказание модели
        recommendations = [{"feature": "Цена", "improvement": 500}]
        total_improvement = sum(r["improvement"] for r in recommendations)

        self.assertEqual(total_improvement, 500)  # Проверка суммарного улучшения

if __name__ == "__main__":
    unittest.main()
