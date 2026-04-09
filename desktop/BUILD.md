# Desktop App Build Guide

This guide covers building the Document Assistant desktop application.

## Architecture

The desktop app is an **Electron client** that connects to a separately-running backend:

```
┌─────────────────┐      HTTP      ┌─────────────────┐
│  Electron App   │ ◄────────────► │  Backend (Port  │
│  (Frontend UI)  │   localhost    │   8000)         │
└─────────────────┘                └─────────────────┘
```

**Important:** The desktop app does NOT bundle or start the backend. You must run the backend separately.

## Prerequisites

- Node.js 18+
- npm
- Docker (for Windows builds on Linux/WSL)
- Backend running on `localhost:8000`

## Development Workflow

1. **Start the backend** (in a separate terminal):
   ```bash
   make start
   # or
   docker compose up -d postgres
   cd backend && uv run uvicorn api.main:app --port 8000
   ```

2. **Start the desktop app**:
   ```bash
   make desktop-dev
   ```

## Building for Production

### Linux

```bash
make desktop-dist
```

Creates:
- `desktop/dist/*.AppImage` - Portable Linux app
- `desktop/dist/*.deb` - Debian package

### Windows

**Recommended: Docker build (avoids Wine issues on WSL)**

```bash
make desktop-exe-docker
```

**Alternative: Native Wine (if properly configured)**

```bash
make desktop-exe
```

Creates in `desktop/dist/`:
- `Document Assistant Setup 1.0.0.exe` - Installer with setup wizard
- `Document Assistant 1.0.0.exe` - Portable executable

## Installation & Usage

### For End Users

1. **Install the app** using the setup wizard, or run the portable version directly
2. **Start the backend** on your server or local machine
3. **Launch the desktop app** - it will automatically connect to `http://localhost:8000/api`

### Windows Security Warnings

Since the app is unsigned, Windows SmartScreen may show warnings:

1. Click **"More info"**
2. Click **"Run anyway"**

Or right-click the `.exe` → **Properties** → Check **"Unblock"** → **OK**

## Configuration

The desktop app expects the backend at:
- **URL:** `http://127.0.0.1:8000/api`
- **Health check:** `http://127.0.0.1:8000/api/health`

To use a different backend URL, modify `frontend/src/services/real-client.ts`:

```typescript
const baseURL = isElectron ? 'http://your-server:8000/api' : '/api'
```

## Troubleshooting

### "Cannot connect to backend"

- Ensure backend is running on port 8000
- Check firewall settings
- Verify `http://localhost:8000/api/health` returns `{"status":"ok"}`

### App shows blank screen

- Check backend is accessible from the machine
- Open DevTools (Ctrl+Shift+I) to see console errors
- Check the Network tab for failed API calls

### "wine: could not load kernel32.dll"

Use Docker build: `make desktop-exe-docker`

## Code Signing (Optional)

For production distribution without security warnings:

1. Purchase a code signing certificate (~$200-700/year)
2. Set environment variables:
   ```bash
   export WIN_CSC_LINK=/path/to/certificate.p12
   export WIN_CSC_KEY_PASSWORD=your_password
   ```
3. Build with `make desktop-exe-docker`

## Build Configuration

Settings are in `desktop/package.json` under `"build"`:

- **appId:** Unique application identifier
- **productName:** Display name
- **extraResources:** Additional files to bundle (empty for client-only mode)
