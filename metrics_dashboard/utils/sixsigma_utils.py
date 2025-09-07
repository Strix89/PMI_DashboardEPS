#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utilities per l'applicazione Six Sigma SPC
Funzioni helper per il monitoraggio statistico delle metriche
"""

from pymongo import MongoClient
import numpy as np

# --- CONFIGURAZIONE ---
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB = "sixsigma_monitoring"
MONGO_COLLECTION = "metrics_advanced_test"

GIORNI_BASELINE_CONFIG = 3
BASELINE_DATA_POINTS = GIORNI_BASELINE_CONFIG * 24 * 60

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
    Applica i Test 1, mR, Saturazione, Test 4 e Test 8.
    Versione estesa per implementazione graduale dei test SPC.
    """
    # Aggiungi il valore corrente alla cronologia per i test
    cronologia_completa = cronologia + [valore]
    
    # Calcola le zone per i test statistici
    cl = baseline["cl_x"]
    ucl_x = baseline["ucl_x"]
    lcl_x = baseline["lcl_x"]
    ucl_mr = baseline["ucl_mr"]
    
    # Struttura del risultato
    result = {
        "stato": "In Controllo",
        "score": 1.0,
        "dettagli_anomalia": None,
        "recalculate_baseline": False,
        "warning_level": "normal",  # normal, warning, critical
        "test_fallito": None,       # Quale test specifico è fallito
        "punto_critico": False,     # Se questo punto deve essere colorato di rosso
        "punti_coinvolti": []       # Indici dei punti coinvolti nel pattern
    }
    
    # === TEST 1: VIOLAZIONE LIMITI X (Priorità Altissima) ===
    if not (lcl_x <= valore <= ucl_x):
        limite_violato = "UCL" if valore > ucl_x else "LCL"
        limite_valore = ucl_x if valore > ucl_x else lcl_x
        
        result.update({
            "stato": f"🔴 CRITICO - Test 1: Violazione Limite X",
            "score": 0.1,
            "test_fallito": "Test 1",
            "punto_critico": True,
            "dettagli_anomalia": {
                "test_name": "Test 1 - Violazione Limite X",
                "valore_attuale": valore,
                "limite_violato": limite_violato,
                "limite_valore": round(limite_valore, 2),
                "descrizione": f"Punto fuori controllo: {valore}% oltrepassa {limite_violato} ({limite_valore:.2f}%)",
                "teoria": "Causa Speciale: Evento singolo anomalo. Possibili cause: errore di misurazione, malfunzionamento sistema, picco temporaneo di carico, errore operativo."
            },
            "warning_level": "critical"
        })
        return result
    
    # === TEST mR: VIOLAZIONE LIMITE MOVING RANGE ===
    mr_value = abs(valore - valore_precedente)
    if mr_value > ucl_mr:
        result.update({
            "stato": f"🔴 CRITICO - Test mR: Alta Variabilità",
            "score": 0.2,
            "test_fallito": "Test mR",
            "punto_critico": True,
            "dettagli_anomalia": {
                "test_name": "Test mR - Alta Variabilità",
                "valore_attuale": valore,
                "valore_precedente": valore_precedente,
                "moving_range": round(mr_value, 2),
                "limite_mr": round(ucl_mr, 2),
                "descrizione": f"Variabilità eccessiva: mR={mr_value:.2f}% supera UCL_mR={ucl_mr:.2f}%",
                "teoria": "Variabilità Eccessiva: Due punti consecutivi troppo distanti indicano instabilità del processo. Possibili cause: cambio improvviso delle condizioni operative, instabilità hardware, interferenze esterne."
            },
            "warning_level": "critical"
        })
        return result
    
    # === TEST SATURAZIONE: VALORE AL 100% ===
    if valore >= 100:
        result.update({
            "stato": f"🔴 CRITICO - Saturazione Risorsa",
            "score": 0.0,
            "test_fallito": "Saturazione",
            "punto_critico": True,
            "dettagli_anomalia": {
                "test_name": "Saturazione Risorsa",
                "valore_attuale": valore,
                "descrizione": f"Risorsa saturata al {valore}%",
                "teoria": "Saturazione Completa: La risorsa ha raggiunto il limite fisico massimo. Richiede intervento immediato per evitare degrado delle performance o blocco del sistema."
            },
            "warning_level": "critical"
        })
        return result
    
    # === TEST 4: RUN TEST (8 punti consecutivi stesso lato media) ===
    if len(cronologia_completa) >= 8:
        last_8 = cronologia_completa[-8:]
        above_cl = all(p > cl for p in last_8)
        below_cl = all(p < cl for p in last_8)
        
        if above_cl or below_cl:
            direction = "sopra" if above_cl else "sotto"
            result.update({
                "stato": f"🟠 ATTENZIONE - Test 4: Run Test",
                "score": 0.4,
                "test_fallito": "Test 4",
                "recalculate_baseline": True,
                "punti_coinvolti": list(range(-8, 0)),  # Ultimi 8 punti
                "dettagli_anomalia": {
                    "test_name": "Test 4 - Run Test",
                    "valore_attuale": valore,
                    "direzione": direction,
                    "media_centrale": round(cl, 2),
                    "punti_coinvolti": last_8,
                    "descrizione": f"8 punti consecutivi {direction} la media (CL={cl:.2f}%)",
                    "teoria": "Shift Sistematico: Il processo è cambiato permanentemente di livello. Possibili cause: nuovo operatore, cambio materiale, regolazione macchina, nuovo lotto di produzione."
                },
                "warning_level": "warning"
            })
            return result
    
    # === TEST 8: TREND LINEARE (6 punti consecutivi crescenti/decrescenti) ===
    if len(cronologia_completa) >= 6:
        last_6 = cronologia_completa[-6:]
        increasing = all(last_6[i] > last_6[i-1] for i in range(1, len(last_6)))
        decreasing = all(last_6[i] < last_6[i-1] for i in range(1, len(last_6)))
        
        if increasing or decreasing:
            direction = "crescente" if increasing else "decrescente"
            result.update({
                "stato": f"🟠 ATTENZIONE - Test 8: Trend Lineare",
                "score": 0.4,
                "test_fallito": "Test 8",
                "recalculate_baseline": True,
                "punti_coinvolti": list(range(-6, 0)),  # Ultimi 6 punti
                "dettagli_anomalia": {
                    "test_name": "Test 8 - Trend Lineare",
                    "valore_attuale": valore,
                    "direzione": direction,
                    "punti_coinvolti": last_6,
                    "valore_iniziale": round(last_6[0], 2),
                    "valore_finale": round(last_6[-1], 2),
                    "descrizione": f"Trend {direction}: {last_6[0]:.1f}% → {last_6[-1]:.1f}%",
                    "teoria": "Deriva del Processo: Trend sistematico nel tempo. Possibili cause: usura attrezzatura, deriva termica, consumo materiale, cambiamento graduale delle condizioni operative."
                },
                "warning_level": "warning"
            })
            return result
    
    # === TEST 2: ZONA A (2 su 3 punti oltre 2σ) ===
    if len(cronologia_completa) >= 3:
        # Calcola le zone sigma
        sigma = (ucl_x - cl) / 3
        zona_a_upper = cl + 2 * sigma  # 2σ sopra media
        zona_a_lower = cl - 2 * sigma  # 2σ sotto media
        
        last_3 = cronologia_completa[-3:]
        beyond_2sigma_upper = sum(1 for p in last_3 if p > zona_a_upper)
        beyond_2sigma_lower = sum(1 for p in last_3 if p < zona_a_lower)
        
        if beyond_2sigma_upper >= 2 or beyond_2sigma_lower >= 2:
            direction = "sopra" if beyond_2sigma_upper >= 2 else "sotto"
            threshold = zona_a_upper if beyond_2sigma_upper >= 2 else zona_a_lower
            
            result.update({
                "stato": f"🟡 ALLERTA - Test 2: Zona A",
                "score": 0.6,
                "test_fallito": "Test 2",
                "punto_critico": True,
                "punti_coinvolti": list(range(-3, 0)),  # Ultimi 3 punti
                "dettagli_anomalia": {
                    "test_name": "Test 2 - Zona A",
                    "valore_attuale": valore,
                    "direzione": direction,
                    "soglia_2sigma": round(threshold, 2),
                    "punti_coinvolti": last_3,
                    "descrizione": f"2 di 3 punti oltre 2σ {direction} la media (soglia: {threshold:.2f}%)",
                    "teoria": "Pre-allarme Shift: Pattern che precede spesso uno shift del processo. Monitorare attentamente i prossimi punti."
                },
                "warning_level": "pending"
            })
            return result
    
    # === TEST 3: ZONA B (4 su 5 punti oltre 1σ) ===
    if len(cronologia_completa) >= 5:
        # Calcola le zone sigma
        sigma = (ucl_x - cl) / 3
        zona_b_upper = cl + 1 * sigma  # 1σ sopra media
        zona_b_lower = cl - 1 * sigma  # 1σ sotto media
        
        last_5 = cronologia_completa[-5:]
        beyond_1sigma_upper = sum(1 for p in last_5 if p > zona_b_upper)
        beyond_1sigma_lower = sum(1 for p in last_5 if p < zona_b_lower)
        
        if beyond_1sigma_upper >= 4 or beyond_1sigma_lower >= 4:
            direction = "sopra" if beyond_1sigma_upper >= 4 else "sotto"
            threshold = zona_b_upper if beyond_1sigma_upper >= 4 else zona_b_lower
            
            result.update({
                "stato": f"🟡 ALLERTA - Test 3: Zona B",
                "score": 0.7,
                "test_fallito": "Test 3",
                "punto_critico": True,
                "punti_coinvolti": list(range(-5, 0)),  # Ultimi 5 punti
                "dettagli_anomalia": {
                    "test_name": "Test 3 - Zona B",
                    "valore_attuale": valore,
                    "direzione": direction,
                    "soglia_1sigma": round(threshold, 2),
                    "punti_coinvolti": last_5,
                    "descrizione": f"4 di 5 punti oltre 1σ {direction} la media (soglia: {threshold:.2f}%)",
                    "teoria": "Variabilità Aumentata: Il processo mostra variabilità elevata. Possibili cause: condizioni instabili, materiale non uniforme, settaggio non ottimale."
                },
                "warning_level": "pending"
            })
            return result
    
    # === TUTTI I TEST PASSATI - PROCESSO IN CONTROLLO ===
    # === TUTTI I TEST PASSATI - PROCESSO IN CONTROLLO ===
    result.update({
        "stato": "✅ In Controllo",
        "score": 1.0,
        "test_fallito": None,
        "punto_critico": False,
        "warning_level": "normal"
    })
    
    return result


def check_pending_failures(cronologia_completa, cl, sigma, ucl_mr, valore_precedente):
    """
    Funzione semplificata per il Test 1 - non utilizzata per ora
    """
    return None
