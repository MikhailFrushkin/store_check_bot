"""Тесты импорта Excel неучтённого товара."""

from pathlib import Path

import pytest
from openpyxl import Workbook

from store_check_bot.services.excel_import import parse_products_from_excel


def _write_sample_xlsx(path: Path) -> None:
    """Минимальный файл в формате «Неучтенные товары»."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        [
            "Магазин",
            "Отдел",
            "Подотдел",
            "Артикул",
            "Наименование",
            "LOC",
            "Гамма",
            "ТОП",
            "Теор. запас",
            "Вместимость",
            "На LS",
            "На SSCC в ТЗ",
            "Кол-во на Z адресе",
            "На RM",
            "НА ЕМ",
            "На RD",
            "Буфер склада",
            "Неучтенный товар",
            "К-Адрес",
            "Z-Адрес",
            "Последнее движение",
        ]
    )
    sheet.append(
        [
            67,
            4,
            435,
            82427762,
            "Тестовый товар",
            "LOC1",
            "A0",
            1,
            84,
            70,
            84,
            None,
            None,
            0,
            0,
            0,
            0,
            14,
            "4-48-R13",
            None,
            None,
        ]
    )
    workbook.save(path)
    workbook.close()


def test_parse_products_from_excel(tmp_path: Path) -> None:
    """Парсинг одной строки с артикулом."""
    file_path = tmp_path / "products.xlsx"
    _write_sample_xlsx(file_path)

    products = parse_products_from_excel(file_path)

    assert len(products) == 1
    assert products[0]["department"] == 4
    assert products[0]["article"] == "82427762"
    assert products[0]["name"] == "Тестовый товар"


def test_parse_missing_columns(tmp_path: Path) -> None:
    """Ошибка при отсутствии артикула."""
    file_path = tmp_path / "bad.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Отдел", "Наименование"])
    sheet.append([1, "X"])
    workbook.save(file_path)
    workbook.close()

    with pytest.raises(ValueError, match="колонки"):
        parse_products_from_excel(file_path)
