import asyncio
import logging
from src.scraper.ava_client import AVALoginClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

async def main():
    # Headless = False pode ser usado localmente para vermos o navegador caso precise depurar.
    # Como estamos num dev container, manteremos headless=True.
    async with AVALoginClient(headless=True) as client:
        success = await client.login()
        if success:
            print("Processo finalizado com sucesso!")
        else:
            print("Processo finalizado com falhas. Verifique os logs e prints.")

if __name__ == "__main__":
    asyncio.run(main())
