import types
from unittest import mock

import pytest

from engine.scraper import orchestrator as orch
from engine.scraper.vendors import pickles_http as pk


def test_pickles_compute_buy_method_variants():
    args = types.SimpleNamespace(strict_prices=True, allow_enquire=False, include_unpriced=False)
    assert orch._pickles_compute_buy_method(
        strict_prices=args.strict_prices,
        final_buy_method=None,
        allow_enquire=args.allow_enquire,
        include_unpriced=args.include_unpriced,
    ) == "buy_now"

    args = types.SimpleNamespace(strict_prices=False, allow_enquire=True, include_unpriced=True)
    assert orch._pickles_compute_buy_method(
        strict_prices=args.strict_prices,
        final_buy_method="buy_now",
        allow_enquire=args.allow_enquire,
        include_unpriced=args.include_unpriced,
    ) is None

    args = types.SimpleNamespace(strict_prices=False, allow_enquire=False, include_unpriced=False)
    assert orch._pickles_compute_buy_method(
        strict_prices=args.strict_prices,
        final_buy_method="buy_now",
        allow_enquire=args.allow_enquire,
        include_unpriced=args.include_unpriced,
    ) == "buy_now"


def test_page_walked_counts_even_when_second_page_empty():
    html = "<html></html>"

    def parse_list_side_effect(html_content, limit, debug=False, hydrate=False, assume_buy_now=True):
        call_index = parse_list_side_effect.calls
        parse_list_side_effect.calls += 1
        if call_index == 0:
            return ([{"url": "https://example.com/a"}], {"kept_real": 1})
        raise RuntimeError("no tiles (pickles)")

    parse_list_side_effect.calls = 0

    with mock.patch.object(pk, "fetch_html", side_effect=[html, html]):
        with mock.patch.object(pk, "parse_list", side_effect=parse_list_side_effect):
            rows, counters, meta = pk.search_pickles(
                make=None,
                model=None,
                state="nt",
                query=None,
                pages=2,
                limit=5,
                hydrate=False,
                debug=False,
            )
    assert meta["pages_walked"] == 2
    assert len(rows) == 1
    assert counters["kept_real"] == 1


def test_parse_detail_html_extracts_specs():
    html = """
    <html>
      <body>
        <h1>2021 Toyota Corolla Ascent Sport</h1>
        <div id="item-buy-now-price">$34,340</div>
        <dl>
          <dt>Odometer</dt><dd>123,456 km</dd>
          <dt>Body</dt><dd>Hatchback</dd>
          <dt>Transmission</dt><dd>Automatic</dd>
          <dt>Fuel</dt><dd>Hybrid</dd>
          <dt>Engine</dt><dd>2.0L</dd>
          <dt>Drivetrain</dt><dd>FWD</dd>
          <dt>Variant</dt><dd>Ascent Sport</dd>
        </dl>
        <div data-testid="location">Woolloongabba QLD</div>
        <img src="https://cdn.example.com/img1.jpg" />
        <img src="/PicklesAuctions/images/watchlist-img.png" />
        <img src="https://cdn.example.com/img2.jpg" />
      </body>
    </html>
    """
    detail = pk._parse_detail_html(html, debug=False)
    assert detail["price"] == 34340
    assert detail["odometer"] == 123456
    assert detail["body"].lower() == "hatchback"
    assert detail["trans"].lower().startswith("automatic")
    assert detail["fuel"].lower() == "hybrid"
    assert detail["engine"].startswith("2.0")
    assert detail["drive"].upper() == "FWD"
    assert detail["variant"].lower() == "ascent sport"
    assert detail["state"].upper() == "QLD"
    assert detail["images"] == ["https://cdn.example.com/img1.jpg", "https://cdn.example.com/img2.jpg"]


def test_clean_media_urls_filters_placeholders():
    urls = [
        "https://cdn.example.com/a.jpg",
        "/PicklesAuctions/images/watchlist-img.png",
        "http://cdn.example.com/b.jpg",
        "ftp://invalid",
        "https://cdn.example.com/a.jpg",
    ]
    cleaned = pk._clean_media_urls(urls)
    assert cleaned == ["https://cdn.example.com/a.jpg", "http://cdn.example.com/b.jpg"]


def test_query_filter_helper():
    make_token, other_tokens = orch._compile_query_tokens("Toyota Corolla", "Toyota")
    row = {"title": "2018 Toyota Corolla Ascent", "make_guess": "Toyota", "model_guess": "Corolla", "variant": "Ascent"}
    assert orch._passes_query_filter(make_token, other_tokens, row)

    row_bad = {"title": "2018 Toyota Hilux SR5", "make_guess": "Toyota", "model_guess": "Hilux", "variant": "SR5"}
    assert not orch._passes_query_filter(make_token, other_tokens, row_bad)
