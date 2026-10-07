from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.config.pricing import PricingConfig, load_pricing_config
from src.utility.usage_cost import LlmUsage, OcrUsage, RequestUsage, record_llm_usage, track_usage


def test_pricing_config_keeps_billing_services_separate() -> None:
    pricing = PricingConfig.model_validate({
        "effective_date": "2026-10-07",
        "llm_rates": {
            "google_ai": {
                "shared-model": {
                    "input_usd_per_million_tokens": "0.10",
                    "output_usd_per_million_tokens": "0.40",
                }
            },
            "google_vertex": {
                "shared-model": {
                    "input_usd_per_million_tokens": "0.20",
                    "output_usd_per_million_tokens": "0.80",
                }
            },
            "openai": {
                "shared-model": {
                    "input_usd_per_million_tokens": "0.30",
                    "output_usd_per_million_tokens": "1.20",
                    "cached_input_usd_per_million_tokens": "0.03",
                }
            },
        },
        "ocr_rates": {
            "google_vision": {
                "document_text_detection": {"usd_per_thousand_units": "1.50"}
            }
        },
    })

    assert pricing.get_llm_rate("google_ai", "shared-model").input_usd_per_million_tokens == Decimal("0.10")
    assert pricing.get_llm_rate("google_vertex", "shared-model").input_usd_per_million_tokens == Decimal("0.20")
    assert pricing.get_llm_rate("openai", "shared-model").cached_input_usd_per_million_tokens == Decimal("0.03")
    assert pricing.get_ocr_rate("google_vision", "document_text_detection").usd_per_thousand_units == Decimal("1.50")
    assert pricing.get_llm_rate("openrouter", "shared-model") is None
    assert pricing.get_ocr_rate("google_vision", "text_detection") is None


@pytest.mark.parametrize("rate", ["-0.01", "NaN", "Infinity"])
def test_pricing_config_rejects_invalid_rates(rate: str) -> None:
    with pytest.raises(ValidationError):
        PricingConfig.model_validate({
            "effective_date": "2026-10-07",
            "llm_rates": {
                "openai": {
                    "example-model": {
                        "input_usd_per_million_tokens": rate,
                        "output_usd_per_million_tokens": "1.00",
                    }
                }
            }
        })


def test_pricing_config_loads_from_file(tmp_path) -> None:
    path = tmp_path / "pricing.json"
    path.write_text('{"effective_date":"2026-10-07","llm_rates":{}}', encoding="utf-8")
    pricing = load_pricing_config(str(path))
    assert pricing is not None
    assert pricing.effective_date.isoformat() == "2026-10-07"
    assert load_pricing_config("") is None


def test_combined_pricing_config_selects_qwen_tiers() -> None:
    pricing = load_pricing_config("pricing.json")
    assert pricing is not None
    assert pricing.get_llm_rate("alibaba", "qwen3.7-flash", 32000).input_usd_per_million_tokens == Decimal("0.030")
    assert pricing.get_llm_rate("alibaba", "qwen3.7-flash", 32001).input_usd_per_million_tokens == Decimal("0.100")
    assert pricing.get_llm_rate("alibaba", "qwen3.7-flash", 256001).input_usd_per_million_tokens == Decimal("0.200")
    assert pricing.get_llm_rate("alibaba", "qwen3.7-flash", 1000001) is None

    usage = RequestUsage([LlmUsage("alibaba", "qwen3.7-flash", 40000, 1000, 10000)])
    assert usage.summarize(pricing)["estimate_cost"] == "0.0036"


def test_google_usage_totals_and_unknown_rates() -> None:
    pricing = PricingConfig.model_validate({
        "effective_date": "2026-10-07",
        "llm_rates": {
            "google_ai": {
                "example-model": {
                    "input_usd_per_million_tokens": "1.00",
                    "output_usd_per_million_tokens": "2.00",
                    "cached_input_usd_per_million_tokens": "0.10",
                }
            }
        },
        "ocr_rates": {
            "google_vision": {
                "document_text_detection": {"usd_per_thousand_units": "1.50"}
            }
        },
    })
    usage = RequestUsage([
        LlmUsage("google_ai", "example-model", 1000, 200, 100),
        OcrUsage("google_vision", "document_text_detection", 2),
    ])
    summary = usage.summarize(pricing)
    assert summary["estimate_cost"] == "0.00431"
    assert summary["price_date"] == "2026-10-07"
    assert summary["complete"] is True
    assert summary["items"][0]["estimate_cost"] == "0.00131"

    usage.events.append(LlmUsage("google_vertex", "example-model", 100, 50))
    summary = usage.summarize(pricing)
    assert summary["estimate_cost"] is None
    assert summary["known_cost"] == "0.00431"
    assert summary["items"][-1]["unpriced_reason"] == "rate_unavailable"


def test_usage_context_is_reset() -> None:
    first = RequestUsage()
    second = RequestUsage()
    with track_usage(first):
        record_llm_usage(LlmUsage("google_ai", "model", 1, 1))
        with track_usage(second):
            record_llm_usage(LlmUsage("google_ai", "model", 2, 2))
        record_llm_usage(LlmUsage("google_ai", "model", 3, 3))
    record_llm_usage(LlmUsage("google_ai", "model", 4, 4))
    assert [event.input_tokens for event in first.events] == [1, 3]
    assert [event.input_tokens for event in second.events] == [2]
