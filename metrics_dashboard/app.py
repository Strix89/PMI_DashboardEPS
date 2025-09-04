from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import sys
import json
import subprocess
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

# Aggiungi il path del progetto per importare storage_layer
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from storage_layer.storage_manager import StorageManager
from storage_layer.models import AssetDocument
from storage_layer.exceptions import StorageManagerError

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'availability-dashboard-secret-key-2025')

# Configurazione database (da file .env)
DATABASE_CONFIG = {
    'connection_string': os.environ.get('MONGODB_CONNECTION_STRING', 'mongodb://localhost:27017'),
    'database_name': os.environ.get('MONGODB_DATABASE_NAME', 'pmi_infrastructure')
}

# Configurazione default dashboard (da file .env)
DEFAULT_CONFIG = {
    'error_budget': int(os.environ.get('DEFAULT_ERROR_BUDGET', 5))
}

class AnalysisJobManager:
    """Gestisce i job di analisi in background"""
    
    def __init__(self):
        self.current_job = None
        self.job_status = "idle"
        self.job_progress = 0
        self.job_result = None
        
    def start_analysis(self, config: Dict[str, Any]) -> str:
        """Avvia l'analisi cumulativa in background"""
        if self.current_job and self.current_job.is_alive():
            return "Job già in esecuzione"
        
        self.job_status = "running"
        self.job_progress = 0
        self.job_result = None
        
        # Avvia il thread per l'analisi
        self.current_job = threading.Thread(
            target=self._run_analysis, 
            args=(config,)
        )
        self.current_job.start()
        return "Job avviato"
    
    def _run_analysis(self, config: Dict[str, Any]):
        """Esegue l'analisi vera e propria"""
        try:
            self.job_progress = 10
            logger.info("Avvio analisi cumulativa...")
            
            # 1. SALVA CONFIGURAZIONE IN FILE JSON TEMPORANEO
            config_file = os.path.join(os.path.dirname(__file__), 'temp_config.json')
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"Configurazione salvata in: {config_file}")
            self.job_progress = 20
            
            # Prepara il comando per l'analyzer
            analyzer_path = os.path.join(
                os.path.dirname(__file__), 
                'utils', 
                'cumulative_availability_analyzer.py'
            )
            
            cmd = [
                sys.executable,  # Usa l'interprete Python corrente
                analyzer_path,
                '--connection-string', DATABASE_CONFIG['connection_string'],
                '--database-name', DATABASE_CONFIG['database_name'],
                '--config-file', config_file  # Passa il file di configurazione
            ]
            
            logger.info(f"Comando da eseguire: {' '.join(cmd)}")
            self.job_progress = 30
            
            # Esegui l'analyzer
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(__file__))
            
            logger.info(f"Risultato subprocess - Return code: {result.returncode}")
            if result.stdout:
                logger.info(f"STDOUT: {result.stdout}")
            if result.stderr:
                logger.error(f"STDERR: {result.stderr}")
            
            self.job_progress = 80
            
            if result.returncode == 0:
                # Trova il file JSON generato
                output_dir = os.path.join(
                    os.path.dirname(__file__), 
                    'output'
                )
                
                if os.path.exists(output_dir):
                    json_files = [f for f in os.listdir(output_dir) 
                                 if f.startswith('cumulative_availability_analysis_') and f.endswith('.json')]
                    
                    if json_files:
                        # Prendi il file più recente
                        latest_file = max(json_files, key=lambda x: os.path.getctime(os.path.join(output_dir, x)))
                        json_path = os.path.join(output_dir, latest_file)
                        
                        logger.info(f"File JSON trovato: {json_path}")
                        
                        with open(json_path, 'r', encoding='utf-8') as f:
                            json_data = json.load(f)
                            self.job_result = {
                                'success': True,
                                'data': json_data,
                                'file_path': json_path,
                                'config': config
                            }
                    else:
                        self.job_result = {
                            'success': False,
                            'error': f'File JSON non trovato nella directory: {output_dir}'
                        }
                else:
                    self.job_result = {
                        'success': False,
                        'error': f'Directory output non esistente: {output_dir}'
                    }
            else:
                self.job_result = {
                    'success': False,
                    'error': f'Errore nell\'esecuzione dell\'analyzer: {result.stderr or "Errore sconosciuto"}'
                }
                
            # Rimuovi file temporaneo di configurazione
            try:
                os.remove(config_file)
                logger.info("File configurazione temporaneo rimosso")
            except Exception as e:
                logger.warning(f"Impossibile rimuovere file temporaneo: {e}")
                
            self.job_progress = 100
            self.job_status = "completed"
            logger.info("Analisi completata!")
            
        except Exception as e:
            logger.error(f"Errore durante l'analisi: {e}")
            # Rimuovi file temporaneo anche in caso di errore
            try:
                config_file = os.path.join(os.path.dirname(__file__), 'temp_config.json')
                if os.path.exists(config_file):
                    os.remove(config_file)
            except:
                pass
            
            self.job_result = {
                'success': False,
                'error': str(e)
            }
            self.job_status = "error"
            self.job_progress = 100
    
    def get_status(self) -> Dict[str, Any]:
        """Ottieni lo status del job corrente"""
        return {
            'status': self.job_status,
            'progress': self.job_progress,
            'result': self.job_result
        }

