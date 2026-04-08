# my-dou (DOU Downloader) 🚀

Ferramenta CLI para download automatizado de arquivos do Diário Oficial da União (DOU) via portal INLABS (Imprensa Nacional).

## ✨ Funcionalidades

- **Download Híbrido:** Usa Playwright para autenticação (bypass de TLS fingerprinting) e `requests` para downloads eficientes.
- **Resiliência:** Extração de dados via BeautifulSoup (DOM) em vez de Regex.
- **Formatos Suportados:** PDFs assinados e arquivos XML (ZIP).
- **Cobertura Completa:** Suporte a edições extras (letras A-Z) e todas as seções (DO1, DO2, DO3, etc.).
- **Segurança:** Gestão de credenciais via variáveis de ambiente (.env).
- **Qualidade:** Suíte de testes unitários com >90% de cobertura.

## 🛠️ Requisitos

- Python >= 3.13
- [uv](https://github.com/astral-sh/uv) (gerenciador de pacotes)

## 🚀 Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/prof-ramos/my-dou.git
   cd my-dou
   ```

2. Instale as dependências e configure o ambiente:
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
