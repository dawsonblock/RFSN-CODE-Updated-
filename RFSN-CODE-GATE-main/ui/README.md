# 🚀 RFSN SWE-Bench Killer - Modern Web UI

A beautiful, modern web interface for the RFSN SWE-Bench Killer AI Code Agent with bright colors and real-time updates.

## ✨ Features

### 🎨 Modern Design
- **Bright, colorful UI** with gradient backgrounds
- **Dark theme** optimized for long coding sessions
- **Responsive layout** works on desktop and mobile
- **Smooth animations** and transitions
- **Real-time updates** via WebSocket

### 📝 Configuration Tab
- **GitHub Repository** upload and configuration
- **GitHub Credentials** for PR creation
- **LLM API Keys** support (OpenAI, Anthropic, Google, DeepSeek)
- **Execution Settings** with profile selection
- **Localization Layers** toggle (Trace, Ripgrep, Symbols, Embeddings)
- **Patch Strategies** selection

### 🔄 Live Process Tab
- **Real-time progress** tracking
- **Live log stream** with color-coded entries
- **Current phase** display
- **Statistics** (steps, patches, elapsed time)
- **Progress bar** visualization

### 📊 Results Tab
- View task results and metrics
- Patch history
- Test results

### 📜 History Tab
- Past task execution history
- Success/failure tracking

## 🚀 Quick Start

### Installation

```bash
# Install Python dependencies
pip install fastapi uvicorn websockets

# Or install from requirements
cd ui
pip install -r requirements.txt
```

### Run the Server

```bash
# From the ui/ directory
python server.py

# Or from the project root
cd /home/user/webapp/RFSN-CODE-GATE-main
python ui/server.py
```

### Open the UI

Open your browser and navigate to:
```
http://localhost:8000
```

## 📁 File Structure

```
ui/
├── index.html          # Main HTML structure
├── styles.css          # Modern CSS with bright colors
├── app.js              # Frontend JavaScript logic
├── server.py           # FastAPI backend server
├── README.md           # This file
└── requirements.txt    # Python dependencies
```

## 🎯 Usage

### 1. Configure

1. **Enter Repository URL**: `https://github.com/owner/repo`
2. **Add Problem Statement**: Describe the bug or issue
3. **GitHub Credentials** (optional): For PR creation
4. **LLM API Key**: Required for patch generation
5. **Adjust Settings**: Max steps, time, localization layers

### 2. Start Agent

Click the **"🚀 Start Agent"** button to begin execution.

### 3. Monitor Progress

Switch to the **"🔄 Live Process"** tab to see:
- Current phase (INGEST, LOCALIZE, PATCH, etc.)
- Live log stream
- Progress statistics
- Real-time updates

### 4. View Results

Check the **"📊 Results"** tab when complete.

## 🎨 Color Palette

The UI uses a modern, vibrant color scheme:

- **Primary**: `#6366f1` (Indigo)
- **Secondary**: `#ec4899` (Pink)
- **Accent**: `#14b8a6` (Teal)
- **Success**: `#10b981` (Green)
- **Warning**: `#f59e0b` (Orange)
- **Danger**: `#ef4444` (Red)
- **Background**: Dark gradient (`#0f172a` → `#1e293b`)

## 🔧 API Endpoints

### REST API

- `GET /` - Serve UI
- `GET /api/health` - Health check
- `POST /api/start` - Start agent
- `POST /api/stop` - Stop agent
- `GET /api/status/{task_id}` - Get task status

### WebSocket

- `WS /ws/{task_id}` - Real-time updates

## 📡 WebSocket Messages

### Server → Client

```json
{
  "type": "phase",
  "phase": "LOCALIZE"
}

{
  "type": "log",
  "level": "info",
  "message": "Found 5 bug locations"
}

{
  "type": "progress",
  "progress": 45.0,
  "current_step": 5,
  "total_steps": 10,
  "patches": 2
}

{
  "type": "complete",
  "success": true,
  "time_taken": 120.5
}
```

## 🛠️ Development

### Run in Development Mode

```bash
# Auto-reload on file changes
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### Customize Colors

Edit `styles.css` and modify the `:root` CSS variables:

```css
:root {
    --primary: #6366f1;
    --secondary: #ec4899;
    /* ... */
}
```

### Add New Features

1. **Frontend**: Edit `app.js` and `index.html`
2. **Backend**: Edit `server.py` and add endpoints
3. **Styling**: Edit `styles.css`

## 🧪 Testing

### Manual Testing

1. Start the server
2. Open browser to `http://localhost:8000`
3. Test each tab
4. Try starting the agent

### With Real Backend

Ensure the RFSN components are available:

```python
# server.py will use real RFSN if available
from eval.run import EvalRunner
from localize import localize_issue
# ...
```

### Mock Mode

If RFSN components are not available, the server runs in mock/simulation mode for demo purposes.

## 🌐 Deployment

### Production Deployment

```bash
# Use gunicorn with uvicorn workers
gunicorn server:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Or use uvicorn directly
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker (Optional)

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

EXPOSE 8000
CMD ["python", "server.py"]
```

## 📝 Configuration Storage

Configuration is saved in browser localStorage:
- Persists across page reloads
- Stored locally (not sent to server)
- Auto-saves on field changes

## ⚡ Performance

- **Lightweight**: Vanilla JavaScript (no frameworks)
- **Fast**: Minimal dependencies
- **Responsive**: Smooth animations at 60fps
- **Efficient**: WebSocket for real-time updates

## 🔒 Security Notes

- API keys stored in localStorage (client-side only)
- CORS enabled for development (restrict in production)
- GitHub tokens never logged
- Secure WebSocket connections recommended (WSS)

## 🐛 Troubleshooting

### Server Won't Start

```bash
# Check if port 8000 is in use
lsof -i :8000

# Try a different port
uvicorn server:app --port 8080
```

### WebSocket Connection Fails

- Ensure backend is running
- Check browser console for errors
- Falls back to simulation mode automatically

### Configuration Not Saving

- Check browser localStorage is enabled
- Clear site data and try again

## 🎓 Tips

1. **Save configuration** before starting
2. **Monitor Live Process tab** for updates
3. **Check logs** for debugging
4. **Use simulation mode** to test UI without backend

## 📚 Related Documentation

- [Main README](../README.md)
- [SWE-Bench Implementation](../SWE_BENCH_IMPLEMENTATION_STATUS.md)
- [Quick Reference](../QUICK_REFERENCE.md)
- [API Documentation](../docs/api.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - See [LICENSE](../LICENSE) file

## 🙏 Acknowledgments

- Built with FastAPI and modern web technologies
- Inspired by VS Code and GitHub's UI
- Color palette inspired by Tailwind CSS

---

**Version**: 0.4.0  
**Status**: Production Ready ✅  
**Last Updated**: 2026-01-30

Enjoy using the RFSN SWE-Bench Killer! 🚀
