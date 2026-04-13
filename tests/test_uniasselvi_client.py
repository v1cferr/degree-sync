import pytest
import os
from src.scraper.providers.uniasselvi.client import UniasselviClient

@pytest.mark.asyncio
async def test_full_login_and_dismiss_flow():
    """
    Testa o fluxo crítico end-to-end:
    - Logar a partir do zero (inserido CPF/Senha, clicando e salvando state)
    - Pular na Home e fechar popups
    - Reiniciar o navegador pra ver se os cookies carregam e desviam do form!
    """
    assert os.getenv("AVA_USER"), "Credencial AVA_USER não encontrada no .env para o teste E2E."
    assert os.getenv("AVA_PASS"), "Credencial AVA_PASS não encontrada no .env para o teste E2E."

    # 1. Flow Inédito sem Cache 
    client = UniasselviClient(headless=True)
    await client.start()
    
    try:
        assert await client.authenticator.is_logged_in() is False, "O client zeroed achou que estava logado!"
        
        success = await client.login()
        assert success is True, "Flow E2E de login falhou. Pode ser Captcha ou Layout alterado."
        assert "ava2.uniasselvi.com.br" in client.browser.page.url
        
        await client.dismiss_home_popups()
    finally:
        await client.close()

    # 2. Flow via Restauração de Sessão
    client_cached = UniasselviClient(headless=True)
    await client_cached.start()
    
    try:
        assert await client_cached.authenticator.is_logged_in() is True, "Falha na restauração do state.json persistido."
        success_cached = await client_cached.login()
        assert success_cached is True
    finally:
        await client_cached.close()
