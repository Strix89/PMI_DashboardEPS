from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Blueprint
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

# Import Six Sigma utilities
from utils.sixsigma_utils import get_collection, calcola_baseline, monitora_nuovo_dato, BASELINE_DATA_POINTS

# Import AnomalySNMP Blueprint
from anomaly_snmp.routes import anomaly_snmp_bp

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'availability-dashboard-secret-key-2025')

# Registra il Blueprint AnomalySNMP
app.register_blueprint(anomaly_snmp_bp)

# Cache per le baseline Six Sigma
baseline_cache = {}

# 🔶 CACHE PER GRAFICI IN PAUSA (Test 4 e 8)
paused_charts_cache = {}  # {"machine_id_metrica": True/False}

# 🔶 CACHE PER PESI METRICHE SIX SIGMA
sixsigma_weights_cache = {}  # {"machine_id": {"cpu": 0.4, "ram": 0.35, "io_wait": 0.25}}

def load_sixsigma_weights_from_db():
    """Carica i pesi salvati da MongoDB all'avvio dell'applicazione"""
    global sixsigma_weights_cache
    try:
        from storage_layer.mongodb_config import mongodb_config
        db = mongodb_config.get_database()
        config_collection = db.get_collection('sixsigma_weights_config')
        
        configs = config_collection.find({})
        for config in configs:
            machine_id = config.get('machine_id')
            weights = config.get('weights')
            if machine_id and weights:
                sixsigma_weights_cache[machine_id] = weights
        
        print(f"📊 Caricati pesi Six Sigma per {len(sixsigma_weights_cache)} macchine da MongoDB")
        
    except Exception as e:
        print(f"⚠️ Errore caricamento pesi da MongoDB: {e}")

