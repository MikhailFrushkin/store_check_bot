"""
Форматирование текста сообщений (HTML).
"""

from datetime import date

from store_check_bot.db.models import Product, VerificationStatus


def product_caption(product: Product, status: str | None = None) -> str:
    """
    Текст карточки неучтённого артикула (без фото).

    Показывает ключевые поля из выгрузки Excel.
    """
    status_line = ""
    if status == VerificationStatus.PROCESSED.value:
        status_line = "\n\n<b>Статус:</b> ✅ Отработан"
    elif status == VerificationStatus.NOT_PROCESSED.value:
        status_line = "\n\n<b>Статус:</b> ❌ Не отработан"

    qty = product.unaccounted_qty
    qty_str = str(int(qty)) if qty is not None and qty == int(qty) else str(qty) if qty else "—"

    return (
        f"<b>{product.name}</b>\n"
        f"Артикул: <code>{product.article}</code>\n"
        f"Неучтённый товар: {qty_str}"
        f"{status_line}"
    )


def format_department_header(on_date: date, department: int, articles: list[Product], data_dep: dict) -> str:
    """
    Заголовок при входе в отдел: дата и список артикулов на сегодня.
    """
    date_str = on_date.strftime("%d.%m.%Y")
    lines = [
        f"<b>Сегодня {date_str}</b>",
        f"Отдел {department}: нужно отработать эти артикула ({len(articles)} шт.):\n",
    ]
    if data_dep['checked'] == data_dep['total']:
        lines = ["Все артикула отработаны 💪"]
    else:
        lines.extend([
            f"✅ Отработано: {data_dep['present']} \n"
            f"❌ Не отработано: {data_dep['absent']} \n"
            f"⏳ Без отметки: {data_dep['unchecked']}",
        ])
    # for product in articles:
    #     lines.append(f"• <code>{product.article}</code> — {product.name[:60]}")

    return "\n".join(lines)


def format_stats_message(stats: list[dict[str, int]]) -> str:
    """Сводка по отделам для админ-кнопки «Результаты»."""
    lines = ["<b>📊 Статистика отработки за сегодня</b>\n"]
    total_assigned = 0
    total_processed = 0
    total_not_processed = 0
    total_pending = 0

    for row in stats:
        dept = row["department"]
        if row["total"] == 0:
            lines.append(f"Отдел {dept}: нет назначений на сегодня")
            continue
        lines.append(
            f"<b>Отдел {dept}</b>: назначено {row['total']}\n"
            f"✅ {row['present']}, ❌ {row['absent']}, ⏳ {row['unchecked']}\n"
        )
        total_assigned += row["total"]
        total_processed += row["present"]
        total_not_processed += row["absent"]
        total_pending += row["unchecked"]

    lines.append(
        f"\n<b>Итого:</b> {total_assigned} "
        f"(✅ {total_processed}, ❌ {total_not_processed}, ⏳ {total_pending})"
    )
    return "\n".join(lines)


def _department_summary_line(row: dict[str, int]) -> str:
    """Одна строка сводки по отделу: отработан / в работе / не начат."""
    dept = row["department"]
    total = row["total"]
    if total == 0:
        return f"Отдел {dept}: — нет назначений"

    processed = row["present"]
    pending = row["unchecked"]

    if processed >= total:
        return f"Отдел {dept}: ✅ <b>отработан</b> ({processed}/{total})"
    if pending >= total:
        return f"Отдел {dept}: ⏳ <b>ещё не начат</b> ({total} арт.)"
    return (
        f"Отдел {dept}: 🔄 в работе "
        f"✅{processed} ❌{row['absent']} ⏳{pending} из {total}"
    )


def format_daily_summary(
    on_date: date,
    progress: dict[str, int],
    dept_stats: list[dict[str, int]] | None = None,
) -> str:
    """
    Текст плановой сводки с разбивкой по отделам.

    Args:
        on_date: Дата проверки.
        progress: Итоги за день (все отделы).
        dept_stats: Статистика по каждому отделу.
    """
    date_str = on_date.strftime("%d.%m.%Y")
    total = progress["total"]
    if total == 0:
        return f"<b>📋 Сводка на {date_str}</b>\nНа сегодня артикулы ещё не назначены."

    lines = [
        f"<b>📋 Сводка на {date_str}</b>",
        f"Всего к проверке: <b>{total}</b> арт.",
        f"✅ Отработано: {progress['processed']} \n"
        f"❌ Не отработано: {progress['not_processed']} \n"
        f"⏳ Без отметки: {progress['pending']}",
        "",
        "<b>По отделам:</b>",
    ]

    if dept_stats:
        for row in dept_stats:
            if row["total"] > 0 or row.get("department"):
                lines.append(_department_summary_line(row))
    else:
        lines.append("(нет данных по отделам)")

    return "\n".join(lines)
