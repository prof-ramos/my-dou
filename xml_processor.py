from __future__ import annotations
import zipfile
from pathlib import Path
from bs4 import BeautifulSoup

class XMLProcessor:
    def filter_by_org(self, zip_path: Path, org_name: str):
        """
        Lê arquivos ZIP do DOU e filtra artigos XML pelo nome do órgão.
        
        Args:
            zip_path: Caminho para o arquivo ZIP.
            org_name: Nome do órgão para filtrar (usa startswith).
            
        Yields:
            Dicionários contendo id, category, type, title, ementa e xml_name.
        """
        with zipfile.ZipFile(zip_path, 'r') as z:
            for name in z.namelist():
                if name.endswith('.xml'):
                    with z.open(name) as f:
                        soup = BeautifulSoup(f.read(), "lxml-xml")
                        article = soup.find("article")
                        if article and article.get("artCategory", "").startswith(org_name):
                            yield {
                                "id": article.get("idMateria"),
                                "category": article.get("artCategory"),
                                "type": article.get("artType"),
                                "title": soup.find("Identifica").get_text(strip=True) if soup.find("Identifica") else "",
                                "ementa": soup.find("Ementa").get_text(strip=True) if soup.find("Ementa") else "",
                                "xml_name": name
                            }
