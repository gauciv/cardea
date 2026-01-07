# Microsoft Sign-In Troubleshooting Guide

## ✅ Backend Configuration
Your backend is correctly configured:
- Azure Auth: **ENABLED**
- Authority: `https://cardea0.ciamlogin.com/`
- JWKS URI: Using External ID domain ✓
- Token Issuer: Using External ID domain ✓

## 🔍 Common Issues & Solutions

### Issue 1: "Redirect URI Mismatch" Error
**Symptom:** Error says redirect URI doesn't match what's configured

**Solution:** Verify in Azure Portal:
1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to: **Microsoft Entra ID** → **App Registrations** → Your App
3. Click **Authentication** in left menu
4. Under **Platform configurations** → **Single-page application**, verify:
   - `http://localhost:5173` is listed
   - `http://localhost:5173/` (with trailing slash) is listed
5. Click **Save** if you made changes

### Issue 2: "AADSTS50011" or "AADSTS700016" Errors
**Symptom:** Error codes starting with AADSTS

**Solution:** This usually means:
- Redirect URI not configured correctly
- Wrong application ID
- Wrong tenant ID

**Check your dashboard/.env:**
```bash
VITE_AZURE_CLIENT_ID=bcbb6cc2-8be4-4bc5-b92c-3263a20fdfaa
VITE_AZURE_TENANT_ID=2b874a6a-cb44-4e64-8e49-08a37b32f42b
VITE_AZURE_AUTHORITY=https://cardea0.ciamlogin.com/
VITE_REDIRECT_URI=http://localhost:5173
```

### Issue 3: Browser Console Shows MSAL Errors
**Symptom:** Errors in browser console about MSAL configuration

**Steps to debug:**
1. Open browser DevTools (F12)
2. Go to Console tab
3. Look for errors starting with "MSAL" or "ClientAuthError"
4. Common fixes:
   - Clear browser cache and localStorage
   - Restart dev server: `npm run dev`
   - Verify environment variables are loaded

### Issue 4: Token Validation Fails on Backend
**Symptom:** Login popup succeeds but then fails

**Check backend logs for:**
```bash
cd oracle
tail -f logs/oracle.log
# Or watch console output
```

**Common causes:**
- Token issuer mismatch (FIXED in latest update)
- JWKS endpoint unreachable
- Token expired

## 🧪 Testing Steps

### Step 1: Verify Environment Variables
```bash
# In dashboard directory
cd dashboard
npm run dev
# Check browser console for:
# - VITE_AZURE_CLIENT_ID should be visible
# - VITE_AZURE_AUTHORITY should be correct
```

### Step 2: Test Microsoft Login Flow
1. Navigate to `http://localhost:5173`
2. Click "Sign in with Microsoft"
3. You should see Microsoft login page
4. Enter credentials
5. After authentication, you should be redirected back

### Step 3: Check Network Tab
1. Open DevTools (F12) → Network tab
2. Click "Sign in with Microsoft"
3. Look for:
   - Request to Azure domain (should succeed)
   - Request to `/api/auth/azure/login` (check response)

## 🔧 Quick Fixes

### Clear All Caches
```bash
# Browser
- Press Ctrl+Shift+Delete
- Clear cache and cookies for localhost

# Frontend
cd dashboard
rm -rf node_modules/.vite
rm -rf dist
npm run dev

# Backend
cd oracle
rm -rf __pycache__
rm -rf src/__pycache__
```

### Restart Everything
```bash
# Terminal 1: Backend
cd oracle
source venv/bin/activate
python src/main.py

# Terminal 2: Frontend
cd dashboard
npm run dev
```

### Verify Azure Portal Settings

**Required Settings in Azure Portal:**

1. **App Registration → Authentication**
   - Platform: Single-page application
   - Redirect URIs: 
     - `http://localhost:5173`
     - `http://localhost:5173/` (with slash)
   - Logout URL: `http://localhost:5173`
   - Implicit grant: ID tokens ✓

2. **App Registration → API permissions**
   - Microsoft Graph → User.Read (optional for External ID)
   - openid, profile, email (should be enabled)

3. **App Registration → Expose an API**
   - Application ID URI: `api://bcbb6cc2-8be4-4bc5-b92c-3263a20fdfaa`
   - Scopes: Add scope `access_as_user`

## 📋 Environment File Checklist

### dashboard/.env
```bash
# Must have VITE_ prefix!
VITE_AZURE_CLIENT_ID=bcbb6cc2-8be4-4bc5-b92c-3263a20fdfaa
VITE_AZURE_TENANT_ID=2b874a6a-cb44-4e64-8e49-08a37b32f42b
VITE_AZURE_AUTHORITY=https://cardea0.ciamlogin.com/
VITE_REDIRECT_URI=http://localhost:5173
VITE_ENABLE_AZURE_AUTH=true
```

### oracle/.env
```bash
# No VITE_ prefix for backend
AZURE_CLIENT_ID=bcbb6cc2-8be4-4bc5-b92c-3263a20fdfaa
AZURE_TENANT_ID=2b874a6a-cb44-4e64-8e49-08a37b32f42b
AZURE_AUTHORITY=https://cardea0.ciamlogin.com/
AZURE_JWKS_URI=https://cardea0.ciamlogin.com/2b874a6a-cb44-4e64-8e49-08a37b32f42b/discovery/v2.0/keys
AZURE_TOKEN_ISSUER=https://cardea0.ciamlogin.com/2b874a6a-cb44-4e64-8e49-08a37b32f42b/v2.0
ENABLE_AZURE_AUTH=true
```

## 🆘 Still Not Working?

**Get detailed error information:**

1. **Enable verbose logging:**
   - In `dashboard/.env`: Set `VITE_DEBUG=true`
   - Restart frontend

2. **Check specific error:**
   - Browser Console (F12) → Copy full error message
   - Backend logs → Look for token validation errors

3. **Common error codes:**
   - `AADSTS50011`: Redirect URI mismatch
   - `AADSTS700016`: Application not found in tenant
   - `AADSTS90002`: Tenant not found
   - `AADSTS65001`: User consent required

**Share the specific error message for targeted help!**
