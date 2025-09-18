# Report Tecnico: Analisi Approfondita del Sistema Metrics Dashboard

## Indice
1. [Panoramica del Sistema](#panoramica-del-sistema)
2. [Architettura e Componenti](#architettura-e-componenti)
3. [Generazione e Struttura dei Dati](#generazione-e-struttura-dei-dati)
4. [Algoritmi di Calcolo delle Metriche](#algoritmi-di-calcolo-delle-metriche)
5. [Struttura del Database](#struttura-del-database)
6. [Moduli di Analisi](#moduli-di-analisi)
7. [Conclusioni](#conclusioni)

---

## Panoramica del Sistema

Il **Metrics Dashboard** è un sistema completo di monitoraggio avanzato per infrastrutture PMI che implementa quattro moduli principali di analisi:

1. **Availability Analytics** - Analisi cumulativa della disponibilità dei servizi
2. **Resilience Analytics** - Analisi della resilienza dei sistemi di backup
3. **Six Sigma SPC** - Controllo statistico dei processi con carte di controllo XmR
4. **AnomalySNMP** - Rilevamento anomalie di rete tramite Machine Learning

Il sistema è costruito su **Flask** come web application principale e utilizza **MongoDB** come database per la persistenza dei dati di monitoraggio.

---

## Architettura e Componenti

### Struttura Modulare

```
metrics_dashboard/
├── app.py                    # Server Flask principale
├── run.py                    # Script di avvio
├── utils/                    # Moduli di elaborazione dati
│   ├── availability_summary.py
│   ├── backup_summary.py
│   ├── cumulative_availability_analyzer.py
│   ├── cumulative_resilience_analyzer.py
│   ├── generate_metrics_spc.py
│   └── sixsigma_utils.py
├── templates/                # Template HTML
├── static/                   # Risorse statiche (CSS, JS)
└── output/                   # File JSON generati dalle analisi
```

### Storage Layer

Il sistema utilizza un layer di astrazione per l'accesso ai dati MongoDB:

```
storage_layer/
├── storage_manager.py        # Gestore principale delle operazioni DB
├── models.py                 # Modelli dati (MetricDocument, AssetDocument)
├── mongodb_config.py         # Configurazione MongoDB
└── exceptions.py             # Eccezioni personalizzate
```

---

## Generazione e Struttura dei Dati

### 1. Dati di Performance (Six Sigma SPC)

Il modulo `generate_metrics_spc.py` genera dati strutturati per il controllo statistico dei processi:

#### Configurazione delle Macchine
```python
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

#### Fasi di Generazione Dati

**Fase 1: Baseline (3 giorni)**
- Genera dati "puliti" con solo variazione per causa comune
- Utilizzati per calcolare i limiti di controllo statistici
- Distribuzione normale basata sui profili delle macchine

**Fase 2: Test (12 giorni)**
- Inietta programmaticamente anomalie per validare il motore SPC
- Probabilità di anomalia: 2% per ogni punto dati
- Tipi di anomalie generate:
  - **Spike**: Violazione limiti 3-sigma (Test 1)
  - **Shift**: Spostamento della media (Test 4)
  - **Trend**: Andamento lineare crescente/decrescente (Test 8)
  - **Oscillazione**: Pattern alternato (Test 7)
  - **Violazioni Zone**: Test 2 e Test 3

#### Struttura Documento Metrica SPC
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "machine_id": "WebServer-01",
  "metrics": {
    "cpu_percent": 28.5,
    "ram_percent": 42.1,
    "io_wait_percent": 4.8
  },
  "phase": "test",
  "injected_anomaly_type": "Test 1 - Violazione Limite 3-Sigma"
}
```

### 2. Dati di Disponibilità (Availability)

Il sistema genera metriche di availability per i servizi monitorati:

#### Struttura Metrica Availability
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "meta": {
    "asset_id": "service_001",
    "metric_name": "availability_status"
  },
  "value": 1.0  // 1.0 = UP, 0.0 = DOWN
}
```

#### Processo di Generazione
1. **Identificazione Servizi**: Query su asset di tipo "service"
2. **Campionamento Temporale**: Misurazioni ogni minuto
3. **Stati Binari**: UP (1.0) o DOWN (0.0)
4. **Persistenza**: Inserimento in collection "metrics"

### 3. Dati di Resilienza (Backup)

Il sistema traccia le operazioni di backup per calcolare la resilienza:

#### Struttura Metrica Backup
```json
{
  "timestamp": "2025-01-15T02:00:00Z",
  "meta": {
    "asset_id": "vm_001",
    "metric_name": "backup_status"
  },
  "value": {
    "backup_completed": 1.0,  // 1.0 = successo, 0.0 = fallimento
    "backup_size_gb": 45.2,
    "duration_minutes": 23,
    "backup_type": "incremental"
  }
}
```

#### Asset Backup Job Acronis
```json
{
  "_id": "backup_job_001",
  "asset_type": "acronis_backup_job",
  "data": {
    "job_name": "VM-Backup-Daily",
    "schedule": "0 2 * * *",
    "backup_type": "incremental",
    "retention_days": 30,
    "target_assets": ["vm_001", "vm_002"],
    "last_run": "2025-01-15T02:00:00Z",
    "next_run": "2025-01-16T02:00:00Z",
    "status": "active"
  }
}
```

---

## Algoritmi di Calcolo delle Metriche

### 1. Algoritmo Availability Score

Il sistema implementa una formula cumulativa sofisticata per il calcolo del punteggio di disponibilità:

```
S(P_f, E_b) = 
- 100% se P_f = 0                                    (Nessun fallimento)
- 100% - (P_f/E_b × 50%) se 0 < P_f ≤ E_b           (Fallimenti sotto soglia)
- max(0, 50% - ((P_f - E_b)/E_b × 50%)) se P_f > E_b (Fallimenti sopra soglia)
```

**Dove:**
- `P_f` = Numero di fallimenti cumulativi per servizio
- `E_b` = Error Budget configurabile per tipo di servizio

#### Implementazione Python
```python
def calculate_cumulative_score(self, cumulative_failures: int, eb_value: int) -> float:
    if cumulative_failures == 0:
        return 1.0  # 100%
    elif 0 < cumulative_failures <= eb_value:
        score = 1.0 - ((cumulative_failures / eb_value) * 0.5)
        return score
    else:  # cumulative_failures > eb_value
        score = max(0.0, 0.5 - (((cumulative_failures - eb_value) / eb_value) * 0.5))
        return score
```

#### Error Budget per Tipo Servizio
```python
default_service_eb_config = {
    "web_service": 5,      # Servizi web (nginx, apache)
    "database": 3,         # Database (mysql, redis, elasticsearch)
    "application": 8,      # Applicazioni (tomcat, reporting)
    "backup": 10,          # Servizi di backup
    "monitoring": 4,       # Prometheus, grafana
    "mail": 6,             # Postfix, dovecot
    "ci_cd": 7,            # Jenkins, gitlab-runner
    "file_sharing": 5,     # NFS, SMB
    "default": 5           # Valore di default
}
```

### 2. Algoritmo Resilience Score

Il sistema calcola la resilienza dei backup utilizzando un approccio multi-metrica:

```
Resilience_Score = (w_RPO × RPO_Compliance) + (w_Success × Success_Rate)
```

#### Componenti del Calcolo

**RPO Compliance:**
```python
def calculate_rpo_compliance(self, last_successful_backup: datetime, 
                           current_time: datetime, target_rpo_hours: int) -> float:
    if last_successful_backup is None:
        return 1.0  # Nessun backup ancora = compliance perfetta
    
    time_diff = current_time - last_successful_backup
    actual_rpo_hours = time_diff.total_seconds() / 3600
    
    # Formula: max(0, 1 - (actual_RPO / target_RPO))
    rpo_compliance = max(0.0, min(1.0, 1.0 - (actual_rpo_hours / target_rpo_hours)))
    return rpo_compliance
```

**Success Rate:**
```python
def calculate_success_rate(self, total_successful: int, total_attempted: int) -> float:
    if total_attempted == 0:
        return 1.0  # Default al 100% se non ci sono tentativi
    return total_successful / total_attempted
```

#### Target RPO Default per Tipo Asset
```python
default_rpo_config = {
    "vm": 24,                    # Virtual Machines - 24 ore
    "container": 12,             # Container - 12 ore  
    "physical_host": 48,         # Server fisici - 48 ore
    "proxmox_node": 24,         # Nodi Proxmox - 24 ore
    "acronis_backup_job": 24,   # Backup job Acronis - 24 ore
    "default": 24               # Valore di default
}
```

#### Pesi Default delle Metriche
```python
default_weights = {
    "w_rpo": 0.6,      # Peso per RPO Compliance (60%)
    "w_success": 0.4   # Peso per Success Rate (40%)
}
```

### 3. Algoritmo Six Sigma SPC

Il sistema implementa un motore completo di Statistical Process Control con carte di controllo XmR:

#### Calcolo Baseline
```python
def calcola_baseline(machine_id, metrica, baseline_cache):
    # Calcolo dei parametri per la carta di controllo XmR
    cl_x = np.mean(valori)  # Linea Centrale
    moving_ranges = [abs(valori[i] - valori[i-1]) for i in range(1, len(valori))]
    cl_mr = np.mean(moving_ranges)
    
    # Limiti di controllo (±3σ)
    ucl_x = cl_x + 2.66 * cl_mr    # Upper Control Limit
    lcl_x = max(0, cl_x - 2.66 * cl_mr)  # Lower Control Limit
    ucl_mr = 3.268 * cl_mr         # UCL per Moving Range
    
    return {
        "cl_x": cl_x,
        "ucl_x": ucl_x,
        "lcl_x": lcl_x,
        "cl_mr": cl_mr,
        "ucl_mr": ucl_mr
    }
```

#### Test Statistici Implementati

| Test | Nome | Score | Descrizione |
|------|------|-------|-------------|
| **Test 1** | Violazione Limiti | 0.1 | Punto fuori UCL/LCL |
| **Test mR** | Variabilità Eccessiva | 0.2 | Moving Range > UCL_mR |
| **Saturazione** | Risorsa al Limite | 0.0 | Valore ≥ 100% |
| **Test 4** | Run Above/Below | 0.4 | 7-9 punti consecutivi stesso lato |
| **Test 7** | Oscillatory Trend | 0.4 | 14 punti alternanti |
| **Test 8** | Linear Trend | 0.4 | 6 punti monotoni |
| **Test 2** | Pre-allarme Shift | 0.6 | 2 di 3 punti oltre 2σ |
| **Test 3** | Variabilità Aumentata | 0.7 | 4 di 5 punti oltre 1σ |

#### P-Score Aggregato
```python
def calculate_p_score(scores, weights):
    """
    P_Score = (w_CPU × Score_CPU) + (w_RAM × Score_RAM) + (w_IO × Score_IO)
    """
    weighted_sum = 0
    total_weight = 0
    
    for metrica in ["cpu", "ram", "io_wait"]:
        weight = weights.get(metrica, 0)
        if weight > 0:
            weighted_sum += scores[metrica] * weight
            total_weight += weight
    
    return weighted_sum / total_weight if total_weight > 0 else 0
```

---

## Struttura del Database

### Database: `infrastructure_monitoring`

#### Collection: `assets`
Contiene informazioni sugli asset dell'infrastruttura:

```json
{
  "_id": "vm_001",
  "asset_type": "vm",
  "hostname": "web-server-01",
  "data": {
    "ip_address": "192.168.1.100",
    "os": "Ubuntu 22.04",
    "cpu_cores": 4,
    "ram_gb": 8,
    "disk_gb": 100,
    "status": "active"
  },
  "last_updated": "2025-01-15T10:00:00Z"
}
```

#### Collection: `metrics`
Contiene le metriche time-series:

```json
{
  "_id": ObjectId("..."),
  "timestamp": "2025-01-15T10:30:00Z",
  "meta": {
    "asset_id": "vm_001",
    "metric_name": "availability_status"
  },
  "value": 1.0
}
```

### Database: `sixsigma_monitoring`

#### Collection: `metrics_advanced_test`
Contiene le metriche SPC con metadati delle anomalie:

```json
{
  "_id": ObjectId("..."),
  "timestamp": "2025-01-15T10:30:00Z",
  "machine_id": "WebServer-01",
  "metrics": {
    "cpu_percent": 28.5,
    "ram_percent": 42.1,
    "io_wait_percent": 4.8
  },
  "phase": "test",
  "injected_anomaly_type": "Test 1 - Violazione Limite 3-Sigma"
}
```

#### Collection: `sixsigma_weights_config`
Configurazione pesi per il P-Score:

```json
{
  "_id": ObjectId("..."),
  "machine_id": "WebServer-01",
  "weights": {
    "cpu": 0.4,
    "ram": 0.35,
    "io_wait": 0.25
  },
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

---

## Moduli di Analisi

### 1. Availability Summary (`availability_summary.py`)

**Funzione:** Genera riassunti delle metriche di availability per ogni servizio.

**Processo:**
1. Seleziona un giorno casuale con dati di availability
2. Recupera tutti i servizi dal database
3. Per ogni servizio analizza:
   - Totale tuple availability
   - Tuple UP (1.0) vs DOWN (0.0)
   - Giorni con misurazioni
   - Misurazioni per giorno
   - Percentuale uptime

**Output Esempio:**
```
--- SERVIZIO: nginx (ID: service_001) ---
ESEMPIO TUPLA AVAILABILITY:
  Timestamp: 2025-01-15T10:30:00Z
  Asset ID: service_001
  Metric Name: availability_status
  Value: 1.0 (UP)

STATISTICHE:
  Totale tuple availability: 1440
  Tuple UP (1.0): 1380
  Tuple DOWN (0.0): 60
  Giorni con misurazioni: 1
  Misurazioni per giorno: 1440.0
  Percentuale uptime: 95.83%
```

### 2. Backup Summary (`backup_summary.py`)

**Funzione:** Genera riassunti completi delle metriche di backup per asset e backup job.

**Sezioni del Report:**
1. **Backup Jobs Acronis**: Informazioni sui job di backup configurati
2. **Metriche di Backup per Asset**: Statistiche per ogni asset
3. **Riepilogo Globale**: Statistiche aggregate

**Metriche Calcolate:**
- Tasso di successo backup (RPO)
- Tempo dall'ultimo backup
- Tempo al prossimo backup
- Distribuzione qualità backup

### 3. Cumulative Availability Analyzer (`cumulative_availability_analyzer.py`)

**Funzione:** Genera analisi cumulativa delle metriche di availability usando la formula avanzata.

**Processo:**
1. Seleziona giorno casuale con dati
2. Per ogni servizio:
   - Determina Error Budget (E_b)
   - Calcola fallimenti cumulativi (P_f)
   - Applica formula cumulativa
   - Determina status (CRITICAL/ATTENZIONE/GOOD)
3. Calcola score aggregato ponderato
4. Salva risultati in JSON

**Output JSON:**
```json
{
  "analysis_dates": ["2025-01-15T00:00:00Z"],
  "analysis_timestamp": "2025-01-15T15:30:00Z",
  "services": {
    "nginx": {
      "service_id": "service_001",
      "error_budget": 5,
      "weight": 0.33,
      "total_failures": 2,
      "final_score": 0.8,
      "final_status": "GOOD"
    }
  },
  "summary": {
    "total_services": 3,
    "aggregated_score": 0.85,
    "aggregated_status": "GOOD"
  }
}
```

### 4. Cumulative Resilience Analyzer (`cumulative_resilience_analyzer.py`)

**Funzione:** Simula ora per ora per una settimana (168 ore) la resilienza dei backup.

**Processo:**
1. Identifica periodo di simulazione (ultima settimana)
2. Per ogni asset/backup job:
   - Simula 168 ore consecutive
   - Calcola RPO Compliance per ogni ora
   - Calcola Success Rate cumulativo
   - Applica formula resilience score
3. Determina livello resilienza (EXCELLENT/GOOD/ACCEPTABLE/CRITICAL/SEVERE)
4. Salva simulazione completa in JSON

**Livelli di Resilienza:**
- **EXCELLENT**: > 90%
- **GOOD**: 75% - 90%
- **ACCEPTABLE**: 60% - 75%
- **CRITICAL**: 40% - 60%
- **SEVERE**: < 40%

### 5. Six Sigma Utils (`sixsigma_utils.py`)

**Funzione:** Motore SPC per il monitoraggio statistico delle metriche di performance.

**Componenti Principali:**
1. **Calcolo Baseline**: Parametri carte di controllo XmR
2. **Test Statistici**: 9 test SPC implementati
3. **Scoring System**: Punteggi basati sulla criticità
4. **P-Score Calculation**: Score aggregato ponderato

**Funzione Principale:**
```python
def monitora_nuovo_dato(valore, valore_precedente, cronologia, baseline):
    """
    Applica tutti i test SPC e restituisce:
    - Stato del processo
    - Score (0.0 - 1.0)
    - Dettagli anomalia
    - Test fallito
    - Warning level
    """
```

---

## Conclusioni

Il sistema **Metrics Dashboard** rappresenta una soluzione completa e sofisticata per il monitoraggio dell'infrastruttura PMI. Le caratteristiche principali includono:

### Punti di Forza

1. **Architettura Modulare**: Separazione chiara tra logica di business, accesso dati e presentazione
2. **Algoritmi Avanzati**: Formule matematiche sofisticate per availability, resilience e SPC
3. **Generazione Dati Strutturata**: Sistema di simulazione con anomalie programmatiche per validazione
4. **Persistenza Robusta**: Layer di astrazione MongoDB con gestione errori e retry
5. **Analisi Multi-Dimensionale**: Quattro moduli complementari per copertura completa

### Struttura Dati Ottimizzata

- **Time-Series Efficient**: Struttura ottimizzata per metriche temporali
- **Metadata Ricchi**: Informazioni contestuali per ogni metrica
- **Configurabilità**: Parametri personalizzabili per ogni tipo di asset
- **Scalabilità**: Architettura progettata per crescita del volume dati

### Algoritmi di Calcolo

- **Availability**: Formula cumulativa con error budget configurabili
- **Resilience**: Approccio multi-metrica con RPO compliance e success rate
- **Six Sigma SPC**: Implementazione completa con 9 test statistici
- **Scoring Ponderato**: Sistemi di punteggio basati su pesi configurabili

Il sistema fornisce una base solida per il monitoraggio proattivo dell'infrastruttura, con capacità di rilevamento anomalie, analisi predittiva e reportistica avanzata per supportare le decisioni operative e strategiche.