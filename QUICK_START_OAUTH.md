# 🚀 Quick Start - Running Cardea with OAuth

## Prerequisites Checklist

- [x] All `.env` files configured with your credentials
- [x] Dependencies installed (`npm install` + `pip install -r requirements.txt`)
- [x] PostgreSQL database running (localhost:5432)
- [x] Redis running (localhost:6379)
- [x] Azure App Registration configured with redirect URIs
- [x] Google OAuth Client configured with redirect URIs

---

## 🎯 Start Services (Development)

### 1. Start Backend (Terminal 1)
```bash
cd oracle
source venv/bin/activate
python src/main.py
```
✅ Backend running on: `http://localhost:8000`

### 2. Start Frontend (Terminal 2)
```bash
cd dashboard
npm run dev
```
✅ Frontend running on: `http://localhost:5173`

### 3. Test Authentication
1. Open browser: `http://localhost:5173`
2. Click **"Sign in with Microsoft"** or **"Sign in with Google"**
3. Complete OAuth flow
4. You should be logged in! ✅

---

## 📍 Important URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:5173 | User interface |
| Backend API | http://localhost:8000 | REST API |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Health Check | http://localhost:8000/health | Status |

---

## 🔑 Environment Files Summary

### Root `.env`
- Centralized credentials for all services
- Both Microsoft and Google credentials

### `oracle/.env` (Backend)
- Database & Redis connections
- Microsoft & Google OAuth settings
- JWT secrets and security config
- Feature flags

### `dashboard/.env` (Frontend)
- All variables start with `VITE_`
- Microsoft Client ID & Tenant ID
- Google Client ID (no secret!)
- Backend API URL

---

## ✅ Verify Configuration

```bash
# Check environment variables are loaded
cd dashboard && npm run dev
# Look for: VITE_AZURE_CLIENT_ID in console

cd oracle && source venv/bin/activate
python -c "from config import settings; print(f'Azure: {settings.AZURE_CLIENT_ID}, Google: {os.getenv(\"GOOGLE_CLIENT_ID\")}')"
```

---

## 🔍 Quick Debugging

### Backend Logs
```bash
cd oracle
tail -f logs/oracle.log
# Or check console output
```

### Frontend Console
1. Open browser DevTools (F12)
2. Check Console tab for errors
3. Check Network tab for API calls

### Common Issues

**"Redirect URI mismatch"**
→ Update redirect URI in Azure Portal to match `http://localhost:5173`

**"CORS error"**
→ Verify `CORS_ORIGINS=http://localhost:5173` in `oracle/.env`

**"Environment variable undefined"**
→ Restart dev server after changing `.env`
→ Ensure Vite variables start with `VITE_`

**"Token validation failed"**
→ Check `AZURE_TENANT_ID` and `AZURE_CLIENT_ID` match Azure Portal
→ Verify secrets haven't expired

---

## 🎨 Login Flow

```
User → Click "Sign in" 
     → Redirect to Microsoft/Google 
     → User authenticates 
     → Redirect back with token 
     → Frontend sends token to backend 
     → Backend validates & creates session 
     → User logged in! ✅
```

---

## 📚 Full Documentation

For detailed setup and configuration:
- **[ENVIRONMENT_CONFIGURATION_SUMMARY.md](ENVIRONMENT_CONFIGURATION_SUMMARY.md)** - Complete config guide
- **[docs/MICROSOFT_ENTRA_SETUP.md](docs/MICROSOFT_ENTRA_SETUP.md)** - Azure Portal setup
- **[docs/OAUTH_SETUP_GUIDE.md](docs/OAUTH_SETUP_GUIDE.md)** - OAuth detailed guide

---

## 🆘 Need Help?

1. Check logs (backend console + browser DevTools)
2. Review configuration files match `.env.example`
3. Verify credentials in Azure Portal & Google Console
4. See [ERROR_SOLUTIONS.md](docs/ERROR_SOLUTIONS.md) for common fixes

---

**Ready to go! Start the services and test your authentication. 🎉**
