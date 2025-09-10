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
    Applica i Test 1, mR, Saturazione, Test 4, Test 7 e Test 8.
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
            "stato": f"🔴 CRITICO - Test 1: Violazione Limiti",
            "score": 0.1,
            "test_fallito": "Test 1",
            "punto_critico": True,
            "dettagli_anomalia": {
                "test_name": "Test 1 - Violazione Limiti",
                "valore_attuale": valore,
                "limite_violato": limite_violato,
                "limite_valore": round(limite_valore, 2),
                "descrizione": f"Valore {valore:.1f}% oltrepassa {limite_violato} ({limite_valore:.1f}%)",
                "teoria": "Evento singolo anomalo rilevato."
            },
            "warning_level": "critical"
        })
        return result
    
    # === TEST mR: VIOLAZIONE LIMITE MOVING RANGE ===
    mr_value = abs(valore - valore_precedente)
    if mr_value > ucl_mr:
        result.update({
            "stato": f"🔴 CRITICO - Test mR: Variabilità Eccessiva",
            "score": 0.2,
            "test_fallito": "Test mR",
            "punto_critico": True,
            "dettagli_anomalia": {
                "test_name": "Test mR - Variabilità Eccessiva",
                "valore_attuale": valore,
                "valore_precedente": valore_precedente,
                "moving_range": round(mr_value, 2),
                "limite_mr": round(ucl_mr, 2),
                "descrizione": f"Moving Range {mr_value:.1f}% supera limite {ucl_mr:.1f}%",
                "teoria": "Variabilità eccessiva tra punti consecutivi."
            },
            "warning_level": "critical"
        })
        return result
    
    # === TEST SATURAZIONE: VALORE AL 100% ===
    if valore >= 100:
        result.update({
            "stato": f"🔴 CRITICO - Test Saturazione: Risorsa al Limite",
            "score": 0.0,
            "test_fallito": "Saturazione",
            "punto_critico": True,
            "dettagli_anomalia": {
                "test_name": "Test Saturazione - Risorsa al Limite",
                "valore_attuale": valore,
                "descrizione": f"Risorsa saturata al {valore:.1f}%",
                "teoria": "Risorsa al limite fisico massimo."
            },
            "warning_level": "critical"
        })
        return result
    
    # === TEST 4: RUN TEST (7, 8 o 9 punti consecutivi stesso lato media) ===
    if len(cronologia_completa) >= 7:
        # Controlla per 9, 8, poi 7 punti consecutivi (dal più lungo al più corto)
        for run_length in [9, 8, 7]:
            if len(cronologia_completa) >= run_length:
                last_points = cronologia_completa[-run_length:]
                above_cl = all(p > cl for p in last_points)
                below_cl = all(p < cl for p in last_points)
                
                if above_cl or below_cl:
                    direction = "sopra" if above_cl else "sotto"
                    performance_change = "miglioramento" if (above_cl and cl < 50) or (below_cl and cl > 50) else "peggioramento"
                    result.update({
                        "stato": f"🟠 ATTENZIONE - Test 4: Run Above/Below Centerline",
                        "score": 0.4,
                        "test_fallito": "Test 4",
                        "recalculate_baseline": True,
                        "punti_coinvolti": list(range(-run_length, 0)),
                        "dettagli_anomalia": {
                            "test_name": "Test 4 - Run Above/Below Centerline",
                            "valore_attuale": valore,
                            "direzione": direction,
                            "media_centrale": round(cl, 2),
                            "punti_coinvolti": last_points,
                            "run_length": run_length,
                            "descrizione": f"{run_length} punti consecutivi {direction} linea centrale {cl:.1f}%",
                            "teoria": f"Media del processo si sta spostando - prestazioni in {performance_change}."
                        },
                        "warning_level": "warning"
                    })
                    return result
    
    # === TEST 7: OSCILLATORY TREND TEST (14 punti alternati sopra/sotto) ===
    if len(cronologia_completa) >= 14:
        last_14 = cronologia_completa[-14:]
        
        # Verifica pattern oscillatorio: p1<p2>p3<p4>p5<p6>p7<p8>p9<p10>p11<p12>p13<p14
        pattern1 = all(
            (last_14[i] < last_14[i+1] if i % 2 == 0 else last_14[i] > last_14[i+1])
            for i in range(13)
        )
        
        # Verifica pattern oscillatorio inverso: p1>p2<p3>p4<p5>p6<p7>p8<p9>p10<p11>p12<p13>p14
        pattern2 = all(
            (last_14[i] > last_14[i+1] if i % 2 == 0 else last_14[i] < last_14[i+1])
            for i in range(13)
        )
        
        if pattern1 or pattern2:
            pattern_type = "crescente-decrescente" if pattern1 else "decrescente-crescente"
            result.update({
                "stato": f"🟠 ATTENZIONE - Test 7: Oscillatory Trend",
                "score": 0.4,
                "test_fallito": "Test 7",
                "recalculate_baseline": True,
                "punti_coinvolti": list(range(-14, 0)),  # Ultimi 14 punti
                "dettagli_anomalia": {
                    "test_name": "Test 7 - Oscillatory Trend",
                    "valore_attuale": valore,
                    "pattern_type": pattern_type,
                    "punti_coinvolti": last_14,
                    "valore_iniziale": round(last_14[0], 2),
                    "valore_finale": round(last_14[-1], 2),
                    "descrizione": f"14 osservazioni successive alternanti: {last_14[0]:.1f}% → {last_14[-1]:.1f}%",
                    "teoria": "Tendenza sistematica nel processo non attribuibile a comportamento normale."
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
                "stato": f"🟠 ATTENZIONE - Test 8: Linear Trend",
                "score": 0.4,
                "test_fallito": "Test 8",
                "recalculate_baseline": True,
                "punti_coinvolti": list(range(-6, 0)),  # Ultimi 6 punti
                "dettagli_anomalia": {
                    "test_name": "Test 8 - Linear Trend",
                    "valore_attuale": valore,
                    "direzione": direction,
                    "punti_coinvolti": last_6,
                    "valore_iniziale": round(last_6[0], 2),
                    "valore_finale": round(last_6[-1], 2),
                    "descrizione": f"6 osservazioni successive monotone {direction}: {last_6[0]:.1f}% → {last_6[-1]:.1f}%",
                    "teoria": f"Causa eccezionale determina {'incremento' if direction == 'crescente' else 'decremento'} delle prestazioni."
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
                "stato": f"🟡 ALLERTA - Test 2: Pre-allarme Shift",
                "score": 0.6,
                "test_fallito": "Test 2",
                "punto_critico": True,
                "punti_coinvolti": list(range(-3, 0)),  # Ultimi 3 punti
                "dettagli_anomalia": {
                    "test_name": "Test 2 - Pre-allarme Shift",
                    "valore_attuale": valore,
                    "direzione": direction,
                    "soglia_2sigma": round(threshold, 2),
                    "punti_coinvolti": last_3,
                    "descrizione": f"2 di 3 punti oltre 2σ {direction} media (soglia {threshold:.1f}%)",
                    "teoria": "Pattern che precede spesso uno shift del processo."
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
                "stato": f"🟡 ALLERTA - Test 3: Variabilità Aumentata",
                "score": 0.7,
                "test_fallito": "Test 3",
                "punto_critico": True,
                "punti_coinvolti": list(range(-5, 0)),  # Ultimi 5 punti
                "dettagli_anomalia": {
                    "test_name": "Test 3 - Variabilità Aumentata",
                    "valore_attuale": valore,
                    "direzione": direction,
                    "soglia_1sigma": round(threshold, 2),
                    "punti_coinvolti": last_5,
                    "descrizione": f"4 di 5 punti oltre 1σ {direction} media (soglia {threshold:.1f}%)",
                    "teoria": "Processo con variabilità elevata rilevata."
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
