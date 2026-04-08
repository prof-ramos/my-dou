# Projeto: my-dou (DOU Downloader)

## Visão Geral
O **my-dou** é uma ferramenta de automação para download de arquivos do Diário Oficial da União (DOU) através do portal INLABS (Imprensa Nacional). O projeto foca em extrair PDFs assinados e arquivos XML (em formato ZIP) de forma programática.

### Arquitetura e Tecnologias
- **Linguagem:** Python (>= 3.13)
- **Gerenciador de Pacotes:** `uv` (utiliza `pyproject.toml` e `uv.lock`)
- **Autenticação:** Híbrida. Usa **Playwright (Chromium)** em modo headless para realizar o login e contornar proteções de fingerprinting TLS, transferindo os cookies de sessão para o `requests`.
- **Parsing:** BeautifulSoup (bs4) com parser `lxml` para extração resiliente de dados do HTML (DOM).
- **Downloads e Listagem:** `requests` para maior eficiência após a autenticação.
- **Configuração:** Variáveis de ambiente via `.env` (usando `python-dotenv`).

## Estrutura de Arquivos Principal
- `main.py`: Ponto de entrada da CLI (comandos: `dates`, `files`, `pdf`, `zip`, `mre`).
- `inlabs_client.py`: Core do projeto. Contém a classe `InlabsClient` que gerencia a sessão, login via Playwright e lógica de download.
- `xml_processor.py`: Módulo especializado em processamento de arquivos XML do DOU, incluindo busca por padrões (como publicações do MRE).
- `tests/`: Suíte de testes unitários com fixtures HTML/XML para garantir >90% de cobertura isolada da rede.

## Comandos Úteis

### Ambiente e Testes
```bash
# Sincronizar ambiente e instalar dependências
uv sync

# Instalar navegadores necessários para o Playwright
uv run playwright install chromium

# Executar testes unitários
uv run pytest
```

### Execução da CLI
```bash
# Listar as últimas 10 datas disponíveis
uv run python main.py dates

# Listar arquivos de uma data específica
uv run python main.py files 2026-04-08

# Baixar PDFs assinados de uma data
uv run python main.py pdf 2026-04-08

# Baixar ZIPs (XML) de seções específicas
uv run python main.py zip 2026-04-08 --sections DO1,DO2

# Buscar e opcionalmente baixar publicações do MRE em XMLs
uv run python main.py mre 2026-04-08 --download
```

## Convenções de Desenvolvimento
- **Python:** Sempre use `from __future__ import annotations`.
- **Tipagem:** Utilize Type Hints em todas as funções e métodos públicos.
- **Linting:** Prefira `ruff` para formatação e linting.
- **Segurança:** Nunca versionar o arquivo `.env` ou a pasta `.omc/`. As credenciais `INLABS_EMAIL` e `INLABS_PASSWORD` devem ser mantidas localmente.

## Integrações MCP
- **Context7:** Utilize o MCP `context7-mcp` para consultar documentações de bibliotecas como `playwright`, `curl-cffi` ou `requests` quando necessário.
