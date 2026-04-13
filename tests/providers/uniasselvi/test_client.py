"""
Testes unitários do UniasselviClient — cobrem:
  • login(): fluxo completo (sessão válida, login novo, salvar state)
  • dismiss_home_popups(): delegação ao authenticator
  • close(): encerramento via browser.close()
  • Context manager (__aenter__ / __aexit__)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from src.scraper.providers.uniasselvi.client import UniasselviClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_client() -> UniasselviClient:
    """Cria um UniasselviClient com browser e authenticator mockados."""
    client = UniasselviClient(headless=True, manual_login_timeout=10)

    # Mock do BrowserManager
    client.browser = AsyncMock()
    client.browser.start = AsyncMock(return_value=AsyncMock())  # page
    client.browser.save_state = AsyncMock()
    client.browser.close = AsyncMock()
    client.browser.page = MagicMock()
    client.browser.page.url = "https://ava2.uniasselvi.com.br/home"

    # Mock do Authenticator
    client.authenticator = AsyncMock()
    client.authenticator.is_logged_in = AsyncMock(return_value=False)
    client.authenticator.execute_login = AsyncMock(return_value=True)
    client.authenticator.dismiss_home_popups = AsyncMock()

    return client


# ---------------------------------------------------------------------------
# Testes — login()
# ---------------------------------------------------------------------------

class TestUniasselviClientLogin:
    """Testa o fluxo de login do UniasselviClient."""

    @pytest.mark.asyncio
    async def test_login_with_existing_session_skips_execute(self):
        """Se já está logado, login() deve retornar True sem chamar execute_login."""
        client = _make_mock_client()
        client.authenticator.is_logged_in.return_value = True

        result = await client.login()

        assert result is True
        client.authenticator.execute_login.assert_not_awaited()
        client.browser.save_state.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_login_from_scratch_calls_execute_and_saves(self):
        """Sem sessão, login() deve chamar execute_login e salvar state no sucesso."""
        client = _make_mock_client()
        client.authenticator.is_logged_in.return_value = False
        client.authenticator.execute_login.return_value = True

        result = await client.login()

        assert result is True
        client.authenticator.execute_login.assert_awaited_once()
        client.browser.save_state.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_login_failure_does_not_save_state(self):
        """Se execute_login falhar, login() não deve salvar state."""
        client = _make_mock_client()
        client.authenticator.is_logged_in.return_value = False
        client.authenticator.execute_login.return_value = False

        result = await client.login()

        assert result is False
        client.authenticator.execute_login.assert_awaited_once()
        client.browser.save_state.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_login_raises_if_not_started(self):
        """login() sem start() prévio deve levantar RuntimeError."""
        client = UniasselviClient(headless=True)
        # authenticator é None pois start() não foi chamado
        with pytest.raises(RuntimeError, match="start"):
            await client.login()


# ---------------------------------------------------------------------------
# Testes — dismiss_home_popups()
# ---------------------------------------------------------------------------

class TestUniasselviClientDismissPopups:
    """Testa o dismiss de popups na Home."""

    @pytest.mark.asyncio
    async def test_dismiss_delegates_to_authenticator(self):
        """dismiss_home_popups() deve delegar para authenticator.dismiss_home_popups()."""
        client = _make_mock_client()

        await client.dismiss_home_popups()

        client.authenticator.dismiss_home_popups.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dismiss_noop_without_authenticator(self):
        """Sem authenticator, dismiss_home_popups() não deve crashar."""
        client = UniasselviClient(headless=True)
        # Não deve levantar exceção
        await client.dismiss_home_popups()


# ---------------------------------------------------------------------------
# Testes — close()
# ---------------------------------------------------------------------------

class TestUniasselviClientClose:
    """Testa o encerramento gracioso do UniasselviClient."""

    @pytest.mark.asyncio
    async def test_close_delegates_to_browser(self):
        """close() deve chamar browser.close()."""
        client = _make_mock_client()

        await client.close()

        client.browser.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# Testes — Context Manager
# ---------------------------------------------------------------------------

class TestUniasselviClientContextManager:
    """Testa o uso como async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_calls_start_and_close(self):
        """async with client deve chamar start() na entrada e close() na saída."""
        client = _make_mock_client()
        client.start = AsyncMock()
        client.close = AsyncMock()

        async with client as c:
            assert c is client
            client.start.assert_awaited_once()

        client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_context_manager_closes_on_exception(self):
        """Mesmo com exceção, close() deve ser chamado."""
        client = _make_mock_client()
        client.start = AsyncMock()
        client.close = AsyncMock()

        with pytest.raises(ValueError):
            async with client:
                raise ValueError("test error")

        client.close.assert_awaited_once()
