import asyncio
import logging
import json
import random
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext, Page
from src.config.settings import settings

logger = logging.getLogger(__name__)

PROFILE_DIR = Path("chrome_profile")
STATE_FILE = Path("state.json")


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

            logger.info("Aguardando campo de usuário...")
            user_field = self._page.locator("input[name*='cpf' i], input[placeholder*='CPF' i], input[name*='login' i], input[type='text'], input[type='tel']").first
            
            try:
                await user_field.wait_for(state="visible", timeout=10000)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                await user_field.fill(settings.ava_user)
                logger.info("CPF preenchido.")
                
                btn_continuar = self._page.locator("button:has-text('CONTINUAR'), button:has-text('Continuar')").first
                if await btn_continuar.is_visible():
                    await asyncio.sleep(random.uniform(1.0, 2.5))
                    await btn_continuar.click()
                    logger.info("Clicou em CONTINUAR.")
                
                logger.info("Aguardando campo de senha...")
                password_field = self._page.locator("input[type='password']").first
                await password_field.wait_for(state="visible", timeout=10000)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                await password_field.fill(settings.ava_pass)
                logger.info("Senha preenchida.")
                
                btn_acessar = self._page.locator("button:has-text('ACESSAR'), button:has-text('Acessar')").first
                if await btn_acessar.is_visible():
                    await asyncio.sleep(random.uniform(1.0, 2.5))
                    await btn_acessar.click()
                    logger.info("Clicou em ACESSAR.")
                else:
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    await password_field.press("Enter")
                    logger.info("Pressionou Enter na senha.")

            except Exception as e:
                logger.warning(
                    f"Fluxo automático falhou ou os campos não apareceram. Erro: {e}. "
                    "Aguardando resolução manual/CAPTCHA."
                )

            await self._wait_until_ava_home()

            current_url = self._page.url
            if "identificacao" in current_url:
                logger.error("Falha no login: ainda na página de identificação.")
                await self._page.screenshot(path="login_error.png")
                return False

            # Perfil persistente salva estado automaticamente ao fechar, 
            # mas forçamos o dump dos cookies de sessão
            await self._context.storage_state(path=STATE_FILE)
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

        try:
            # Tenta encontrar e selecionar o curso se for um radio button
            radios = self._page.locator("input[type='radio']")
            if await radios.count() > 0 and await radios.first.is_visible():
                if not await radios.first.is_checked():
                    logger.info("Selecionando o curso (radio button)...")
                    await asyncio.sleep(random.uniform(1.0, 2.5))
                    await radios.first.check()
                    await asyncio.sleep(1)
            
            # Tenta encontrar e selecionar se for um card/bloco clicável genérico de curso
            cards = self._page.locator(".curso, .card, [class*='course']")
            if await cards.count() > 0 and await cards.first.is_visible():
                logger.info("Clicando no primeiro card de curso...")
                await asyncio.sleep(random.uniform(1.0, 2.5))
                await cards.first.click()
                await asyncio.sleep(1)
        except Exception as e:
            pass

        selectors = [
            "button:has-text('Entrar')",
            "a:has-text('Entrar')",
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
            "a:has-text('Acessar Ambiente')",
        ]

        for selector in selectors:
            locator = self._page.locator(selector).first
            if await locator.count() > 0 and await locator.is_visible():
                try:
                    logger.info("Clicando em botão de continuidade: %s", selector)
                    await asyncio.sleep(random.uniform(1.0, 2.5))
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

    async def dismiss_home_popups(self) -> None:
        """Fecha eventuais popups, modais promocionais ou de avisos estruturais da tela inicial."""
        if not self._page:
            return

        logger.info("Aguardando carregamento de possíveis popups da Home...")
        await asyncio.sleep(random.uniform(2.5, 4.0)) # Popups costumam ter animações de entrada
        
        selectors = [
            "button:has-text('✕')",
            "button:has-text('X')",
            "button:has-text('Fechar')",
            "a:has-text('Fechar')",
            "button:has-text('FECHAR')",
            "a:has-text('FECHAR')",
            "[aria-label*='Fechar' i]",
            ".close",
            ".btn-close",
            "button[class*='close' i]",
            "button[id*='fechar' i]"
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
                        logger.info("Popup detectado e visível. Fechando... (%s)", selector)
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                        await locator.click(timeout=3000)
                        closed_any = True
                        await asyncio.sleep(random.uniform(1.0, 2.0))  # aguarda animação de saída/entrada do póximo
                        break  # sai do for e começa o while novamente em busca de mais popups
                except Exception:
                    continue

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
