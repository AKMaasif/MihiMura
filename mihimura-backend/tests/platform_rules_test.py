"""Offline tests for server-side platform rules (no Supabase calls)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.platform import PRODUCTS, _priced_items, _required  # noqa: E402


def expect_value_error(fn, *args) -> None:
    try:
        fn(*args)
    except ValueError:
        return
    raise AssertionError(f"{fn.__name__}{args} should have raised ValueError")


def run() -> None:
    catalog_price = {p["id"]: p["price"] for p in PRODUCTS}

    # Prices always come from the server catalog, whatever the browser sends.
    items = _priced_items([{"id": "p1", "quantity": 2, "price": 0, "name": "free seed"}])
    assert items[0]["price"] == catalog_price["p1"]
    assert items[0]["name"] != "free seed"
    assert items[0]["quantity"] == 2

    expect_value_error(_priced_items, [{"id": "does-not-exist", "quantity": 1}])
    expect_value_error(_priced_items, [{"id": "p1", "quantity": 0}])
    expect_value_error(_priced_items, [{"id": "p1", "quantity": "lots"}])
    expect_value_error(_priced_items, [])

    expect_value_error(_required, {"name": ""}, "name")
    _required({"name": "North field"}, "name")

    print("MihiMura platform rules test: PASS")


if __name__ == "__main__":
    run()