# Istanza globale del job manager
job_manager = AnalysisJobManager()

@app.route('/')
def index():
    """Pagina iniziale con selezione file JSON o generazione"""
    # Controlla se ci sono file JSON esistenti
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    json_files = []
    
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            if filename.endswith('.json') and 'cumulative_availability_analysis' in filename:
                filepath = os.path.join(output_dir, filename)
                try:
                    # Leggi info base del file
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    json_files.append({
                        'filename': filename,
                        'analysis_timestamp': data.get('analysis_timestamp', 'N/A'),
                        'analysis_dates': data.get('analysis_dates', []),
                        'total_services': len(data.get('services', {})),
                        'filepath': filepath
                    })
                except Exception as e:
                    logger.warning(f"Errore nel leggere {filename}: {e}")
    
    # Ordina per timestamp più recente
    json_files.sort(key=lambda x: x['analysis_timestamp'], reverse=True)
    
    return render_template('index.html', 
                         json_files=json_files, 
                         has_files=len(json_files) > 0)

@app.route('/config')
def config():
    """Pagina di configurazione per generare nuovo file JSON"""
    return render_template('config.html', default_config=DEFAULT_CONFIG)

@app.route('/load_json/<filename>')
def load_json(filename):
    """Carica un file JSON esistente per la dashboard"""
    try:
        output_dir = os.path.join(os.path.dirname(__file__), 'output')
        filepath = os.path.join(output_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'File non trovato'})
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Imposta la configurazione nella sessione (necessario per la dashboard)
        session['config'] = {
            'error_budget': DEFAULT_CONFIG['error_budget'],
            'loaded_from_file': True,
            'filename': filename
        }
        
        # Imposta il risultato nel job manager
        job_manager.job_result = {
            'success': True,
            'data': data
        }
        job_manager.job_status = "completed"
        job_manager.job_progress = 100
        
        logger.info(f"File JSON caricato con successo: {filename}")
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        logger.error(f"Errore nel caricamento file JSON: {str(e)}")
        return jsonify({'success': False, 'error': f'Errore nel caricamento: {str(e)}'})
        
    except Exception as e:
        logger.error(f"Errore nel caricare il file JSON {filename}: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_services')
def get_services():
    """API per ottenere tutti i servizi disponibili"""
    try:
        # FORZA REFRESH - rimuovi dalla sessione per debug
        if 'services' in session:
            session.pop('services')
            logger.info("Cache servizi pulita per debug")
        
        # Prima controlla se i servizi sono già in sessione
        if 'services' in session:
            logger.info(f"Servizi già in sessione: {len(session['services'])}")
            return jsonify({'success': True, 'services': session['services']})
        
        storage_manager = StorageManager(
            connection_string=DATABASE_CONFIG['connection_string'],
            database_name=DATABASE_CONFIG['database_name']
        )
        storage_manager.connect()
        
        # Debug: prima vediamo tutti i servizi che ci sono
        logger.info("Debug: cercando servizi nel database...")
        
        # Prova con diversi tipi di asset
        services = storage_manager.get_assets_by_type(asset_type="service")
        logger.info(f"Servizi trovati con type='service': {len(services)}")
        
        # Se non trova servizi, proviamo a vedere tutti gli asset
        if len(services) == 0:
            all_assets = list(storage_manager.database['assets'].find().limit(10))
            logger.info(f"Debug: primi 10 asset nel DB: {[asset.get('name', 'NO_NAME') + ' (' + asset.get('type', 'NO_TYPE') + ')' for asset in all_assets]}")
            
            # Proviamo con tutti gli asset che potrebbero essere servizi
            potential_services = list(storage_manager.database['assets'].find())
            services = [asset for asset in potential_services if asset.get('name')]
            logger.info(f"Tutti gli asset con nome: {len(services)}")
        
        service_list = []
        
        for service in services:
            # Il nome è nel campo 'service_name', non 'name'
            service_name = service.get('service_name', service.get('name', f"Service_{service.get('_id', 'unknown')}"))
            
            service_list.append({
                'id': str(service.get('_id')),
                'name': service_name,
                'description': service.get('description', f'Servizio {service_name}'),
                'status': service.get('status', 'active'),
                'type': service.get('type', service.get('data', {}).get('service_type', 'service'))
            })
        
        # Salva i servizi in sessione per riutilizzo
        session['services'] = service_list
        session.permanent = True
        
        storage_manager.disconnect()
        logger.info(f"Trovati {len(service_list)} servizi/asset - salvati in sessione")
        return jsonify({'success': True, 'services': service_list})
        
    except Exception as e:
        logger.error(f"Errore nel recupero dei servizi: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/start_analysis', methods=['POST'])
def start_analysis():
    """Avvia l'analisi cumulativa con i parametri configurati"""
    try:
        config = request.json
        logger.info(f"Configurazione ricevuta: {config}")
        
        # Salva la configurazione in sessione
        session['config'] = config
        
        # Avvia il job di analisi
        result = job_manager.start_analysis(config)
        
        return jsonify({'success': True, 'message': result})
        
    except Exception as e:
        logger.error(f"Errore nell'avvio dell'analisi: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/job_status')
def job_status():
    """Ottieni lo status del job di analisi"""
    status = job_manager.get_status()
    return jsonify(status)

@app.route('/dashboard')
def dashboard():
    """Pagina dashboard con i risultati"""
    if 'config' not in session:
        return redirect(url_for('index'))
    
    job_status = job_manager.get_status()
    if job_status['status'] != 'completed' or not job_status['result'] or not job_status['result']['success']:
        return redirect(url_for('index'))
    
    return render_template('dashboard.html')

@app.route('/get_dashboard_data')
def get_dashboard_data():
    """API per ottenere i dati del dashboard"""
    try:
        job_status = job_manager.get_status()
        if job_status['status'] != 'completed' or not job_status['result'] or not job_status['result']['success']:
            return jsonify({'success': False, 'error': 'Nessun dato disponibile'})
        
        analysis_data = job_status['result']['data']
        
        # Usa direttamente il summary dal JSON se disponibile
        if 'summary' in analysis_data and 'aggregated_score' in analysis_data['summary']:
            aggregated_score = analysis_data['summary']['aggregated_score']
        else:
            # Fallback: calcola manualmente
            services_data = analysis_data.get('services', {})
            total_score = 0
            total_weight = 0
            
            for service_name, service_data in services_data.items():
                score = service_data.get('final_score', 0)
                weight = service_data.get('weight', 0)
                total_score += score * weight
                total_weight += weight
                
            aggregated_score = total_score / total_weight if total_weight > 0 else 0
        
        # Converti detailed_metrics in timeline per compatibilità con frontend
        services_with_timeline = {}
        for service_name, service_data in analysis_data.get('services', {}).items():
            detailed_metrics = service_data.get('detailed_metrics', [])
            
            # Crea timeline dai detailed_metrics
            timeline = []
            for metric in detailed_metrics:
                timeline.append({
                    'timestamp': metric.get('timestamp'),
                    'cumulative_percentage': metric.get('score', 0) * 100,  # Converti a percentuale
                    'status': metric.get('status_type', 'UNKNOWN'),
                    'failures': metric.get('cumulative_failures', 0)
                })
            
            services_with_timeline[service_name] = {
                'service_id': service_data.get('service_id'),
                'error_budget': service_data.get('error_budget', 0),
                'weight': service_data.get('weight', 0),
                'final_score': service_data.get('final_score', 0),
                'final_status': service_data.get('final_status', 'UNKNOWN'),
                'total_failures': service_data.get('total_failures', 0),
                'timeline': timeline
            }
        
        result = {
            'success': True,
            'aggregated_health_score': round(aggregated_score, 2),
            'services': services_with_timeline,
            'config': analysis_data.get('configuration', {}),  # Aggiungi la configurazione
            'analysis_info': {
                'analysis_dates': analysis_data.get('analysis_dates', []),
                'total_services': len(services_with_timeline),
                'last_updated': analysis_data.get('analysis_timestamp')
            }
        }
        
        logger.info(f"Dashboard data preparato: {len(services_with_timeline)} servizi, score aggregato: {aggregated_score:.2f}%")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Errore nel recupero dei dati del dashboard: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/reset_config')
def reset_config():
    """Reset della configurazione"""
    session.clear()
    job_manager.job_status = "idle"
    job_manager.job_progress = 0
    job_manager.job_result = None
    return redirect(url_for('index'))

if __name__ == '__main__':
    print("🚀 Avvio Availability Dashboard...")
    print(f"📊 Database: {DATABASE_CONFIG['database_name']}")
    print("🌐 Accesso: http://localhost:5001")
    print("-" * 60)
    app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)
