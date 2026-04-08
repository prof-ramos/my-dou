from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from inlabs_client import InlabsClient, InlabsError

@pytest.fixture
def client():
    """Retorna um InlabsClient sem instanciar usando as vars reais de ambiente."""
    return InlabsClient(email="test@inlabs.gov.br", password="senha_super_segura")

def test_init(client):
    assert client._email == "test@inlabs.gov.br"
    assert client._password == "senha_super_segura"
    assert "User-Agent" in client._session.headers

def test_from_env(mocker):
    mocker.patch("os.getenv", side_effect=lambda k, d="": {
        "INLABS_EMAIL": "env@test.com",
        "INLABS_PASSWORD": "env_password"
    }.get(k, d))
    mocker.patch("inlabs_client.load_dotenv")
    
    client = InlabsClient.from_env()
    assert client._email == "env@test.com"
    assert client._password == "env_password"

def test_from_env_missing(mocker):
    mocker.patch("os.getenv", return_value="")
    mocker.patch("inlabs_client.load_dotenv")
    
    with pytest.raises(InlabsError, match="Configure INLABS_EMAIL e INLABS_PASSWORD"):
        InlabsClient.from_env()

def test_session_cookie(client):
    client._session.cookies.set("inlabs_session_cookie", "test_cookie")
    assert client.session_cookie == "test_cookie"

def test_list_available_dates(client, mocker):
    """Verifica se o parser do BeautifulSoup extrai as datas corretamente."""
    html_content = (Path(__file__).parent / "fixtures" / "dates.html").read_text()
    
    mock_get = mocker.patch.object(client._session, "get")
    mock_get.return_value = MagicMock(status_code=200, text=html_content)
    
    dates = client.list_available_dates()
    assert dates == ["2026-04-08", "2026-04-07", "2026-04-06"]

def test_list_files(client, mocker):
    """Verifica se a extração de nomes de arquivos, datas e tamanhos está correta."""
    html_content = (Path(__file__).parent / "fixtures" / "files.html").read_text()
    
    mock_get = mocker.patch.object(client._session, "get")
    mock_get.return_value = MagicMock(status_code=200, text=html_content)
    
    files = client.list_files("2026-04-08")
    assert len(files) == 1
    f = files[0]
    assert f["name"] == "2026_04_08_ASSINADO_do1.pdf"
    assert f["size"] == "5.2 MB"

def test_error_status_code(client, mocker):
    mock_get = mocker.patch.object(client._session, "get")
    mock_get.return_value = MagicMock(status_code=502)
    with pytest.raises(InlabsError, match="Erro ao listar datas: 502"):
        client.list_available_dates()

def test_download_file_success(client, mocker, tmp_path):
    mock_get = mocker.patch.object(client._session, "get")
    mock_get.return_value = MagicMock(status_code=200, content=b"fake pdf content", headers={})
    
    res = client._download_file("http://url", "test.pdf", tmp_path, {})
    assert res == tmp_path / "test.pdf"
    assert res.read_bytes() == b"fake pdf content"

def test_download_file_404(client, mocker, tmp_path):
    mock_get = mocker.patch.object(client._session, "get")
    mock_get.return_value = MagicMock(status_code=404)
    res = client._download_file("http://url", "test.pdf", tmp_path, {})
    assert res is None

def test_download_file_error_html(client, mocker, tmp_path):
    mock_get = mocker.patch.object(client._session, "get")
    mock_get.return_value = MagicMock(status_code=200, headers={"Content-Type": "text/html"})
    res = client._download_file("http://url", "test.pdf", tmp_path, {})
    assert res is None

def test_download_pdf(client, mocker, tmp_path):
    client._session.cookies.set("inlabs_session_cookie", "valid_cookie")
    mocker.patch.object(client, "_download_file", return_value=tmp_path / "file.pdf")
    
    downloaded = client.download_pdf("2026-04-08", sections=["do1"], output_dir=tmp_path, include_extras=False)
    assert len(downloaded) == 1
    assert downloaded[0] == tmp_path / "file.pdf"

def test_download_pdf_no_auth(client):
    with pytest.raises(InlabsError, match="Não autenticado"):
        client.download_pdf("2026-04-08")

def test_download_zip(client, mocker, tmp_path):
    client._session.cookies.set("inlabs_session_cookie", "valid_cookie")
    mocker.patch.object(client, "_download_file", return_value=tmp_path / "file.zip")
    
    downloaded = client.download_zip("2026-04-08", sections=["DO1"], output_dir=tmp_path)
    assert len(downloaded) == 1

def test_login_retry_logic(client, mocker):
    # Mock do _do_login_playwright para falhar 2 vezes e depois ter sucesso
    mock_do_login = mocker.patch.object(client, "_do_login_playwright")
    mock_do_login.side_effect = [Exception("Fail 1"), Exception("Fail 2"), None]
    
    client.login()
    assert mock_do_login.call_count == 3

def test_login_fails_after_retries(client, mocker):
    mock_do_login = mocker.patch.object(client, "_do_login_playwright")
    mock_do_login.side_effect = Exception("Permanent Fail")
    
    with pytest.raises(Exception, match="Permanent Fail"):
        client.login()

def test_do_login_playwright_mocked(client, mocker):
    # Mock complexo do Playwright
    mock_pw = mocker.patch("playwright.sync_api.sync_playwright")
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()
    
    mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    
    # Simular sucesso no login
    mock_page.content.return_value = "<html><body>Sair</body></html>"
    mock_context.cookies.return_value = [{"name": "inlabs_session_cookie", "value": "secret"}]
    
    client._do_login_playwright()
    assert client.session_cookie == "secret"

def test_do_login_maintenance(client, mocker):
    mock_pw = mocker.patch("playwright.sync_api.sync_playwright")
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()
    
    mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    
    # Simular manutenção no goto ou no content
    mock_page.content.return_value = "Sistema em Manutenção"
    
    with pytest.raises(InlabsError, match="Sistema em manutenção"):
        client._do_login_playwright()

def test_do_login_invalid_creds(client, mocker):
    mock_pw = mocker.patch("playwright.sync_api.sync_playwright")
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()
    
    mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    
    mock_page.content.return_value = "Senha incorreta"
    
    with pytest.raises(InlabsError, match="Credenciais inválidas"):
        client._do_login_playwright()
