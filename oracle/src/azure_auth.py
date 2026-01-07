"""
Microsoft Azure / Entra ID Authentication Module

This module handles validation of Microsoft Azure AD / Entra ID access tokens
for the Cardea Oracle backend API.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import jwt
import requests
from jwt import PyJWKClient
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class AzureAuthService:
    """Service for validating Microsoft Azure AD tokens"""

    def __init__(self):
        """Initialize Azure Authentication Service"""
        self.client_id = os.getenv("AZURE_CLIENT_ID", "")
        self.tenant_id = os.getenv("AZURE_TENANT_ID", "")
        self.authority = os.getenv(
            "AZURE_AUTHORITY",
            f"https://login.microsoftonline.com/{self.tenant_id}",
        )
        self.jwks_uri = os.getenv(
            "AZURE_JWKS_URI",
            f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys",
        )
        self.token_issuer = os.getenv(
            "AZURE_TOKEN_ISSUER",
            f"https://login.microsoftonline.com/{self.tenant_id}/v2.0",
        )
        self.api_scope = os.getenv(
            "AZURE_API_SCOPE", f"api://{self.client_id}/access_as_user"
        )
        self.enabled = os.getenv("ENABLE_AZURE_AUTH", "true").lower() == "true"

        # Validate configuration
        if self.enabled:
            if not self.client_id or "PASTE_YOUR" in self.client_id:
                logger.warning(
                    "Azure Client ID not configured. Set AZURE_CLIENT_ID in .env"
                )
                self.enabled = False
            if not self.tenant_id or "PASTE_YOUR" in self.tenant_id:
                logger.warning(
                    "Azure Tenant ID not configured. Set AZURE_TENANT_ID in .env"
                )
                self.enabled = False

        # Initialize JWK client for token signature verification
        if self.enabled:
            try:
                self.jwks_client = PyJWKClient(self.jwks_uri)
                logger.info("Azure Authentication Service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Azure auth JWK client: {e}")
                self.enabled = False
        else:
            self.jwks_client = None
            logger.info("Azure Authentication is disabled")

    def is_enabled(self) -> bool:
        """Check if Azure authentication is enabled and configured"""
        return self.enabled

    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a Microsoft Azure AD access token

        Args:
            token: The JWT access token from the frontend

        Returns:
            Dict containing user information from the token

        Raises:
            HTTPException: If token validation fails
        """
        if not self.enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Azure authentication is not enabled",
            )

        try:
            # Get the signing key from Microsoft's JWKS endpoint
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            # For External ID, the issuer might have trailing slash variations
            # Accept both with and without trailing slash
            issuer_options = [
                self.token_issuer,
                self.token_issuer.rstrip('/'),
                f"{self.token_issuer}/",
            ]

            # Decode and validate the token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": False,  # We'll verify issuer manually below
                },
            )

            # Manually verify issuer (allow variations)
            token_issuer = payload.get("iss", "")
            if not any(token_issuer == iss or token_issuer == iss.rstrip('/') for iss in issuer_options):
                logger.error(f"Token issuer mismatch. Expected one of {issuer_options}, got {token_issuer}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token issuer: {token_issuer}",
                )

            # Extract user information
            user_info = {
                "provider": "microsoft",
                "user_id": payload.get("oid") or payload.get("sub"),
                "email": payload.get("email") or payload.get("preferred_username"),
                "name": payload.get("name", ""),
                "given_name": payload.get("given_name", ""),
                "family_name": payload.get("family_name", ""),
                "tenant_id": payload.get("tid"),
                "app_id": payload.get("appid") or payload.get("azp"),
                "expires_at": datetime.fromtimestamp(payload.get("exp", 0)),
                "scopes": payload.get("scp", "").split() if payload.get("scp") else [],
            }

            logger.info(
                f"Successfully validated Microsoft token for user: {user_info['email']}"
            )
            return user_info

        except jwt.ExpiredSignatureError:
            logger.warning("Microsoft token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidAudienceError:
            logger.warning("Invalid token audience")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token audience",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidIssuerError:
            logger.warning("Invalid token issuer")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid Microsoft token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Error validating Microsoft token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error validating token",
            )

    def verify_user_in_tenant(self, token: str, user_email: str) -> bool:
        """
        Verify that a user exists in the Azure AD tenant

        Args:
            token: Access token with appropriate permissions
            user_email: Email of the user to verify

        Returns:
            True if user exists in tenant, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Microsoft Graph API endpoint
            graph_url = f"https://graph.microsoft.com/v1.0/users/{user_email}"
            headers = {"Authorization": f"Bearer {token}"}

            response = requests.get(graph_url, headers=headers, timeout=10)
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error verifying user in tenant: {e}")
            return False

    def get_user_profile(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Fetch user profile information from Microsoft Graph API

        Args:
            token: Access token with User.Read permission

        Returns:
            Dict containing user profile information or None if failed
        """
        if not self.enabled:
            return None

        try:
            # Microsoft Graph API endpoint
            graph_url = "https://graph.microsoft.com/v1.0/me"
            headers = {"Authorization": f"Bearer {token}"}

            response = requests.get(graph_url, headers=headers, timeout=10)

            if response.status_code == 200:
                profile = response.json()
                return {
                    "id": profile.get("id"),
                    "email": profile.get("mail") or profile.get("userPrincipalName"),
                    "display_name": profile.get("displayName"),
                    "given_name": profile.get("givenName"),
                    "surname": profile.get("surname"),
                    "job_title": profile.get("jobTitle"),
                    "office_location": profile.get("officeLocation"),
                }
            else:
                logger.warning(
                    f"Failed to fetch user profile: {response.status_code}"
                )
                return None

        except Exception as e:
            logger.error(f"Error fetching user profile: {e}")
            return None


# Global instance
azure_auth_service = AzureAuthService()
