# PMI Dashboard

A Flask-based web application dashboard for IT infrastructure management.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy and configure environment variables:
   ```bash
   cp .env .env.local
   # Edit .env.local with your specific configuration
   ```

3. Run the application:
   ```bash
   python app.py
   ```

The application will be available at http://127.0.0.1:5000

## Project Structure

```
pmi_dashboard/
├── app.py                 # Main Flask application
├── config.py             # Configuration management
├── proxmox/              # Proxmox module (to be implemented)
├── static/               # Static assets (CSS, JS, images)
├── templates/            # Jinja2 templates
├── data/                 # Application data files
├── .env                  # Environment configuration template
└── requirements.txt      # Python dependencies
```

## Configuration

All configuration is managed through environment variables. See `.env` for available options and their descriptions.