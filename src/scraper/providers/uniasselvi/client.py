import logging
from src.scraper.core.browser import BrowserManager
from src.scraper.providers.uniasselvi.auth import UniasselviAuthenticator

logger = logging.getLogger(__name__)

class UniasselviClient:
    def __init__(self, headless: bool = False, manual_login_timeout: int = 300):
        self.browser = BrowserManager(headless=headless)
        self.manual_login_timeout = manual_login_timeout
        self.authenticator = None

    async def start(self):
        """Prepara o navegador, as variáveis de sessão e o autenticador."""
        page = await self.browser.start()
        self.authenticator = UniasselviAuthenticator(page, manual_login_timeout=self.manual_login_timeout)

    async def login(self) -> bool:
        """Garante que a autenticação foi concluída e salva no disco."""
        if not self.authenticator:
            raise RuntimeError("UniasselviClient.start() deve ser chamado primeiro.")
            
        if await self.authenticator.is_logged_in():
            return True
        
        success = await self.authenticator.execute_login()
        if success:
            await self.browser.save_state()
            
        return success

    async def dismiss_home_popups(self) -> None:
        """Remove os popups promocionais ou de notificação da Home."""
        if self.authenticator:
            await self.authenticator.dismiss_home_popups()

    async def close(self):
        """Encerra a engine e a memória web local."""
        await self.browser.close()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
