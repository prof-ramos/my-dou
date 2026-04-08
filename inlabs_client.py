"""Cliente para autenticação e download de arquivos do portal INLABS (DOU).

Usa Playwright (headless) para o login, pois o servidor bloqueia
login via requests/curl com fingerprinting TLS. Após login,
usa requests para listagem e downloads (mais eficiente).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import requests
from dotenv import load_dotenv

BASE_URL = "https://inlabs.in.gov.br"
ACCESS_URL = f"{BASE_URL}/acessar.php"
LOGIN_URL = f"{BASE_URL}/logar.php"
INDEX_URL = f"{BASE_URL}/index.php?p="

# Header obrigatório pelo INLABS para downloads (hex de "script")
ORIGEM_HEADER = "736372697074"

# Seções DOU disponíveis
PdfSection = Literal["do1", "do2", "do3"]
ZipSection = Literal["DO1", "DO2", "DO3", "DO1E", "DO2E", "DO3E"]

PDF_SECTIONS: list[PdfSection] = ["do1", "do2", "do3"]
ZIP_SECTIONS: list[ZipSection] = ["DO1", "DO2", "DO3", "DO1E", "DO2E", "DO3E"]
PDF_EXTRA_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Padrão de data YYYY-MM-DD
DATE_RE = re.compile(r"\?p=(\d{4}-\d{2}-\d{2})")


class InlabsError(Exception):
    """Erro na comunicação com o portal INLABS."""


class InlabsClient:
    """Cliente para interação com o portal INLABS."""

    def __init__(self, email: str, password: str) -> None:
        self._email = email
        self._password = password
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/146.0.0.0 Safari/537.36"
            ),
        })

    @classmethod
    def from_env(cls) -> InlabsClient:
        """Cria cliente a partir de variáveis de ambiente (.env)."""
        load_dotenv()
        import os

        email = os.getenv("INLABS_EMAIL", "")
        password = os.getenv("INLABS_PASSWORD", "")
        if not email or not password:
            raise InlabsError(
                "Configure INLABS_EMAIL e INLABS_PASSWORD no .env"
            )
        return cls(email, password)

    @property
    def session_cookie(self) -> str | None:
        """Retorna o cookie de sessão INLABS."""
        return self._session.cookies.get("inlabs_session_cookie")

    def login(self) -> None:
        """Autentica no portal INLABS via Playwright headless. Retry automático."""
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                self._do_login_playwright()
                return
            except Exception as e:
                if attempt < max_attempts:
                    print(f"  Tentativa {attempt}/{max_attempts} falhou: {e}. Retentando...")
                else:
                    raise

    def _do_login_playwright(self) -> None:
        """Executa login via Playwright headless."""
        from playwright.sync_api import sync_playwright

        print("Autenticando via browser headless...")
        cookies: list[dict[str, str]] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/146.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            try:
                # Acessar página de login
                page.goto(ACCESS_URL, wait_until="networkidle", timeout=30000)

                # Verificar se não está em manutenção
                if "Manutenção" in page.content():
                    raise InlabsError("Sistema em manutenção.")

                # O formulário de "Acessar" é o segundo form (índice 1)
                login_form = page.locator("form").nth(1)
                login_form.locator('input[name="email"]').fill(self._email)
                login_form.locator('input[name="password"]').fill(self._password)
                login_form.locator('input[type="submit"]').click()

                # Aguardar navegação completar
                page.wait_for_load_state("networkidle", timeout=30000)

                # Verificar login
                content = page.content()
                if "Sair" not in content:
                    if "Manutenção" in content:
                        raise InlabsError("Sistema em manutenção.")
                    if "inválid" in content.lower() or "incorret" in content.lower():
                        raise InlabsError("Credenciais inválidas.")
                    raise InlabsError("Falha no login: botão Sair não encontrado.")

                # Extrair cookies e transferir para requests.Session
                cookies = context.cookies()
            finally:
                browser.close()

        for cookie in cookies:
            self._session.cookies.set(cookie["name"], cookie["value"])

        if not self.session_cookie:
            raise InlabsError("Cookie de sessão não recebido após login.")

        print(f"Autenticado: {self.session_cookie[:20]}...")

    def list_available_dates(self) -> list[str]:
        """Retorna lista de datas disponíveis (mais recente primeiro)."""
        resp = self._session.get(INDEX_URL, timeout=30)
        if resp.status_code != 200:
            raise InlabsError(f"Erro ao listar datas: {resp.status_code}")

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "lxml")
        
        dates = []
        for a in soup.find_all("a", href=DATE_RE):
            match = DATE_RE.search(a.get("href", ""))
            if match:
                dates.append(match.group(1))
        return sorted(set(dates), reverse=True)

    def list_files(self, date_str: str) -> list[dict[str, str]]:
        """Lista arquivos disponíveis para uma data específica.

        Retorna lista de dicts com chaves: name, url, size, modified.
        """
        url = f"{INDEX_URL}{date_str}"
        resp = self._session.get(url, timeout=30)
        if resp.status_code != 200:
            raise InlabsError(f"Erro ao listar arquivos de {date_str}: {resp.status_code}")

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "lxml")
        
        files = []
        for a in soup.find_all("a", href=re.compile(r"dl=")):
            href = a.get("href", "")
            filename = href.split("dl=")[-1]
            
            td_parent = a.find_parent("td")
            if td_parent:
                next_tds = td_parent.find_next_siblings("td")
                size = next_tds[0].get_text(strip=True) if len(next_tds) > 0 else ""
                modified = next_tds[1].get_text(strip=True) if len(next_tds) > 1 else ""
            else:
                size = ""
                modified = ""

            link = href.replace("&amp;", "&")
            full_url = f"{BASE_URL}/{link.lstrip('/')}"
            
            files.append({
                "name": filename,
                "url": full_url,
                "size": size,
                "modified": modified,
            })
        return files

    def download_pdf(
        self,
        date_str: str,
        sections: list[PdfSection] | None = None,
        output_dir: str | Path = ".",
        include_extras: bool = True,
    ) -> list[Path]:
        """Download de PDFs assinados do DOU.

        Args:
            date_str: Data no formato YYYY-MM-DD.
            sections: Seções a baixar (do1, do2, do3). Padrão: todas.
            output_dir: Diretório de saída.
            include_extras: Se True, tenta baixar edições extras (A-Z).

        Returns:
            Lista de caminhos dos arquivos baixados.
        """
        if not self.session_cookie:
            raise InlabsError("Não autenticado. Chame login() primeiro.")

        sections = sections or PDF_SECTIONS
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        download_headers = {
            "origem": ORIGEM_HEADER,
            "Cookie": f"inlabs_session_cookie={self.session_cookie}",
        }

        d = date_str.replace("-", "_")
        downloaded: list[Path] = []

        for section in sections:
            filename = f"{d}_ASSINADO_{section}.pdf"
            url = f"{INDEX_URL}{date_str}&dl={filename}"
            path = self._download_file(url, filename, output_dir, download_headers)
            if path:
                downloaded.append(path)

            if include_extras:
                for letter in PDF_EXTRA_LETTERS:
                    extra_filename = f"{d}_ASSINADO_{section}_extra_{letter}.pdf"
                    url = f"{INDEX_URL}{date_str}&dl={extra_filename}"
                    path = self._download_file(
                        url, extra_filename, output_dir, download_headers
                    )
                    if path:
                        downloaded.append(path)

        return downloaded

    def download_zip(
        self,
        date_str: str,
        sections: list[ZipSection] | None = None,
        output_dir: str | Path = ".",
    ) -> list[Path]:
        """Download de ZIPs com XML do DOU.

        Args:
            date_str: Data no formato YYYY-MM-DD.
            sections: Seções a baixar (DO1, DO2, DO3, DO1E, etc.). Padrão: todas.
            output_dir: Diretório de saída.

        Returns:
            Lista de caminhos dos arquivos baixados.
        """
        if not self.session_cookie:
            raise InlabsError("Não autenticado. Chame login() primeiro.")

        sections = sections or ZIP_SECTIONS
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        download_headers = {
            "origem": ORIGEM_HEADER,
            "Cookie": f"inlabs_session_cookie={self.session_cookie}",
        }

        downloaded: list[Path] = []

        for section in sections:
            filename = f"{date_str}-{section}.zip"
            url = f"{INDEX_URL}{date_str}&dl={filename}"
            path = self._download_file(url, filename, output_dir, download_headers)
            if path:
                downloaded.append(path)

        return downloaded

    def _download_file(
        self,
        url: str,
        filename: str,
        output_dir: Path,
        headers: dict[str, str],
    ) -> Path | None:
        """Faz download de um arquivo. Retorna o caminho ou None se 404."""
        resp = self._session.get(url, headers=headers, timeout=120)

        if resp.status_code == 404:
            return None

        if resp.status_code != 200:
            print(f"  [ERRO] {filename}: HTTP {resp.status_code}")
            return None

        # Verificar se recebeu HTML (erro) em vez do arquivo
        content_type = resp.headers.get("Content-Type", "")
        if "text/html" in content_type:
            print(f"  [ERRO] {filename}: recebeu HTML em vez do arquivo")
            return None

        filepath = output_dir / filename
        filepath.write_bytes(resp.content)
        size_mb = len(resp.content) / (1024 * 1024)
        print(f"  [OK] {filename} ({size_mb:.1f} MB)")
        return filepath
