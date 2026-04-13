import os
import pytest
from pathlib import Path
from dotenv import load_dotenv

@pytest.fixture(scope="session", autouse=True)
def load_env():
    # Assegura que as credenciais do .env da raiz do projeto estarão ativas
    load_dotenv(Path(__file__).parent.parent / ".env")

@pytest.fixture(scope="session", autouse=True)
def isolated_browser_state(tmp_path_factory):
    """
    Gera as flags que sobreescrevem os caminhos de sessão, para que o teste 
    E2E crie o seu próprio diretório sem destruir o session cookie do usuário (state.json main).
    """
    tmp_env = tmp_path_factory.mktemp("ava_test_sandbox")
    
    os.environ["AVA_PROFILE_DIR"] = str(tmp_env / "test_profile")
    os.environ["AVA_STATE_FILE"]  = str(tmp_env / "test_state.json")
    os.environ["HEADLESS"] = "true"
    os.environ["MANUAL_LOGIN_TIMEOUT"] = "120"

    yield tmp_env
