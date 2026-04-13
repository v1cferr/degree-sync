import asyncio
import logging
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext, Page
from src.config.settings import settings

logger = logging.getLogger(__name__)

PROFILE_DIR = Path("chrome_profile")


class AVALoginClient:
    def __init__(self, headless: bool = False, manual_login_timeout: int = 300):
        self.headless = headless
        self.manual_login_timeout = manual_login_timeout
        self._playwright = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def start(self):
        """Inicia o Chrome real com perfil persistente (cookies, cache, etc.)."""
        self._playwright = await async_playwright().start()
        PROFILE_DIR.mkdir(exist_ok=True)

        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=self.headless,
            viewport={"width": 1280, "height": 720},
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
        )
        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()

    async def _is_logged_in(self) -> bool:
        """Verifica se já está logado tentando acessar o AVA diretamente."""
        if not self._page:
            return False
        try:
            await self._page.goto("https://ava2.uniasselvi.com.br/home", timeout=30000)
            await self._page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(3)
            url = self._page.url
            logged = "ava2.uniasselvi.com.br" in url and "identificacao" not in url
            if logged:
                logger.info("Sessão anterior ainda válida — já logado em %s", url)
            return logged
        except Exception:
            return False

    async def login(self) -> bool:
        """Realiza login no AVA.

        Tenta restaurar sessão salva primeiro. Se não funcionar, faz login
        normalmente (com suporte a resolução manual de CAPTCHA).
        Após login bem-sucedido, salva a sessão para reuso.
        """
        if not self._page:
            raise RuntimeError("O cliente deve ser iniciado com start() antes do login.")

        # Tenta sessão do perfil persistente
        if await self._is_logged_in():
            return True
        logger.info("Sessão não encontrada ou expirada. Fazendo login...")

        login_url = "https://areasegura.uniasselvi.com.br/identificacao"

        try:
            logger.info("Acessando a página de login do AVA...")
            await self._page.goto(login_url)
            await self._page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(3)

            logger.info("Preenchendo credenciais (quando os campos estiverem disponíveis)...")
            fields_ready = await self._page.locator(
                "input[type='password'], input[name*='cpf' i], input[placeholder*='CPF' i], input[name*='login' i]"
            ).count()

            if fields_ready:
                user_field = self._page.locator(
                    "input[name*='cpf' i], input[placeholder*='CPF' i], input[name*='login' i], input[type='text'], input[type='tel']"
                ).first
                await user_field.fill(settings.ava_user)

                password_field = self._page.locator("input[type='password']").first
                await password_field.fill(settings.ava_pass)

                logger.info("Tentando enviar formulário de login...")
                await self._page.locator(
                    "button[type='submit'], input[type='submit'], button:has-text('Entrar'), button:has-text('Acessar')"
                ).first.click()
            else:
                logger.warning(
                    "Campos de login não apareceram automaticamente. "
                    "Faça o login manualmente na janela do navegador."
                )

            await self._wait_until_ava_home()

            current_url = self._page.url
            if "identificacao" in current_url:
                logger.error("Falha no login: ainda na página de identificação.")
                await self._page.screenshot(path="login_error.png")
                return False

            # Perfil persistente salva estado automaticamente ao fechar
            logger.info("Login bem-sucedido! URL atual: %s", current_url)
            await self._page.screenshot(path="login_success.png")
            return True

        except Exception as e:
            logger.error("Ocorreu um erro durante o login: %s", e)
            if self._page:
                await self._page.screenshot(path="login_exception.png")
            return False

    async def _wait_until_ava_home(self) -> None:
        """Aguarda até a URL ser do AVA home ou timeout (para login manual/CAPTCHA)."""
        if not self._page:
            return

        def _is_at_ava(url: str) -> bool:
            return "ava2.uniasselvi.com.br" in url and "identificacao" not in url

        if _is_at_ava(self._page.url):
            return

        logger.warning(
            "Aguardando login completo (resolva CAPTCHA/desafio se necessário). "
            "Timeout: %ds", self.manual_login_timeout
        )

        waited = 0
        interval = 2
        next_navigate_try = 0
        while waited < self.manual_login_timeout:
            if _is_at_ava(self._page.url):
                logger.info("Redirecionado para o AVA com sucesso.")
                return

            await self._try_click_continue()

            # Fallback: em alguns fluxos o portal autentica, mas nao redireciona automaticamente.
            if waited >= next_navigate_try:
                await self._try_go_to_ava_home()
                next_navigate_try += 8

            await asyncio.sleep(interval)
            waited += interval

        raise TimeoutError(
            "Tempo esgotado aguardando chegar ao AVA. Resolva o desafio e tente novamente."
        )

    async def _try_click_continue(self) -> None:
        if not self._page:
            return

        selectors = [
            "button:has-text('Continuar')",
            "a:has-text('Continuar')",
            "button:has-text('Prosseguir')",
            "a:has-text('Prosseguir')",
            "button:has-text('Acessar')",
            "a:has-text('Acessar')",
            "button:has-text('Ir para o AVA')",
            "a:has-text('Ir para o AVA')",
            "button:has-text('AVA')",
            "a:has-text('AVA')",
        ]

        for selector in selectors:
            locator = self._page.locator(selector).first
            if await locator.count() > 0 and await locator.is_visible():
                try:
                    logger.info("Clicando em botão de continuidade: %s", selector)
                    await locator.click(timeout=2000)
                    await self._page.wait_for_load_state("domcontentloaded")
                    return
                except Exception:
                    continue

    async def _try_go_to_ava_home(self) -> None:
        if not self._page:
            return
        try:
            await self._page.goto("https://ava2.uniasselvi.com.br/home", timeout=8000)
            await self._page.wait_for_load_state("domcontentloaded")
        except Exception:
            # Durante desafio/captcha essa navegacao pode falhar e sera tentada novamente.
            pass

    async def close(self):
        """Encerra o contexto persistente e o Playwright."""
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
