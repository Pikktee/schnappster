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


# --- Ad endpoints ---


def test_list_ads_empty(client):
    response = client.get("/api/ads/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_ads(client, sample_ads):
    response = client.get("/api/ads/")
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_list_ads_filter_by_adsearch(client, sample_ads, sample_adsearch):
    response = client.get(f"/api/ads/?adsearch_id={sample_adsearch.id}")
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_list_ads_filter_by_analyzed(client, sample_ads):
    response = client.get("/api/ads/?is_analyzed=true")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["external_id"] == "1001"


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
