import json

from tools.ted_to_d1_sql import render, sql_text, stable_id


def test_sql_text_escapes_quotes_and_null():
    assert sql_text(None) == "NULL"
    assert sql_text("O'Brien") == "'O''Brien'"


def test_stable_id_is_repeatable():
    assert stable_id("company", "Example", "123") == stable_id("company", "Example", "123")
    assert stable_id("company", "Example", "123") != stable_id("company", "Other", "123")


def test_render_is_idempotent_and_contains_source_entity_observation():
    payload = {
        "source": {
            "id": "ted-open-data",
            "name": "TED Open Data",
            "endpoint": "https://data.ted.europa.eu/",
            "retrieved_at": "2026-09-04T00:00:00+00:00",
        },
        "observations": [
            {
                "publication_number": "123/2026",
                "legal_name": "O'Brien SRL",
                "procedure_type": "Open procedure",
                "publication_date": "2026-09-03",
            }
        ],
    }
    sql = render(payload)
    assert "BEGIN TRANSACTION;" in sql
    assert "INSERT INTO sources" in sql
    assert "INSERT INTO entities" in sql
    assert "INSERT OR IGNORE INTO observations" in sql
    assert "O''Brien SRL" in sql
    assert sql.endswith("COMMIT;\n")
    json.dumps(payload)
