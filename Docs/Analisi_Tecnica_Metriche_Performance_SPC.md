# Analisi Tecnica: Sistema di Calcolo Metriche Performance e SPC

## 📋 Panoramica del Sistema

Il modulo **Six Sigma SPC (Statistical Process Control)** del progetto `metrics_dashboard` implementa un sistema completo di monitoraggio statistico delle performance per l'infrastruttura IT. Il sistema utilizza carte di controllo XmR (Individual & Moving Range) per rilevare anomalie nelle metriche di CPU, RAM e I/O Wait attraverso 9 test statistici avanzati.

## 🏗️ Architettura del Sistema

### Componenti Principali

#### 1. **Backend - Motore SPC** (`utils/sixsigma_utils.py`)
- **Funzione**: Calcolo baseline, test statistici, scoring
- **Database**: MongoDB `sixsigma_monitoring.metrics_advanced_test`
- **Algoritmo**: Carte di controllo XmR con 9 test SPC

#### 2. **Frontend - Dashboard Interattiva** (`templates/sixsigma_dashboard.html`)
- **Librerie**: Chart.js con plugin annotation
- **Visualizzazione**: Grafici X e mR real-time con colorazione dinamica
- **Controlli**: Play/Pause, zoom, selezione macchina

#### 3. **JavaScript Engine** (`static/js/sixsigma_script.js`)
- **Funzione**: Simulazione temporale, aggiornamento grafici, gestione stati
- **Comunicazione**: API REST con backend Flask
- **Features**: Auto-refresh, gestione anomalie, log separati

#### 4. **Generatore Dati di Test** (`utils/generate_metrics_spc.py`)
- **Funzione**: Simulazione dataset con anomalie programmate
- **Fasi**: Baseline (3 giorni) + Test (12 giorni) con iniezione anomalie
- **Anomalie**: 6 tipologie diverse per validare tutti i test SPC

## 🔬 Algoritmi di Calcolo

### Formula Baseline XmR

Il sistema calcola i parametri di controllo utilizzando la teoria delle carte XmR:

```python
# Calcolo parametri baseline da dati storici (3 giorni = 4320 punti)
def calcola_baseline(machine_id, metrica, baseline_cache):
    # 1. Recupera dati fase "baseline" da MongoDB
    data = collection.find({"machine_id": machine_id, "phase": "baseline"})
    valori = [d['metrics'][f'{metrica}_percent'] for d in data]
    
    # 2. Calcola Centro Linea (CL) - Media del processo
    cl_x = np.mean(valori)
    
    # 3. Calcola Moving Range per ogni coppia consecutiva
    moving_ranges = [abs(valori[i] - valori[i-1]) for i in range(1, len(valori))]
    cl_mr = np.mean(moving_ranges)
    
    # 4. Calcola Limiti di Controllo (±3σ)
    ucl_x = cl_x + 2.66 * cl_mr    # Upper Control Limit X
    lcl_x = max(0, cl_x - 2.66 * cl_mr)  # Lower Control Limit X (non negativo)
    ucl_mr = 3.268 * cl_mr         # Upper Control Limit mR
    
    return {
        "cl_x": cl_x,      # Centro Linea X
        "ucl_x": ucl_x,    # Limite Superiore X  
        "lcl_x": lcl_x,    # Limite Inferiore X
        "cl_mr": cl_mr,    # Centro Linea mR
        "ucl_mr": ucl_mr   # Limite Superiore mR
    }
```

### Test Statistici Implementati

Il sistema implementa 9 test SPC con priorità e scoring differenziati:

#### **Test Critici (Score 0.0-0.2)**

##### Test 1: Violazione Limiti 3-Sigma
```python
# Priorità: ALTISSIMA - Evento singolo anomalo
if not (lcl_x <= valore <= ucl_x):
    return {
        "stato": "🔴 CRITICO - Test 1: Violazione Limiti",
        "score": 0.1,
        "punto_critico": True,
        "colore": "rosso"
    }
```

##### Test mR: Variabilità Eccessiva
```python
# Controlla variabilità tra punti consecutivi
mr_value = abs(valore - valore_precedente)
if mr_value > ucl_mr:
    return {
        "stato": "🔴 CRITICO - Test mR: Variabilità Eccessiva", 
        "score": 0.2,
        "punto_critico": True,
        "colore": "rosso"
    }
```

