# degree-sync

Assistente de estudos e copiloto para estudantes de graduação EAD, focado em automação de processos acadêmicos, geração de resumos via RAG (Retrieval-Augmented Generation) e monitoramento de prazos.

## Descrição

O degree-sync foi concebido para resolver a falta de tempo de estudantes que conciliam trabalho em tempo integral com o ensino superior. O sistema automatiza a coleta de materiais didáticos, monitora datas de entrega e utiliza inteligência artificial para facilitar o consumo de conteúdo denso através de uma interface de chat e notificações proativas.

## Funcionalidades Planejadas

- Coleta automatizada de trilhas de aprendizagem e livros da disciplina via Playwright.
- Processamento e armazenamento de conteúdos em banco de dados vetorial (Supabase/pgvector).
- Chatbot para consultas rápidas sobre o material didático utilizando RAG.
- Notificações de prazos e lembretes via integração com WhatsApp (Evolution API).
- Geração automática de simulados baseados no conteúdo das provas presenciais.

## Stack Tecnológica

- Linguagem: Python 3.12+
- Gerenciador de pacotes: uv
- Automação de navegador: Playwright
- Banco de dados e Vetores: Supabase (PostgreSQL + pgvector)
- Interface de API: FastAPI
- Containerização: Docker e Dev Containers

## Estrutura do Projeto

degree-sync/
├── .devcontainer/     # Configurações do ambiente de desenvolvimento isolado
├── docs/               # Documentação técnica e especificações
├── scripts/            # Scripts de utilidade e manutenção
├── src/                # Código-fonte da aplicação
│   ├── api/            # Endpoints e lógica de servidor
│   ├── scraper/        # Scripts de extração do AVA (Playwright)
│   ├── engine/         # Lógica de embeddings e integração com LLM
│   └── notify/         # Sistema de mensageria e notificações
├── docker-compose.yml  # Orquestração dos serviços locais
└── pyproject.toml      # Configurações do projeto e dependências (uv)

## Configuração do Ambiente

O projeto está configurado para ser executado dentro de um Dev Container, garantindo que todas as dependências do sistema operacional necessárias para o Playwright e o Python estejam presentes.

1. Certifique-se de ter o Docker instalado.
2. No VS Code, abra a pasta do projeto.
3. Quando solicitado, selecione "Reopen in Container".
4. O ambiente instalará automaticamente as dependências utilizando o uv.

### Uso do uv

Para gerenciar dependências ou executar scripts dentro do container:

- Instalar dependências: uv sync
- Adicionar nova dependência: uv add [pacote]
- Executar o scraper localmente: uv run python src/scraper/main.py

## Variáveis de Ambiente

Crie um arquivo .env na raiz do projeto com as seguintes chaves:

- AVA_USER: Usuário de acesso ao portal acadêmico.
- AVA_PASS: Senha de acesso ao portal acadêmico.
- SUPABASE_URL: URL do seu projeto no Supabase.
- SUPABASE_KEY: Chave de API do Supabase.
- WHATSAPP_API_URL: Endereço da instância da Evolution API.
- WHATSAPP_API_TOKEN: Token de autenticação da API de mensagens.
