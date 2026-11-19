"""P28-13: offline, operator-supplied JWKS verification; never trust token claims unverified.

The deployment must separately implement pinned HTTPS discovery, bounded JWKS
refresh, rotation, trusted issuer configuration and monitoring. No network here.
"""
from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import urlsplit
import jwt
from jwt import InvalidTokenError

from phase28.authorization import Principal


class AuthenticationFailed(PermissionError):
    """Generic authentication failure without leaking token or key details."""


class OIDCVerifier:
    def __init__(self, *, issuer: str, audience: str, jwks: Mapping):
        try:
            url = urlsplit(issuer)
            if (url.scheme != "https" or not url.hostname or url.username or
                    url.password or url.fragment or url.query or issuer.endswith("/")):
                raise ValueError
            if not isinstance(audience, str) or not audience.strip():
                raise ValueError
            if not isinstance(jwks, Mapping) or not isinstance(jwks.get("keys"), list):
                raise ValueError
            keys = {}
            for obj in jwks["keys"]:
                if not isinstance(obj, dict) or obj.get("kty") != "RSA" or obj.get("alg", "RS256") != "RS256":
                    raise ValueError
                if obj.get("use", "sig") != "sig" or ("key_ops" in obj and "verify" not in obj["key_ops"]):
                    raise ValueError
                kid = obj.get("kid")
                if not isinstance(kid, str) or not (1 <= len(kid) <= 128) or kid in keys:
                    raise ValueError
                keys[kid] = jwt.PyJWK.from_dict(obj, algorithm="RS256").key
            if not keys:
                raise ValueError
        except (TypeError, ValueError, jwt.PyJWTError) as exc:
            raise ValueError("Invalid trusted OIDC configuration") from exc
        self._issuer = issuer
        self._audience = audience
        self._keys = keys

    def verify(self, token: str) -> Principal:
        try:
            if not isinstance(token, str) or not token or len(token) > 16384:
                raise AuthenticationFailed("Unauthorized")
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256" or header.get("typ", "JWT") != "JWT":
                raise AuthenticationFailed("Unauthorized")
            kid = header.get("kid")
            if not isinstance(kid, str) or kid not in self._keys:
                raise AuthenticationFailed("Unauthorized")
            claims = jwt.decode(
                token, self._keys[kid], algorithms=["RS256"],
                audience=self._audience, issuer=self._issuer,
                options={"require": ["exp", "iat", "nbf", "sub", "iss", "aud"]},
                leeway=0,
            )
            roles = claims.get("roles")
            tenant = claims.get("tenant_id")
            if (not isinstance(roles, list) or not roles or len(roles) > 32 or
                    any(not isinstance(r, str) for r in roles) or len(set(roles)) != len(roles)):
                raise AuthenticationFailed("Unauthorized")
            return Principal(subject=claims["sub"], tenant_id=tenant, roles=frozenset(roles))
        except (InvalidTokenError, KeyError, TypeError, ValueError, AuthenticationFailed) as exc:
            raise AuthenticationFailed("Unauthorized") from exc
