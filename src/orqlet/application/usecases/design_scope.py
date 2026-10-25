"""What a design or a plan touches, as the facts that the change class is computed from."""

from __future__ import annotations

from collections.abc import Iterable

from orqlet.application.contracts.design_set import DesignSet, ExpectedChange
from orqlet.domain.change_class import ChangePolicy, ChangeScope, shared_directory

# Surfaces for which this release has an extractor. Every other surface is `verification: manual`,
# which the proposal allows (17.4.1): the approval record marks it unverifiable by CI and the
# Architecture Reviewer compares it by hand.
EXTRACTOR_SURFACES = frozenset({"public-api", "dependency", "security"})


def change_policy(design: DesignSet) -> ChangePolicy:
    config = design.extractor_config
    return ChangePolicy(
        security_globs=config.security_globs,
        d3_globs=config.migration_paths,
    )


def change_scope(
    design: DesignSet, paths: tuple[str, ...], changes: Iterable[ExpectedChange]
) -> ChangeScope:
    """The scope of `paths` (files or globs) with the surfaces the given expected changes name."""
    surfaces = {change.surface for change in changes}
    return ChangeScope(
        paths=paths,
        one_module=bool(shared_directory(paths)),
        changes_interface=bool({"public-api", "http-contract"} & surfaces),
        changes_dependency="dependency" in surfaces,
        changes_persisted_format="persisted-schema" in surfaces,
        trust_boundary="trust-boundary" in surfaces or bool(design.scope.trust_boundaries),
        security_domain="security" in surfaces,
        data_model="persisted-schema" in surfaces,
    )
