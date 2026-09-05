from tools.sync_datagov import normalize as normalize_ckan
from tools.sync_ted import normalize as normalize_ted


def test_ckan_normalize_uses_dataset_url_not_metadata_timestamp():
    result = normalize_ckan(
        {
            "results": [
                {
                    "id": "abc",
                    "name": "achizitii-publice",
                    "title": "Achiziții publice",
                    "metadata_created": "2026-09-01T00:00:00Z",
                    "resources": [],
                    "organization": {"title": "Instituție"},
                }
            ]
        },
        "achizitii publice",
    )
    dataset = result["datasets"][0]
    assert dataset["url"] == "https://data.gov.ro/dataset/achizitii-publice"
    assert dataset["url"] != "2026-09-01T00:00:00Z"


def test_ted_normalize_preserves_source_and_publication_fields():
    result = normalize_ted(
        {
            "results": {
                "bindings": [
                    {
                        "publicationNumber": {"value": "123/2026"},
                        "legalName": {"value": "Example SRL"},
                        "procedureType": {"value": "Open procedure"},
                        "country": {"value": "RO"},
                        "publicationDate": {"value": "2026-09-03"},
                    }
                ]
            }
        },
        "SELECT * WHERE {}",
        "https://data.ted.europa.eu/",
    )
    assert result["count"] == 1
    observation = result["observations"][0]
    assert observation["source"] == "TED Open Data"
    assert observation["publication_number"] == "123/2026"
    assert observation["legal_name"] == "Example SRL"
    assert observation["publication_date"] == "2026-09-03"
