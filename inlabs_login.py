"""Script de login no portal INLABS (Imprensa Nacional) via terminal."""

from __future__ import annotations

import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ACCESS_URL = "https://inlabs.in.gov.br/acessar.php"
LOGIN_URL = "https://inlabs.in.gov.br/logar.php"
INDEX_URL = "https://inlabs.in.gov.br/index.php?p="


def login() -> requests.Session:
    load_dotenv()

    email = __import__("os").getenv("INLABS_EMAIL", "")
    password = __import__("os").getenv("INLABS_PASSWORD", "")

    if not email or not password:
        print("Erro: configure INLABS_EMAIL e INLABS_PASSWORD no arquivo .env")
        sys.exit(1)

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36"
        ),
    })

    # Passo 1: acessar a página de login para pegar cookies de sessão (PHPSESSID, etc.)
    print("Acessando página de login...")
    resp = session.get(ACCESS_URL)
    print(f"  Página de login: {resp.status_code} ({len(resp.cookies)} cookies)")

    # Passo 2: POST com credenciais
    print(f"Logando como {email}...")
    resp = session.post(
        LOGIN_URL,
        data={"email": email, "password": password},
        allow_redirects=True,
    )

    if resp.status_code == 200 and "Sair" in resp.text:
        print("Login realizado com sucesso!")
        session_cookie = session.cookies.get("inlabs_session_cookie")
        if session_cookie:
            print(f"  Sessão: inlabs_session_cookie={session_cookie[:20]}...")
        return session

    if "Manutenção" in resp.text or resp.status_code == 502:
        print("Erro: sistema em manutenção (502). Tente novamente mais tarde.")
        sys.exit(1)

    if "inválid" in resp.text.lower() or "incorret" in resp.text.lower():
        print("Erro: credenciais inválidas.")
        sys.exit(1)

    print(f"Erro inesperado: status {resp.status_code}")
    sys.exit(1)


if __name__ == "__main__":
    session = login()
    resp = session.get(INDEX_URL)
    print(f"Página principal: {resp.status_code} ({len(resp.text)} bytes)")
