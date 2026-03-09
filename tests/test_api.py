"""Tests for API endpoints."""


# --- AdSearch endpoints ---


def test_list_adsearches_empty(client):
    response = client.get("/api/adsearches/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_adsearch(client):
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
    """Non-Kleinanzeigen URLs must be rejected."""
    response = client.post(
        "/api/adsearches/",
        json={"name": "Test", "url": "https://www.ebay.de/sch/i.html?_nkw=podmic"},
    )
    assert response.status_code == 422


def test_create_adsearch_rejects_bare_prefix_url(client):
    """The bare prefix 'https://www.kleinanzeigen.de/s-' must be rejected."""
    response = client.post(
        "/api/adsearches/",
        json={"name": "Test", "url": "https://www.kleinanzeigen.de/s-"},
    )
    assert response.status_code == 422


def test_create_adsearch_rejects_detail_page_url(client):
    """Kleinanzeigen ad detail pages must be rejected."""
    response = client.post(
        "/api/adsearches/",
        json={"name": "Test", "url": "https://www.kleinanzeigen.de/s-anzeige/rode-podmic/123456"},
    )
    assert response.status_code == 422


def test_patch_adsearch_rejects_detail_page_url(client, sample_adsearch):
    """PATCH must also reject detail-page URLs."""
    response = client.patch(
        f"/api/adsearches/{sample_adsearch.id}",
        json={"url": "https://www.kleinanzeigen.de/s-anzeige/rode-podmic/123456"},
    )
    assert response.status_code == 422


def test_get_adsearch(client, sample_adsearch):
    response = client.get(f"/api/adsearches/{sample_adsearch.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Search"


def test_get_adsearch_not_found(client):
    response = client.get("/api/adsearches/999")
    assert response.status_code == 404


def test_patch_adsearch(client, sample_adsearch):
    response = client.patch(
        f"/api/adsearches/{sample_adsearch.id}",
        json={"name": "Updated Name"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_delete_adsearch(client, sample_adsearch):
    response = client.delete(f"/api/adsearches/{sample_adsearch.id}")
    assert response.status_code == 204

    response = client.get(f"/api/adsearches/{sample_adsearch.id}")
    assert response.status_code == 404


def test_delete_adsearch_keeps_ads(client, sample_ads):
    """Test that deleting an adsearch keeps the related ads (adsearch_id becomes NULL)."""
    # Get the adsearch_id from sample_ads
    adsearch_id = sample_ads[0].adsearch_id
    ad_id = sample_ads[0].id

    response = client.delete(f"/api/adsearches/{adsearch_id}")
    assert response.status_code == 204

    # Verify adsearch is deleted
    response = client.get(f"/api/adsearches/{adsearch_id}")
    assert response.status_code == 404

    # Verify ads are NOT deleted (adsearch_id should be None now)
    response = client.get(f"/api/ads/{ad_id}")
    assert response.status_code == 200
    assert response.json()["adsearch_id"] is None


# --- Ad endpoints ---


def test_list_ads_empty(client):
    response = client.get("/api/ads/")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_list_ads(client, sample_ads):
    response = client.get("/api/ads/")
    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert len(response.json()["items"]) == 3


def test_list_ads_filter_by_adsearch(client, sample_ads, sample_adsearch):
    response = client.get(f"/api/ads/?adsearch_id={sample_adsearch.id}")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 3


def test_list_ads_filter_by_analyzed(client, sample_ads):
    response = client.get("/api/ads/?is_analyzed=true")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["external_id"] == "1001"


def test_get_ad(client, sample_ads):
    ad = sample_ads[0]
    response = client.get(f"/api/ads/{ad.id}")
    assert response.status_code == 200
    result = response.json()
    assert result["title"] == "Rode PodMic"
    assert result["bargain_score"] == 7.0


def test_get_ad_has_image_url(client, sample_ads):
    """Test that AdRead includes computed image_url field."""
    ad = sample_ads[0]
    response = client.get(f"/api/ads/{ad.id}")
    assert response.status_code == 200
    result = response.json()
    assert result["image_url"] == "https://img.kleinanzeigen.de/test1.jpg"


def test_get_ad_image_url_none_when_no_images(client, sample_ads):
    """Test that image_url is None when no images exist."""
    ad = sample_ads[2]  # No image_urls set
    response = client.get(f"/api/ads/{ad.id}")
    assert response.status_code == 200
    assert response.json()["image_url"] is None


def test_get_ad_not_found(client):
    response = client.get("/api/ads/999")
    assert response.status_code == 404


# --- Settings endpoints ---


def test_list_settings(client):
    response = client.get("/api/settings/")
    assert response.status_code == 200
    settings = response.json()
    assert len(settings) >= 2
    keys = [s["key"] for s in settings]
    assert "exclude_commercial_sellers" in keys
    assert "min_seller_rating" in keys
    assert "telegram_notifications_enabled" in keys


def test_get_telegram_configured(client):
    response = client.get("/api/settings/telegram-configured")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert isinstance(data["configured"], bool)


def test_get_setting(client):
    response = client.get("/api/settings/exclude_commercial_sellers")
    assert response.status_code == 200
    assert response.json()["value"] == "false"


def test_get_setting_unknown(client):
    response = client.get("/api/settings/nonexistent")
    assert response.status_code == 404


def test_update_setting(client):
    response = client.put(
        "/api/settings/exclude_commercial_sellers",
        json={"value": "true"},
    )
    assert response.status_code == 200
    assert response.json()["value"] == "true"


def test_update_setting_invalid_value(client):
    response = client.put(
        "/api/settings/exclude_commercial_sellers",
        json={"value": "maybe"},
    )
    assert response.status_code == 422


def test_update_setting_invalid_rating(client):
    response = client.put(
        "/api/settings/min_seller_rating",
        json={"value": "5"},
    )
    assert response.status_code == 422
