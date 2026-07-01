from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator

from ecl_trainer.core.models import FrozenModel


class IndustryDomain(StrEnum):
    FINANCIAL_SERVICES = "financial_services"
    HEALTHCARE_CLINICAL = "healthcare_clinical"
    IT_SOFTWARE = "it_software"
    LEGAL_REGULATORY = "legal_regulatory"
    RETAIL_ECOMMERCE = "retail_ecommerce"
    CONTACT_CENTERS = "contact_centers"
    TELECOM = "telecom"
    MEDIA_GAMING = "media_gaming"
    MANUFACTURING = "manufacturing"
    PHARMA_BIOTECH = "pharma_biotech"
    EDUCATION = "education"
    GOVERNMENT = "government"
    HR_TALENT = "hr_talent"
    MARKETING_ADVERTISING = "marketing_advertising"
    AUTOMOTIVE_MOBILITY = "automotive_mobility"
    LOGISTICS_SUPPLY_CHAIN = "logistics_supply_chain"
    ENERGY_UTILITIES = "energy_utilities"
    AEROSPACE_DEFENSE = "aerospace_defense"
    TRAVEL_HOSPITALITY = "travel_hospitality"
    REAL_ESTATE_PROPTECH = "real_estate_proptech"


class DomainSelectionMode(StrEnum):
    AUTO = "auto"
    EXPLICIT = "explicit"
    CORE_ONLY = "core_only"


class DomainExtensionStatus(StrEnum):
    ACTIVE = "active"
    REGISTERED = "registered"
    DISABLED = "disabled"
    MISSING_SEED = "missing_seed"


TOP_20_DOMAINS: tuple[IndustryDomain, ...] = tuple(IndustryDomain)

DOMAIN_ALIASES: dict[str, IndustryDomain] = {
    "banking": IndustryDomain.FINANCIAL_SERVICES,
    "bfsi": IndustryDomain.FINANCIAL_SERVICES,
    "finance": IndustryDomain.FINANCIAL_SERVICES,
    "financial": IndustryDomain.FINANCIAL_SERVICES,
    "financial_services": IndustryDomain.FINANCIAL_SERVICES,
    "healthcare": IndustryDomain.HEALTHCARE_CLINICAL,
    "clinical": IndustryDomain.HEALTHCARE_CLINICAL,
    "legal": IndustryDomain.LEGAL_REGULATORY,
    "software": IndustryDomain.IT_SOFTWARE,
    "it": IndustryDomain.IT_SOFTWARE,
}


class AtlasToggleConfig(FrozenModel):
    global_core_enabled: bool = True
    enabled_domains: list[IndustryDomain] = Field(default_factory=list)
    domain_selection_mode: DomainSelectionMode = DomainSelectionMode.AUTO

    @field_validator("global_core_enabled")
    @classmethod
    def global_core_cannot_be_disabled(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("global_core_enabled is always true")
        return value


class DomainSelectionResult(FrozenModel):
    global_core_used: bool = True
    enabled_domains: list[IndustryDomain] = Field(default_factory=list)
    skipped_domains: list[IndustryDomain] = Field(default_factory=list)
    domain_selection_mode: DomainSelectionMode = DomainSelectionMode.AUTO
    domain_extension_status: dict[str, str] = Field(default_factory=dict)


def parse_domain(value: str | IndustryDomain) -> IndustryDomain:
    if isinstance(value, IndustryDomain):
        return value
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in DOMAIN_ALIASES:
        return DOMAIN_ALIASES[normalized]
    return IndustryDomain(normalized)


def parse_domains(values: str | list[str] | list[IndustryDomain] | None) -> list[IndustryDomain]:
    if values is None:
        return []
    if isinstance(values, str):
        if not values.strip():
            return []
        return [parse_domain(part) for part in values.split(",") if part.strip()]
    return [parse_domain(value) for value in values]


def infer_domain_from_metadata(metadata: dict[str, Any]) -> IndustryDomain | None:
    candidates: list[Any] = []
    for key in ("industry_domain", "domain_id", "domain", "industry", "domain_category"):
        value = metadata.get(key)
        if value is not None:
            candidates.append(value)
    for tag in metadata.get("semantic_tags", []) or []:
        if isinstance(tag, dict) and tag.get("key") in {"industry_domain", "domain_category", "industry"}:
            candidates.append(tag.get("value"))
    for candidate in candidates:
        try:
            return parse_domain(str(candidate))
        except ValueError:
            continue
    return None
