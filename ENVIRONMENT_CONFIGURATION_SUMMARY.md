# Cardea Platform - Environment Configuration Summary

**Date Configured:** January 7, 2026  
**Status:** ✅ Ready for Microsoft and Google Authentication

---

## 📋 Configuration Overview

Your Cardea platform has been configured with best practices for secure authentication using:
- ✅ **Microsoft Entra External ID** (Azure AD)
- ✅ **Google OAuth 2.0**
- ✅ **Traditional username/password** authentication
- ✅ **Email OTP** authentication (via Microsoft External ID)

---

## 🔧 What Was Configured

### 1. Environment Files Updated

#### **Root `.env`** (`/cardea/.env`)
- Centralized configuration for all Microsoft and Google credentials
- Database and Redis connection strings
- Security tokens and JWT secrets
- Azure AI Services (optional)
- Application settings and feature flags

#### **Backend `.env`** (`/oracle/.env`)
- Microsoft Entra ID OAuth configuration
- Google OAuth 2.0 configuration
- External ID native authentication settings
- Database and Redis connections
- API server settings
- Feature flags for authentication methods

#### **Frontend `.env`** (`/dashboard/.env`)
- All variables prefixed with `VITE_` (required for Vite)
- Microsoft MSAL browser configuration
- Google OAuth client ID
- Backend API URLs
- Authentication feature flags

### 2. Dependencies Installed

#### **Frontend (Dashboard)**
```bash
✅ @react-oauth/google@latest - Google Sign-In for React
✅ @azure/msal-browser@4.27.0 - Microsoft Authentication Library
✅ @azure/msal-react@3.0.23 - MSAL React wrapper
```

#### **Backend (Oracle)**
```bash
✅ google-auth==2.27.0 - Google token validation library
✅ msal==1.26.0 - Microsoft Authentication Library for Python
✅ python-jose[cryptography] - JWT token handling
```

### 3. Security Improvements

✅ **Proper .gitignore** - All `.env` files are excluded from version control  
✅ **Template files** - `.env.example` files created for documentation  
✅ **Credential separation** - Client secrets kept on backend only  
✅ **CORS configuration** - Proper origin restrictions  
✅ **JWT secrets** - Strong token signing keys configured

---

## 🚀 How to Use Your Authentication

### Microsoft Login Flow

1. **User clicks "Sign in with Microsoft"**
2. Frontend redirects to Azure login page
3. User authenticates with Microsoft credentials
4. Azure redirects back with authorization code
5. Frontend exchanges code for access token
6. Frontend sends token to backend API
7. Backend validates token with Microsoft JWKS endpoint
8. Backend creates/updates user in database
9. Backend returns session token to frontend

### Google Login Flow

1. **User clicks "Sign in with Google"**
2. Google OAuth popup appears
3. User authenticates with Google credentials
4. Google returns ID token to frontend
5. Frontend sends token to backend API
6. Backend validates token with Google's tokeninfo endpoint
7. Backend creates/updates user in database
8. Backend returns session token to frontend

---

## 📁 File Structure

```
cardea/
├── .env                          # Root configuration (your credentials)
├── .env.example                  # Template (safe to commit)
├── .gitignore                    # Excludes .env files ✅
│
├── dashboard/                    # Frontend (React + Vite)
│   ├── .env                      # Frontend config (VITE_ prefix)
│   ├── .env.example              # Template
│   ├── src/
│   │   ├── authConfig.ts         # Microsoft MSAL configuration
│   │   └── components/
│   │       └── LoginPage.tsx     # Login UI with OAuth buttons
│   └── package.json              # Includes @react-oauth/google ✅
│
└── oracle/                       # Backend (Python FastAPI)
    ├── .env                      # Backend config
    ├── .env.example              # Template
    ├── requirements.txt          # Includes google-auth ✅
    └── src/
        ├── azure_auth.py         # Microsoft token validation
        ├── google_auth.py        # Google token validation
        ├── external_id_auth.py   # Email OTP authentication
        ├── auth.py               # Main auth orchestration
        └── main.py               # FastAPI application
```

---

## ✅ Configuration Checklist

### Microsoft Entra External ID Setup
- [x] Tenant ID configured
- [x] Client ID configured
- [x] Client Secret configured (stored securely)
- [x] Authority URL set to External ID tenant
- [x] Redirect URIs match in Azure Portal and .env
- [x] API scope exposed and configured
- [x] JWKS URI and Token Issuer configured

### Google OAuth 2.0 Setup
- [x] Client ID configured
- [x] Client Secret configured (backend only)
- [x] Authorized redirect URIs configured in Google Console
- [x] Token validation endpoint configured

### Security Best Practices
- [x] `.env` files excluded from git
- [x] Strong JWT secrets generated
- [x] Client secrets not exposed in frontend
- [x] CORS origins restricted to known domains
- [x] Token expiration times configured
- [x] Rate limiting enabled

### Application Configuration
- [x] Database connection configured
- [x] Redis connection configured
- [x] API URLs configured
- [x] Feature flags set correctly
- [x] Debug logging enabled for development

---

## 🔐 Security Notes

### ⚠️ CRITICAL - Do Not Expose
The following values are **highly sensitive** and must **NEVER** be:
- Committed to git
- Shared publicly
- Embedded in frontend code
- Logged to console

**Backend Secrets (oracle/.env):**
- `AZURE_CLIENT_SECRET`
- `GOOGLE_CLIENT_SECRET`
- `SECRET_KEY` / `JWT_SECRET`
- `DB_PASSWORD`
- `AZURE_OPENAI_API_KEY`

