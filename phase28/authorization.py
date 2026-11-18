"""P28-06: tenant-aware, deny-before-retrieve authorization (offline lab).

Principal must come from verified gateway/OIDC authentication, NOT user input.
This module makes no network, model, or database calls on denial.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar
import re

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_T = TypeVar("_T")


class AccessDenied(PermissionError):
    """Generic denial, without revealing resources or tenant membership."""


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    tenant_id: str
    roles: frozenset[str]

    def __post_init__(self) -> None:
        if not isinstance(self.subject, str) or not _ID.fullmatch(self.subject):
            raise ValueError("Invalid principal subject")
        if not isinstance(self.tenant_id, str) or not _ID.fullmatch(self.tenant_id):
            raise ValueError("Invalid principal tenant")
        if not isinstance(self.roles, frozenset) or any(
            not isinstance(role, str) or not _ID.fullmatch(role)
            for role in self.roles
        ):
            raise ValueError("Invalid principal roles")


@dataclass(frozen=True, slots=True)
class DocumentScope:
    tenant_id: str
    domain: str

    def __post_init__(self) -> None:
        for value in (self.tenant_id, self.domain):
            if not isinstance(value, str) or not _ID.fullmatch(value):
                raise ValueError("Invalid document scope")


class DomainAuthorizer:
    """Explicit role -> permitted domains; unknown roles/domains deny.

    Rules are trusted configuration, not payload supplied by a caller.
    """

    def __init__(self, grants: dict[str, frozenset[str]]) -> None:
        if not isinstance(grants, dict):
            raise TypeError("grants must be a dictionary")
        validated = {}
        for role, domains in grants.items():
            if not isinstance(role, str) or not _ID.fullmatch(role):
                raise ValueError("Invalid role policy")
            if not isinstance(domains, frozenset) or any(
                not isinstance(d, str) or not _ID.fullmatch(d) for d in domains
            ):
                raise ValueError("Invalid domain policy")
            validated[role] = domains
        self._grants = validated

    def authorize(self, principal: Principal, scope: DocumentScope) -> None:
        if not isinstance(principal, Principal) or not isinstance(scope, DocumentScope):
            raise AccessDenied("Access denied")
        if principal.tenant_id != scope.tenant_id:
            raise AccessDenied("Access denied")
        if not any(scope.domain in self._grants.get(role, frozenset())
                   for role in principal.roles):
            raise AccessDenied("Access denied")


def guarded_retrieve(
    *, principal: Principal, scope: DocumentScope,
    authorizer: DomainAuthorizer, retrieve: Callable[[DocumentScope], _T],
) -> _T:
    """Call retrieval only after the trusted authorization check.

    Retrieval must independently constrain queries by both tenant AND domain.
    Never trust document-level ACLs obtained from an unverified index response.
    """
    if not isinstance(authorizer, DomainAuthorizer):
        raise TypeError("authorizer must be DomainAuthorizer")
    if not callable(retrieve):
        raise TypeError("retrieve must be callable")
    authorizer.authorize(principal, scope)
    return retrieve(scope)
