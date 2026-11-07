"""
Role-Based Access Control (RBAC) Module.
Enforces principle of least privilege across investigative agencies and judicial roles.
"""

from __future__ import annotations
from enum import Enum
from typing import Set, Dict


class Role(str, Enum):
    INVESTIGATOR = "INVESTIGATOR"         # Case investigator (e.g. สอท. / สน.)
    SUPERVISOR = "SUPERVISOR"             # Inquiry official / Superintendent
    EVIDENCE_AUDITOR = "EVIDENCE_AUDITOR" # Independent forensic evidence auditor
    COURT_CLERK = "COURT_CLERK"           # Judicial / Court registrar
    ANALYST = "ANALYST"                   # Intelligence analyst (masked PII only)


class Permission(str, Enum):
    VIEW_UNMASKED_PII = "VIEW_UNMASKED_PII"
    SOLVE_FLOW_MATCHING = "SOLVE_FLOW_MATCHING"
    PIN_FORCE_MATCH = "PIN_FORCE_MATCH"
    EXPORT_COURT_DOSSIER = "EXPORT_COURT_DOSSIER"
    REQUEST_AOC_FREEZING = "REQUEST_AOC_FREEZING"
    AUDIT_MERKLE_CHAIN = "AUDIT_MERKLE_CHAIN"
    ADMIN_CASE_MANAGEMENT = "ADMIN_CASE_MANAGEMENT"


ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.INVESTIGATOR: {
        Permission.VIEW_UNMASKED_PII,
        Permission.SOLVE_FLOW_MATCHING,
        Permission.PIN_FORCE_MATCH,
        Permission.EXPORT_COURT_DOSSIER,
        Permission.REQUEST_AOC_FREEZING,
    },
    Role.SUPERVISOR: {
        Permission.VIEW_UNMASKED_PII,
        Permission.SOLVE_FLOW_MATCHING,
        Permission.PIN_FORCE_MATCH,
        Permission.EXPORT_COURT_DOSSIER,
        Permission.REQUEST_AOC_FREEZING,
        Permission.ADMIN_CASE_MANAGEMENT,
    },
    Role.EVIDENCE_AUDITOR: {
        Permission.AUDIT_MERKLE_CHAIN,
        Permission.SOLVE_FLOW_MATCHING,
    },
    Role.COURT_CLERK: {
        Permission.EXPORT_COURT_DOSSIER,
        Permission.AUDIT_MERKLE_CHAIN,
    },
    Role.ANALYST: {
        Permission.SOLVE_FLOW_MATCHING,
    },
}


class RBACManager:
    """Validates user authorization against assigned role."""

    @staticmethod
    def has_permission(role: Role, permission: Permission) -> bool:
        return permission in ROLE_PERMISSIONS.get(role, set())

    @staticmethod
    def assert_permission(role: Role, permission: Permission) -> None:
        if not RBACManager.has_permission(role, permission):
            raise PermissionError(f"Role '{role.value}' lacks required permission '{permission.value}'")
