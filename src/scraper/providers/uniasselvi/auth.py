import asyncio
import logging
import random
from playwright.async_api import Page
from src.config.settings import settings

logger = logging.getLogger(__name__)

class UniasselviAuthenticator:
    def __init__(self, page: Page, manual_login_timeout: int = 300):
        self._page = page
        self.manual_login_timeout = manual_login_timeout

    async def is_logged_in(self) -> bool:
        """Verifica se já está logado tentando acessar a Home diretamente."""
        try:
            await self._page.goto("https://ava2.uniasselvi.com.br/home", timeout=30000)
            await self._page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(3)
            url = self._page.url
            if "ava2.uniasselvi.com.br" in url and "identificacao" not in url:
                logger.info("Sessão válida detectada: %s", url)
                return True
            return False
        except Exception:
            return False

    async def execute_login(self) -> bool:
        """Realiza o fluxo de preenchimento e botões de login."""
        logger.info("Iniciando fluxo de login...")
        login_url = "https://areasegura.uniasselvi.com.br/identificacao"

        try:
            await self._page.goto(login_url)
            await self._page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(3)

            logger.info("Visualizando CPF...")
            user_field = self._page.locator("input[name*='cpf' i], input[placeholder*='CPF' i], input[name*='login' i], input[type='text'], input[type='tel']").first
            
            try:
                await user_field.wait_for(state="visible", timeout=10000)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                await user_field.fill(settings.ava_user)
                
                btn_continuar = self._page.locator("button:has-text('CONTINUAR'), button:has-text('Continuar')").first
                if await btn_continuar.is_visible():
                    await asyncio.sleep(random.uniform(1.0, 2.5))
                    await btn_continuar.click()
                
                logger.info("Visualizando senha...")
                password_field = self._page.locator("input[type='password']").first
                await password_field.wait_for(state="visible", timeout=10000)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                await password_field.fill(settings.ava_pass)
                
                btn_acessar = self._page.locator("button:has-text('ACESSAR'), button:has-text('Acessar')").first
                if await btn_acessar.is_visible():
                    await asyncio.sleep(random.uniform(1.0, 2.5))
                    await btn_acessar.click()
                else:
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    await password_field.press("Enter")
            except Exception as e:
                logger.warning("Campos não carregaram como esperado (talvez precise de interação manual): %s", e)

            await self._wait_until_ava_home()

            current_url = self._page.url
            if "identificacao" in current_url:
                logger.error("Preso na tela de login/identificação.")
                await self._page.screenshot(path="login_error.png")
                return False

            await self._page.screenshot(path="login_success.png")
            return True

        except Exception as e:
            logger.error("Erro fatal no fluxo de login: %s", e)
            await self._page.screenshot(path="login_exception.png")
            return False

    async def _wait_until_ava_home(self) -> None:
        """Checa ciclo de redirecionamento ou timeout visual (CAPTCHA)."""
        def _is_at_ava(url: str) -> bool:
            return "ava2.uniasselvi.com.br" in url and "identificacao" not in url

        if _is_at_ava(self._page.url):
            return

        logger.warning(
            "Esperando transição de AVA ou prompt humano. Expirando em %ds...",
            self.manual_login_timeout
        )

        waited = 0
        interval = 2
        next_navigate_try = 0

        while waited < self.manual_login_timeout:
            if _is_at_ava(self._page.url):
                logger.info("Redirecionou para a Home.")
                return

            await self._try_select_and_continue()

            if waited >= next_navigate_try:
                try:
                    await self._page.goto("https://ava2.uniasselvi.com.br/home", timeout=8000)
                    await self._page.wait_for_load_state("domcontentloaded")
                except Exception:
                    pass
                next_navigate_try += 8

            await asyncio.sleep(interval)
            waited += interval

        raise TimeoutError("CAPTCHA manual ou erro crítico impediu o acesso durante o timeout.")

    async def _try_select_and_continue(self) -> None:
        try:
            radios = self._page.locator("input[type='radio']")
            if await radios.count() > 0 and await radios.first.is_visible():
                if not await radios.first.is_checked():
                    await asyncio.sleep(random.uniform(1.0, 2.5))
                    await radios.first.check()
                    await asyncio.sleep(1)
            
            cards = self._page.locator(".curso, .card, [class*='course']")
            if await cards.count() > 0 and await cards.first.is_visible():
                await asyncio.sleep(random.uniform(1.0, 2.5))
                await cards.first.click()
                await asyncio.sleep(1)
        except Exception:
            pass

        selectors = [
            "button:has-text('Entrar')", "a:has-text('Entrar')",
            "button:has-text('Continuar')", "a:has-text('Continuar')",
            "button:has-text('Prosseguir')", "a:has-text('Prosseguir')",
            "button:has-text('Acessar')", "a:has-text('Acessar')",
            "button:has-text('Ir para o AVA')", "a:has-text('Ir para o AVA')"
        ]

        for selector in selectors:
            locator = self._page.locator(selector).first
            if await locator.count() > 0 and await locator.is_visible():
                try:
                    await asyncio.sleep(random.uniform(1.0, 2.5))
                    await locator.click(timeout=2000)
                    await self._page.wait_for_load_state("domcontentloaded")
                    return
                except Exception:
                    continue

    async def dismiss_home_popups(self) -> None:
        logger.info("Verificando se existem modais na Home...")
        await asyncio.sleep(random.uniform(2.5, 4.0))
        
        selectors = [
            "button:has-text('✕')", "button:has-text('X')",
            "button:has-text('Fechar')", "a:has-text('Fechar')",
            "button:has-text('FECHAR')", "a:has-text('FECHAR')",
            "[aria-label*='Fechar' i]", ".close", ".btn-close",
            "button[class*='close' i]", "button[id*='fechar' i]"
        ]

        closed_any = True
        attempts = 0
        while closed_any and attempts < 10:
            closed_any = False
            attempts += 1
            for selector in selectors:
                try:
                    locator = self._page.locator(selector).first
                    if await locator.count() > 0 and await locator.is_visible():
                        logger.info("Limpando modal (%s)...", selector)
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                        await locator.click(timeout=3000)
                        closed_any = True
                        await asyncio.sleep(random.uniform(1.0, 2.0))
                        break
                except Exception:
                    continue
