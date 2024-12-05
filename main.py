import logging
import asyncio
from datetime import datetime
from tortoise import Tortoise

from loader import client, tortoise_orm_config, dp, bot


from bot.handlers import user, admin, menu,\
                 support_chat, channel_chat,\
                 chanel_chat_listener, schedule_broadcast


async def on_startup() -> None:
    await Tortoise.init(tortoise_orm_config)
    await client.start()

    dp.include_routers(
        user.router,
        admin.router,
        menu.router,
        support_chat.router,
        channel_chat.router,
        chanel_chat_listener.router
    )

    dp.startup.register(menu.set_menu)
    logging.info("Bot started.")


async def on_shutdown() -> None:
    await Tortoise.close_connections()
    logging.info("Database was closed.")
    logging.info("Bot stopped.")


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        filename=f"log-{datetime.now().strftime("%d_%m_%Y-%H_%M_%S")}.log",
        filemode="w",
        encoding='utf-8',
        format="%(asctime)s %(levelname)s %(message)s"
    )
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await asyncio.gather(
        dp.start_polling(bot),
        schedule_broadcast.load_scheduled_broadcast_data()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.warning("Bot stopped!")