##### Test Saturazione: Risorsa al Limite
```python
# Rilevamento saturazione fisica risorsa
if valore >= 100:
    return {
        "stato": "🔴 CRITICO - Test Saturazione: Risorsa al Limite",
        "score": 0.0,
        "punto_critico": True,
        "colore": "rosso"
    }
```

#### **Test Statistici con Ricalcolo Baseline (Score 0.4)**

##### Test 4: Run Above/Below Centerline
```python
# 7, 8 o 9 punti consecutivi stesso lato della media
for run_length in [9, 8, 7]:
    if len(cronologia_completa) >= run_length:
        last_points = cronologia_completa[-run_length:]
        above_cl = all(p > cl for p in last_points)
        below_cl = all(p < cl for p in last_points)
        
        if above_cl or below_cl:
            return {
                "stato": "🟠 ATTENZIONE - Test 4: Run Above/Below Centerline",
                "score": 0.4,
                "recalculate_baseline": True,
                "punti_coinvolti": list(range(-run_length, 0)),
                "colore": "arancione"
            }
```

##### Test 7: Oscillatory Trend
```python
# 14 punti alternati sopra/sotto (pattern oscillatorio)
if len(cronologia_completa) >= 14:
    last_14 = cronologia_completa[-14:]
    
    # Pattern crescente-decrescente: p1<p2>p3<p4>...
    pattern1 = all(
        (last_14[i] < last_14[i+1] if i % 2 == 0 else last_14[i] > last_14[i+1])
        for i in range(13)
    )
    
    if pattern1 or pattern2:  # pattern2 = inverso
        return {
            "stato": "🟠 ATTENZIONE - Test 7: Oscillatory Trend",
            "score": 0.4,
            "recalculate_baseline": True,
            "punti_coinvolti": list(range(-14, 0)),
            "colore": "arancione"
        }
```

##### Test 8: Linear Trend
```python
# 6 punti consecutivi monotoni (crescenti o decrescenti)
if len(cronologia_completa) >= 6:
    last_6 = cronologia_completa[-6:]
    increasing = all(last_6[i] > last_6[i-1] for i in range(1, len(last_6)))
    decreasing = all(last_6[i] < last_6[i-1] for i in range(1, len(last_6)))
    
    if increasing or decreasing:
        return {
            "stato": "🟠 ATTENZIONE - Test 8: Linear Trend",
            "score": 0.4,
            "recalculate_baseline": True,
            "punti_coinvolti": list(range(-6, 0)),
            "colore": "arancione"
        }
```

#### **Test Zone (Score 0.6-0.7)**

##### Test 2: Pre-allarme Shift (Zona A)
```python
# 2 di 3 punti oltre 2σ dalla media
if len(cronologia_completa) >= 3:
    sigma = (ucl_x - cl) / 3
    zona_a_upper = cl + 2 * sigma
    zona_a_lower = cl - 2 * sigma
    
    last_3 = cronologia_completa[-3:]
    beyond_2sigma_upper = sum(1 for p in last_3 if p > zona_a_upper)
    beyond_2sigma_lower = sum(1 for p in last_3 if p < zona_a_lower)
    
    if beyond_2sigma_upper >= 2 or beyond_2sigma_lower >= 2:
        return {
            "stato": "🟡 ALLERTA - Test 2: Pre-allarme Shift",
            "score": 0.6,
            "punti_coinvolti": list(range(-3, 0)),
            "colore": "giallo"
        }
```

##### Test 3: Variabilità Aumentata (Zona B)
```python
# 4 di 5 punti oltre 1σ dalla media
if len(cronologia_completa) >= 5:
    sigma = (ucl_x - cl) / 3
    zona_b_upper = cl + 1 * sigma
    zona_b_lower = cl - 1 * sigma
    
    last_5 = cronologia_completa[-5:]
    beyond_1sigma_upper = sum(1 for p in last_5 if p > zona_b_upper)
    beyond_1sigma_lower = sum(1 for p in last_5 if p < zona_b_lower)
    
    if beyond_1sigma_upper >= 4 or beyond_1sigma_lower >= 4:
        return {
            "stato": "🟡 ALLERTA - Test 3: Variabilità Aumentata",
            "score": 0.7,
            "punti_coinvolti": list(range(-5, 0)),
            "colore": "giallo"
        }
```

### Formula P-Score Aggregato

