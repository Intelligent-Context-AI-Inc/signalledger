from __future__ import annotations

from typing import Any

from ecl_trainer.oracle.atlas import _EclInternalCore
from ecl_trainer.oracle.domains import (
    DomainExtensionStatus,
    DomainSelectionMode,
    DomainSelectionResult,
    IndustryDomain,
    infer_domain_from_metadata,
    parse_domains,
)


def resolve_domain_selection(
    *,
    metadata: dict[str, Any] | None,
    enabled_domains: str | list[str] | list[IndustryDomain] | None,
    domain_selection_mode: str | DomainSelectionMode,
    core: _EclInternalCore,
) -> DomainSelectionResult:
    mode = DomainSelectionMode(domain_selection_mode)
    requested = parse_domains(enabled_domains)
    statuses = core.domain_statuses()
    selected: list[IndustryDomain] = []
    skipped: list[IndustryDomain] = []

    if mode == DomainSelectionMode.CORE_ONLY:
        return DomainSelectionResult(
            enabled_domains=[],
            skipped_domains=[],
            domain_selection_mode=mode,
            domain_extension_status=statuses,
        )
    if mode == DomainSelectionMode.EXPLICIT:
        selected = requested
    else:
        inferred = infer_domain_from_metadata(metadata or {})
        selected = [inferred] if inferred else []
        if not selected:
            return DomainSelectionResult(
                enabled_domains=[],
                skipped_domains=[],
                domain_selection_mode=DomainSelectionMode.CORE_ONLY,
                domain_extension_status={"skipped_no_domain": "true", **statuses},
            )

    active: list[IndustryDomain] = []
    for domain in selected:
        if statuses.get(domain.value) == DomainExtensionStatus.ACTIVE.value:
            active.append(domain)
        else:
            skipped.append(domain)
    return DomainSelectionResult(
        enabled_domains=active,
        skipped_domains=skipped,
        domain_selection_mode=mode,
        domain_extension_status=statuses,
    )
