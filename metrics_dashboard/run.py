#!/usr/bin/env python3
"""
Availability Dashboard - Launcher

Script di avvio per la dashboard di availability monitoring.
"""

import os
import sys
from app import app

if __name__ == '__main__':
    # Configurazione per il debug
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    print("🚀 Avvio Availability Dashboard...")
    print(f"📊 Modalità debug: {'ON' if debug_mode else 'OFF'}")
    print("🌐 Accesso: http://localhost:5001")
    print("⚙️  Per modificare la configurazione, visitare: http://localhost:5001")
    print("📈 Per accedere alla dashboard: http://localhost:5001/dashboard")
    print("-" * 60)
    
    app.run(
        debug=debug_mode, 
        host='0.0.0.0', 
        port=5001,
        threaded=True
    )
