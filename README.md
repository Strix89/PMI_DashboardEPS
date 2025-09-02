# PMI Dashboard

A comprehensive Flask-based web application dashboard for IT infrastructure management, featuring Proxmox VE integration, real-time monitoring, and responsive design with light/dark theme support.

## Features

### 🖥️ **Proxmox VE Management**
- **Multi-node Support**: Manage multiple Proxmox VE clusters from a single interface
- **Real-time Monitoring**: Live metrics for CPU, memory, disk usage, and network I/O
- **VM/LXC Control**: Start, stop, restart virtual machines and containers
- **Operation History**: Track all operations with detailed logging and status
- **Connection Testing**: Validate Proxmox connections before adding nodes

### 🎨 **Modern User Interface**
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices
- **Dark/Light Themes**: Toggle between themes with persistent preferences
- **Touch-Friendly**: Swipe gestures and touch optimizations for mobile
- **Accessibility**: WCAG compliant with keyboard navigation and screen reader support
- **Progressive Web App**: Install as a native app on mobile devices

### 🔧 **Advanced Features**
- **Real-time Updates**: Auto-refreshing metrics with configurable intervals
- **Error Handling**: Comprehensive error handling with recovery suggestions
- **Logging System**: Multi-level logging with rotation and structured output
- **Configuration Management**: Environment-based configuration with validation
- **Security**: API token authentication, HTTPS support, and security headers

### 📱 **Mobile Optimizations**
- **Foldable Device Support**: Adaptive layouts for foldable screens
- **Haptic Feedback**: Vibration feedback for supported devices
- **Pull-to-Refresh Prevention**: Optimized touch interactions
- **Orientation Handling**: Automatic layout adjustments for landscape/portrait

## Quick Start

### Prerequisites
- Python 3.8 or higher
- Proxmox VE 6.0 or higher with API access
- Modern web browser (Chrome 90+, Firefox 88+, Safari 14+)

### Installation

1. **Clone and Setup**:
   ```bash
   git clone <repository-url>
   cd pmi_dashboard
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env .env.local
   # Edit .env.local with your configuration
   ```

3. **Run Application**:
   ```bash
   python app.py
   ```

4. **Access Dashboard**:
   Open http://127.0.0.1:5000 in your browser

### First-Time Setup

1. **Add Proxmox Node**: Click "Add Node" and enter your Proxmox server details
2. **Create API Token**: In Proxmox, create an API token with appropriate permissions
3. **Test Connection**: Use the connection test feature to verify setup
4. **Start Monitoring**: View real-time metrics and manage your infrastructure

## Project Architecture

### Directory Structure
```
pmi_dashboard/
├── app.py                      # Main Flask application entry point
├── config.py                   # Configuration management system
├── logging_config.py           # Comprehensive logging setup
├── proxmox/                    # Proxmox VE integration module
│   ├── __init__.py            # Module initialization and exports
│   ├── api_client.py          # Proxmox API client with error handling
│   ├── models.py              # Data models and validation
│   ├── routes.py              # Flask routes and API endpoints
│   └── history.py             # Operation history management
├── static/                     # Frontend assets
│   ├── css/
│   │   └── style.css          # Main stylesheet with theme support
│   ├── js/                    # JavaScript modules
│   │   ├── main.js            # Core dashboard functionality
│   │   ├── theme.js           # Theme management system
│   │   ├── proxmox.js         # Proxmox API client
│   │   ├── notifications.js   # Notification system
│   │   ├── metrics-*.js       # Real-time metrics components
│   │   └── *.js               # Additional UI components
│   └── images/                # Static images and icons
├── templates/                  # Jinja2 HTML templates
│   ├── base.html              # Base template with navigation
│   ├── index.html             # Main dashboard page
│   ├── error.html             # Error page template
│   └── components/            # Reusable template components
├── data/                       # Application data storage
│   ├── proxmox_config.json    # Proxmox node configurations
│   └── operation_history.json # Operation history log
├── logs/                       # Application logs (auto-created)
├── .env                        # Environment configuration template
├── CONFIG_GUIDE.md            # Detailed configuration documentation
└── requirements.txt           # Python dependencies
```

### Technology Stack

#### Backend
- **Flask 2.3+**: Web framework with Blueprint organization
- **Python 3.8+**: Core language with type hints
- **Requests**: HTTP client for Proxmox API communication
- **python-dotenv**: Environment variable management

