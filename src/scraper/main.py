import asyncio
import logging
import os
from src.scraper.providers.uniasselvi.client import UniasselviClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

async def main():
    headless = os.getenv("HEADLESS", "false").strip().lower() in {"1", "true", "yes"}
    manual_login_timeout = int(os.getenv("MANUAL_LOGIN_TIMEOUT", "300"))

    client = UniasselviClient(
        headless=headless,
        manual_login_timeout=manual_login_timeout,
    )
    await client.start()

    try:
        success = await client.login()
        if success:
            print("Login OK ou sessão válida! Verificando popups da Home...")
            await client.dismiss_home_popups()
            print("Tudo limpo na Home! Pronto para os próximos passos.")

        else:
            print("Falha no login. Verifique os logs e screenshots.")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
