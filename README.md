# degree-sync

Copiloto acadêmico para estudantes de graduação EAD — automatiza login, coleta de materiais e interações com o AVA (Ambiente Virtual de Aprendizagem), com foco inicial no portal da **Uniasselvi**.

> [!IMPORTANT]
> **O scraper precisa rodar com navegador visível** (`HEADLESS=false`).
> O site da Uniasselvi usa **Cloudflare Turnstile**, que bloqueia qualquer acesso headless — mesmo com sessão/cookies salvos. O Turnstile intercepta na camada de CDN antes dos cookies do AVA serem avaliados.
> Nas execuções seguintes com `chrome_profile/` salvo, o Cloudflare passa automaticamente (sem CAPTCHA manual) desde que o navegador esteja visível.

## O que faz hoje

O scraper gerencia o ciclo completo de acesso ao AVA:

| Feature | Status | Descrição |
|---|---|---|
| Login automatizado | ✅ Funcional | Preenche CPF/senha, navega pelo fluxo, lida com telas intermediárias |
| Persistência de sessão | ✅ Funcional | Salva perfil do browser em `chrome_profile/` — evita re-login |
| Dismiss de popups | ✅ Funcional | Fecha modais promocionais e notificações da Home |
| Fallback manual | ✅ Funcional | Aguarda interação humana se CAPTCHA aparecer (timeout configurável) |
| Modo headless | ❌ Bloqueado | Cloudflare Turnstile bloqueia — não é contornável sem ferramentas extra |

### Fluxo de Autenticação

```
┌─────────────────────────────────────────────────────┐
│  1ª Execução (sem chrome_profile/)                  │
│                                                     │
│  Abre navegador visível                             │
│  → Cloudflare Turnstile passa (browser real)        │
│  → Preenche CPF/Senha automaticamente               │
│  → Se CAPTCHA manual → aguarda até 300s             │
│  → Login OK → salva chrome_profile/                 │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Execuções seguintes (com chrome_profile/)          │
│                                                     │
│  Abre navegador visível                             │
│  → Cloudflare passa automaticamente                 │
│  → Cookies do AVA restaurados → pula login          │
│  → Direto na Home                                   │
└─────────────────────────────────────────────────────┘
```

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.13+ |
| Gerenciador de pacotes | [uv](https://docs.astral.sh/uv/) |
| Automação de navegador | [Playwright](https://playwright.dev/python/) |
| Configuração | [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) + dotenv |
| Testes | pytest + pytest-asyncio |
| Linting | [Ruff](https://docs.astral.sh/ruff/) |

## Estrutura do Projeto

```
degree-sync/
├── src/
│   ├── config/
│   │   └── settings.py                  # Variáveis de ambiente (pydantic-settings)
│   └── scraper/
│       ├── main.py                       # Entrypoint do scraper
│       ├── core/
│       │   └── browser.py               # BrowserManager (Playwright, cookies, state)
│       └── providers/
│           └── uniasselvi/
│               ├── auth.py              # Fluxo de login + dismiss de popups
│               └── client.py            # UniasselviClient (orquestra browser + auth)
├── tests/
│   ├── conftest.py                      # Fixtures globais (env, sandbox isolado)
│   ├── core/
│   │   └── test_browser.py             # Testes unitários — BrowserManager
│   └── providers/
│       └── uniasselvi/
│           ├── test_client.py           # Testes unitários — UniasselviClient
│           └── test_e2e.py              # Teste E2E contra o site real
├── chrome_profile/                      # Perfil persistente do Chromium (gitignored)
├── .env.example                         # Template de variáveis de ambiente
└── pyproject.toml                       # Dependências e config do projeto
```

## Setup

### Pré-requisitos

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) instalado
- **Ambiente com display gráfico** (não funciona em servidor headless/CI puro)

### Instalação

```bash
git clone https://github.com/v1cferr/degree-sync.git
cd degree-sync

# Instalar dependências (inclui dev)
uv sync

# Instalar os navegadores do Playwright
uv run playwright install chromium
```

### Variáveis de Ambiente

```bash
cp .env.example .env
```

| Variável | Descrição | Default |
|---|---|---|
| `AVA_USER` | CPF de acesso ao portal acadêmico | *(obrigatório)* |
| `AVA_PASS` | Senha de acesso ao portal acadêmico | *(obrigatório)* |
| `HEADLESS` | Rodar sem interface gráfica (**não recomendado**) | `false` |
| `MANUAL_LOGIN_TIMEOUT` | Tempo máximo (segundos) aguardando CAPTCHA manual | `300` |

## Comandos Úteis

### Scraper

```bash
# Rodar o scraper (navegador visível — modo recomendado)
uv run python main.py
```

### Testes

```bash
# Testes unitários — rápido, sem browser (padrão)
uv run pytest tests/ -v

# Testes E2E contra o site real (precisa de display + credenciais)
uv run pytest tests/ -v -m e2e

# Todos os testes (unitários + E2E)
uv run pytest tests/ -v -m ''

# Por módulo
uv run pytest tests/core/ -v                        # BrowserManager
uv run pytest tests/providers/uniasselvi/ -v         # Uniasselvi
```

### Linting

```bash
uv run ruff check .              # Verificar
uv run ruff check . --fix        # Corrigir
```

## Cobertura de Testes

| Módulo | Testes | Tipo |
|---|---|---|
| `BrowserManager` — start, save_state, close | 8 | Unitário (mocks) |
| `UniasselviClient` — login, popups, context manager | 9 | Unitário (mocks) |
| Fluxo completo de login + restauração de sessão | 1 | E2E (site real) |

> **Nota:** Testes E2E são excluídos do `pytest` padrão. Use `-m e2e` para rodá-los.

## Por que não funciona em headless?

O site da Uniasselvi está atrás do **Cloudflare Turnstile**, que detecta automação em múltiplas camadas:

- **TLS fingerprint** (JA3/JA4) — a assinatura do handshake do Chromium headless é diferente
- **Hardware attestation** — Canvas/WebGL retornam valores distintos sem GPU real
- **Behavioral analysis** — ausência de movimentos de mouse e padrões humanos
- **`navigator.webdriver`** — mesmo patcheado, há dezenas de outros sinais

O Turnstile bloqueia **na CDN**, antes do servidor do AVA receber a requisição. Mesmo com cookies válidos no `chrome_profile/`, a página de verificação do Cloudflare é exibida primeiro — e o headless não passa.

**Soluções possíveis (futuro):**
- [Camoufox](https://github.com/nichochar/camoufox) — Firefox anti-detect customizado
- [Nodriver](https://github.com/nichochar/nodriver) — automação sem WebDriver
- Proxies residenciais + TLS impersonation

## Funcionalidades Futuras

- Coleta automatizada de trilhas de aprendizagem e livros da disciplina
- Processamento de conteúdos em banco de dados vetorial (Supabase/pgvector)
- Chatbot RAG para consultas rápidas sobre o material didático
- Notificações de prazos via WhatsApp (Evolution API)
- Geração automática de simulados
