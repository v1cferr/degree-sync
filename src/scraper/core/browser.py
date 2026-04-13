import logging
import json
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext, Page

logger = logging.getLogger(__name__)

PROFILE_DIR = Path("chrome_profile")
STATE_FILE = Path("state.json")

class BrowserManager:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self._playwright = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def page(self) -> Page | None:
        return self._page
        
    @property
    def context(self) -> BrowserContext | None:
        return self._context

    async def start(self) -> Page:
        """Inicia o Playwright, lidando com perfis e injeção de cookies persistentes."""
        self._playwright = await async_playwright().start()
        PROFILE_DIR.mkdir(exist_ok=True)

        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=self.headless,
            viewport={"width": 1280, "height": 720},
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
        )

        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    if "cookies" in state:
                        await self._context.add_cookies(state["cookies"])
                        logger.info("Cookies de sessão restaurados.")
            except Exception as e:
                logger.warning("Falha ao restaurar state.json: %s", e)

        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        return self._page

    async def save_state(self):
        """Força o despejo dos cookies para uso posterior."""
        if not self._context:
            return
        await self._context.storage_state(path=STATE_FILE)
        logger.debug("Sessão salva no disco.")

    async def close(self):
        """Encerra graciosamente o navegador e o Playwright."""
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
