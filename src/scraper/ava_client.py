import asyncio
import logging
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from src.config.settings import settings

logger = logging.getLogger(__name__)

class AVALoginClient:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def start(self):
        """Inicializa o navegador e abre um novo contexto."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self._page = await self._context.new_page()

    async def login(self) -> bool:
        """Realiza o processo de login no AVA da Uniasselvi."""
        if not self._page:
            raise RuntimeError("O cliente deve ser iniciado com start() antes do login.")

        login_url = "https://areasegura.uniasselvi.com.br/identificacao"
        
        try:
            logger.info("Acessando a página de login do AVA...")
            await self._page.goto(login_url)

            # Preencher o CPF (usuário)
            logger.info("Preenchendo credenciais...")
            # Encontraremos os campos pelo placeholder ou ID/Name (vamos usar placeholder/texto primeiro, ou seletor de input text)
            # Como não vimos a tela, vamos tentar seletores genéricos ou aguardar que a página carregue.
            
            # The input for CPF usually has some name="login" or placeholder="CPF"
            await self._page.wait_for_selector("input[type='text'], input[placeholder*='CPF'], input[name*='login']")
            inputs = await self._page.locator("input[type='text'], input[type='tel'], input[placeholder*='CPF']").all()
            if inputs:
                await inputs[0].fill(settings.ava_user)
            
            # Senha
            password_inputs = await self._page.locator("input[type='password']").all()
            if password_inputs:
                await password_inputs[0].fill(settings.ava_pass)

            # Clicar no botão de submeter (Entrar / Log in)
            logger.info("Efetuando login...")
            await self._page.locator("button[type='submit'], input[type='submit'], button:has-text('Entrar'), button:has-text('Acessar')").first.click()

            # Aguardar o login concluir - uma forma genérica é esperar a navegação ou esperar algum elemento do dashboard carregar
            # Como não sabemos o que tem no dashboard, vamos aguardar pela network idle ou URL mudar
            await self._page.wait_for_load_state("networkidle")
            
            current_url = self._page.url
            if "identificacao" in current_url:
                logger.error("Falha no login: A URL não mudou ou retornou erro de credenciais.")
                await self._page.screenshot(path="login_error.png")
                return False
                
            logger.info(f"Login bem-sucedido! URL atual: {current_url}")
            await self._page.screenshot(path="login_success.png")
            return True

        except Exception as e:
            logger.error(f"Ocorreu um erro durante o login: {e}")
            if self._page:
                await self._page.screenshot(path="login_exception.png")
            return False

    async def close(self):
        """Encerra a sessão do navegador e Playwright."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
