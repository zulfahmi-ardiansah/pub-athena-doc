from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Iterator, List, Optional, Tuple, Union

from src.config.pricing import PricingConfig


@dataclass(frozen=True)
class LlmUsage:
    billing_service: str
    model: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    cached_input_tokens: int = 0


@dataclass(frozen=True)
class OcrUsage:
    billing_service: str
    feature: str
    units: Optional[int]


UsageEvent = Union[LlmUsage, OcrUsage]


@dataclass
class RequestUsage:
    events: List[UsageEvent] = field(default_factory=list)

    def _price_event(
        self, event: UsageEvent, pricing: Optional[PricingConfig]
    ) -> Tuple[Optional[Decimal], Optional[str]]:
        if isinstance(event, LlmUsage):
            if event.input_tokens is None or event.output_tokens is None:
                return None, "usage_unavailable"
            rate = pricing.get_llm_rate(
                event.billing_service, event.model, event.input_tokens
            ) if pricing else None
            if rate is None:
                return None, "rate_unavailable"
            if event.cached_input_tokens and rate.cached_input_usd_per_million_tokens is None:
                return None, "cached_rate_unavailable"
            regular_input = event.input_tokens - event.cached_input_tokens
            if regular_input < 0:
                return None, "invalid_usage"
            cached_rate = rate.cached_input_usd_per_million_tokens or Decimal(0)
            cost = (
                Decimal(regular_input) * rate.input_usd_per_million_tokens
                + Decimal(event.cached_input_tokens) * cached_rate
                + Decimal(event.output_tokens) * rate.output_usd_per_million_tokens
            ) / Decimal(1_000_000)
            return cost, None

        if event.units is None:
            return None, "usage_unavailable"
        rate = pricing.get_ocr_rate(event.billing_service, event.feature) if pricing else None
        if rate is None:
            return None, "rate_unavailable"
        return Decimal(event.units) * rate.usd_per_thousand_units / Decimal(1_000), None

    def summarize(self, pricing: Optional[PricingConfig]) -> Dict[str, object]:
        items: List[Dict[str, object]] = []
        known_cost = Decimal(0)
        complete = True
        for event in self.events:
            cost, reason = self._price_event(event, pricing)
            if cost is None:
                complete = False
            else:
                known_cost += cost
            if isinstance(event, LlmUsage):
                item: Dict[str, object] = {
                    "service": event.billing_service,
                    "model": event.model,
                    "input_tokens": event.input_tokens,
                    "output_tokens": event.output_tokens,
                    "cached_input_tokens": event.cached_input_tokens,
                }
            else:
                item = {
                    "service": event.billing_service,
                    "feature": event.feature,
                    "units": event.units,
                }
            item["estimate_cost"] = format(cost, "f") if cost is not None else None
            if reason:
                item["unpriced_reason"] = reason
            items.append(item)

        return {
            "currency": "USD",
            "price_date": pricing.effective_date.isoformat() if pricing else None,
            "estimate_cost": format(known_cost, "f") if complete else None,
            "known_cost": format(known_cost, "f"),
            "complete": complete,
            "items": items,
        }


_current_usage: ContextVar[Optional[RequestUsage]] = ContextVar("request_usage", default=None)


@contextmanager
def track_usage(usage: RequestUsage) -> Iterator[None]:
    token = _current_usage.set(usage)
    try:
        yield
    finally:
        _current_usage.reset(token)


def record_llm_usage(event: LlmUsage) -> None:
    usage = _current_usage.get()
    if usage is not None:
        usage.events.append(event)


def record_ocr_usage(event: OcrUsage) -> None:
    usage = _current_usage.get()
    if usage is not None:
        usage.events.append(event)
