from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, model_validator


class LlmTokenPricing(BaseModel):
    input_usd_per_million_tokens: Decimal = Field(ge=0, allow_inf_nan=False)
    output_usd_per_million_tokens: Decimal = Field(ge=0, allow_inf_nan=False)
    cached_input_usd_per_million_tokens: Optional[Decimal] = Field(
        default=None, ge=0, allow_inf_nan=False
    )


class LlmTokenPricingTier(LlmTokenPricing):
    max_input_tokens: int = Field(gt=0)


class LlmTieredPricing(BaseModel):
    tiers: List[LlmTokenPricingTier] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_tier_order(self) -> "LlmTieredPricing":
        limits = [tier.max_input_tokens for tier in self.tiers]
        if limits != sorted(set(limits)):
            raise ValueError("Pricing tiers must have strictly increasing max_input_tokens")
        return self


class OcrUnitPricing(BaseModel):
    usd_per_thousand_units: Decimal = Field(ge=0, allow_inf_nan=False)


class PricingConfig(BaseModel):
    effective_date: date
    llm_rates: Dict[str, Dict[str, Union[LlmTokenPricing, LlmTieredPricing]]] = Field(default_factory=dict)
    ocr_rates: Dict[str, Dict[str, OcrUnitPricing]] = Field(default_factory=dict)

    def get_llm_rate(
        self, billing_service: str, model: str, input_tokens: Optional[int] = None
    ) -> Optional[LlmTokenPricing]:
        rate = self.llm_rates.get(billing_service, {}).get(model)
        if isinstance(rate, LlmTokenPricing):
            return rate
        if isinstance(rate, LlmTieredPricing) and input_tokens is not None:
            return next(
                (tier for tier in rate.tiers if input_tokens <= tier.max_input_tokens), None
            )
        return None

    def get_ocr_rate(self, billing_service: str, feature: str) -> Optional[OcrUnitPricing]:
        return self.ocr_rates.get(billing_service, {}).get(feature)


def load_pricing_config(path: str) -> Optional[PricingConfig]:
    if not path:
        return None
    return PricingConfig.model_validate_json(Path(path).read_text(encoding="utf-8"))
