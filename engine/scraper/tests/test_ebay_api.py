from engine.integrations.ebay_api import normalize


def test_normalize_maps_basic_fields():
    item = {
        "itemId": "1234567890",
        "itemWebUrl": "https://www.ebay.com.au/itm/1234567890",
        "title": "2018 Toyota Corolla Ascent Sport",
        "price": {"value": "18990.00", "currency": "AUD"},
        "itemLocation": {"country": "AU", "stateOrProvince": "NSW", "postalCode": "2000"},
        "image": {"imageUrl": "https://i.ebayimg.com/images/g/abc/s-l1600.jpg"},
        "seller": {"username": "demo_seller", "feedbackPercentage": "99.5", "feedbackScore": 1234},
    }
    out = normalize(item)
    assert out["source"] == "ebay"
    assert out["source_id"] == "1234567890"
    assert out["source_url"].endswith("/1234567890")
    assert out["price"] == 18990
    assert out["year"] == 2018
    assert out["state"] == "NSW"
    assert out["postcode"] == "2000"
    assert out["media"] == ["https://i.ebayimg.com/images/g/abc/s-l1600.jpg"]