Il sistema calcola un Performance Score ponderato utilizzando pesi configurabili:

```python
# Calcolo P-Score con pesi configurati per macchina
def calcola_p_score(scores, machine_weights):
    if machine_weights:
        # Calcolo pesato basato sulla configurazione
        weighted_sum = 0
        total_weight = 0
        
        for metrica in ["cpu", "ram", "io_wait"]:
            weight = machine_weights.get(metrica, 0)
            if weight > 0:
                weighted_sum += scores[metrica] * weight
                total_weight += weight
        
        p_score = weighted_sum / total_weight if total_weight > 0 else 0
    else:
        # Fallback: media semplice se non configurato
        p_score = np.mean(list(scores.values()))
    
    return round(p_score, 3)
```

**Pesi Default:**
- CPU: 40% (criticità alta - impatto diretto performance)
- RAM: 35% (criticità media-alta - stabilità sistema)  
- I/O Wait: 25% (criticità media - throughput applicazioni)

## 🎨 Sistema di Visualizzazione

### Colorazione Dinamica dei Punti

Il frontend applica colorazione differenziata basata sui test falliti:

```javascript
// Logica di colorazione punti nei grafici
function getPointColor(testFallito, isPuntoCritico) {
    if (testFallito === "Test 1" || testFallito === "Test mR" || testFallito === "Saturazione") {
        return {
            color: '#ff0000',      // Rosso critico
            radius: 8,
            borderWidth: 3
        };
    }
    
    if (testFallito === "Test 4" || testFallito === "Test 7" || testFallito === "Test 8") {
        return {
            color: '#ffa500',      // Arancione warning
            radius: 7,
            borderWidth: 2
        };
    }
    
    if (testFallito === "Test 2" || testFallito === "Test 3") {
        return {
            color: '#ffff00',      // Giallo allerta
            radius: 6,
            borderWidth: 2
        };
    }
    
    return {
        color: '#007bff',          // Blu normale
        radius: 4,
        borderWidth: 1
    };
}
```

### Performance Score Visuale

```javascript
// Classificazione visuale P-Score
function updateScoreDisplay(pScore) {
    const scoreElement = document.getElementById('score-value');
    
    // Rimuove classi esistenti
    scoreElement.classList.remove('score-excellent', 'score-good', 'score-poor', 'score-default');
    
    // Applica classe basata sul valore
    if (pScore > 0.8) {
        scoreElement.classList.add('score-excellent');  // Verde
    } else if (pScore > 0.5) {
        scoreElement.classList.add('score-good');       // Giallo
    } else {
        scoreElement.classList.add('score-poor');       // Rosso
    }
    
    scoreElement.querySelector('span').textContent = pScore.toFixed(3);
}
```

## 🔄 Gestione Ricalcolo Baseline

### Meccanismo di Pausa e Ricalcolo

Per i Test 4, 7 e 8 che indicano shift del processo, il sistema implementa un meccanismo di ricalcolo baseline:

```python
# 1. RILEVAMENTO PATTERN
if testFallito in ["Test 4", "Test 7", "Test 8"]:
    # Pausa il grafico per raccogliere nuovi dati
    pausedCharts[metrica] = True
    recalculateCounters[metrica] = 1
    
    # Notifica backend della pausa
    fetch(f'/sixsigma/api/pause_chart/{machine_id}/{metrica}')

# 2. RACCOLTA DATI (20 punti)
if pausedCharts[metrica]:
    recalculateCounters[metrica] += 1
    
    if recalculateCounters[metrica] >= RECALCULATE_WAIT_POINTS:
        # Avvia ricalcolo baseline
        triggerBaselineRecalculation(metrica)

# 3. RICALCOLO BASELINE
def triggerBaselineRecalculation(metrica):
    # Prende ultimi 200 punti per ricalcolo
    cursor = collection.find({"machine_id": machine_id}).sort("timestamp", -1).limit(200)
    dati = list(cursor)
    
    # Ricalcola parametri baseline
    new_baseline = calcola_baseline_from_data(dati)
    
    # Aggiorna cache e ricrea grafici
    currentBaselines[metrica] = new_baseline
    setupChartsForMetric(metrica, new_baseline)
    
    # Riattiva il grafico
    pausedCharts[metrica] = False
```

## 📊 Simulazione e Generazione Dati

