"""
Role-Based Access Control (RBAC) System
Defines roles, permissions, and authorization logic
"""
from enum import Enum
from typing import List, Set
from functools import wraps
from fastapi import HTTPException, Depends
from pydantic import BaseModel


class Role(str, Enum):
    """User roles in the system"""
    AUDITOR = "auditor"
    MANAGER = "manager"
    ADMIN = "admin"


class Permission(str, Enum):
    """System permissions"""
    # Audit permissions
    VIEW_ASSIGNED_AUDITS = "view_assigned_audits"
    VIEW_ALL_AUDITS = "view_all_audits"
    CREATE_AUDIT = "create_audit"
    SUBMIT_AUDIT = "submit_audit"
    ADD_NOTES = "add_notes"
    MARK_COMPLIANCE = "mark_compliance"
    
    # Script permissions
    VIEW_SCRIPTS = "view_scripts"
    CREATE_SCRIPT = "create_script"
    EDIT_SCRIPT = "edit_script"
    DELETE_SCRIPT = "delete_script"
    
    # Analytics permissions
    VIEW_OWN_METRICS = "view_own_metrics"
    VIEW_ALL_ANALYTICS = "view_all_analytics"
    VIEW_TEAM_ANALYTICS = "view_team_analytics"
    EXPORT_REPORTS = "export_reports"
    
    # Management permissions
    MANAGE_USERS = "manage_users"
    CONFIGURE_SYSTEM = "configure_system"
    VIEW_ALL_TEAMS = "view_all_teams"
    SET_RETENTION_POLICY = "set_retention_policy"
    
    # Audio permissions
    UPLOAD_AUDIO = "upload_audio"
    DELETE_AUDIO = "delete_audio"


# Role-Permission Mapping
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.AUDITOR: {
        # Auditor can only view assigned audits and their own performance
        Permission.VIEW_ASSIGNED_AUDITS,
        Permission.SUBMIT_AUDIT,
        Permission.ADD_NOTES,
        Permission.MARK_COMPLIANCE,
        Permission.VIEW_SCRIPTS,
        Permission.VIEW_OWN_METRICS,
        Permission.UPLOAD_AUDIO,
    },
    
    Role.MANAGER: {
        # Manager has full access to analytics and reporting
        Permission.VIEW_ALL_AUDITS,
        Permission.VIEW_ALL_ANALYTICS,
        Permission.VIEW_TEAM_ANALYTICS,
        Permission.EXPORT_REPORTS,
        Permission.VIEW_SCRIPTS,
        Permission.CREATE_SCRIPT,
        Permission.EDIT_SCRIPT,
        Permission.DELETE_SCRIPT,
        Permission.VIEW_ALL_TEAMS,
        Permission.CONFIGURE_SYSTEM,
        Permission.SET_RETENTION_POLICY,
    },
    
    Role.ADMIN: set(Permission),  # Admin has all permissions
}


class RolePermissions(BaseModel):
    """Model for role permissions configuration"""
    role: Role
    permissions: List[Permission]
    description: str


def get_role_permissions(role: Role) -> Set[Permission]:
    """Get all permissions for a given role"""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(user_role: Role, required_permission: Permission) -> bool:
    """Check if a role has a specific permission"""
    role_perms = get_role_permissions(user_role)
    return required_permission in role_perms


def require_permission(permission: Permission):
    """
    Decorator to protect routes with permission check
    Usage: @require_permission(Permission.VIEW_ALL_AUDITS)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs (injected by Depends)
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            user_role = Role(current_user.role)
            if not has_permission(user_role, permission):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Insufficient permissions. Required: {permission.value}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(*allowed_roles: Role):
    """
    Decorator to protect routes with role check
    Usage: @require_role(Role.MANAGER, Role.ADMIN)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            user_role = Role(current_user.role)
            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied. Required role: {', '.join([r.value for r in allowed_roles])}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Role descriptions for documentation
ROLE_DESCRIPTIONS = {
    Role.AUDITOR: {
        "name": "Auditor (Team Lead)",
        "description": "Access to assigned telecaller recordings and audit tasks only",
        "capabilities": [
            "View and play assigned recordings",
            "Fill and submit audit evaluation forms",
            "Add timestamped notes and remarks",
            "Mark compliance/non-compliance",
            "View own audit history and metrics",
        ],
        "restrictions": [
            "Cannot see other teams' data",
            "Cannot access system configuration",
            "Cannot view organization-wide analytics",
        ]
    },
    
    Role.MANAGER: {
        "name": "Manager / Senior Management",
        "description": "Full access to all teams, reports, analytics, and configurations",
        "capabilities": [
            "View every call and audit detail",
            "Filter audits by team, auditor, campaign, date",
            "Export reports (CSV/PDF)",
            "Configure audit form weights and scoring",
            "Set recording retention and deletion policies",
            "View compliance trends and alerts",
            "Manage team assignments",
            "Access leadership dashboard",
        ],
        "restrictions": []
    },
}


def get_role_description(role: Role) -> dict:
    """Get detailed description of a role"""
    return ROLE_DESCRIPTIONS.get(role, {})