#### Frontend
- **Vanilla JavaScript**: No framework dependencies for better performance
- **CSS Custom Properties**: Dynamic theming system
- **Font Awesome 6**: Icon library
- **Progressive Web App**: Manifest and service worker support

#### Data Storage
- **JSON Files**: Configuration and history storage
- **Browser localStorage**: User preferences and theme settings

## Configuration

### Environment Variables (.env)
The application uses environment variables for all configuration. Key settings include:

```bash
# Flask Application
SECRET_KEY=your-secret-key-here
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
FLASK_DEBUG=False

# Proxmox Defaults
PROXMOX_DEFAULT_PORT=8006
PROXMOX_SSL_VERIFY=False
PROXMOX_TIMEOUT=30

# Monitoring
METRICS_REFRESH_INTERVAL=10

# Security (Production)
FORCE_HTTPS=True
SESSION_TIMEOUT=60
```

See [CONFIG_GUIDE.md](CONFIG_GUIDE.md) for complete configuration documentation.

### Proxmox Setup
1. **Create API Token**: In Proxmox web interface, go to Datacenter → Permissions → API Tokens
2. **Set Permissions**: Assign appropriate privileges (VM.Monitor, VM.PowerMgmt, etc.)
3. **Configure Node**: Add node in PMI Dashboard with token credentials

## API Documentation

### REST Endpoints

#### Node Management
- `GET /api/proxmox/nodes` - List all configured nodes with status
- `POST /api/proxmox/nodes` - Add new Proxmox node
- `PUT /api/proxmox/nodes/{id}` - Update node configuration
- `DELETE /api/proxmox/nodes/{id}` - Remove node
- `POST /api/proxmox/nodes/{id}/test` - Test node connection

#### Resource Management
- `GET /api/proxmox/nodes/{id}/resources` - Get VMs and containers
- `GET /api/proxmox/nodes/{id}/resources/{vmid}/metrics` - Get resource metrics
- `POST /api/proxmox/nodes/{id}/resources/{vmid}/start` - Start VM/container
- `POST /api/proxmox/nodes/{id}/resources/{vmid}/stop` - Stop VM/container
- `POST /api/proxmox/nodes/{id}/resources/{vmid}/restart` - Restart VM/container

#### Operation History
- `GET /api/proxmox/history` - Get operation history with filtering
- `GET /api/proxmox/nodes/{id}/history` - Get node-specific history

## Development

### Code Style
- **Python**: PEP 8 compliant with type hints
- **JavaScript**: ES6+ with JSDoc comments
- **CSS**: BEM methodology with custom properties
- **HTML**: Semantic markup with ARIA attributes

### Testing
```bash
# Run Python tests
python -m pytest tests/

# Run JavaScript tests (if available)
npm test

# Lint code
flake8 pmi_dashboard/
eslint static/js/
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## Deployment

### Production Deployment
1. **Environment Setup**:
   ```bash
   export FLASK_DEBUG=False
   export SECRET_KEY="your-secure-key"
   export FORCE_HTTPS=True
   ```

2. **WSGI Server** (recommended):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 app:app
   ```

3. **Reverse Proxy**: Configure nginx/Apache for SSL termination

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

### Security Checklist
- [ ] Change default SECRET_KEY
- [ ] Disable debug mode in production
- [ ] Enable HTTPS with valid certificates
- [ ] Set up proper file permissions
- [ ] Configure firewall rules
- [ ] Use secure API tokens with minimal permissions
- [ ] Enable logging and monitoring
- [ ] Regular security updates

## Troubleshooting

### Common Issues

**Connection Errors**:
- Verify Proxmox server is accessible
- Check API token permissions
- Validate SSL certificate settings

**Performance Issues**:
- Adjust METRICS_REFRESH_INTERVAL
- Check network latency to Proxmox servers
- Monitor application logs for errors

**Mobile Issues**:
- Clear browser cache
- Check viewport meta tag
- Verify touch event handling

### Debug Mode
Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
export FLASK_DEBUG=True
```

### Log Files
- `logs/app.log` - General application logs
- `logs/errors.log` - Error messages with context
- `logs/api.log` - API request/response logs
- `logs/security.log` - Security-related events
- `logs/performance.log` - Performance metrics

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- **Documentation**: See CONFIG_GUIDE.md for detailed configuration
- **Issues**: Report bugs and feature requests via GitHub issues
- **Security**: Report security vulnerabilities privately

## Changelog

### Version 1.0.0
- Initial release with Proxmox VE integration
- Real-time monitoring and metrics
- Responsive design with theme support
- Mobile optimizations and PWA features
- Comprehensive logging and error handling