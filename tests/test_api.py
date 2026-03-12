"""Tests für die API-Endpunkte."""

from unittest.mock import patch

# --- AdSearch-Endpunkte ---


def test_list_adsearches_empty(client):
    """GET /adsearches/ liefert 200 und leere Liste, wenn keine Suchen existieren."""
    response = client.get("/api/adsearches/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_adsearch(client):
    """POST /adsearches/ mit gültigen Daten liefert 201 und erstellten Suchauftrag mit id und is_active."""
    data = {
        "name": "PodMic Frankfurt",
        "url": "https://www.kleinanzeigen.de/s-audio-hifi/60325/podmic/k0c172l4305r250",
    }
    response = client.post("/api/adsearches/", json=data)
    assert response.status_code == 201
    result = response.json()
    assert result["name"] == "PodMic Frankfurt"
    assert result["id"] is not None
    assert result["is_active"] is True


def test_create_adsearch_rejects_invalid_url(client):
    """POST lehnt Nicht-Kleinanzeigen-URLs mit 422 ab."""
    response = client.post(
        "/api/adsearches/",
        json={"name": "Test", "url": "https://www.ebay.de/sch/i.html?_nkw=podmic"},
    )
    assert response.status_code == 422


def test_create_adsearch_rejects_bare_prefix_url(client):
    """POST lehnt das reine Präfix https://www.kleinanzeigen.de/s- mit 422 ab."""
    response = client.post(
        "/api/adsearches/",
        json={"name": "Test", "url": "https://www.kleinanzeigen.de/s-"},
    )
    assert response.status_code == 422


def test_create_adsearch_rejects_detail_page_url(client):
    """POST lehnt Kleinanzeigen-Detailseiten-URLs mit 422 ab."""
    response = client.post(
        "/api/adsearches/",
        json={"name": "Test", "url": "https://www.kleinanzeigen.de/s-anzeige/rode-podmic/123456"},
    )
    assert response.status_code == 422


def test_patch_adsearch_rejects_detail_page_url(client, sample_adsearch):
    """PATCH lehnt Detailseiten-URL mit 422 ab."""
    response = client.patch(
        f"/api/adsearches/{sample_adsearch.id}",
        json={"url": "https://www.kleinanzeigen.de/s-anzeige/rode-podmic/123456"},
    )
    assert response.status_code == 422


@patch("app.routes.api.adsearch.fetch_page_with_status")
def test_patch_adsearch_rejects_unreachable_url(mock_fetch, client, sample_adsearch):
    """PATCH lehnt URL ab, die 404 zurückgibt (serverseitige Validierung)."""
    mock_fetch.return_value = (404, "")
    response = client.patch(
        f"/api/adsearches/{sample_adsearch.id}",
        json={"url": "https://www.kleinanzeigen.de/s-some/category/k0c123"},
    )
    assert response.status_code == 422
    assert "404" in response.json().get("detail", "")
    mock_fetch.assert_called_once()


@patch("app.routes.api.adsearch._validate_search_url_reachable")
def test_patch_adsearch_uses_title_when_name_cleared(mock_validate, client, sample_adsearch):
    """PATCH mit leerem Namen nutzt den Seitentitel als Namen."""
    mock_validate.return_value = "Neuer Titel von der Seite"

    response = client.patch(
        f"/api/adsearches/{sample_adsearch.id}",
        json={"name": ""},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["name"] == "Neuer Titel von der Seite"
    mock_validate.assert_called_once()


def test_get_adsearch(client, sample_adsearch):
    """GET /adsearches/{id} liefert 200 und Suchdaten für existierende id."""
    response = client.get(f"/api/adsearches/{sample_adsearch.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Search"


def test_get_adsearch_not_found(client):
    """GET /adsearches/999 liefert 404, wenn die id nicht existiert."""
    response = client.get("/api/adsearches/999")
    assert response.status_code == 404


def test_patch_adsearch(client, sample_adsearch):
    """PATCH /adsearches/{id} aktualisiert Felder und liefert 200."""
    response = client.patch(
        f"/api/adsearches/{sample_adsearch.id}",
        json={"name": "Updated Name"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_delete_adsearch(client, sample_adsearch):
    """DELETE /adsearches/{id} liefert 204 und entfernt den Suchauftrag."""
    response = client.delete(f"/api/adsearches/{sample_adsearch.id}")
    assert response.status_code == 204

    response = client.get(f"/api/adsearches/{sample_adsearch.id}")
    assert response.status_code == 404


def test_delete_adsearch_deletes_ads(client, sample_ads):
    """Beim Löschen eines Suchauftrags werden auch alle zugehörigen Anzeigen gelöscht."""
    adsearch_id = sample_ads[0].adsearch_id
    ad_id = sample_ads[0].id

    response = client.delete(f"/api/adsearches/{adsearch_id}")
    assert response.status_code == 204

    # Verify adsearch is deleted
    response = client.get(f"/api/adsearches/{adsearch_id}")
    assert response.status_code == 404

    # Verify ads are also deleted
    response = client.get(f"/api/ads/{ad_id}")
    assert response.status_code == 404


def test_delete_adsearch_deletes_ai_analysis_logs(client, sample_ads, sample_ai_analysis_log):
    """Beim Löschen eines Suchauftrags werden auch zugehörige KI-Analyse-Logs gelöscht."""
    adsearch_id = sample_ads[0].adsearch_id

    response = client.get("/api/aianalysislogs/")
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.delete(f"/api/adsearches/{adsearch_id}")
    assert response.status_code == 204

    response = client.get("/api/aianalysislogs/")
    assert response.status_code == 200
    assert len(response.json()) == 0


# --- Anzeigen-Endpunkte ---


def test_list_ads_empty(client):
    """GET /ads/ liefert 200 und leere items, wenn keine Anzeigen existieren."""
    response = client.get("/api/ads/")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_list_ads(client, sample_ads):
    """GET /ads/ liefert 200 und eine Liste von Anzeigen."""
    response = client.get("/api/ads/")
    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert len(response.json()["items"]) == 3


def test_list_ads_filter_by_adsearch(client, sample_ads, sample_adsearch):
    """GET /ads/?adsearch_id=X liefert nur Anzeigen für diese Suche."""
    response = client.get(f"/api/ads/?adsearch_id={sample_adsearch.id}")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 3


def test_list_ads_filter_by_analyzed(client, sample_ads):
    """GET /ads/?is_analyzed=true liefert nur analysierte Anzeigen."""
    response = client.get("/api/ads/?is_analyzed=true")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["external_id"] == "1001"


def test_get_ad(client, sample_ads):
    """GET /ads/{id} liefert 200 und Anzeigendaten für existierende id."""
    ad = sample_ads[0]
    response = client.get(f"/api/ads/{ad.id}")
    assert response.status_code == 200
    result = response.json()
    assert result["title"] == "Rode PodMic"
    assert result["bargain_score"] == 7.0


def test_get_ad_has_image_url(client, sample_ads):
    """AdRead enthält das berechnete image_url (erstes Bild aus image_urls)."""
    ad = sample_ads[0]
    response = client.get(f"/api/ads/{ad.id}")
    assert response.status_code == 200
    result = response.json()
    assert result["image_url"] == "https://img.kleinanzeigen.de/test1.jpg"


def test_get_ad_image_url_none_when_no_images(client, sample_ads):
    """image_url ist None, wenn die Anzeige keine image_urls hat."""
    ad = sample_ads[2]  # No image_urls set
    response = client.get(f"/api/ads/{ad.id}")
    assert response.status_code == 200
    assert response.json()["image_url"] is None


def test_get_ad_not_found(client):
    """GET /ads/999 liefert 404, wenn die id nicht existiert."""
    response = client.get("/api/ads/999")
    assert response.status_code == 404


# --- Einstellungen-Endpunkte ---


def test_list_settings(client):
    """GET /settings/ liefert 200 und Liste der Einstellungen mit Metadaten."""
    response = client.get("/api/settings/")
    assert response.status_code == 200
    settings = response.json()
    assert len(settings) >= 2
    keys = [s["key"] for s in settings]
    assert "exclude_commercial_sellers" in keys
    assert "min_seller_rating" in keys
    assert "telegram_notifications_enabled" in keys


def test_get_telegram_configured(client):
    """GET /settings/telegram-configured liefert configured true/false."""
    response = client.get("/api/settings/telegram-configured")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert isinstance(data["configured"], bool)


def test_get_setting(client):
    """GET /settings/{key} liefert den Wert für einen unterstützten Schlüssel."""
    response = client.get("/api/settings/exclude_commercial_sellers")
    assert response.status_code == 200
    assert response.json()["value"] == "false"


def test_get_setting_unknown(client):
    """GET /settings/nonexistent liefert 404."""
    response = client.get("/api/settings/nonexistent")
    assert response.status_code == 404


def test_update_setting(client):
    """PUT /settings/{key} aktualisiert den Wert und liefert den neuen Wert."""
    response = client.put(
        "/api/settings/exclude_commercial_sellers",
        json={"value": "true"},
    )
    assert response.status_code == 200
    assert response.json()["value"] == "true"


def test_update_setting_invalid_value(client):
    """PUT mit ungültigem Wert liefert 422."""
    response = client.put(
        "/api/settings/exclude_commercial_sellers",
        json={"value": "maybe"},
    )
    assert response.status_code == 422


def test_update_setting_invalid_rating(client):
    """PUT min_seller_rating mit ungültigem Wert liefert 422."""
    response = client.put(
        "/api/settings/min_seller_rating",
        json={"value": "5"},
    )
    assert response.status_code == 422


# --- Version-Endpunkt ---


def test_get_version(client):
    """GET /version/ liefert die Version aus den Paket-Metadaten (pyproject.toml)."""
    response = client.get("/api/version/")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert isinstance(data["version"], str)
    assert data["version"]  # non-empty, e.g. "0.1.0"
