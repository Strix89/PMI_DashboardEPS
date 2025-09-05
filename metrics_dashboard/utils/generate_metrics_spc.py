#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Questo script simula la raccolta di metriche di performance (CPU, RAM, I/O Wait)
e le inserisce in un database MongoDB.

È progettato per scopi accademici e genera un dataset strutturato in due fasi:
1.  FASE BASELINE: Un periodo di dati "stabili" (solo variazione per causa comune)
    per calcolare i limiti di controllo in modo affidabile.
2.  FASE TEST: Un periodo in cui vengono iniettate programmaticamente diverse
    tipologie di "cause eccezionali" (anomalie) per validare un motore di
    rilevamento basato su SPC (Statistical Process Control).
"""

import pymongo
import datetime
import random
import numpy as np
from tqdm import tqdm

# --- CONFIGURAZIONE GLOBALE ---
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB = "sixsigma_monitoring"
MONGO_COLLECTION = "metrics_advanced_test"
SVUOTA_COLLECTION_PRIMA_ESECUZIONE = True

# --- CONFIGURAZIONE SIMULAZIONE ---
NUM_MACCHINE = 3
DURATA_SIMULAZIONE_GIORNI = 15 # Aumentiamo per dare spazio a più anomalie
INTERVALLO_MINUTI = 1
GIORNI_BASELINE = 3 # Giorni di dati puliti per l'addestramento della baseline

# --- CONFIGURAZIONE ANOMALIE ---
# Probabilità generale che, ad un dato punto, inizi una sequenza anomala
PROBABILITA_INIZIO_ANOMALIA = 0.02 # 2% di probabilità ad ogni passo

# --- PROFILI DELLE MACCHINE ---
# Ogni macchina ha una sua "personalità" statistica.
# "mean" (Media): Valore medio atteso. Diventerà la Linea Centrale (CL).
# "std_dev" (Deviazione Standard, sigma): Variabilità normale. Determina l'ampiezza dei limiti di controllo.
PROFILI_MACCHINE = [
    {"machine_id": "WebServer-01", "profile": {"cpu": {"mean": 25, "std_dev": 4}, "ram": {"mean": 40, "std_dev": 6}, "io_wait": {"mean": 5, "std_dev": 1.5}}},
    {"machine_id": "Database-Server-01", "profile": {"cpu": {"mean": 60, "std_dev": 12}, "ram": {"mean": 75, "std_dev": 5}, "io_wait": {"mean": 20, "std_dev": 8}}},
    {"machine_id": "Backup-Node-01", "profile": {"cpu": {"mean": 10, "std_dev": 2}, "ram": {"mean": 20, "std_dev": 3}, "io_wait": {"mean": 2, "std_dev": 1}}}
]

# --- MOTORE DI INIEZIONE ANOMALIE ---

def clamp(valore):
    """Funzione helper per mantenere i valori percentuali tra 0 e 100."""
    return max(0.0, min(valore, 100.0))

def genera_valore_normale(profilo):
    """Genera un valore "normale" basato sul profilo, senza anomalie (solo causa comune)."""
    valore = np.random.normal(profilo["mean"], profilo["std_dev"])
    return clamp(valore)

def genera_spike(profilo):
    """
    Genera un singolo punto dato estremamente anomalo.
    OBIETTIVO: Attivare il Test 1 (Violazione Limite 3-Sigma).
    """
    media, sigma = profilo['mean'], profilo['std_dev']
    # Genera un valore molto al di fuori dei 3-sigma (tra 3.5 e 5 sigma di distanza)
    valore_anomalo = media + random.choice([-1, 1]) * random.uniform(3.5, 5) * sigma
    return [clamp(valore_anomalo)], "Test 1 - Violazione Limite 3-Sigma"

def genera_shift(profilo, lunghezza=9):
    """
    Genera una sequenza di dati con una media spostata.
    OBIETTIVO: Attivare il Test 4 (Run Test).
    """
    media, sigma = profilo['mean'], profilo['std_dev']
    # Sposta la media di circa 1.5-2 sigma in una direzione casuale
    nuova_media = media + random.choice([-1, 1]) * random.uniform(1.5, 2.0) * sigma
    valori = np.random.normal(nuova_media, sigma, lunghezza)
    return [clamp(v) for v in valori], "Test 4 - Run Test (Shift Media)"

def genera_trend(profilo, lunghezza=7):
    """
    Genera una sequenza con un andamento lineare crescente o decrescente.
    OBIETTIVO: Attivare il Test 8 (Trend Lineare).
    """
    media, sigma = profilo['mean'], profilo['std_dev']
    direzione = random.choice([-1, 1])
    # Ogni passo si sposta di una frazione di sigma per creare una pendenza
    step = sigma * random.uniform(0.4, 0.8)
    # Aggiunge un po' di rumore per rendere il trend più realistico
    valori = [clamp(media + (i * step * direzione) + np.random.normal(0, sigma/3)) for i in range(lunghezza)]
    return valori, "Test 8 - Trend Lineare"

def genera_violazione_zone(profilo):
    """
    Genera sequenze che violano i test delle zone A e B.
    OBIETTIVO: Attivare il Test 2 o il Test 3.
    """
    media, sigma = profilo['mean'], profilo['std_dev']
    direzione = random.choice([-1, 1])
    # Sceglie casualmente se generare una violazione di Zona A o Zona B
    # Test 2: 2 su 3 punti in Zona A (>2 sigma)
    if random.random() > 0.5:
        zona_a_start = media + (2.1 * sigma * direzione)
        valori = [
            clamp(zona_a_start),
            clamp(media + (0.5 * sigma * direzione)), # Un punto "normale" per interrompere la sequenza
            clamp(zona_a_start + random.uniform(0, sigma))
        ]
        return valori, "Test 2 - Violazione Zona A (2 su 3)"
    # Test 3: 4 su 5 punti in Zona B (>1 sigma)
    else:
        zona_b_start = media + (1.1 * sigma * direzione)
        valori = [
            clamp(zona_b_start + random.uniform(0, sigma*0.8)),
            clamp(zona_b_start + random.uniform(0, sigma*0.8)),
            clamp(media), # Un punto "normale"
            clamp(zona_b_start + random.uniform(0, sigma*0.8)),
            clamp(zona_b_start + random.uniform(0, sigma*0.8)),
        ]
        return valori, "Test 3 - Violazione Zona B (4 su 5)"

def genera_oscillazione(profilo, lunghezza=14):
    """
    Genera una sequenza di dati che si alterna rapidamente attorno alla media.
    OBIETTIVO: Attivare il Test 7 (Trend Oscillatorio).
    """
    media, sigma = profilo['mean'], profilo['std_dev']
    valori = [media]
    for i in range(lunghezza):
        if i % 2 == 0: # Punto alto
            valori.append(clamp(media + random.uniform(0.5, 1.5) * sigma))
        else: # Punto basso
            valori.append(clamp(media - random.uniform(0.5, 1.5) * sigma))
    return valori[1:], "Test 7 - Trend Oscillatorio"

def genera_stratificazione(profilo, lunghezza=15):
    """
    Genera una sequenza di dati "troppo stabili", tutti all'interno della Zona C.
    OBIETTIVO: Attivare il Test 6 (Stratificazione).
    """
    media, sigma = profilo['mean'], profilo['std_dev']
    # Genera valori solo entro +/- 1 sigma dalla media, usando una deviazione standard ridotta
    valori = np.random.normal(media, sigma / 2.5, lunghezza)
    return [clamp(v) for v in valori], "Test 6 - Stratificazione (Variabilità Ridotta)"

# Mappa delle funzioni per generare le anomalie in modo casuale
ANOMALY_GENERATORS = [
    genera_spike,
    genera_shift,
    genera_trend,
    genera_violazione_zone,
    genera_oscillazione,
    genera_stratificazione
]

def main():
    print("--- Avvio Generatore Dati Strutturato per Test SPC ---")
    
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        if SVUOTA_COLLECTION_PRIMA_ESECUZIONE:
            collection.delete_many({})
            print(f"✅ Collection '{MONGO_COLLECTION}' svuotata.")
        print(f"✅ Connesso a MongoDB.")
    except pymongo.errors.ConnectionFailure as e:
        print(f"❌ Errore di connessione a MongoDB: {e}"); return

    total_iterations = (DURATA_SIMULAZIONE_GIORNI * 24 * 60) // INTERVALLO_MINUTI
    baseline_end_index = (GIORNI_BASELINE * 24 * 60) // INTERVALLO_MINUTI
    
    start_time = datetime.datetime.now(datetime.timezone.utc)
    documenti_da_inserire = []
    
    print(f"Generazione di {DURATA_SIMULAZIONE_GIORNI} giorni di dati...")
    
    progress = {m['machine_id']: 0 for m in PROFILI_MACCHINE}

    with tqdm(total=total_iterations * NUM_MACCHINE) as pbar:
        while min(progress.values()) < total_iterations:
            for machine in PROFILI_MACCHINE[:NUM_MACCHINE]:
                machine_id = machine['machine_id']
                
                if progress[machine_id] >= total_iterations:
                    continue

                idx = progress[machine_id]
                timestamp = start_time + datetime.timedelta(minutes=idx * INTERVALLO_MINUTI)
                
                is_baseline = idx < baseline_end_index
                
                # Durante la fase di test, con una certa probabilità, si inietta un'anomalia
                if not is_baseline and random.random() < PROBABILITA_INIZIO_ANOMALIA:
                    anomaly_func = random.choice(ANOMALY_GENERATORS)
                    metrica_anomala = random.choice(["cpu", "ram", "io_wait"])
                    
                    valori_anomali, nome_anomalia = anomaly_func(machine['profile'][metrica_anomala])
                    
                    # Genera la sequenza anomala e la inserisce nel flusso di dati
                    for k, val_anomalo in enumerate(valori_anomali):
                        if progress[machine_id] >= total_iterations: break
                        
                        ts = start_time + datetime.timedelta(minutes=progress[machine_id] * INTERVALLO_MINUTI)
                        doc = {"timestamp": ts, "machine_id": machine_id, "metrics": {}, "phase": "test", "injected_anomaly_type": "None"}
                        
                        for metrica in ["cpu", "ram", "io_wait"]:
                            if metrica == metrica_anomala:
                                doc['metrics'][f'{metrica}_percent'] = val_anomalo
                                doc['injected_anomaly_type'] = nome_anomalia
                            else: # Le altre metriche si comportano normalmente
                                val_norm = genera_valore_normale(machine['profile'][metrica])
                                doc['metrics'][f'{metrica}_percent'] = val_norm
                        
                        documenti_da_inserire.append(doc)
                        progress[machine_id] += 1
                        pbar.update(1)
                else:
                    # Se non viene iniettata un'anomalia, genera un punto dato normale
                    phase = "baseline" if is_baseline else "test"
                    doc = {"timestamp": timestamp, "machine_id": machine_id, "metrics": {}, "phase": phase, "injected_anomaly_type": "None"}
                    for metrica in ["cpu", "ram", "io_wait"]:
                        val = genera_valore_normale(machine['profile'][metrica])
                        doc['metrics'][f'{metrica}_percent'] = val
                    
                    documenti_da_inserire.append(doc)
                    progress[machine_id] += 1
                    pbar.update(1)

    if documenti_da_inserire:
        print(f"\nInserimento di {len(documenti_da_inserire)} documenti in MongoDB...")
        # Ordina i documenti per timestamp prima dell'inserimento per garantire l'ordine
        documenti_da_inserire.sort(key=lambda x: x['timestamp'])
        collection.insert_many(documenti_da_inserire)
        print("✅ Inserimento completato.")
    
    client.close()
    print("✅ Connessione a MongoDB chiusa.")

if __name__ == "__main__":
    main()

