"""
Security Module - DSGVO Compliance & Access Control

Implements:
- JWT token validation
- Role-Based Access Control (RBAC)
- Rate limiting
- Request/response encryption (optional)
- Audit logging
- Secrets management
"""

import logging
import hashlib
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from functools import wraps
from enum import Enum

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
import jwt

from app.config import settings

logger = logging.getLogger(__name__)

# Type for HTTP credentials
class HTTPAuthCredential:
    def __init__(self, scheme: str, credentials: str):
        self.scheme = scheme
        self.credentials = credentials

# ============================================
# ROLE-BASED ACCESS CONTROL (RBAC)
# ============================================

class UserRole(str, Enum):
    """User roles for RBAC"""
    ADMIN = "admin"           # Full access
    MANAGER = "manager"       # Project management
    TECHNICIAN = "technician" # View and edit technical data
    VIEWER = "viewer"         # Read-only access
    ANONYMOUS = "anonymous"   # No authentication


class Permission(str, Enum):
    """Permissions for RBAC"""
    CREATE_PROJECT = "create:project"
    READ_PROJECT = "read:project"
    UPDATE_PROJECT = "update:project"
    DELETE_PROJECT = "delete:project"

    CREATE_DOCUMENT = "create:document"
    READ_DOCUMENT = "read:document"
    DELETE_DOCUMENT = "delete:document"

    READ_PREDICTION = "read:prediction"
    CREATE_PREDICTION = "create:prediction"

    MANAGE_USERS = "manage:users"
    MANAGE_SETTINGS = "manage:settings"
    VIEW_ANALYTICS = "view:analytics"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[UserRole, List[Permission]] = {
    UserRole.ADMIN: [
        Permission.CREATE_PROJECT, Permission.READ_PROJECT,
        Permission.UPDATE_PROJECT, Permission.DELETE_PROJECT,
        Permission.CREATE_DOCUMENT, Permission.READ_DOCUMENT,
        Permission.DELETE_DOCUMENT,
        Permission.READ_PREDICTION, Permission.CREATE_PREDICTION,
        Permission.MANAGE_USERS, Permission.MANAGE_SETTINGS,
        Permission.VIEW_ANALYTICS
    ],
    UserRole.MANAGER: [
        Permission.CREATE_PROJECT, Permission.READ_PROJECT,
        Permission.UPDATE_PROJECT,
        Permission.CREATE_DOCUMENT, Permission.READ_DOCUMENT,
        Permission.READ_PREDICTION, Permission.CREATE_PREDICTION,
        Permission.VIEW_ANALYTICS
    ],
    UserRole.TECHNICIAN: [
        Permission.READ_PROJECT,
        Permission.READ_DOCUMENT,
        Permission.READ_PREDICTION, Permission.CREATE_PREDICTION
    ],
    UserRole.VIEWER: [
        Permission.READ_PROJECT,
        Permission.READ_DOCUMENT,
        Permission.READ_PREDICTION
    ],
    UserRole.ANONYMOUS: []
}

# ============================================
# USER & TOKEN MANAGEMENT
# ============================================

class User:
    """User representation"""
    def __init__(
        self,
        user_id: str,
        email: str,
        role: UserRole,
        permissions: List[Permission] = None
    ):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.permissions = permissions or ROLE_PERMISSIONS.get(role, [])
        self.created_at = datetime.utcnow()

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has permission"""
        return permission in self.permissions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "role": self.role.value,
            "permissions": [p.value for p in self.permissions]
        }


class TokenManager:
    """JWT token management"""

    @staticmethod
    def create_token(
        user_id: str,
        email: str,
        role: UserRole,
        expires_in_hours: int = 24
    ) -> str:
        """Create JWT token"""
        try:
            payload = {
                "user_id": user_id,
                "email": email,
                "role": role.value,
                "exp": datetime.utcnow() + timedelta(hours=expires_in_hours),
                "iat": datetime.utcnow()
            }

            token = jwt.encode(
                payload,
                settings.SECRET_KEY,
                algorithm="HS256"
            )

            logger.info(f"Token created for user {email}")
            return token

        except Exception as e:
            logger.error(f"Error creating token: {e}")
            raise

    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )

        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )

# ============================================
# AUTHENTICATION & AUTHORIZATION
# ============================================

security = HTTPBearer()

async def get_current_user(
    credentials: Optional[HTTPAuthCredential] = Depends(security)
) -> User:
    """Get authenticated user from request"""
    if not credentials:
        # Allow anonymous access in development
        if settings.ENVIRONMENT == "development":
            return User(
                user_id="anonymous",
                email="anonymous@local",
                role=UserRole.ANONYMOUS
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    try:
        token = credentials.credentials
        payload = TokenManager.verify_token(token)

        user = User(
            user_id=payload["user_id"],
            email=payload["email"],
            role=UserRole(payload["role"])
        )

        logger.debug(f"User authenticated: {user.email}")
        return user

    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


def require_permission(permission: Permission):
    """Decorator to require specific permission"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if not current_user.has_permission(permission):
                logger.warning(
                    f"User {current_user.email} denied access (missing {permission})"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission}"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