### Dataset Strutturato per Test

Il generatore crea un dataset in due fasi per validare il sistema SPC:

```python
# Configurazione simulazione
DURATA_SIMULAZIONE_GIORNI = 15
GIORNI_BASELINE = 3  # Dati puliti per baseline
PROBABILITA_INIZIO_ANOMALIA = 0.02  # 2% probabilità anomalia

# Profili macchine con caratteristiche diverse
PROFILI_MACCHINE = [
    {
        "machine_id": "WebServer-01", 
        "profile": {
            "cpu": {"mean": 25, "std_dev": 4}, 
            "ram": {"mean": 40, "std_dev": 6}, 
            "io_wait": {"mean": 5, "std_dev": 1.5}
        }
    },
    {
        "machine_id": "Database-Server-01", 
        "profile": {
            "cpu": {"mean": 60, "std_dev": 12}, 
            "ram": {"mean": 75, "std_dev": 5}, 
            "io_wait": {"mean": 20, "std_dev": 8}
        }
    }
]
```

### Iniezione Anomalie Programmate

```python
# Generatori di anomalie per validare ogni test
ANOMALY_GENERATORS = [
    genera_spike,           # Test 1: Violazione Limite
    genera_shift,           # Test 4: Run Above/Below
    genera_trend,           # Test 8: Linear Trend
    genera_violazione_zone, # Test 2/3: Zone A/B
    genera_oscillazione,    # Test 7: Oscillatory
    genera_stratificazione  # Test 6: Variabilità Ridotta
]

def genera_spike(profilo):
    """Genera punto anomalo per Test 1"""
    media, sigma = profilo['mean'], profilo['std_dev']
    # Valore tra 3.5 e 5 sigma di distanza
    valore_anomalo = media + random.choice([-1, 1]) * random.uniform(3.5, 5) * sigma
    return [clamp(valore_anomalo)], "Test 1 - Violazione Limite 3-Sigma"

def genera_shift(profilo, lunghezza=9):
    """Genera sequenza per Test 4"""
    media, sigma = profilo['mean'], profilo['std_dev']
    # Sposta media di 1.5-2 sigma
    nuova_media = media + random.choice([-1, 1]) * random.uniform(1.5, 2.0) * sigma
    valori = np.random.normal(nuova_media, sigma, lunghezza)
    return [clamp(v) for v in valori], "Test 4 - Run Above/Below Centerline"
```

## 🌐 API e Comunicazione

### Endpoints Principali

#### **GET /sixsigma/api/macchine**
```json
// Response: Lista macchine disponibili
[
    "WebServer-01",
    "Database-Server-01", 
    "Backup-Node-01"
]
```

#### **GET /sixsigma/api/baseline/{machine_id}**
```json
// Response: Parametri baseline per tutte le metriche
{
    "cpu": {
        "cl_x": 25.2,
        "ucl_x": 35.8,
        "lcl_x": 14.6,
        "cl_mr": 4.0,
        "ucl_mr": 13.1
    },
    "ram": {
        "cl_x": 40.1,
        "ucl_x": 56.0,
        "lcl_x": 24.2,
        "cl_mr": 6.0,
        "ucl_mr": 19.6
    },
    "io_wait": {
        "cl_x": 5.1,
        "ucl_x": 9.1,
        "lcl_x": 1.1,
        "cl_mr": 1.5,
        "ucl_mr": 4.9
    }
}
```

#### **GET /sixsigma/api/data/{machine_id}/{offset}**
```json
// Response: Prossimo punto dati con analisi SPC completa
{
    "timestamp": "2025-01-09T10:30:00.000Z",
    "metrics": {
        "cpu_percent": 28.5,
        "ram_percent": 42.1,
        "io_wait_percent": 6.2
    },
    "moving_ranges": {
        "cpu": 2.1,
        "ram": 1.8,
        "io_wait": 0.8
    },
    "scores": {
        "cpu": 1.0,
        "ram": 1.0,
        "io_wait": 1.0
    },
    "stati": {
        "cpu": "✅ In Controllo",
        "ram": "✅ In Controllo", 
        "io_wait": "✅ In Controllo"
    },
    "test_falliti": {
        "cpu": null,
        "ram": null,
        "io_wait": null
    },
    "punti_critici": {
        "cpu": false,
        "ram": false,
        "io_wait": false
    },
    "punti_coinvolti": {
        "cpu": [],
        "ram": [],
        "io_wait": []
    },
    "p_score": 1.0,
    "next_offset": 124
}
```

