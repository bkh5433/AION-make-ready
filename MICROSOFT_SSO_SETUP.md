# Microsoft SSO Setup Guide for AION Vista

## Prerequisites

- Azure account (choose one option):
    1. **For Testing/Development**:
        - Free Azure account (sign up at portal.azure.com)
        - Uses default `*.onmicrosoft.com` domain
        - Perfect for testing SSO implementation

    2. **For Production**:
        - Organization's Azure AD tenant
        - Custom domain (e.g., aionmanagement.com)
        - Administrative access to Azure AD

- Your application running locally or in production

## Testing Account Setup

1. Go to [portal.azure.com](https://portal.azure.com)
2. Click "Create a free account"
3. Sign up with any Microsoft account
4. You'll get:
    - Free Azure credits
    - A tenant with `*.onmicrosoft.com` domain
    - Full Azure AD features needed for SSO testing

## Step 1: Register Application in Azure Portal

1. Go to [portal.azure.com](https://portal.azure.com)
2. Navigate to Azure Active Directory
3. Select "App registrations" from the left menu
4. Click "New registration"
5. Fill in the registration details:
   ```
   Name: AION Vista
   Supported account types: Single tenant
   Redirect URI (type: Web): http://localhost:5173/auth/microsoft/callback
   ```
6. Click "Register"

## Step 2: Collect Configuration Values

After registration, collect these values from the Azure Portal:

1. From the Overview page, note down:
   ```
   Application (client) ID -> MICROSOFT_CLIENT_ID
   Directory (tenant) ID -> MICROSOFT_TENANT_ID (already set in .env)
   ```

2. Generate Client Secret:
    - Go to "Certificates & secrets"
    - Click "New client secret"
    - Add a description (e.g., "AION Vista SSO")
    - Choose an expiration (e.g., 24 months)
    - Copy the generated value immediately -> MICROSOFT_CLIENT_SECRET

## Step 3: Configure API Permissions

1. In your app registration, go to "API permissions"
2. Click "Add a permission"
3. Select "Microsoft Graph"
4. Choose "Delegated permissions"
5. Add these permissions:
   ```
   - openid
   - User.Read
   - email
   - profile
   ```
6. Click "Grant admin consent" for your tenant

## Step 4: Configure Authentication Settings

1. Go to "Authentication" in your app registration
2. Under "Platform configurations":
    - Verify your redirect URI
    - Enable "Access tokens"
    - Enable "ID tokens"
3. Save changes

## Step 5: Update Environment Variables

Update your `.env` file with the collected values:

```env
MICROSOFT_SSO_ENABLED=TRUE
MICROSOFT_CLIENT_ID=<copied-client-id>
MICROSOFT_CLIENT_SECRET=<copied-client-secret>
MICROSOFT_TENANT_ID=531ad474-be34-4584-a4bf-c885279053f5
MICROSOFT_REDIRECT_URI=http://localhost:5173/auth/microsoft/callback
MICROSOFT_DOMAIN_HINT=aionmanagement.com
```

## Step 6: Production Deployment

When deploying to production:

1. Add production redirect URI in Azure:
    - Go back to Authentication settings
    - Add new redirect URI for your production domain
    - Format: `https://your-domain.com/auth/microsoft/callback`

2. Update production environment variables:
   ```env
   MICROSOFT_REDIRECT_URI=https://your-domain.com/auth/microsoft/callback
   ```

3. Update CORS settings if needed:
   ```env
   CORS_ORIGINS=https://your-domain.com
   ```

## Step 7: Testing

1. Start your application
2. Click "Sign in with Microsoft" button
3. You should be redirected to Microsoft login
4. After successful login, you'll be redirected back to your application
5. Check application logs for any issues

## Troubleshooting

### Common Issues:

1. **Redirect URI Mismatch**
    - Error: "The reply URL does not match the configured URLs"
    - Solution: Verify redirect URI in Azure matches your .env file

2. **Permission Issues**
    - Error: "Insufficient permissions"
    - Solution: Ensure admin consent is granted for all required permissions

3. **Token Validation Fails**
    - Error: "Failed to validate token"
    - Solution: Verify client ID and secret are correct

### Debug Steps:

1. Check application logs at `logs/api.log`
2. Monitor network requests in browser DevTools
3. Verify environment variables are loaded correctly
4. Ensure all Azure configurations match your application settings

## Security Notes

- Keep your client secret secure and never commit it to version control
- Always use HTTPS in production
- Regularly rotate client secrets
- Monitor failed login attempts
- Review Azure AD sign-in logs periodically

## Support

If you encounter issues:

1. Check Azure Portal for error messages
2. Review application logs
3. Verify network connectivity
4. Ensure all required permissions are granted 