"""
Сборка всех роутеров Aiogram в один корневой router.

Порядок подключения:
    start — /start, главное меню
    department — выбор отдела и список товаров
    check — инлайн-кнопки «Есть» / «Нет»
    admin — загрузка Excel и отчёты (только привилегированные пользователи)
"""

from aiogram import Router

from store_check_bot.handlers import admin, check, department, settings, start

router = Router()
router.include_router(start.router)
router.include_router(department.router)
router.include_router(check.router)
router.include_router(admin.router)
router.include_router(settings.router)