### ✅ Safe to Expose (Frontend)
These values are embedded in the frontend bundle:
- `VITE_AZURE_CLIENT_ID` - Microsoft Client ID (not secret)
- `VITE_GOOGLE_CLIENT_ID` - Google Client ID (not secret)
- `VITE_AZURE_TENANT_ID` - Tenant ID (public metadata)
- `VITE_API_URL` - Backend API URL

### 🔒 Security Best Practices

1. **Rotate Secrets Regularly**
   - Azure Client Secret: Every 90 days
   - Google Client Secret: Every 90 days
   - JWT Secret: When compromised

2. **Production Checklist**
   - [ ] Change all default passwords
   - [ ] Use environment-specific secrets
   - [ ] Enable HTTPS/TLS for all endpoints
   - [ ] Configure production CORS origins
   - [ ] Disable DEBUG mode
   - [ ] Set LOG_LEVEL to WARNING or ERROR
   - [ ] Use managed secrets (Azure Key Vault, AWS Secrets Manager)
   - [ ] Enable API rate limiting
   - [ ] Configure monitoring and alerting

3. **Development vs Production**
   ```bash
   # Development
   DEBUG=true
   LOG_LEVEL=INFO
   VITE_REDIRECT_URI=http://localhost:5173
   
   # Production
   DEBUG=false
   LOG_LEVEL=WARNING
   VITE_REDIRECT_URI=https://your-domain.com
   ```

---

## 🧪 Testing Your Configuration

### 1. Verify Environment Files

```bash
# Check that .env files exist and are not committed
cd /path/to/cardea
ls -la .env oracle/.env dashboard/.env
git status | grep ".env"  # Should show nothing

# Verify variables are loaded
cd dashboard
npm run dev  # Check console for "VITE_AZURE_CLIENT_ID"

cd ../oracle
source venv/bin/activate
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('AZURE_CLIENT_ID'))"
```

### 2. Test Microsoft Login

1. Start backend: `cd oracle && python src/main.py`
2. Start frontend: `cd dashboard && npm run dev`
3. Navigate to `http://localhost:5173`
4. Click "Sign in with Microsoft"
5. Should redirect to Azure login
6. After login, should return to your app with token

### 3. Test Google Login

1. Ensure backend and frontend are running
2. Click "Sign in with Google"
3. Google OAuth popup should appear
4. After login, popup closes and you're authenticated

### 4. Verify Token Validation

```bash
# Check backend logs for successful token validation
cd oracle
tail -f logs/oracle.log | grep "validated.*token"
```

---

## 🐛 Troubleshooting

### Common Issues

#### "AADSTS50011: Redirect URI mismatch"
**Solution:** Ensure `VITE_REDIRECT_URI` in `dashboard/.env` matches the redirect URI configured in Azure Portal.

#### "Invalid Google OAuth client"
**Solution:** Verify `VITE_GOOGLE_CLIENT_ID` matches your Google Cloud Console OAuth client ID.

#### "CORS error when calling backend"
**Solution:** Add your frontend URL to `CORS_ORIGINS` in `oracle/.env`.

#### "Environment variables not loading (Vite)"
**Solution:** 
1. Ensure all variables start with `VITE_`
2. Restart dev server after changing .env
3. Check `import.meta.env.VITE_VARIABLE_NAME`

#### "Token validation failed"
**Solution:**
1. Check `AZURE_JWKS_URI` and `AZURE_TOKEN_ISSUER` are correct
2. Verify token isn't expired
3. Ensure backend has network access to Microsoft/Google endpoints

---

## 📚 Related Documentation

- [MICROSOFT_ENTRA_SETUP.md](docs/MICROSOFT_ENTRA_SETUP.md) - Azure Portal setup guide
- [OAUTH_SETUP_GUIDE.md](docs/OAUTH_SETUP_GUIDE.md) - Detailed OAuth configuration
- [AUTHENTICATION_FLOW_DIAGRAMS.md](docs/AUTHENTICATION_FLOW_DIAGRAMS.md) - Flow diagrams
- [ERROR_SOLUTIONS.md](docs/ERROR_SOLUTIONS.md) - Common errors and solutions

---

## 🎯 Next Steps

1. **Test Authentication**
   - Start both backend and frontend
   - Test Microsoft login
   - Test Google login
   - Verify tokens are validated correctly

2. **Review Azure Portal Configuration**
   - Confirm redirect URIs match
   - Verify API scope is exposed
   - Check certificate/secret expiration dates

3. **Review Google Cloud Console**
   - Confirm authorized redirect URIs
   - Verify OAuth consent screen is configured
   - Check quotas and usage limits

4. **Production Deployment**
   - Create production .env files with production values
   - Update redirect URIs to production domain
   - Configure managed secrets storage
   - Enable monitoring and logging

---

## 🆘 Support

If you encounter issues:

1. **Check Logs**
   - Backend: `oracle/logs/` or console output
   - Frontend: Browser Developer Console (F12)

2. **Verify Configuration**
   - Run configuration tests above
   - Compare with .env.example templates

3. **Review Documentation**
   - Check docs/ folder for detailed guides
   - Review Azure/Google OAuth documentation

4. **Common Commands**
   ```bash
   # Reinstall dependencies
   cd dashboard && npm install
   cd oracle && pip install -r requirements.txt
   
   # Clear cache and restart
   rm -rf dashboard/node_modules/.vite
   cd oracle && rm -rf __pycache__
   
   # Check environment variables
   cd dashboard && npm run dev  # Check console
   cd oracle && python -c "from config import settings; print(settings)"
   ```

---

**Configuration completed successfully! ✅**  
Your Cardea platform is ready for Microsoft and Google authentication.