#### **POST /sixsigma/api/save_config**
```json
// Request: Configurazione pesi per macchine
{
    "WebServer-01": {
        "cpu": 0.5,
        "ram": 0.3,
        "io_wait": 0.2
    },
    "Database-Server-01": {
        "cpu": 0.3,
        "ram": 0.5,
        "io_wait": 0.2
    }
}

// Response: Conferma salvataggio
{
    "success": true,
    "message": "Configurazione salvata con successo",
    "config": { /* configurazione salvata */ }
}
```

## 🗄️ Struttura Database

### Collection: sixsigma_monitoring.metrics_advanced_test

```javascript
// Documento esempio con dati metriche e fase
{
    "_id": ObjectId("..."),
    "timestamp": ISODate("2025-01-09T10:30:00.000Z"),
    "machine_id": "WebServer-01",
    "phase": "baseline",  // "baseline" o "test"
    "metrics": {
        "cpu_percent": 25.4,
        "ram_percent": 39.8,
        "io_wait_percent": 5.2
    },
    "injected_anomaly_type": "None"  // Tipo anomalia iniettata (per test)
}
```

### Collection: sixsigma_monitoring.sixsigma_weights_config

```javascript
// Configurazione pesi per macchina
{
    "_id": ObjectId("..."),
    "machine_id": "WebServer-01",
    "weights": {
        "cpu": 0.4,
        "ram": 0.35,
        "io_wait": 0.25
    },
    "updated_at": ISODate("2025-01-09T10:30:00.000Z"),
    "created_by": "dashboard_config"
}
```

## 🎯 Casi d'Uso e Scenari

### Scenario 1: Monitoraggio Normale
1. **Baseline**: Sistema calcola parametri da 3 giorni di dati storici
2. **Monitoraggio**: Punti dati entrano nei limiti di controllo
3. **Visualizzazione**: Punti blu, P-Score > 0.8, stato "In Controllo"
4. **Log**: Nessun messaggio (solo test falliti vengono loggati)

### Scenario 2: Spike CPU (Test 1)
1. **Rilevamento**: CPU raggiunge 85% (UCL = 35%)
2. **Classificazione**: Test 1 fallito, score = 0.1
3. **Visualizzazione**: Punto rosso grande, P-Score < 0.5
4. **Log**: "🔴 CRITICO - Test 1: Violazione Limiti | 85.0% oltrepassa UCL (35.0%)"

### Scenario 3: Shift Processo (Test 4)
1. **Rilevamento**: 8 punti consecutivi sopra media
2. **Azione**: Grafico in pausa, colorazione arancione retroattiva
3. **Raccolta**: 20 nuovi punti per ricalcolo baseline
4. **Ricalcolo**: Nuovi limiti di controllo, grafico riattivato
5. **Log**: "🟠 ATTENZIONE - Test 4: Run Above/Below Centerline | prestazioni processo cambiate"

### Scenario 4: Configurazione Pesi
1. **Accesso**: `/sixsigma/config` per configurazione
2. **Modifica**: Slider auto-bilancianti (CPU 50%, RAM 30%, I/O 20%)
3. **Salvataggio**: Persistenza in MongoDB
4. **Applicazione**: P-Score ricalcolato con nuovi pesi

## 🔧 Configurazione e Personalizzazione

### Parametri Configurabili

```python
# Configurazione baseline
GIORNI_BASELINE_CONFIG = 3          # Giorni per calcolo baseline
BASELINE_DATA_POINTS = 3 * 24 * 60  # Punti dati baseline (1 punto/minuto)

# Configurazione simulazione
MAX_POINTS_ON_CHART = 20            # Punti visibili su grafico
RECALCULATE_WAIT_POINTS = 20        # Punti per ricalcolo baseline

# Configurazione test SPC
TEST_SCORES = {
    "test1": 0.1,        # Violazione Limite
    "testmr": 0.2,       # Variabilità Eccessiva  
    "saturazione": 0.0,  # Saturazione Risorsa
    "test4": 0.4,        # Run Above/Below
    "test7": 0.4,        # Oscillatory Trend
    "test8": 0.4,        # Linear Trend
    "test2": 0.6,        # Pre-allarme Shift
    "test3": 0.7,        # Variabilità Aumentata
    "in_controllo": 1.0  # Processo Stabile
}
```