# Carica i pesi all'avvio
load_sixsigma_weights_from_db()

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
        
    def start_analysis(self, config: Dict[str, Any], analysis_type: str = "availability") -> str:
        """Avvia l'analisi cumulativa in background"""
        if self.current_job and self.current_job.is_alive():
            return "Job già in esecuzione"
        
        self.job_status = "running"
        self.job_progress = 0
        self.job_result = None
        
        # Avvia il thread per l'analisi
        self.current_job = threading.Thread(
            target=self._run_analysis, 
            args=(config, analysis_type)
        )
        self.current_job.start()
        return "Job avviato"
    
    def _run_analysis(self, config: Dict[str, Any], analysis_type: str = "availability"):
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
            if analysis_type == "resilience":
                analyzer_filename = 'cumulative_resilience_analyzer.py'
            else:  # default: availability
                analyzer_filename = 'cumulative_availability_analyzer.py'
                
            analyzer_path = os.path.join(
                os.path.dirname(__file__), 
                'utils', 
                analyzer_filename
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
                    # Determina il pattern del file in base al tipo di analisi
                    if analysis_type == "resilience":
                        file_pattern = 'resilience_analysis_'
                    else:  # availability
                        file_pattern = 'cumulative_availability_analysis_'
                    
                    json_files = [f for f in os.listdir(output_dir) 
                                 if f.startswith(file_pattern) and f.endswith('.json')]
                    
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
    """Pagina iniziale per selezione dashboard type"""
    return render_template('index.html')

@app.route('/availability')
def availability_index():
    """Pagina iniziale availability con selezione file JSON o generazione"""
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
    
    return render_template('availability_index.html', 
                         json_files=json_files, 
                         has_files=len(json_files) > 0)

@app.route('/resilience')
def resilience_index():
    """Pagina iniziale resilience con selezione file JSON o generazione"""
    # Controlla se ci sono file JSON esistenti
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    json_files = []
    
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            if filename.endswith('.json') and 'resilience_analysis' in filename:
                filepath = os.path.join(output_dir, filename)
                try:
                    # Leggi info base del file
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Estrai data di generazione dal filename
                    # Format: resilience_analysis_YYYYMMDD_HHMMSS.json
                    generation_date = "Data non disponibile"
                    generation_date_short = "N/A"
                    try:
                        # Estrai timestamp dal nome file
                        timestamp_part = filename.replace('resilience_analysis_', '').replace('.json', '')
                        if '_' in timestamp_part:
                            date_part, time_part = timestamp_part.split('_')
                            # Converti YYYYMMDD_HHMMSS in formato leggibile
                            from datetime import datetime
                            dt = datetime.strptime(f"{date_part}_{time_part}", "%Y%m%d_%H%M%S")
                            generation_date = dt.strftime("%d/%m/%Y alle %H:%M:%S")
                            generation_date_short = dt.strftime("%Y-%m-%d")  # Per il titolo
                    except Exception as date_error:
                        logger.warning(f"Errore nell'estrazione data da {filename}: {date_error}")
                    
                    json_files.append({
                        'filename': filename,
                        'generation_date': generation_date,
                        'generation_date_short': generation_date_short,
                        'simulation_period': data.get('simulation_period', {}),
                        'total_assets': len(data.get('individual_assets', {})),
                        'filepath': filepath
                    })
                except Exception as e:
                    logger.warning(f"Errore nel leggere {filename}: {e}")
    
    # Ordina per timestamp più recente (dal nome file)
    json_files.sort(key=lambda x: x['filename'], reverse=True)
    
    return render_template('resilience_index.html', 
                         json_files=json_files, 
                         has_files=len(json_files) > 0)

@app.route('/sixsigma')
def sixsigma_index():
    """Pagina Six Sigma di selezione - simile a availability e resilience"""
    return render_template('sixsigma_index.html')

@app.route('/sixsigma/dashboard')
def sixsigma_dashboard():
    """Pagina Six Sigma SPC Dashboard vera"""
    return render_template('sixsigma_dashboard.html')

@app.route('/sixsigma/api/macchine')
def sixsigma_get_macchine():
    """API che restituisce la lista delle macchine uniche presenti nel database."""
    collection = get_collection()
    macchine = collection.distinct("machine_id")
    return jsonify(macchine)

@app.route('/sixsigma/api/baseline/<machine_id>')
def sixsigma_get_baseline(machine_id):
    """API per caricare tutti i parametri di baseline per una macchina selezionata."""
    baselines = {
        "cpu": calcola_baseline(machine_id, "cpu", baseline_cache),
        "ram": calcola_baseline(machine_id, "ram", baseline_cache),
        "io_wait": calcola_baseline(machine_id, "io_wait", baseline_cache)
    }
    if any(b is None for b in baselines.values()):
        return jsonify({"error": "Dati insufficienti per calcolare la baseline"}), 500
    return jsonify(baselines)

@app.route('/sixsigma/api/data/<machine_id>/<int:offset>')
def sixsigma_get_next_data(machine_id, offset):
    """API che simula il tempo reale per Six Sigma"""
    collection = get_collection()
    
    history_limit = 20
    skip_offset = BASELINE_DATA_POINTS + offset
    
    # **FIX: Non includere mai i dati della baseline nella cronologia della simulazione**
    simulation_start = BASELINE_DATA_POINTS  # Primo punto della simulazione
    start_skip = max(simulation_start, skip_offset - history_limit)
    
    cursor = collection.find({"machine_id": machine_id}).sort("timestamp", 1).skip(start_skip).limit(skip_offset - start_skip + 1)
    dati = list(cursor)

    if len(dati) <= 1:
        return jsonify({"error": "Fine dei dati di simulazione"}), 404
    
    dato_corrente = dati[-1]
    cronologia_dati = dati[:-1]
    
    scores, stati, moving_ranges, dettagli_anomalie = {}, {}, {}, {}
    warning_levels = {}
    test_falliti = {}
    punti_critici = {}
    punti_coinvolti = {}  # 🔶 NUOVO: Per Test 4 e 8
    
    for metrica in ["cpu", "ram", "io_wait"]:
        baseline = baseline_cache.get(f"{machine_id}_{metrica}")
        if not baseline:
            return jsonify({"error": f"Baseline per {metrica} non trovata. Caricarla prima."}), 500

        valore_corrente = dato_corrente['metrics'][f'{metrica}_percent']
        cronologia_metrica = [d['metrics'][f'{metrica}_percent'] for d in cronologia_dati]
        valore_precedente = cronologia_metrica[-1] if cronologia_metrica else 0
        
        # **DEBUG: Log cronologia per verificare il fix**
        if offset <= 10:  # Solo per i primi punti
            print(f"DEBUG [offset={offset}] {metrica}: cronologia_len={len(cronologia_metrica)}, simulation_start={BASELINE_DATA_POINTS}, current_pos={skip_offset}")
        
        # Nuova funzione restituisce un dizionario
        risultato = monitora_nuovo_dato(valore_corrente, valore_precedente, cronologia_metrica, baseline)
        
        # 🔶 GESTIONE PENALTY SCORE DURANTE RICALCOLO BASELINE
        paused_key = f"{machine_id}_{metrica}"
        if paused_charts_cache.get(paused_key, False):
            # Se il grafico è in pausa per ricalcolo, applica SOLO penalty score
            # ma mantieni tutti gli altri dati normali per il frontend
            scores[metrica] = 0.3  # Penalty score fisso durante ricalcolo
            # NON modificare stati, test_falliti, ecc. - il frontend gestisce tutto
        else:
            # Comportamento normale
            scores[metrica] = risultato["score"]
        
        # Questi rimangono sempre uguali, pausa o no
        stati[metrica] = risultato["stato"]
        moving_ranges[metrica] = round(abs(valore_corrente - valore_precedente), 2)
        dettagli_anomalie[metrica] = risultato["dettagli_anomalia"]
        warning_levels[metrica] = risultato["warning_level"]
        test_falliti[metrica] = risultato["test_fallito"]
        punti_critici[metrica] = risultato["punto_critico"]
        punti_coinvolti[metrica] = risultato["punti_coinvolti"]  # 🔶 NUOVO

    # 🔶 CALCOLO DEL P_SCORE CON PESI CONFIGURATI
    machine_weights = sixsigma_weights_cache.get(machine_id)
    
    if machine_weights:
        # Calcolo pesato basato sulla configurazione
        weighted_sum = 0
        total_weight = 0
        
        for metrica in ["cpu", "ram", "io_wait"]:
            weight = machine_weights.get(metrica, 0)
            if weight > 0:  # Solo se il peso è configurato
                weighted_sum += scores[metrica] * weight
                total_weight += weight
        
        p_score = round(weighted_sum / total_weight if total_weight > 0 else 0, 3)
    else:
        # Fallback: media semplice se non configurato
        import numpy as np
        p_score = round(np.mean(list(scores.values())), 3)
    
    # Per ora non gestiamo il ricalcolo baseline (solo Test 1)
    overall_recalculate = False

    response = {
        "timestamp": dato_corrente['timestamp'].isoformat(),
        "metrics": dato_corrente['metrics'],
        "moving_ranges": moving_ranges,
        "scores": scores,
        "stati": stati,
        "dettagli_anomalie": dettagli_anomalie,
        "warning_levels": warning_levels,
        "test_falliti": test_falliti,
        "punti_critici": punti_critici,
        "punti_coinvolti": punti_coinvolti,  # 🔶 NUOVO: Per Test 4 e 8
        "p_score": p_score,
        "next_offset": offset + 1
    }
    return jsonify(response)

@app.route('/sixsigma/api/pause_chart/<machine_id>/<metrica>')
def sixsigma_pause_chart(machine_id, metrica):
    """API per mettere in pausa un grafico per ricalcolo baseline"""
    paused_key = f"{machine_id}_{metrica}"
    paused_charts_cache[paused_key] = True
    return jsonify({"success": True, "message": f"Grafico {metrica} messo in pausa"})

@app.route('/sixsigma/api/resume_chart/<machine_id>/<metrica>')
def sixsigma_resume_chart(machine_id, metrica):
    """API per riattivare un grafico dopo ricalcolo baseline"""
    paused_key = f"{machine_id}_{metrica}"
    paused_charts_cache[paused_key] = False
    return jsonify({"success": True, "message": f"Grafico {metrica} riattivato"})

@app.route('/sixsigma/api/recalculate_baseline/<machine_id>/<metrica>')
def sixsigma_recalculate_baseline(machine_id, metrica):
    """API per ricalcolare la baseline di una specifica metrica"""
    collection = get_collection()
    
    # Prendi gli ultimi 200 punti dati per il ricalcolo
    recalc_points = 200
    cursor = collection.find({"machine_id": machine_id}).sort("timestamp", -1).limit(recalc_points)
    dati = list(cursor)
    dati.reverse()  # Riordina cronologicamente
    
    if len(dati) < 50:
        return jsonify({"error": "Dati insufficienti per ricalcolare la baseline"}), 400
    
    # Simula il calcolo baseline sui nuovi dati
    valori = [d['metrics'][f'{metrica}_percent'] for d in dati]
    
    # Calcolo dei parametri per la carta di controllo XmR
    import numpy as np
    cl_x = np.mean(valori)
    moving_ranges = [abs(valori[i] - valori[i-1]) for i in range(1, len(valori))]
    cl_mr = np.mean(moving_ranges) if moving_ranges else 0
    
    ucl_x = cl_x + 2.66 * cl_mr
    lcl_x = max(0, cl_x - 2.66 * cl_mr)
    ucl_mr = 3.268 * cl_mr

    new_baseline = {
        "cl_x": round(cl_x, 2),
        "ucl_x": round(ucl_x, 2),
        "lcl_x": round(lcl_x, 2),
        "cl_mr": round(cl_mr, 2),
        "ucl_mr": round(ucl_mr, 2)
    }
    
    # Aggiorna la cache
    cache_key = f"{machine_id}_{metrica}"
    baseline_cache[cache_key] = new_baseline
    
    return jsonify({
        "success": True,
        "machine_id": machine_id,
        "metrica": metrica,
        "new_baseline": new_baseline,
        "data_points_used": len(dati),
        "message": f"Baseline per {metrica} ricalcolata con {len(dati)} punti dati"
    })

@app.route('/availability/config')
def availability_config():
    """Pagina di configurazione per generare nuovo file JSON availability"""
    return render_template('availability_config.html', default_config=DEFAULT_CONFIG)

@app.route('/resilience/config')
def resilience_config():
    """Pagina di configurazione per generare nuovo file JSON resilience"""
    return render_template('resilience_config.html')

@app.route('/sixsigma/config')
def sixsigma_config():
    """Pagina di configurazione pesi Six Sigma per ogni macchina"""
    print("🔧 DEBUG: Caricamento pagina sixsigma/config")
    
    # Recupera la lista delle macchine disponibili dal database usando la stessa logica dell'API macchine
    try:
        collection = get_collection()
        machines = collection.distinct("machine_id")
        print(f"🔧 DEBUG: Macchine trovate nel DB Six Sigma: {machines}")
        
        if not machines:
            # Fallback se non ci sono macchine nel DB
            machines = ['machine_001', 'machine_002', 'machine_003']
            print("🔧 DEBUG: Usato fallback per macchine")
            
    except Exception as e:
        print(f"🔧 DEBUG: Errore nel caricamento macchine: {e}")
        # Fallback con macchine di esempio
        machines = ['machine_001', 'machine_002', 'machine_003']
        print("🔧 DEBUG: Usato fallback per errore")
    
    # Configurazione di default per i pesi delle metriche
    default_weights = {
        'cpu': 0.4,     # CPU peso maggiore (criticalità alta)
        'ram': 0.35,    # RAM peso medio-alto
        'io_wait': 0.25 # I/O peso minore
    }
    
    print(f"🔧 DEBUG: Rendering template con machines={machines}, default_weights={default_weights}")
    
    return render_template('sixsigma_config.html', 
                         machines=machines, 
                         default_weights=default_weights)

@app.route('/sixsigma/api/save_config', methods=['POST'])
def sixsigma_save_config():
    """API per salvare la configurazione dei pesi Six Sigma"""
    try:
        config_data = request.json
        
        # Validazione: tutti i pesi di ogni macchina devono sommare a 1.0
        for machine, weights in config_data.items():
            total = weights.get('cpu', 0) + weights.get('ram', 0) + weights.get('io_wait', 0)
            if abs(total - 1.0) > 0.01:  # Tolleranza per errori di arrotondamento
                return jsonify({
                    "success": False, 
                    "message": f"I pesi per {machine} non sommano a 100% (attuale: {total*100:.1f}%)"
                }), 400
        
        # Salva nel database MongoDB
        try:
            from storage_layer.mongodb_config import mongodb_config
            db = mongodb_config.get_database()
            config_collection = db.get_collection('sixsigma_weights_config')
            
            # Salva ogni configurazione di macchina come documento separato
            for machine_id, weights in config_data.items():
                config_doc = {
                    "machine_id": machine_id,
                    "weights": weights,
                    "updated_at": datetime.now(),
                    "created_by": "dashboard_config"
                }
                
                # Upsert: aggiorna se esiste, crea se non esiste
                config_collection.replace_one(
                    {"machine_id": machine_id},
                    config_doc,
                    upsert=True
                )
            
            print(f"💾 Configurazione pesi salvata in MongoDB per {len(config_data)} macchine")
            
        except Exception as db_error:
            print(f"⚠️ Errore salvataggio MongoDB: {db_error}")
            # Continua comunque con il salvataggio in cache
        
        # Salva anche nella cache globale per accesso rapido
        global sixsigma_weights_cache
        sixsigma_weights_cache = config_data
        
        return jsonify({
            "success": True,
            "message": "Configurazione salvata con successo",
            "config": config_data
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Errore nel salvataggio: {str(e)}"
        }), 500

@app.route('/sixsigma/api/weights/<machine_id>')
def sixsigma_get_weights(machine_id):
    """API per ottenere i pesi configurati per una macchina specifica"""
    try:
        global sixsigma_weights_cache
        
        # Prima prova a caricare da MongoDB
        try:
            from storage_layer.mongodb_config import mongodb_config
            db = mongodb_config.get_database()
            config_collection = db.get_collection('sixsigma_weights_config')
            
            config_doc = config_collection.find_one({"machine_id": machine_id})
            if config_doc and 'weights' in config_doc:
                weights = config_doc['weights']
                # Aggiorna anche la cache
                sixsigma_weights_cache[machine_id] = weights
                
                return jsonify({
                    "success": True,
                    "machine_id": machine_id,
                    "weights": {
                        "cpu": weights.get('cpu', 0.4),
                        "ram": weights.get('ram', 0.35),
                        "io_wait": weights.get('io_wait', 0.25)
                    },
                    "source": "database"
                })
                
        except Exception as db_error:
            print(f"⚠️ Errore caricamento MongoDB: {db_error}")
        
        # Fallback: se non trovato in MongoDB, controlla la cache
        if machine_id in sixsigma_weights_cache:
            weights = sixsigma_weights_cache[machine_id]
            return jsonify({
                "success": True,
                "machine_id": machine_id,
                "weights": {
                    "cpu": weights.get('cpu', 0.4),
                    "ram": weights.get('ram', 0.35),
                    "io_wait": weights.get('io_wait', 0.25)
                },
                "source": "cache"
            })
        else:
            # Restituiamo i pesi di default
            return jsonify({
                "success": True,
                "machine_id": machine_id,
                "weights": {
                    "cpu": 0.4,
                    "ram": 0.35,
                    "io_wait": 0.25
                },
                "source": "default"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Errore nel recupero pesi: {str(e)}"
        }), 500

@app.route('/availability/load_json/<filename>')
def availability_load_json(filename):
    """Carica un file JSON esistente per la dashboard availability"""
    try:
        output_dir = os.path.join(os.path.dirname(__file__), 'output')
        filepath = os.path.join(output_dir, filename)
        
        if not os.path.exists(filepath) or 'cumulative_availability_analysis' not in filename:
            return jsonify({'success': False, 'error': 'File non trovato'})
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Imposta la configurazione nella sessione
        session['config'] = {
            'error_budget': DEFAULT_CONFIG['error_budget'],
            'loaded_from_file': True,
            'filename': filename,
            'dashboard_type': 'availability'
        }
        
        # Imposta il risultato nel job manager
        job_manager.job_result = {
            'success': True,
            'data': data
        }
        job_manager.job_status = "completed"
        job_manager.job_progress = 100
        
        logger.info(f"File JSON availability caricato con successo: {filename}")
        return redirect(url_for('availability_dashboard'))
        
    except Exception as e:
        logger.error(f"Errore nel caricamento file JSON availability: {str(e)}")
        return jsonify({'success': False, 'error': f'Errore nel caricamento: {str(e)}'})

@app.route('/resilience/load_json/<filename>')
def resilience_load_json(filename):
    """Carica un file JSON esistente per la dashboard resilience"""
    try:
        output_dir = os.path.join(os.path.dirname(__file__), 'output')
        filepath = os.path.join(output_dir, filename)
        
        if not os.path.exists(filepath) or 'resilience_analysis' not in filename:
            return jsonify({'success': False, 'error': 'File non trovato'})
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Imposta la configurazione nella sessione
        session['config'] = {
            'loaded_from_file': True,
            'filename': filename,
            'dashboard_type': 'resilience'
        }
        
        # Imposta il risultato nel job manager
        job_manager.job_result = {
            'success': True,
            'data': data
        }
        job_manager.job_status = "completed"
        job_manager.job_progress = 100
        
        logger.info(f"File JSON resilience caricato con successo: {filename}")
        return redirect(url_for('resilience_dashboard'))
        
    except Exception as e:
        logger.error(f"Errore nel caricamento file JSON resilience: {str(e)}")
        return jsonify({'success': False, 'error': f'Errore nel caricamento: {str(e)}'})

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

@app.route('/job_status')
def job_status():
    """Ottieni lo status del job di analisi"""
    status = job_manager.get_status()
    return jsonify(status)

@app.route('/availability/dashboard')
def availability_dashboard():
    """Pagina dashboard availability con i risultati"""
    if 'config' not in session or session.get('config', {}).get('dashboard_type') != 'availability':
        return redirect(url_for('availability_index'))
    
    job_status = job_manager.get_status()
    if job_status['status'] != 'completed' or not job_status['result'] or not job_status['result']['success']:
        return redirect(url_for('availability_index'))
    
    return render_template('availability_dashboard.html')

@app.route('/resilience/dashboard')
def resilience_dashboard():
    """Pagina dashboard resilience con i risultati"""
    if 'config' not in session or session.get('config', {}).get('dashboard_type') != 'resilience':
        return redirect(url_for('resilience_index'))
    
    job_status = job_manager.get_status()
    if job_status['status'] != 'completed' or not job_status['result'] or not job_status['result']['success']:
        return redirect(url_for('resilience_index'))
    
    return render_template('resilience_dashboard.html')

@app.route('/availability/get_dashboard_data')
def availability_get_dashboard_data():
    """API per ottenere i dati del dashboard availability"""
    try:
        logger.info(f"Debug: dashboard_type in session: {session.get('config', {}).get('dashboard_type')}")
        
        if session.get('config', {}).get('dashboard_type') != 'availability':
            logger.warning("Dashboard type mismatch")
            return jsonify({'success': False, 'error': 'Dashboard type mismatch'})
            
        job_status = job_manager.get_status()
        logger.info(f"Debug: job status: {job_status.get('status')}")
        
        if job_status['status'] != 'completed' or not job_status['result'] or not job_status['result']['success']:
            logger.warning("No data available or job not completed")
            return jsonify({'success': False, 'error': 'Nessun dato disponibile'})
        
        analysis_data = job_status['result']['data']
        logger.info(f"Debug: analysis_data keys: {list(analysis_data.keys())}")
        logger.info(f"Debug: services count: {len(analysis_data.get('services', {}))}")
        
        # Trasforma la struttura per il frontend
        if 'services' in analysis_data:
            for service_name, service_data in analysis_data['services'].items():
                # Rinomina detailed_metrics in timeline per compatibilità frontend
                if 'detailed_metrics' in service_data:
                    service_data['timeline'] = service_data['detailed_metrics']
                    logger.info(f"Debug: Servizio {service_name} - timeline length: {len(service_data['timeline'])}")
                    # Mantieni anche detailed_metrics per compatibilità
        
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
        
        return jsonify({
            'success': True,
            'services': analysis_data.get('services', {}),
            'summary': analysis_data.get('summary', {}),
            'aggregated_score': aggregated_score,
            'data': analysis_data  # Mantieni anche il campo data per compatibilità
        })
        
    except Exception as e:
        logger.error(f"Errore nel recupero dati availability dashboard: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/resilience/get_dashboard_data')
def resilience_get_dashboard_data():
    """API per ottenere i dati del dashboard resilience"""
    try:
        if session.get('config', {}).get('dashboard_type') != 'resilience':
            return jsonify({'success': False, 'error': 'Dashboard type mismatch'})
            
        job_status = job_manager.get_status()
        if job_status['status'] != 'completed' or not job_status['result'] or not job_status['result']['success']:
            return jsonify({'success': False, 'error': 'Nessun dato disponibile'})
        
        analysis_data = job_status['result']['data']
        
        # Calcola aggregated score per resilience usando solo individual_assets
        total_weighted_score = 0
        total_weight = 0
        
        # Processa solo asset individuali (inclusi backup jobs)
        for asset_id, asset_data in analysis_data.get('individual_assets', {}).items():
            simulation_data = asset_data.get('simulation_data', [])
            config_used = asset_data.get('config_used', {})
            
            if simulation_data:
                # Usa l'ultimo punto della simulazione
                latest = simulation_data[-1]
                score = latest.get('resilience_score', 0)
                
                # Peso basato su w_rpo e w_success dal config_used
                weights = config_used.get('weights', {'w_rpo': 0.6, 'w_success': 0.4})
                weight = weights.get('w_rpo', 0.6) + weights.get('w_success', 0.4)  # Somma dei pesi come peso totale
                
                total_weighted_score += score * weight
                total_weight += weight
                
        aggregated_score = total_weighted_score / total_weight if total_weight > 0 else 0
        
        return jsonify({
            'success': True,
            'data': analysis_data,
            'aggregated_score': aggregated_score
        })
        
    except Exception as e:
        logger.error(f"Errore nel recupero dati resilience dashboard: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/availability/start_analysis', methods=['POST'])
def availability_start_analysis():
    """Avvia l'analisi availability"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Nessun dato ricevuto'})
        
        # Imposta il tipo di dashboard
        data['dashboard_type'] = 'availability'
        session['config'] = data
        session['config']['dashboard_type'] = 'availability'
        
        # Avvia il job di analisi
        job_id = job_manager.start_analysis(data, "availability")
        
        return jsonify({'success': True, 'job_id': job_id})
        
    except Exception as e:
        logger.error(f"Errore nell'avvio analisi availability: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/availability/analysis_progress')
def availability_analysis_progress():
    """Verifica il progresso dell'analisi availability"""
    try:
        progress_data = {
            'status': job_manager.job_status,
            'progress': job_manager.job_progress
        }
        
        if job_manager.job_status == "completed" and job_manager.job_result:
            progress_data['result'] = job_manager.job_result
        elif job_manager.job_status == "failed" and job_manager.job_result:
            progress_data['error'] = job_manager.job_result.get('error', 'Errore sconosciuto')
        
        return jsonify(progress_data)
        
    except Exception as e:
        logger.error(f"Errore nel controllo progresso availability: {e}")
        return jsonify({
            'status': 'failed',
            'progress': 0,
            'error': str(e)
        })

@app.route('/resilience/start_analysis', methods=['POST'])
def resilience_start_analysis():
    """Avvia l'analisi resilience"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Nessun dato ricevuto'})
        
        # Imposta il tipo di dashboard  
        data['dashboard_type'] = 'resilience'
        session['config'] = data
        session['config']['dashboard_type'] = 'resilience'
        
        # Avvia il job di analisi
        job_id = job_manager.start_analysis(data, "resilience")
        
        return jsonify({'success': True, 'job_id': job_id})
        
    except Exception as e:
        logger.error(f"Errore nell'avvio analisi resilience: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/resilience/analysis_progress')
def resilience_analysis_progress():
    """Verifica il progresso dell'analisi resilience"""
    try:
        progress_data = {
            'status': job_manager.job_status,
            'progress': job_manager.job_progress
        }
        
        if job_manager.job_status == "failed" and job_manager.job_result:
            progress_data['error'] = job_manager.job_result.get('error', 'Errore sconosciuto')
        
        return jsonify(progress_data)
        
    except Exception as e:
        logger.error(f"Errore nel controllo progresso: {e}")
        return jsonify({
            'status': 'failed',
            'progress': 0,
            'error': str(e)
        })

@app.route('/resilience/get_dashboard_data')
def get_resilience_dashboard_data():
    """Carica i dati per il dashboard resilience"""
    try:
        # Controlla se ci sono risultati dell'analisi
        if job_manager.job_result and job_manager.job_result.get('success'):
            analysis_data = job_manager.job_result['data']
            
            # Estrai le informazioni necessarie per il dashboard
            dashboard_data = {
                'simulation_period': analysis_data.get('simulation_period', {}),
                'backup_jobs': analysis_data.get('backup_jobs', {}),
                'individual_assets': analysis_data.get('individual_assets', {}),
                'aggregated_scores': analysis_data.get('aggregated_scores', {}),
                'configuration': analysis_data.get('configuration', {})
            }
            
            return jsonify({'success': True, 'data': dashboard_data})
        else:
            return jsonify({
                'success': False, 
                'error': 'Nessun dato di analisi disponibile. Esegui prima un\'analisi.'
            })
            
    except Exception as e:
        logger.error(f"Errore nel caricamento dati dashboard: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/resilience/get_backup_jobs')
def get_resilience_backup_jobs():
    """Carica i backup jobs disponibili per la configurazione"""
    try:
        # Prendi dalla storage o da una configurazione predefinita
        storage_manager = StorageManager(
            connection_string=DATABASE_CONFIG['connection_string'],
            database_name=DATABASE_CONFIG['database_name']
        )
        storage_manager.connect()
        
        # Cerca backup jobs nel database
        backup_jobs = storage_manager.get_assets_by_type(asset_type="acronis_backup_job")
        logger.info(f"Backup jobs trovati con type='acronis_backup_job': {len(backup_jobs)}")
        
        # Se non trova backup jobs, prova con altri asset
        if len(backup_jobs) == 0:
            # Cerca asset che potrebbero essere backup jobs
            all_assets = list(storage_manager.database['assets'].find())
            backup_jobs = [asset for asset in all_assets if 
                          asset.get('name', '').lower().find('backup') != -1 or
                          asset.get('type', '') == 'backup' or
                          asset.get('service_type', '') == 'backup']
            logger.info(f"Asset con 'backup' nel nome o tipo: {len(backup_jobs)}")
        
        # Se ancora non ci sono, crea dati di esempio
        if len(backup_jobs) == 0:
            backup_jobs = [
                {
                    '_id': 'backup_job_1',
                    'name': 'Daily VM Backup',
                    'job_name': 'Daily VM Backup',
                    'type': 'backup_job',
                    'backup_type': 'VM',
                    'schedule': 'daily'
                },
                {
                    '_id': 'backup_job_2', 
                    'name': 'Weekly Database Backup',
                    'job_name': 'Weekly Database Backup',
                    'type': 'backup_job',
                    'backup_type': 'Database',
                    'schedule': 'weekly'
                },
                {
                    '_id': 'backup_job_3',
                    'name': 'File Server Backup',
                    'job_name': 'File Server Backup', 
                    'type': 'backup_job',
                    'backup_type': 'File',
                    'schedule': 'daily'
                }
            ]
            logger.info("Utilizzando backup jobs di esempio")
        
        backup_job_list = []
        
        for job in backup_jobs:
            job_name = job.get('job_name', job.get('name', f"BackupJob_{job.get('_id', 'unknown')}"))
            
            backup_job_list.append({
                'id': str(job.get('_id')),
                'name': job_name,
                'description': job.get('description', f'Backup job {job_name}'),
                'backup_type': job.get('backup_type', job.get('data', {}).get('backup_type', 'unknown')),
                'schedule': job.get('schedule', 'unknown'),
                'type': job.get('type', 'backup_job')
            })
        
        storage_manager.disconnect()
        logger.info(f"Trovati {len(backup_job_list)} backup jobs")
        return jsonify({'success': True, 'backup_jobs': backup_job_list})
        
    except Exception as e:
        logger.error(f"Errore nel caricamento backup jobs: {e}")
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