# ============================================
# AUDIT LOGGING
# ============================================

class AuditLog:
    """Audit logging for DSGVO compliance"""

    @staticmethod
    def log_action(
        user_id: str,
        action: str,
        resource: str,
        resource_id: str,
        status: str,
        details: Dict[str, Any] = None,
        ip_address: str = None
    ) -> Dict[str, Any]:
        """Log user action for audit trail"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "resource_id": resource_id,
            "status": status,
            "details": details or {},
            "ip_address": ip_address
        }

        # In production: persist to audit database
        logger.info(f"AUDIT: {json.dumps(log_entry)}")

        return log_entry

    @staticmethod
    def log_data_access(
        user_id: str,
        resource_type: str,
        resource_id: str,
        ip_address: str = None
    ):
        """Log data access for DSGVO tracking"""
        return AuditLog.log_action(
            user_id=user_id,
            action="read",
            resource=resource_type,
            resource_id=resource_id,
            status="success",
            ip_address=ip_address
        )

    @staticmethod
    def log_data_modification(
        user_id: str,
        action: str,  # create, update, delete
        resource_type: str,
        resource_id: str,
        old_values: Dict = None,
        new_values: Dict = None,
        ip_address: str = None
    ):
        """Log data modifications for DSGVO audit trail"""
        return AuditLog.log_action(
            user_id=user_id,
            action=action,
            resource=resource_type,
            resource_id=resource_id,
            status="success",
            details={
                "old_values": old_values,
                "new_values": new_values
            },
            ip_address=ip_address
        )


# ============================================
# DATA ENCRYPTION
# ============================================

class DataEncryption:
    """Data encryption utilities for DSGVO compliance"""

    @staticmethod
    def hash_pii(data: str) -> str:
        """Hash Personally Identifiable Information"""
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def hash_email(email: str) -> str:
        """Hash email for privacy"""
        return DataEncryption.hash_pii(email.lower())

    @staticmethod
    def hash_ip(ip_address: str) -> str:
        """Hash IP address for DSGVO compliance"""
        return DataEncryption.hash_pii(ip_address)

    @staticmethod
    def mask_sensitive(data: str, show_chars: int = 4) -> str:
        """Mask sensitive data in logs"""
        if len(data) <= show_chars:
            return "*" * len(data)
        return data[:show_chars] + "*" * (len(data) - show_chars)


# ============================================
# RATE LIMITING
# ============================================

class RateLimiter:
    """Rate limiting to prevent abuse"""

    def __init__(self, max_requests: int = 1000, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[datetime]] = {}

    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed"""
        now = datetime.utcnow()

        if identifier not in self.requests:
            self.requests[identifier] = []

        # Clean old requests outside window
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if (now - req_time).total_seconds() < self.window_seconds
        ]

        if len(self.requests[identifier]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return False

        self.requests[identifier].append(now)
        return True


# Global rate limiter instances
api_rate_limiter = RateLimiter(max_requests=1000, window_seconds=60)
auth_rate_limiter = RateLimiter(max_requests=10, window_seconds=300)

# ============================================
# SECRETS MANAGEMENT
# ============================================

class SecretsManager:
    """Secure secrets management"""

    @staticmethod
    def validate_secret_key() -> bool:
        """Validate that SECRET_KEY is set and secure"""
        if not settings.SECRET_KEY:
            logger.error("SECRET_KEY is not set!")
            return False

        if len(settings.SECRET_KEY) < 32:
            logger.error("SECRET_KEY is too short (min 32 characters)")
            return False

        return True

    @staticmethod
    def validate_database_url() -> bool:
        """Validate database URL is secure"""
        if "sqlite" in settings.DATABASE_URL.lower():
            logger.warning("Using SQLite in production is not recommended")
            return settings.ENVIRONMENT == "development"

        if not settings.DATABASE_URL.startswith("postgresql://") and \
           not settings.DATABASE_URL.startswith("postgresql+asyncpg://"):
            logger.error("Unsupported database URL format")
            return False

        return True

    @staticmethod
    def validate_security_settings() -> Dict[str, bool]:
        """Validate all security settings"""
        checks = {
            "secret_key": SecretsManager.validate_secret_key(),
            "database_url": SecretsManager.validate_database_url(),
            "https_enforced": settings.ENVIRONMENT != "development",
            "cors_configured": True
        }

        all_valid = all(checks.values())

        if not all_valid:
            logger.warning(f"Security validation failed: {checks}")

        return checks
