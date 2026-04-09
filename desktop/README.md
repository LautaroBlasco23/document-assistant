# Document Assistant Desktop App

This is the Electron desktop application for Document Assistant.

## Prerequisites

- Node.js 18+ and npm
- Python 3.12+ with `uv` package manager (for backend)
- PostgreSQL (running via Docker or locally)

## Setup

```bash
# Install dependencies
cd desktop && npm install

# In development, also ensure backend dependencies are synced
cd ../backend && uv sync
```

## Development

In development mode, the Electron app will:
1. Start the frontend Vite dev server (port 5173)
2. Launch Electron pointing to the dev server
3. Auto-start the Python backend

```bash
cd desktop
npm run dev
```

## Building

### Build Frontend

The frontend must be built before packaging the Electron app:

```bash
cd desktop
npm run build:renderer
```

### Build Electron

```bash
cd desktop
npm run build
```

## Distribution

### Linux

```bash
cd desktop
npm run dist:linux
```

Creates:
- `dist/Document Assistant-1.0.0.AppImage`
- `dist/document-assistant-desktop_1.0.0_amd64.deb`

### macOS

```bash
cd desktop
npm run dist:mac
```

Creates:
- `dist/Document Assistant-1.0.0.dmg`
- `dist/Document Assistant-1.0.0-mac.zip`

### Windows

```bash
cd desktop
npm run dist:win
```

Creates:
- `dist/Document Assistant Setup 1.0.0.exe`
- `dist/Document Assistant 1.0.0.exe` (portable)

## Architecture

The desktop app consists of:

- **Main Process** (`src/main/`): Electron's main process that manages windows and spawns the backend
- **Preload Script** (`src/preload/`): Secure bridge between main and renderer processes
- **Renderer Process**: The existing React frontend running in a BrowserWindow

### Backend Management

The main process automatically:
1. Spawns the Python backend using `uv run uvicorn`
2. Monitors backend health via `/api/health` endpoint
3. Shuts down backend when the app quits

### API Communication

In production, the frontend is served via `file://` protocol. API calls go to `http://127.0.0.1:8000/api/*`.

The preload script exposes a `window.desktopAPI` object for:
- Backend status monitoring
- Native file dialogs
- Window controls

## Troubleshooting

### Backend fails to start

1. Ensure `uv` is installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. Ensure PostgreSQL is running: `docker compose up -d postgres`
3. Check logs in the app or console

### Frontend not loading

1. Ensure frontend is built: `npm run build:renderer`
2. Check that `frontend/dist/index.html` exists

### Port conflicts

The app uses:
- Port 8000 for the backend API
- Port 5173 for the Vite dev server (dev mode only)
