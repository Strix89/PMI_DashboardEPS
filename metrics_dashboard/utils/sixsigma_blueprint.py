#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Blueprint per l'applicazione Six Sigma SPC
Integrato nella dashboard principale di metrics_dashboard
"""

from flask import Blueprint, jsonify, render_template
from pymongo import MongoClient
import numpy as np

# Crea il blueprint
sixsigma_bp = Blueprint('sixsigma', __name__, url_prefix='/sixsigma', 
                       template_folder='../templates', static_folder='../static')

# --- CONFIGURAZIONE ---
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB = "sixsigma_monitoring"
MONGO_COLLECTION = "metrics_advanced_test"

GIORNI_BASELINE_CONFIG = 3
BASELINE_DATA_POINTS = GIORNI_BASELINE_CONFIG * 24 * 60

# Cache per le baseline
baseline_cache = {}

# --- MOTORE SPC ---

def get_collection():
    """Funzione helper per connettersi a MongoDB e ottenere la collection."""
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    return db[MONGO_COLLECTION]

def calcola_baseline(machine_id, metrica, baseline_cache):
    """
    Calcola e restituisce i parametri della baseline (CL, UCL, LCL) per una
    macchina e una metrica specifica, usando i dati della fase "baseline".
    """
    cache_key = f"{machine_id}_{metrica}"
    if cache_key in baseline_cache:
        return baseline_cache[cache_key]

    collection = get_collection()
    query = {"machine_id": machine_id, "phase": "baseline"}
    data = list(collection.find(query).sort("timestamp", 1).limit(BASELINE_DATA_POINTS))
    
    if len(data) < 20:
        return None

    valori = [d['metrics'][f'{metrica}_percent'] for d in data]
    
    # Calcolo dei parametri per la carta di controllo XmR
    cl_x = np.mean(valori)
    moving_ranges = [abs(valori[i] - valori[i-1]) for i in range(1, len(valori))]
    cl_mr = np.mean(moving_ranges) if moving_ranges else 0
    
    ucl_x = cl_x + 2.66 * cl_mr
    lcl_x = max(0, cl_x - 2.66 * cl_mr)
    ucl_mr = 3.268 * cl_mr

    baseline = {
        "cl_x": round(cl_x, 2),
        "ucl_x": round(ucl_x, 2),
        "lcl_x": round(lcl_x, 2),
        "cl_mr": round(cl_mr, 2),
        "ucl_mr": round(ucl_mr, 2)
    }
    baseline_cache[cache_key] = baseline
    return baseline

def monitora_nuovo_dato(valore, valore_precedente, cronologia, baseline):
    """
    Applica i test di stabilità Six Sigma e restituisce il nome del test fallito e uno score.
    """
    # Aggiungi il valore corrente alla cronologia per i test
    cronologia_completa = cronologia + [valore]
    
    # Test di Priorità Alta (eventi critici)
    if valore >= 100: 
        return "Critico - Saturazione Risorsa", 0.0
    if not (baseline["lcl_x"] <= valore <= baseline["ucl_x"]): 
        return "Critico - Violazione Limite X (Test 1)", 0.1
    if abs(valore - valore_precedente) > baseline["ucl_mr"]: 
        return "Critico - Alta Variabilità mR", 0.2
    
    # Calcola le zone per i test statistici
    cl = baseline["cl_x"]
    sigma = (baseline["ucl_x"] - baseline["cl_x"]) / 2.66  # Stima della deviazione standard
    
    # Test 2: 2 su 3 punti consecutivi in Zona A (oltre 2 sigma)
    if len(cronologia_completa) >= 3:
        last_3 = cronologia_completa[-3:]
        zona_a_violations = 0
        for val in last_3:
            if abs(val - cl) > 2 * sigma:
                zona_a_violations += 1
        if zona_a_violations >= 2:
            return "Attenzione - Test 2 Zona A (2 su 3)", 0.4
    
    # Test 3: 4 su 5 punti consecutivi in Zona B (oltre 1 sigma)
    if len(cronologia_completa) >= 5:
        last_5 = cronologia_completa[-5:]
        zona_b_violations = 0
        for val in last_5:
            if abs(val - cl) > 1 * sigma:
                zona_b_violations += 1
        if zona_b_violations >= 4:
            return "Attenzione - Test 3 Zona B (4 su 5)", 0.5
    
    # Test 4: Run Test (8 punti consecutivi sopra/sotto CL)
    if len(cronologia_completa) >= 8:
        last_8 = cronologia_completa[-8:]
        if all(p > cl for p in last_8) or all(p < cl for p in last_8):
            return "Attenzione - Run Test (Test 4)", 0.5
    
    # Test 6: Stratificazione (15 punti consecutivi nella Zona C)
    if len(cronologia_completa) >= 15:
        last_15 = cronologia_completa[-15:]
        if all(abs(val - cl) < sigma for val in last_15):
            return "Attenzione - Test 6 Stratificazione", 0.6
    
    # Test 7: Trend Oscillatorio (14 punti alternati)
    if len(cronologia_completa) >= 14:
        last_14 = cronologia_completa[-14:]
        alternating = True
        for i in range(1, len(last_14)):
            if (last_14[i] > last_14[i-1]) == (last_14[i-1] > last_14[i-2] if i > 1 else True):
                alternating = False
                break
        if alternating:
            return "Attenzione - Test 7 Trend Oscillatorio", 0.7
    
    # Test 8: Trend Lineare (6 punti consecutivi crescenti/decrescenti)
    if len(cronologia_completa) >= 6:
        last_6 = cronologia_completa[-6:]
        if all(last_6[i] > last_6[i-1] for i in range(1, len(last_6))) or \
           all(last_6[i] < last_6[i-1] for i in range(1, len(last_6))):
            return "Attenzione - Test 8 Trend Lineare", 0.4
    
    return "In Controllo", 1.0

# --- ROUTES ---

@sixsigma_bp.route('/')
def index():
    """Renderizza la pagina principale della dashboard Six Sigma."""
    return render_template('sixsigma_index.html')

@sixsigma_bp.route('/api/macchine')
def get_macchine():
    """API che restituisce la lista delle macchine uniche presenti nel database."""
    collection = get_collection()
    macchine = collection.distinct("machine_id")
    return jsonify(macchine)

@sixsigma_bp.route('/api/baseline/<machine_id>')
def get_baseline(machine_id):
    """API per caricare tutti i parametri di baseline per una macchina selezionata."""
    baselines = {
        "cpu": calcola_baseline(machine_id, "cpu"),
        "ram": calcola_baseline(machine_id, "ram"),
        "io_wait": calcola_baseline(machine_id, "io_wait")
    }
    if any(b is None for b in baselines.values()):
        return jsonify({"error": "Dati insufficienti per calcolare la baseline"}), 500
    return jsonify(baselines)

@sixsigma_bp.route('/api/data/<machine_id>/<int:offset>')
def get_next_data(machine_id, offset):
    """
    API che simula il "tempo reale": prende il prossimo dato di test dal DB,
    lo analizza e restituisce il risultato completo.
    """
    collection = get_collection()
    
    history_limit = 20
    skip_offset = BASELINE_DATA_POINTS + offset
    start_skip = max(0, skip_offset - history_limit)
    
    cursor = collection.find({"machine_id": machine_id}).sort("timestamp", 1).skip(start_skip).limit(history_limit + 1)
    dati = list(cursor)

    if len(dati) <= 1:
        return jsonify({"error": "Fine dei dati di simulazione"}), 404
    
    dato_corrente = dati[-1]
    cronologia_dati = dati[:-1]
    
    scores, stati, moving_ranges = {}, {}, {}
    
    for metrica in ["cpu", "ram", "io_wait"]:
        baseline = baseline_cache.get(f"{machine_id}_{metrica}")
        if not baseline:
            return jsonify({"error": f"Baseline per {metrica} non trovata. Caricarla prima."}), 500

        valore_corrente = dato_corrente['metrics'][f'{metrica}_percent']
        cronologia_metrica = [d['metrics'][f'{metrica}_percent'] for d in cronologia_dati]
        valore_precedente = cronologia_metrica[-1] if cronologia_metrica else 0
        
        stato, score = monitora_nuovo_dato(valore_corrente, valore_precedente, cronologia_metrica, baseline)
        scores[metrica] = score
        stati[metrica] = stato
        moving_ranges[metrica] = round(abs(valore_corrente - valore_precedente), 2)

    # Calcolo del P_score aggregato
    p_score = round(np.mean(list(scores.values())), 3)

    response = {
        "timestamp": dato_corrente['timestamp'].isoformat(),
        "metrics": dato_corrente['metrics'],
        "moving_ranges": moving_ranges,
        "scores": scores,
        "stati": stati,
        "p_score": p_score,
        "next_offset": offset + 1
    }
    return jsonify(response)
