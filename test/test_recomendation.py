import subprocess
from pathlib import Path


def test_recomendation_script_runs():
    script_path = Path("ml_model/recomendation.py").resolve()
    dataset_path = Path("ml_model/dataset/product1.csv").resolve()

    result = subprocess.run(
        ["python", str(script_path), str(dataset_path)],
        capture_output=True,
        text=True
    )

    # Убедимся, что скрипт завершился без ошибок
    assert result.returncode == 0, f"Скрипт завершился с ошибкой:\n{result.stderr}"

    output = result.stdout

    # Проверим наличие ключевых блоков отчёта
    assert "Текущая позиция товара" in output
    assert "--- Анализ текущих показателей ---" in output
    assert "--- Рекомендации по улучшению ---" in output
    assert "--- Итоговый отчет ---" in output