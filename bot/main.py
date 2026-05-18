import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import BOT_TOKEN
from bot.database import init_db

from bot.handlers.common import router as common_router
from bot.handlers.tool1 import router as tool1_router
from bot.handlers.tool2 import router as tool2_router
from bot.handlers.tool3 import router as tool3_router
from bot.handlers.tool4 import router as tool4_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

async def main():
    # 初始化数据库
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # 注册所有路由
    dp.include_router(common_router)
    dp.include_router(tool1_router)
    dp.include_router(tool2_router)
    dp.include_router(tool3_router)
    dp.include_router(tool4_router)

    logging.info("🚀 Telegram Bot Tool 已启动（Polling模式）")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())