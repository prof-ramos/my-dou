"""Cliente para autenticação e download de arquivos do portal INLABS (DOU)."""

from __future__ import annotations

import re
import time
from datetime import date
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

MAX_RETRIES = 3
RETRY_DELAY = 10  # segundos

# Seções DOU disponíveis
PdfSection = Literal["do1", "do2", "do3"]
ZipSection = Literal["DO1", "DO2", "DO3", "DO1E", "DO2E", "DO3E"]

PDF_SECTIONS: list[PdfSection] = ["do1", "do2", "do3"]
ZIP_SECTIONS: list[ZipSection] = ["DO1", "DO2", "DO3", "DO1E", "DO2E", "DO3E"]
PDF_EXTRA_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


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
        """Autentica no portal INLABS (2 passos: GET + POST). Retry automático em caso de manutenção."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self._do_login()
                return
            except InlabsError as e:
                if "manutenção" in str(e).lower() and attempt < MAX_RETRIES:
                    print(f"  Servidor em manutenção, aguardando {RETRY_DELAY}s... (tentativa {attempt}/{MAX_RETRIES})")
                    time.sleep(RETRY_DELAY)
                    self._session = requests.Session()
                    self._session.headers.update({
                        "User-Agent": (
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/146.0.0.0 Safari/537.36"
                        ),
                    })
                else:
                    raise

    def _do_login(self) -> None:
        """Executa o fluxo de login."""
        # Passo 1: GET para obter cookies de sessão PHP
        resp = self._session.get(ACCESS_URL, timeout=30)
        if resp.status_code != 200:
            raise InlabsError(
                f"Erro ao acessar página de login: {resp.status_code}"
            )

        # Passo 2: POST com credenciais
        resp = self._session.post(
            LOGIN_URL,
            data={"email": self._email, "password": self._password},
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            allow_redirects=True,
            timeout=30,
        )

        if resp.status_code == 200 and "Sair" in resp.text:
            if not self.session_cookie:
                raise InlabsError(
                    "Login aparentou sucesso mas cookie de sessão não foi recebido"
                )
            return

        if "Manutenção" in resp.text or resp.status_code == 502:
            raise InlabsError("Sistema em manutenção (502). Tente novamente mais tarde.")

        if "inválid" in resp.text.lower() or "incorret" in resp.text.lower():
            raise InlabsError("Credenciais inválidas.")

        raise InlabsError(f"Erro inesperado no login: status {resp.status_code}")

    def list_available_dates(self) -> list[str]:
        """Retorna lista de datas disponíveis (mais recente primeiro)."""
        resp = self._session.get(INDEX_URL, timeout=30)
        if resp.status_code != 200:
            raise InlabsError(f"Erro ao listar datas: {resp.status_code}")

        dates = re.findall(r"index\.php\?p=(\d{4}-\d{2}-\d{2})", resp.text)
        return sorted(set(dates), reverse=True)

    def list_files(self, date_str: str) -> list[dict[str, str]]:
        """Lista arquivos disponíveis para uma data específica.

        Retorna lista de dicts com chaves: name, url, size, modified.
        """
        url = f"{INDEX_URL}{date_str}"
        resp = self._session.get(url, timeout=30)
        if resp.status_code != 200:
            raise InlabsError(f"Erro ao listar arquivos de {date_str}: {resp.status_code}")

        files = []
        pattern = re.findall(
            r'href="([^"]+)"[^>]*>\s*([^<]+)\s*</a>\s*</td>\s*<td>([^<]*)</td>\s*<td>([^<]*)</td>',
            resp.text,
        )
        for link, name, size, modified in pattern:
            link = link.strip()
            name = name.strip()
            if not link or link.startswith(("#", "javascript", "http")):
                continue
            full_url = f"{BASE_URL}/{link.lstrip('/')}"
            files.append({
                "name": name,
                "url": full_url,
                "size": size.strip(),
                "modified": modified.strip(),
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
