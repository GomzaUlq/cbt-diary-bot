from aiogram import Router
from .steps import diary_router as steps_router
from .save import diary_router as save_router
from .continue_entries import diary_router as continue_router
from .delete_entries import diary_router as delete_router
from .view_entries import diary_router as view_router
from .callbacks import diary_router as callbacks_router

# Собираем всё в один роутер
diary_router = Router()

diary_router.include_router(steps_router)
diary_router.include_router(save_router)
diary_router.include_router(continue_router)
diary_router.include_router(delete_router)
diary_router.include_router(view_router)
diary_router.include_router(callbacks_router)

__all__ = ["diary_router"]