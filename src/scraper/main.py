import asyncio
import logging
import os
from src.scraper.ava_client import AVALoginClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

async def main():
    headless = os.getenv("HEADLESS", "false").strip().lower() in {"1", "true", "yes"}
    manual_login_timeout = int(os.getenv("MANUAL_LOGIN_TIMEOUT", "300"))

    client = AVALoginClient(
        headless=headless,
        manual_login_timeout=manual_login_timeout,
    )
    await client.start()

    try:
        success = await client.login()
        if success:
            print("Login OK! Sessão salva. Navegador aberto para inspeção.")
            print("Pressione Enter no terminal para encerrar...")
            await asyncio.get_event_loop().run_in_executor(None, input)
        else:
            print("Falha no login. Verifique os logs e screenshots.")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