### Pesi Default per Tipo Macchina

```python
# Profili consigliati per diversi tipi di macchine
WEIGHT_PROFILES = {
    "web_server": {
        "cpu": 0.5,      # CPU critica per web serving
        "ram": 0.3,      # RAM importante per caching
        "io_wait": 0.2   # I/O meno critico
    },
    "database_server": {
        "cpu": 0.3,      # CPU importante ma non critica
        "ram": 0.5,      # RAM critica per buffer pool
        "io_wait": 0.2   # I/O importante per query
    },
    "backup_node": {
        "cpu": 0.2,      # CPU meno critica
        "ram": 0.3,      # RAM moderatamente importante
        "io_wait": 0.5   # I/O critico per backup operations
    }
}
```

## 📈 Metriche e KPI

### Performance Indicators

| Metrica | Descrizione | Range | Interpretazione |
|---------|-------------|-------|-----------------|
| **P-Score** | Performance Score Aggregato | 0.0 - 1.0 | > 0.8 Eccellente, 0.5-0.8 Buono, < 0.5 Critico |
| **Test Success Rate** | % Test SPC Passati | 0% - 100% | > 95% Processo Stabile |
| **Baseline Stability** | Giorni senza Ricalcolo | 0+ giorni | > 7 giorni Processo Maturo |
| **Anomaly Detection Rate** | Anomalie Rilevate/Totale | 0% - 100% | 2-5% Range Normale |

### Statistiche Dashboard

```javascript
// Contatori test implementati nel frontend
let testStatistics = {
    test1: 0,      // Violazione Limite
    test2: 0,      // Zona A (Pre-allarme)
    test3: 0,      // Zona B (Variabilità)
    test4: 0,      // Run Test
    test7: 0,      // Trend Oscillatorio
    test8: 0,      // Trend Lineare
    testmr: 0,     // Alta Variabilità mR
    testsat: 0,    // Saturazione Risorsa
    testok: 0      // In Controllo
};
```

## 🚀 Deployment e Scalabilità

### Requisiti di Sistema

- **CPU**: 2+ cores per elaborazione real-time
- **RAM**: 4GB+ per cache baseline e grafici
- **Storage**: 10GB+ per dati storici MongoDB
- **Network**: Bassa latenza per aggiornamenti real-time

### Ottimizzazioni Performance

```python
# Cache baseline per evitare ricalcoli
baseline_cache = {}  # In-memory cache per parametri baseline

# Limitazione punti grafico per performance frontend
MAX_POINTS_ON_CHART = 20

# Batch processing per inserimenti MongoDB
documenti_da_inserire = []
if len(documenti_da_inserire) >= 1000:
    collection.insert_many(documenti_da_inserire)
```

### Monitoraggio Sistema

```python
# Logging strutturato per debugging
logger.info(f"Baseline calcolata per {machine_id}: CL={cl_x:.2f}, UCL={ucl_x:.2f}")
logger.warning(f"Test {test_name} fallito per {machine_id}: {dettagli}")
logger.error(f"Errore ricalcolo baseline: {error_message}")
```

## 📋 Conclusioni

Il sistema Six Sigma SPC implementato nel progetto `metrics_dashboard` rappresenta una soluzione completa e avanzata per il monitoraggio statistico delle performance IT. Le caratteristiche principali includono:

### Punti di Forza
- **Completezza**: 9 test SPC implementati con teoria statistica rigorosa
- **Flessibilità**: Pesi configurabili per adattamento a diversi tipi di macchine
- **Visualizzazione**: Dashboard interattiva con colorazione dinamica e feedback real-time
- **Robustezza**: Gestione automatica ricalcolo baseline per shift del processo
- **Scalabilità**: Architettura modulare con cache e ottimizzazioni performance

### Applicazioni Pratiche
- Monitoraggio proattivo infrastruttura IT
- Rilevamento precoce degradi performance
- Analisi trend e pattern comportamentali
- Ottimizzazione allocazione risorse
- Compliance SLA e quality assurance

### Valore Aggiunto
Il sistema trasforma il monitoraggio reattivo tradizionale in un approccio predittivo basato su evidenze statistiche, consentendo interventi preventivi prima che si verifichino impatti sui servizi business-critical.