# my-dou (DOU Downloader) 🚀

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Package Manager: uv](https://img.shields.io/badge/package%20manager-uv-6140cc.svg)](https://github.com/astral-sh/uv)
[![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen.svg)](tests/)
[![Status](https://img.shields.io/badge/status-WAF%20blocked-red.svg)]()

## ⚠️ AVISO IMPORTANTE: WAF do INLABS

**Este projeto está temporariamente inoperacional.**

O portal INLABS implementou um WAF (Web Application Firewall) muito agressivo que bloqueia:
- Requests diretas (curl, requests, curl-cffi)
- Playwright em modo headless
- Acesso originado de VPS/servidores

### Possíveis Soluções (NÃO TESTADAS)

1. **Executar em máquina local** (não VPS)
2. **Usar Playwright em modo não-headless** (requiere GUI/X11)
3. **Proxy residencial** (data center IPs são bloqueados)
4. **API oficial** (se disponível no futuro)

Se você encontrar uma solução que funcione, por favor abra um PR.

---

Ferramenta CLI para download automatizado de arquivos do Diário Oficial da União (DOU) via portal INLABS (Imprensa Nacional).

## ✨ Funcionalidades (QUANDO OPERACIONAL)

- **Download Híbrido:** Usa Playwright para autenticação (bypass de TLS fingerprinting) e `requests` para downloads eficientes.
- **Resiliência:** Extração de dados via BeautifulSoup (DOM) em vez de Regex.
- **Formatos Suportados:** PDFs assinados e arquivos XML (ZIP).
- **Cobertura Completa:** Suporte a edições extras (letras A-Z) e todas as seções (DO1, DO2, DO3, etc.).
- **Segurança:** Gestão de credenciais via variáveis de ambiente (.env).
- **Qualidade:** Suíte de testes unitários com >90% de cobertura.

## 🛠️ Requisitos

- Python >= 3.13
- [uv](https://github.com/astral-sh/uv) (gerenciador de pacotes)
- **NÃO funciona em VPS** devido ao WAF do INLABS

## 🚀 Instalação

1. Clone o repositório:
```bash
git clone https://github.com/prof-ramos/my-dou.git
cd my-dou
```

2. Instale as dependências:
```bash
uv sync
uv run playwright install chromium
```

3. Configure as credenciais no arquivo `.env`:
```bash
echo "INLABS_EMAIL=seu_email@exemplo.com" > .env
echo "INLABS_PASSWORD=sua_senha" >> .env
```

## 📖 Uso

⚠️ **Os comandos abaixo NÃO funcionarão até que o WAF seja contornado.**

### Listar datas disponíveis
```bash
uv run python main.py dates
```

### Listar arquivos de uma data específica
```bash
uv run python main.py files 2026-04-08
```

### Baixar PDFs assinados
```bash
uv run python main.py pdf 2026-04-08
```

### Baixar arquivos XML (ZIP)
```bash
uv run python main.py zip 2026-04-08 --sections DO1,DO2
```

### Buscar publicações do MRE em arquivos XML
```bash
uv run python main.py mre 2026-04-08 --download
```

## 🧪 Testes

O projeto utiliza `pytest` para testes unitários isolados da rede.
```bash
uv run pytest
```

Para ver o relatório de cobertura:
```bash
uv run pytest --cov=inlabs_client
```

## 📄 Licença
Este projeto é de uso educacional e profissional para automação de processos de clipping e monitoramento oficial.
