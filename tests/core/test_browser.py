"""
Testes unitários do BrowserManager — cobrem:
  • start(): criação de contexto, restore de cookies, e obtenção de page
  • save_state(): persistência do state.json
  • close(): encerramento gracioso do contexto e playwright
"""
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from src.scraper.core.browser import BrowserManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_playwright():
    """Cria mocks completos do Playwright: playwright, context, page."""
    pw = AsyncMock()
    context = AsyncMock()
    page = AsyncMock()
    page.url = "about:blank"

    # launch_persistent_context retorna o context mock
    pw.chromium.launch_persistent_context.return_value = context
    context.pages = [page]
    context.add_cookies = AsyncMock()
    context.storage_state = AsyncMock()
    context.close = AsyncMock()

    return pw, context, page


def _patch_async_playwright(pw_mock):
    """
    Cria o patch correto para async_playwright().
    async_playwright() retorna um objeto cujo .start() é awaitable e retorna o pw.
    """
    ap_instance = MagicMock()
    ap_instance.start = AsyncMock(return_value=pw_mock)

    patcher = patch("src.scraper.core.browser.async_playwright", return_value=ap_instance)
    return patcher


# ---------------------------------------------------------------------------
# Testes — start()
# ---------------------------------------------------------------------------

class TestBrowserManagerStart:
    """Testa a inicialização do BrowserManager."""

    @pytest.mark.asyncio
    async def test_start_creates_context_and_returns_page(self, tmp_path):
        """start() deve lançar um contexto persistente e retornar a primeira page."""
        pw_mock, ctx_mock, page_mock = _make_mock_playwright()
        mgr = BrowserManager(headless=True)

        with _patch_async_playwright(pw_mock):
            with patch.dict("os.environ", {
                "AVA_PROFILE_DIR": str(tmp_path / "profile"),
                "AVA_STATE_FILE": str(tmp_path / "state.json"),
            }):
                page = await mgr.start()

        assert page is page_mock
        pw_mock.chromium.launch_persistent_context.assert_awaited_once()
        # Deve ter criado o diretório de perfil
        assert (tmp_path / "profile").exists()

    @pytest.mark.asyncio
    async def test_start_restores_cookies_from_state_file(self, tmp_path):
        """Se state.json existir com cookies, start() deve injetá-los no contexto."""
        state_file = tmp_path / "state.json"
        cookies = [{"name": "session", "value": "abc123", "domain": ".uniasselvi.com.br", "path": "/"}]
        state_file.write_text(json.dumps({"cookies": cookies}), encoding="utf-8")

        pw_mock, ctx_mock, page_mock = _make_mock_playwright()
        mgr = BrowserManager(headless=True)

        with _patch_async_playwright(pw_mock):
            with patch.dict("os.environ", {
                "AVA_PROFILE_DIR": str(tmp_path / "profile"),
                "AVA_STATE_FILE": str(state_file),
            }):
                await mgr.start()

        ctx_mock.add_cookies.assert_awaited_once_with(cookies)

    @pytest.mark.asyncio
    async def test_start_without_state_file_skips_cookies(self, tmp_path):
        """Sem state.json, start() não deve tentar restaurar cookies."""
        pw_mock, ctx_mock, page_mock = _make_mock_playwright()
        mgr = BrowserManager(headless=True)

        with _patch_async_playwright(pw_mock):
            with patch.dict("os.environ", {
                "AVA_PROFILE_DIR": str(tmp_path / "profile"),
                "AVA_STATE_FILE": str(tmp_path / "nonexistent_state.json"),
            }):
                await mgr.start()

        ctx_mock.add_cookies.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_start_handles_corrupt_state_file(self, tmp_path):
        """Se o state.json estiver corrompido, start() deve continuar sem crashar."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{{invalid json", encoding="utf-8")

        pw_mock, ctx_mock, page_mock = _make_mock_playwright()
        mgr = BrowserManager(headless=True)

        with _patch_async_playwright(pw_mock):
            with patch.dict("os.environ", {
                "AVA_PROFILE_DIR": str(tmp_path / "profile"),
                "AVA_STATE_FILE": str(state_file),
            }):
                page = await mgr.start()

        # Deve retornar a page normalmente mesmo com state corrompido
        assert page is page_mock
        ctx_mock.add_cookies.assert_not_awaited()


# ---------------------------------------------------------------------------
# Testes — save_state()
# ---------------------------------------------------------------------------

class TestBrowserManagerSaveState:
    """Testa a persistência de sessão do BrowserManager."""

    @pytest.mark.asyncio
    async def test_save_state_calls_storage_state(self, tmp_path):
        """save_state() deve chamar context.storage_state() com o path correto."""
        pw_mock, ctx_mock, page_mock = _make_mock_playwright()
        mgr = BrowserManager(headless=True)

        state_path = str(tmp_path / "saved_state.json")

        with _patch_async_playwright(pw_mock):
            with patch.dict("os.environ", {
                "AVA_PROFILE_DIR": str(tmp_path / "profile"),
                "AVA_STATE_FILE": state_path,
            }):
                await mgr.start()
                await mgr.save_state()

        ctx_mock.storage_state.assert_awaited_once_with(path=state_path)

    @pytest.mark.asyncio
    async def test_save_state_noop_without_context(self):
        """save_state() sem contexto inicializado não deve dar erro."""
        mgr = BrowserManager(headless=True)
        # Não deve levantar nenhuma exceção
        await mgr.save_state()


# ---------------------------------------------------------------------------
# Testes — close()
# ---------------------------------------------------------------------------

class TestBrowserManagerClose:
    """Testa o encerramento gracioso do BrowserManager."""

    @pytest.mark.asyncio
    async def test_close_shuts_down_context_and_playwright(self, tmp_path):
        """close() deve encerrar o contexto e parar o Playwright."""
        pw_mock, ctx_mock, page_mock = _make_mock_playwright()
        mgr = BrowserManager(headless=True)

        with _patch_async_playwright(pw_mock):
            with patch.dict("os.environ", {
                "AVA_PROFILE_DIR": str(tmp_path / "profile"),
                "AVA_STATE_FILE": str(tmp_path / "state.json"),
            }):
                await mgr.start()
                await mgr.close()

        ctx_mock.close.assert_awaited_once()
        pw_mock.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_noop_without_start(self):
        """close() sem start() prévio não deve crashar."""
        mgr = BrowserManager(headless=True)
        # Não deve levantar exceção
        await mgr.close()
