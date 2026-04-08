"""Explora e cataloga todos os endpoints úteis do portal INLABS para automação de DOU."""

from __future__ import annotations

import re
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = "https://inlabs.in.gov.br"
ACCESS_URL = f"{BASE}/acessar.php"
LOGIN_URL = f"{BASE}/logar.php"

email = __import__("os").getenv("INLABS_EMAIL")
password = __import__("os").getenv("INLABS_PASSWORD")

session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    ),
})

# Login
print("=" * 60)
print("1. LOGIN")
print("=" * 60)
r = session.get(ACCESS_URL)
print(f"  GET {ACCESS_URL} -> {r.status_code} (cookies: {list(session.cookies.keys())})")

r = session.post(LOGIN_URL, data={"email": email, "password": password}, allow_redirects=False)
print(f"  POST {LOGIN_URL} -> {r.status_code}")
print(f"  Location: {r.headers.get('location', 'N/A')}")
print(f"  Set-Cookie: {[c.name for c in session.cookies]}")

# Seguir redirects manualmente para capturar tudo
url = r.headers.get("location", "")
while url:
    if not url.startswith("http"):
        url = BASE + "/" + url.lstrip("/")
    print(f"  GET {url} -> ", end="")
    r = session.get(url, allow_redirects=False)
    print(f"{r.status_code}")
    url = r.headers.get("location", "")

# Página principal (listagem de datas)
print()
print("=" * 60)
print("2. PÁGINA PRINCIPAL - Listagem de datas")
print("=" * 60)
r = session.get(f"{BASE}/index.php?p=")
print(f"  GET {BASE}/index.php?p= -> {r.status_code} ({len(r.text)} bytes)")

# Extrair datas disponíveis
datas = re.findall(r'index\.php\?p=(\d{4}-\d{2}-\d{2})', r.text)
datas = sorted(set(datas), reverse=True)
print(f"  Datas encontradas: {len(datas)}")
print(f"  Mais recente: {datas[0] if datas else 'N/A'}")
print(f"  Mais antiga: {datas[-1] if datas else 'N/A'}")

# Extrair tamanhos
tamanhos = re.findall(r'(\d{4}-\d{2}-\d{2})</a>\s*</td>\s*<td>([^<]+)</td>', r.text)
print(f"\n  Últimas 5 datas com tamanho:")
for data, tam in tamanhos[:5]:
    print(f"    {data} -> {tam.strip()}")

# Navegar em uma data específica
print()
print("=" * 60)
print("3. LISTAGEM DE ARQUIVOS DE UMA DATA (2026-04-08)")
print("=" * 60)
r = session.get(f"{BASE}/index.php?p=2026-04-08")
print(f"  GET {BASE}/index.php?p=2026-04-08 -> {r.status_code} ({len(r.text)} bytes)")

# Extrair links de arquivos
arquivos = re.findall(r'href="([^"]+)"[^>]*>\s*([^<]+)\s*</a>\s*</td>\s*<td>([^<]*)</td>\s*<td>([^<]*)</td>', r.text)
print(f"  Arquivos/links encontrados: {len(arquivos)}")

if not arquivos:
    # Tentar padrão alternativo
    arquivos = re.findall(r'href="([^"]+)"', r.text)
    print(f"  Todos os links: {len(arquivos)}")
    for link in arquivos[:20]:
        print(f"    {link}")
else:
    for link, nome, tam, data_mod in arquivos[:30]:
        link = link.strip()
        nome = nome.strip()
        tam = tam.strip()
        data_mod = data_mod.strip()
        if link and not link.startswith("http") and not link.startswith("#") and not link.startswith("javascript"):
            full_url = link if link.startswith("http") else BASE + "/" + link.lstrip("/")
            print(f"    {nome} | {tam} | {data_mod} | {full_url}")

