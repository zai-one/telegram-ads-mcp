"""Wheel JSON Schema for a later campaign-setup caller. No live cabinet."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import telegram_ads_mcp
from telegram_ads_mcp.parse import scale_budget_chart

SCHEMAS = Path(telegram_ads_mcp.__file__).resolve().parent / "schemas"


def _load(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def _validator(name: str) -> Draft202012Validator:
    schema = _load(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_schema_examples_validate() -> None:
    for name in (
        "campaign-brief.schema.json",
        "review-artifact.schema.json",
        "stats-dump.schema.json",
    ):
        schema = _load(name)
        validator = _validator(name)
        examples = schema.get("examples") or []
        assert examples, name
        for example in examples:
            validator.validate(example)


def test_stats_dump_rejects_charts() -> None:
    validator = _validator("stats-dump.schema.json")
    dump = {
        "schema_version": "1",
        "ad_id": "35",
        "period": "5min",
        "summary": {"spend": 0.2688, "spend_already_scaled": True},
        "charts": {"budget": {"totals": {"Spent budget": 268800}}},
    }
    with pytest.raises(Exception):
        validator.validate(dump)
    validator.validate(
        {
            "schema_version": "1",
            "ad_id": "35",
            "period": "day",
            "summary": {
                "spend": 0.2688,
                "spend_already_scaled": True,
                "spend_scale": 1_000_000,
            },
        }
    )


def test_review_artifact_caps_problems_and_string_money() -> None:
    validator = _validator("review-artifact.schema.json")
    ok = {
        "schema_version": "1",
        "cabinet": "ton",
        "currency": "GRAM",
        "write_gate": "confirm",
        "problems": [
            {
                "ad_id": "35",
                "status": "Active",
                "spent": "0.54",
                "budget": "1",
                "why": "Active with 0 views in 24h.",
            }
        ],
        "recommendation": "Leave on_hold; do not activate.",
    }
    validator.validate(ok)
    bad_money = json.loads(json.dumps(ok))
    bad_money["problems"][0]["spent"] = 0.54
    with pytest.raises(Exception):
        validator.validate(bad_money)
    too_many = json.loads(json.dumps(ok))
    too_many["problems"] = ok["problems"] * 6
    with pytest.raises(Exception):
        validator.validate(too_many)


def test_campaign_brief_search_forbids_media_and_requires_on_hold() -> None:
    validator = _validator("campaign-brief.schema.json")
    search = {
        "schema_version": "1",
        "tool": "create_ad",
        "title": "q",
        "promote_url": "https://t.me/example",
        "cpm": "0.2",
        "target_type": "search",
        "active": "on_hold",
        "search_queries": "1;2",
        "text": "",
        "picture": False,
    }
    validator.validate(search)
    with_media = dict(search, media="abc")
    with pytest.raises(Exception):
        validator.validate(with_media)
    live = dict(search, active="active")
    with pytest.raises(Exception):
        validator.validate(live)


def test_scale_budget_chart_scale_one_still_flagged() -> None:
    raw = {
        "interval_seconds": 300,
        "names": {"y0": "Spent budget"},
        "timestamps": [0, 300000],
        "series": {"Spent budget": [100, None, "x"]},
        "totals": {"Spent budget": 100},
    }
    out = scale_budget_chart(raw, 1.0)
    assert out["values_already_scaled"] is True
    assert out["totals"]["Spent budget"] == 100
    assert out["series"]["Spent budget"][1] is None
    assert out["series"]["Spent budget"][2] == "x"
