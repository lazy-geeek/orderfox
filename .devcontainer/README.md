# OrderFox Dev Container Configuration

This dev container is configured for optimal development of the OrderFox trading application, with special considerations for Windows host to container connectivity.

## Key Configuration Changes

### Frontend Proxy Configuration

The frontend is configured to use Vite's built-in proxy to avoid CORS issues when connecting from a Windows host browser to the dev container:

- **API Base URL**: `/api/v1` (relative) instead of `http://localhost:8000/api/v1` (absolute)
- **WebSocket Base URL**: `/api/v1` (relative) for WebSocket connections
- **Vite Proxy**: Configured to forward `/api/v1/*` requests to `http://localhost:8000`
- **WebSocket Proxy**: Configured to forward `/api/v1/ws/*` WebSocket connections to `ws://localhost:8000`

### Files Modified for Dev Container Compatibility

1. **`frontend_vanilla/.env`**:
   ```env
   VITE_APP_API_BASE_URL=/api/v1
   VITE_APP_WS_BASE_URL=/api/v1
   ```

2. **`frontend_vanilla/vite.config.js`**:
   ```javascript
   proxy: {
     '/api': {
       target: 'http://localhost:8000',
       changeOrigin: true,
       secure: false
     },
     '/api/v1/ws': {
       target: 'ws://localhost:8000',
       ws: true,
       changeOrigin: true
     }
   }
   ```

3. **`devcontainer.json`**:
   ```json
   "containerEnv": {
     "VITE_APP_API_BASE_URL": "/api/v1",
     "VITE_APP_WS_BASE_URL": "/api/v1"
   }
   ```

## Network Flow

```
Windows Browser → localhost:3000 (Vite Dev Server)
                ↓
Vite Proxy → localhost:8000 (FastAPI Backend)
```

This configuration ensures:
- ✅ No CORS issues
- ✅ All requests appear to come from same origin (`localhost:3000`)
- ✅ WebSocket connections work properly
- ✅ Hot Module Reload functions correctly

## Port Forwarding

The following ports are forwarded from container to host:

- **3000**: Vite dev server (frontend)
- **8000**: FastAPI backend
- **5678**: Python debugger (debugpy)

## Automatic Setup

When the container is built, the `post-create.sh` script automatically:

1. Installs all dependencies
2. Configures frontend environment for proxy usage
3. Sets up VS Code debugging configuration
4. Creates necessary directories and files
5. Configures shell environment

## Manual Rebuild

If you need to rebuild the container with these changes:

```bash
# From VS Code Command Palette
Dev Containers: Rebuild Container

# Or via CLI
docker-compose down
docker-compose build --no-cache
docker-compose up
```

## Troubleshooting

### CORS Errors
- Ensure `frontend_vanilla/.env` uses relative URLs
- Verify Vite proxy configuration in `vite.config.js`
- Check that frontend is accessing `localhost:3000`, not `localhost:8000`

### WebSocket Connection Issues
- Verify WebSocket proxy is configured for `/api/v1/ws` path
- Check that WebSocket URL is relative in environment config
- Ensure HMR is properly configured or disabled if causing issues

### Port Conflicts
- Check that ports 3000, 8000, and 5678 are available
- Verify port forwarding in `devcontainer.json`
- Use `docker ps` to check for conflicting containers