from msal import ConfidentialClientApplication
from flask import url_for, current_app
from datetime import datetime
from typing import Optional, Dict
import asyncio
import aiohttp
import jwt
from config import Config


class MicrosoftAuth:
    def __init__(self):
        self.client_id = Config.MICROSOFT_CONFIG['client_id']
        self.client_secret = Config.MICROSOFT_CONFIG['client_secret']
        self.tenant_id = Config.MICROSOFT_CONFIG['tenant_id']
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.redirect_uri = Config.MICROSOFT_CONFIG['redirect_uri']

        self.msal_app = ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority
        )

        # Use only the Microsoft Graph API scope
        self.scopes = Config.MICROSOFT_CONFIG['scopes']

    def get_auth_url(self) -> str:
        """Generate Microsoft login URL"""
        return self.msal_app.get_authorization_request_url(
            scopes=self.scopes,
            redirect_uri=self.redirect_uri,
            # prompt="select_account",  # Force account selection
            domain_hint=Config.MICROSOFT_CONFIG['domain_hint']
        )

    async def get_token_from_code(self, code: str) -> Optional[Dict]:
        """Exchange authorization code for access token"""
        try:
            current_app.logger.debug(f"Getting token from code (first 10 chars): {code[:10]}...")
            current_app.logger.debug(f"Using redirect URI: {self.redirect_uri}")
            current_app.logger.debug(f"Using scopes: {self.scopes}")

            # MSAL's acquire_token_by_authorization_code is synchronous
            result = self.msal_app.acquire_token_by_authorization_code(
                code=code,
                scopes=self.scopes,
                redirect_uri=self.redirect_uri
            )

            current_app.logger.debug(f"Token result keys: {result.keys() if result else None}")

            if "access_token" in result:
                # Log success but not the actual token
                current_app.logger.debug("Successfully acquired access token")
                return result
            elif "error" in result:
                error_desc = result.get('error_description', result.get('error'))
                current_app.logger.error(f"Error getting token: {error_desc}")
                return None
            else:
                current_app.logger.error("No token or error in response")
                return None
        except Exception as e:
            current_app.logger.error(f"Error getting token: {str(e)}")
            current_app.logger.exception(e)  # This will log the full stack trace
            return None

    async def validate_token(self, token: str) -> Optional[Dict]:
        """Validate Microsoft access token and get user info using Microsoft Graph API"""
        try:
            # Log token info (first few characters only for security)
            token_preview = token[:10] + "..." if token else "None"
            current_app.logger.debug(f"Validating token: {token_preview}")

            # Use Microsoft Graph API to get user information
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }

                current_app.logger.debug("Making request to Microsoft Graph API")
                async with session.get('https://graph.microsoft.com/v1.0/me', headers=headers) as response:
                    response_text = await response.text()
                    current_app.logger.debug(f"Graph API response status: {response.status}")
                    current_app.logger.debug(f"Graph API response: {response_text}")

                    if response.status == 200:
                        try:
                            user_data = await response.json()
                            current_app.logger.debug(f"Parsed user data: {user_data}")

                            # Extract and validate required fields
                            email = user_data.get("userPrincipalName")
                            name = user_data.get("displayName")
                            microsoft_id = user_data.get("id")

                            if not all([email, name, microsoft_id]):
                                current_app.logger.error("Missing required user information from Graph API")
                                return None

                            return {
                                'email': email,
                                'name': name,
                                'microsoft_id': microsoft_id
                            }

                        except Exception as e:
                            current_app.logger.error(f"Error parsing user data: {str(e)}")
                            return None
                    else:
                        current_app.logger.error(f"Error validating token: {response.status}")
                        return None

        except Exception as e:
            current_app.logger.error(f"Error validating token: {str(e)}")
            return None

    async def handle_callback(self, code: str, auth_middleware) -> Optional[Dict]:
        """Handle the complete Microsoft authentication callback process"""
        try:
            # Get token from code
            token_result = await self.get_token_from_code(code)
            if not token_result or 'access_token' not in token_result:
                current_app.logger.error("Failed to get access token")
                return None

            # Get user info from token
            user_info = await self.validate_token(token_result['access_token'])
            if not user_info:
                current_app.logger.error("Failed to validate token")
                return None

            # Check if user exists and create/update as needed
            users = auth_middleware.users_ref.where('email', '==', user_info['email']).limit(1).stream()
            user_doc = next((doc for doc in users), None)

            if user_doc:
                # Existing user
                user = user_doc.to_dict()
                user_id = user_doc.id
            else:
                # Create new user
                user_id = user_info['microsoft_id']
                user = {
                    'email': user_info['email'],
                    'username': user_info['email'],
                    'name': user_info['name'],
                    'role': 'user',
                    'isActive': True,
                    'createdAt': datetime.utcnow().isoformat(),
                    'lastLogin': datetime.utcnow().isoformat(),
                    'auth_provider': 'microsoft',
                    'microsoft_id': user_info['microsoft_id']
                }
                # Add the user to Firestore
                auth_middleware.users_ref.document(user_id).set(user)

            # Update last login
            auth_middleware.users_ref.document(user_id).update({
                'lastLogin': datetime.utcnow().isoformat()
            })

            # Generate JWT token
            token = auth_middleware.generate_token({
                'user_id': user_id,
                'username': user['username'],
                'email': user['email'],
                'name': user['name'],
                'role': user['role']
            })

            return {
                'token': token,
                'user': user
            }

        except Exception as e:
            current_app.logger.error(f"Error in handle_callback: {str(e)}")
            return None

    def get_logout_url(self) -> str:
        """Generate Microsoft logout URL"""
        return f"{self.authority}/oauth2/v2.0/logout"
