"""
Microsoft Entra External ID - Native Authentication Service
Handles email OTP-based registration and authentication

Native Authentication provides a secure way to:
1. Register users with email + password
2. Send OTP codes to user emails (Microsoft handles email delivery)
3. Verify OTP codes and complete registration
4. Authenticate users with email/password after registration

Microsoft Entra External ID handles:
- Email delivery for OTP codes
- Secure code generation and validation
- User identity management
- Token issuance

No SMTP configuration needed - Microsoft handles all email infrastructure.
"""

import os
import logging
import secrets
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class ExternalIDAuthService:
    """
    Microsoft Entra External ID Native Authentication Service
    
    Implements the Native Authentication flow:
    1. Initiate signup with email -> Microsoft sends OTP
    2. Verify OTP code -> Validates user email ownership
    3. Complete registration -> Creates user with password
    4. Login -> Authenticate with email/password
    """
    
    def __init__(self):
        # Microsoft Entra External ID Configuration
        self.tenant_subdomain = os.getenv("AZURE_EXTERNAL_ID_TENANT_SUBDOMAIN", "")
        self.tenant_id = os.getenv("AZURE_EXTERNAL_ID_TENANT_ID", "")
        self.client_id = os.getenv("AZURE_EXTERNAL_ID_CLIENT_ID", "")
        self.client_secret = os.getenv("AZURE_EXTERNAL_ID_CLIENT_SECRET", "")
        
        # Construct authority URL for External ID tenant
        # Format: https://{tenant-subdomain}.ciamlogin.com
        if self.tenant_subdomain:
            self.authority = f"https://{self.tenant_subdomain}.ciamlogin.com"
        else:
            self.authority = os.getenv("AZURE_EXTERNAL_ID_AUTHORITY", "")
        
        # Native Auth API endpoints - Use v1.0 for Native Authentication
        # Reference: https://learn.microsoft.com/en-us/entra/external-id/customers/reference-native-authentication-api
        self.signup_start_endpoint = f"{self.authority}/{self.tenant_id}/signup/v1.0/start"
        self.signup_challenge_endpoint = f"{self.authority}/{self.tenant_id}/signup/v1.0/challenge"
        self.signup_continue_endpoint = f"{self.authority}/{self.tenant_id}/signup/v1.0/continue"
        self.token_endpoint = f"{self.authority}/{self.tenant_id}/oauth2/v2.0/token"
        
        # In-memory session storage (use Redis in production)
        self._pending_registrations: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"External ID Auth Service initialized - Authority: {self.authority}")
    
    def is_enabled(self) -> bool:
        """Check if External ID authentication is properly configured"""
        return all([
            self.tenant_subdomain or self.authority,
            self.tenant_id,
            self.client_id,
        ])
    
    async def initiate_email_otp_signup(
        self,
        email: str,
        given_name: Optional[str] = None,
        family_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Step 1: Initiate signup flow - triggers OTP email from Microsoft
        
        This calls the /signup/start endpoint which:
        1. Validates the email format
        2. Checks if user already exists
        3. Initiates the OTP challenge flow
        
        Args:
            email: User's email address
            given_name: User's first name (optional for initial call)
            family_name: User's last name (optional for initial call)
        
        Returns:
            Session ID to continue the flow
        """
        if not self.is_enabled():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Native authentication is not configured"
            )
        
        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Start signup
                signup_start_data = {
                    "client_id": self.client_id,
                    "challenge_type": "oob",  # Out-of-band (email OTP)
                    "username": email,
                }
                
                response = await client.post(
                    self.signup_start_endpoint,
                    data=signup_start_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                result = response.json()
                
                # Log the full request/response for debugging
                logger.info(f"Signup start request URL: {self.signup_start_endpoint}")
                logger.info(f"Signup start response status: {response.status_code}")
                logger.info(f"Signup start response: {result}")
                
                if response.status_code == 200:
                    # Signup started - continuation token received
                    continuation_token = result.get("continuation_token")
                    
                    # Step 2: Request OTP challenge
                    challenge_data = {
                        "client_id": self.client_id,
                        "challenge_type": "oob",
                        "continuation_token": continuation_token,
                    }
                    
                    challenge_response = await client.post(
                        self.signup_challenge_endpoint,
                        data=challenge_data,
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )
                    
                    challenge_result = challenge_response.json()
                    
                    if challenge_response.status_code == 200:
                        # OTP sent successfully
                        session_id = secrets.token_urlsafe(32)
                        
                        # Store session data for verification
                        self._pending_registrations[session_id] = {
                            "email": email,
                            "given_name": given_name,
                            "family_name": family_name,
                            "continuation_token": challenge_result.get("continuation_token"),
                            "challenge_type": challenge_result.get("challenge_type"),
                            "challenge_channel": challenge_result.get("challenge_channel"),
                            "code_length": challenge_result.get("code_length", 6),
                            "created_at": datetime.utcnow(),
                            "expires_at": datetime.utcnow() + timedelta(minutes=10),
                        }
                        
                        logger.info(f"OTP sent to {email} via Microsoft Entra External ID")
                        
                        return {
                            "status": "otp_sent",
                            "message": "Verification code sent to your email",
                            "session_id": session_id,
                            "code_length": challenge_result.get("code_length", 6),
                            "expires_in_seconds": 600,  # 10 minutes
                        }
                    else:
                        logger.error(f"Challenge request failed: {challenge_result}")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=challenge_result.get("error_description", "Failed to send verification code")
                        )
                
                elif "user_already_exists" in str(result.get("error", "")):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="An account with this email already exists. Please log in instead."
                    )
                else:
                    logger.error(f"Signup start failed: {result}")
                    error_detail = result.get("error_description", result.get("error", "Failed to initiate registration"))
                    raise HTTPException(
                        status_code=response.status_code if response.status_code >= 400 else status.HTTP_400_BAD_REQUEST,
                        detail=f"Registration failed: {error_detail}"
                    )
                    
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during signup initiation: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Authentication service error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error during signup: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Registration failed: {str(e)}"
            )
    
    async def verify_email_otp(
        self,
        session_id: str,
        otp_code: str
    ) -> Dict[str, Any]:
        """
        Step 2: Verify the OTP code entered by user
        
        Args:
            session_id: Session ID from initiate step
            otp_code: 6-digit OTP code from email
        
        Returns:
            Verification status and updated continuation token
        """
        # Get pending registration
        session = self._pending_registrations.get(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired session. Please start registration again."
            )
        
        if datetime.utcnow() > session["expires_at"]:
            del self._pending_registrations[session_id]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session expired. Please start registration again."
            )
        
        try:
            async with httpx.AsyncClient() as client:
                # Continue signup with OTP
                continue_data = {
                    "client_id": self.client_id,
                    "continuation_token": session["continuation_token"],
                    "grant_type": "oob",
                    "oob": otp_code,
                }
                
                response = await client.post(
                    self.signup_continue_endpoint,
                    data=continue_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                result = response.json()
                
                if response.status_code == 200:
                    # OTP verified - update session with new continuation token
                    session["continuation_token"] = result.get("continuation_token")
                    session["otp_verified"] = True
                    session["otp_verified_at"] = datetime.utcnow()
                    
                    logger.info(f"OTP verified for {session['email']}")
                    
                    return {
                        "status": "otp_verified",
                        "message": "Email verified successfully. Please complete your registration.",
                        "session_id": session_id,
                        "email": session["email"],
                    }
                
                elif "invalid_grant" in str(result.get("error", "")):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid verification code. Please try again."
                    )
                else:
                    logger.error(f"OTP verification failed: {result}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=result.get("error_description", "Verification failed")
                    )
                    
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during OTP verification: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service temporarily unavailable"
            )
    
    async def complete_registration(
        self,
        session_id: str,
        password: str,
        given_name: str,
        family_name: str
    ) -> Dict[str, Any]:
        """
        Step 3: Complete registration with password and user details
        
        Args:
            session_id: Session ID from previous steps
            password: User's chosen password
            given_name: User's first name
            family_name: User's last name
        
        Returns:
            Access token and user information
        """
        # Get pending registration
        session = self._pending_registrations.get(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired session. Please start registration again."
            )
        
        if not session.get("otp_verified"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not verified. Please verify your email first."
            )
        
        try:
            async with httpx.AsyncClient() as client:
                # Continue signup with password and attributes
                continue_data = {
                    "client_id": self.client_id,
                    "continuation_token": session["continuation_token"],
                    "grant_type": "password",
                    "password": password,
                    "attributes": {
                        "givenName": given_name,
                        "surname": family_name,
                        "displayName": f"{given_name} {family_name}",
                    }
                }
                
                response = await client.post(
                    self.signup_continue_endpoint,
                    json=continue_data,  # Use JSON for attributes
                    headers={"Content-Type": "application/json"}
                )
                
                result = response.json()
                
                if response.status_code == 200:
                    # Registration complete - tokens received
                    # Clean up pending registration
                    del self._pending_registrations[session_id]
                    
                    logger.info(f"Registration completed for {session['email']}")
                    
                    return {
                        "status": "registration_complete",
                        "message": "Account created successfully!",
                        "access_token": result.get("access_token"),
                        "token_type": result.get("token_type", "Bearer"),
                        "expires_in": result.get("expires_in", 3600),
                        "user": {
                            "email": session["email"],
                            "given_name": given_name,
                            "family_name": family_name,
                            "full_name": f"{given_name} {family_name}",
                        }
                    }
                
                elif "password_too_weak" in str(result.get("error", "")):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Password does not meet security requirements. Please use a stronger password."
                    )
                else:
                    logger.error(f"Registration completion failed: {result}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=result.get("error_description", "Registration failed")
                    )
                    
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during registration completion: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service temporarily unavailable"
            )
    
    async def sign_in_with_password(
        self,
        email: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Authenticate user with email and password
        
        Args:
            email: User's email
            password: User's password
        
        Returns:
            Access tokens and user info
        """
        if not self.is_enabled():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Native authentication is not configured"
            )
        
        try:
            async with httpx.AsyncClient() as client:
                # Sign in with ROPC flow (Resource Owner Password Credentials)
                token_data = {
                    "client_id": self.client_id,
                    "scope": "openid profile email offline_access",
                    "grant_type": "password",
                    "username": email,
                    "password": password,
                }
                
                # Add client secret if configured
                if self.client_secret:
                    token_data["client_secret"] = self.client_secret
                
                response = await client.post(
                    self.token_endpoint,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                result = response.json()
                
                if response.status_code == 200:
                    # Parse ID token for user info
                    id_token = result.get("id_token", "")
                    user_info = self._parse_id_token(id_token)
                    
                    logger.info(f"User signed in: {email}")
                    
                    return {
                        "status": "authenticated",
                        "access_token": result.get("access_token"),
                        "id_token": result.get("id_token"),
                        "refresh_token": result.get("refresh_token"),
                        "token_type": result.get("token_type", "Bearer"),
                        "expires_in": result.get("expires_in", 3600),
                        "user": user_info,
                    }
                
                elif "invalid_grant" in str(result.get("error", "")):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid email or password"
                    )
                else:
                    logger.error(f"Sign in failed: {result}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=result.get("error_description", "Authentication failed")
                    )
                    
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during sign in: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service temporarily unavailable"
            )
    
    def _parse_id_token(self, id_token: str) -> Dict[str, Any]:
        """Parse ID token to extract user information"""
        try:
            import base64
            import json
            
            # Split JWT and decode payload (second part)
            parts = id_token.split('.')
            if len(parts) != 3:
                return {}
            
            # Add padding if needed
            payload = parts[1]
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            
            decoded = base64.urlsafe_b64decode(payload)
            claims = json.loads(decoded)
            
            return {
                "email": claims.get("email", claims.get("preferred_username", "")),
                "given_name": claims.get("given_name", ""),
                "family_name": claims.get("family_name", ""),
                "full_name": claims.get("name", ""),
                "sub": claims.get("sub", ""),
            }
        except Exception as e:
            logger.error(f"Failed to parse ID token: {e}")
            return {}
    
    async def resend_otp(self, session_id: str) -> Dict[str, Any]:
        """
        Resend OTP code to user's email
        
        Args:
            session_id: Existing session ID
        
        Returns:
            Status message
        """
        session = self._pending_registrations.get(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired session. Please start registration again."
            )
        
        # Re-initiate OTP for the same email
        email = session["email"]
        given_name = session.get("given_name")
        family_name = session.get("family_name")
        
        # Delete old session
        del self._pending_registrations[session_id]
        
        # Create new session
        return await self.initiate_email_otp_signup(email, given_name, family_name)


# Global instance
external_id_auth_service = ExternalIDAuthService()