# Verificar se há subpastas (seções DOU)
print()
print("=" * 60)
print("4. EXPLORANDO SUBPASTAS (seções DOU)")
print("=" * 60)
# Links que parecem subpastas
subpastas = re.findall(r'href="(index\.php\?p=[^"]+)"', r.text)
for sp in subpastas[:10]:
    full = BASE + "/" + sp.lstrip("/") if not sp.startswith("http") else sp
    print(f"  Subpasta: {sp}")

# Tentar acessar subpasta (ex: seção 1)
for sp in subpastas:
    if sp != "index.php?p=2026-04-08" and sp != "index.php?p=":
        full = BASE + "/" + sp.lstrip("/") if not sp.startswith("http") else sp
        print(f"\n  GET {full} -> ", end="")
        r2 = session.get(full)
        print(f"{r2.status_code} ({len(r2.text)} bytes)")
        # Extrair arquivos dessa subpasta
        sub_arquivos = re.findall(r'href="([^"]+\.zip[^"]*)"', r2.text)
        if not sub_arquivos:
            sub_arquivos = re.findall(r'href="([^"]+\.xml[^"]*)"', r2.text)
        if not sub_arquivos:
            sub_arquivos = re.findall(r'href="([^"]+)"', r2.text)
        print(f"  Links encontrados: {len(sub_arquivos)}")
        for sa in sub_arquivos[:10]:
            if sa and not sa.startswith("#") and not sa.startswith("javascript"):
                sa_full = sa if sa.startswith("http") else BASE + "/" + sa.lstrip("/")
                print(f"    {sa_full}")
        break  # só a primeira subpasta

# Tentar padrões de URL conhecidos para XML/PDF
print()
print("=" * 60)
print("5. TESTANDO PADRÕES DE URL PARA DOWNLOAD")
print("=" * 60)
padroes = [
    f"{BASE}/index.php?p=2026-04-08&d=1",  # seção 1
    f"{BASE}/index.php?p=2026-04-08&d=2",  # seção 2
    f"{BASE}/index.php?p=2026-04-08&d=3",  # seção 3
    f"{BASE}/index.php?p=2026-04-08&s=1",  # seção 1 (alt)
    f"{BASE}/index.php?p=2026-04-08&secao=1",
    f"{BASE}/download.php?p=2026-04-08",
    f"{BASE}/api/dou/2026-04-08",
]
for url in padroes:
    r = session.get(url, allow_redirects=False)
    print(f"  {url} -> {r.status_code}")
    if r.status_code == 302:
        print(f"    Location: {r.headers.get('location', 'N/A')}")

# Verificar a página de ajuda para mais endpoints
print()
print("=" * 60)
print("6. PÁGINA DE AJUDA")
print("=" * 60)
r = session.get(f"{BASE}/ajuda.php")
print(f"  GET {BASE}/ajuda.php -> {r.status_code} ({len(r.text)} bytes)")
# Extrair URLs da página de ajuda
help_links = re.findall(r'href="([^"]+)"', r.text)
for hl in help_links:
    if hl and not hl.startswith("#") and not hl.startswith("javascript") and "google" not in hl:
        full = hl if hl.startswith("http") else BASE + "/" + hl.lstrip("/")
        print(f"    {full}")

# Minha conta
print()
print("=" * 60)
print("7. MINHA CONTA")
print("=" * 60)
r = session.get(f"{BASE}/minha-conta.php")
print(f"  GET {BASE}/minha-conta.php -> {r.status_code} ({len(r.text)} bytes)")
# Mostrar conteúdo relevante
if r.status_code == 200:
    # Extrair formulários e inputs
    forms = re.findall(r'<form[^>]*action="([^"]*)"', r.text)
    inputs = re.findall(r'<input[^>]*name="([^"]*)"[^>]*>', r.text)
    print(f"  Formulários: {forms}")
    print(f"  Inputs: {inputs}")

print()
print("=" * 60)
print("8. COOKIES FINAIS DA SESSÃO")
print("=" * 60)
for c in session.cookies:
    print(f"  {c.name} = {c.value[:40]}... (domain={c.domain}, path={c.path})")
