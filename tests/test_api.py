"""Tests for API endpoints."""

from unittest.mock import patch

# --- AdSearch endpoints ---


def test_list_adsearches_empty(client):
    """GET /adsearches/ returns 200 and empty list when no searches exist."""
    response = client.get("/api/adsearches/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_adsearch(client):
    """POST /adsearches/ with valid data returns 201 and created search with id and is_active."""
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
    """POST rejects non-Kleinanzeigen URLs with 422."""
    response = client.post(
        "/api/adsearches/",
        json={"name": "Test", "url": "https://www.ebay.de/sch/i.html?_nkw=podmic"},
    )
    assert response.status_code == 422


def test_create_adsearch_rejects_bare_prefix_url(client):
    """POST rejects bare prefix https://www.kleinanzeigen.de/s- with 422."""
    response = client.post(
        "/api/adsearches/",
        json={"name": "Test", "url": "https://www.kleinanzeigen.de/s-"},
    )
    assert response.status_code == 422


def test_create_adsearch_rejects_detail_page_url(client):
    """POST rejects Kleinanzeigen detail page URLs with 422."""
    response = client.post(
        "/api/adsearches/",
        json={"name": "Test", "url": "https://www.kleinanzeigen.de/s-anzeige/rode-podmic/123456"},
    )
    assert response.status_code == 422


def test_patch_adsearch_rejects_detail_page_url(client, sample_adsearch):
    """PATCH rejects detail-page URL with 422."""
    response = client.patch(
        f"/api/adsearches/{sample_adsearch.id}",
        json={"url": "https://www.kleinanzeigen.de/s-anzeige/rode-podmic/123456"},
    )
    assert response.status_code == 422


@patch("app.routes.api.adsearch.fetch_page_checked")
def test_patch_adsearch_rejects_unreachable_url(mock_fetch, client, sample_adsearch):
    """PATCH rejects URL that returns 404 (server-side validation)."""
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
    """PATCH with empty name uses page title as name."""
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
    """GET /adsearches/{id} returns 200 and search data for existing id."""
    response = client.get(f"/api/adsearches/{sample_adsearch.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Search"


def test_get_adsearch_not_found(client):
    """GET /adsearches/999 returns 404 when id does not exist."""
    response = client.get("/api/adsearches/999")
    assert response.status_code == 404


def test_patch_adsearch(client, sample_adsearch):
    """PATCH /adsearches/{id} updates fields and returns 200."""
    response = client.patch(
        f"/api/adsearches/{sample_adsearch.id}",
        json={"name": "Updated Name"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_delete_adsearch(client, sample_adsearch):
    """DELETE /adsearches/{id} returns 204 and removes the search."""
    response = client.delete(f"/api/adsearches/{sample_adsearch.id}")
    assert response.status_code == 204

    response = client.get(f"/api/adsearches/{sample_adsearch.id}")
    assert response.status_code == 404


def test_delete_adsearch_deletes_ads(client, sample_ads):
    """Deleting an adsearch also deletes all related ads."""
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


# --- Ad endpoints ---


def test_list_ads_empty(client):
    """GET /ads/ returns 200 and empty items when no ads exist."""
    response = client.get("/api/ads/")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_list_ads(client, sample_ads):
    """GET /ads/ returns 200 and list of ads."""
    response = client.get("/api/ads/")
    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert len(response.json()["items"]) == 3


def test_list_ads_filter_by_adsearch(client, sample_ads, sample_adsearch):
    """GET /ads/?adsearch_id=X returns only ads for that search."""
    response = client.get(f"/api/ads/?adsearch_id={sample_adsearch.id}")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 3


def test_list_ads_filter_by_analyzed(client, sample_ads):
    """GET /ads/?is_analyzed=true returns only analyzed ads."""
    response = client.get("/api/ads/?is_analyzed=true")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["external_id"] == "1001"


def test_get_ad(client, sample_ads):
    """GET /ads/{id} returns 200 and ad data for existing id."""
    ad = sample_ads[0]
    response = client.get(f"/api/ads/{ad.id}")
    assert response.status_code == 200
    result = response.json()
    assert result["title"] == "Rode PodMic"
    assert result["bargain_score"] == 7.0


def test_get_ad_has_image_url(client, sample_ads):
    """AdRead includes computed image_url (first image from image_urls)."""
    ad = sample_ads[0]
    response = client.get(f"/api/ads/{ad.id}")
    assert response.status_code == 200
    result = response.json()
    assert result["image_url"] == "https://img.kleinanzeigen.de/test1.jpg"


def test_get_ad_image_url_none_when_no_images(client, sample_ads):
    """image_url is None when ad has no image_urls."""
    ad = sample_ads[2]  # No image_urls set
    response = client.get(f"/api/ads/{ad.id}")
    assert response.status_code == 200
    assert response.json()["image_url"] is None


def test_get_ad_not_found(client):
    """GET /ads/999 returns 404 when id does not exist."""
    response = client.get("/api/ads/999")
    assert response.status_code == 404


# --- Settings endpoints ---


def test_list_settings(client):
    """GET /settings/ returns 200 and list of settings with metadata."""
    response = client.get("/api/settings/")
    assert response.status_code == 200
    settings = response.json()
    assert len(settings) >= 2
    keys = [s["key"] for s in settings]
    assert "exclude_commercial_sellers" in keys
    assert "min_seller_rating" in keys
    assert "telegram_notifications_enabled" in keys


def test_get_telegram_configured(client):
    """GET /settings/telegram-configured returns configured true/false."""
    response = client.get("/api/settings/telegram-configured")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert isinstance(data["configured"], bool)


def test_get_setting(client):
    """GET /settings/{key} returns value for supported key."""
    response = client.get("/api/settings/exclude_commercial_sellers")
    assert response.status_code == 200
    assert response.json()["value"] == "false"


def test_get_setting_unknown(client):
    """GET /settings/nonexistent returns 404."""
    response = client.get("/api/settings/nonexistent")
    assert response.status_code == 404


def test_update_setting(client):
    """PUT /settings/{key} updates value and returns new value."""
    response = client.put(
        "/api/settings/exclude_commercial_sellers",
        json={"value": "true"},
    )
    assert response.status_code == 200
    assert response.json()["value"] == "true"


def test_update_setting_invalid_value(client):
    """PUT with invalid value returns 422."""
    response = client.put(
        "/api/settings/exclude_commercial_sellers",
        json={"value": "maybe"},
    )
    assert response.status_code == 422


def test_update_setting_invalid_rating(client):
    """PUT min_seller_rating with invalid value returns 422."""
    response = client.put(
        "/api/settings/min_seller_rating",
        json={"value": "5"},
    )
    assert response.status_code == 422


# --- Version endpoint ---


def test_get_version(client):
    """GET /version/ returns version from package metadata (pyproject.toml)."""
    response = client.get("/api/version/")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert isinstance(data["version"], str)
    assert data["version"]  # non-empty, e.g. "0.1.0"
