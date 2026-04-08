from __future__ import annotations
import zipfile
import pytest
from pathlib import Path
from xml_processor import XMLProcessor

@pytest.fixture
def fake_zip(tmp_path: Path):
    zip_path = tmp_path / "test_dou.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        # Article from MRE
        mre_xml = """<?xml version="1.0" encoding="utf-8"?>
        <article idMateria="123" artCategory="Ministério das Relações Exteriores" artType="Portaria">
            <Identifica>PORTARIA Nº 1</Identifica>
            <Ementa>Dispõe sobre algo do MRE.</Ementa>
        </article>
        """
        z.writestr("art1.xml", mre_xml)
        
        # Article from another org
        other_xml = """<?xml version="1.0" encoding="utf-8"?>
        <article idMateria="456" artCategory="Ministério da Fazenda" artType="Instrução Normativa">
            <Identifica>IN 123</Identifica>
            <Ementa>Dispõe sobre impostos.</Ementa>
        </article>
        """
        z.writestr("art2.xml", other_xml)
        
        # Another MRE article with slightly different category (testing startswith)
        mre_xml_2 = """<?xml version="1.0" encoding="utf-8"?>
        <article idMateria="789" artCategory="Ministério das Relações Exteriores/Gabinete" artType="Despacho">
            <Identifica>DESPACHO Nº 45</Identifica>
            <Ementa>Autoriza viagem.</Ementa>
        </article>
        """
        z.writestr("art3.xml", mre_xml_2)
        
    return zip_path

def test_filter_mre_articles(fake_zip: Path):
    processor = XMLProcessor()
    results = list(processor.filter_by_org(fake_zip, "Ministério das Relações Exteriores"))
    
    assert len(results) == 2
    
    # Check first result
    assert results[0]["id"] == "123"
    assert results[0]["category"] == "Ministério das Relações Exteriores"
    assert results[0]["type"] == "Portaria"
    assert results[0]["title"] == "PORTARIA Nº 1"
    assert results[0]["ementa"] == "Dispõe sobre algo do MRE."
    assert results[0]["xml_name"] == "art1.xml"
    
    # Check second result
    assert results[1]["id"] == "789"
    assert results[1]["category"] == "Ministério das Relações Exteriores/Gabinete"
    assert results[1]["type"] == "Despacho"
    assert results[1]["title"] == "DESPACHO Nº 45"
    assert results[1]["ementa"] == "Autoriza viagem."
    assert results[1]["xml_name"] == "art3.xml"

def test_filter_no_results(fake_zip: Path):
    processor = XMLProcessor()
    results = list(processor.filter_by_org(fake_zip, "Ministério Inexistente"))
    assert len(results) == 0
