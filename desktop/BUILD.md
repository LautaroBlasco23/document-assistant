# Desktop App Build Guide

This guide covers building the Document Assistant desktop application for different platforms.

## Prerequisites

- Node.js 18+
- npm
- Docker (for Windows builds on Linux/WSL)

## Development

```bash
make desktop-dev
```

This starts the Electron app in development mode with hot reload.

## Building for Linux

```bash
make desktop-dist
```

Creates:
- `desktop/dist/*.AppImage` - Portable Linux app
- `desktop/dist/*.deb` - Debian package

## Building for Windows

### Option 1: Docker (Recommended)

This is the most reliable method, especially on WSL2:

```bash
make desktop-exe-docker
```

This uses the official `electronuserland/builder:wine` Docker image which has Wine properly configured.

**Requirements:**
- Docker installed and running

### Option 2: Native Wine (Alternative)

If you have Wine properly configured:

```bash
make desktop-exe
```

**Note:** Wine on WSL2 often has issues with `kernel32.dll` as you experienced. If you see this error, use the Docker method instead.

**To fix Wine on Ubuntu/WSL:**
```bash
sudo dpkg --add-architecture i386
sudo apt update
sudo apt install -y wine64 wine32
winecfg  # Initialize Wine
```

### Windows Build Output

Creates in `desktop/dist/`:
- `Document Assistant Setup 1.0.0.exe` - Installer with setup wizard
- `Document Assistant 1.0.0.exe` - Portable executable

## App Icon

The app icon is located at `desktop/build/icon.ico`. 

A placeholder SVG icon is provided at `desktop/build/icon.svg`. To convert it to ICO format:

1. Use an online converter like [convertio.co](https://convertio.co/svg-ico/)
2. Or install ImageMagick: `sudo apt install imagemagick` then:
   ```bash
   convert -background transparent desktop/build/icon.svg -define icon:auto-resize=256,128,64,48,32,16 desktop/build/icon.ico
   ```

## Code Signing (Optional but Recommended)

Without code signing, Windows will show a security warning when users run your app.

To sign your Windows executable:
1. Purchase a code signing certificate from a provider like DigiCert, Sectigo, or SSL.com
2. Set environment variables:
   ```bash
   export WIN_CSC_LINK=/path/to/certificate.p12
   export WIN_CSC_KEY_PASSWORD=your_password
   ```
3. Build with: `make desktop-exe-docker`

For EV (Extended Validation) certificates that avoid SmartScreen warnings, consider using a CI/CD service like GitHub Actions with a Windows runner.

## Troubleshooting

### "wine: could not load kernel32.dll"

Use the Docker build method: `make desktop-exe-docker`

### "author is missed in the package.json"

Fixed - the author field is now set in `package.json`.

### "default Electron icon is used"

Create `desktop/build/icon.ico` from the provided SVG or your own icon.

## Build Configuration

Build settings are in `desktop/package.json` under the `"build"` section:

- **Windows targets:** NSIS installer + Portable executable
- **Linux targets:** AppImage + Debian package  
- **Mac targets:** DMG + ZIP (requires macOS or CI/CD)
