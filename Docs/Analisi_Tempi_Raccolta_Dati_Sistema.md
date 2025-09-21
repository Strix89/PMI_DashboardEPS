# Analisi Tempi di Raccolta Dati - Sistema Metrics Dashboard

## Panoramica Generale

Il sistema `metrics_dashboard` e `storage_layer` genera dati simulati per testare e sviluppare le funzionalità di monitoraggio. Ecco un'analisi dettagliata dei tempi di raccolta e degli intervalli di generazione dati.

## Dati Generati dal Storage Layer (`seed_database.py`)

### 1. **Metriche di Performance (CPU, RAM, I/O Wait)**

#### Intervallo di Raccolta
- **Frequenza**: **MINUTO per MINUTO** (ogni 60 secondi)
- **Periodo Default**: **14 giorni** di dati storici
- **Granularità**: 1 minuto

#### Calcolo Totale Dati Performance
```python
# Dal codice seed_database.py:
minutes_per_day = 24 * 60  # 1440 minuti al giorno
total_minutes = days * minutes_per_day  # 14 * 1440 = 20.160 minuti
total_metrics = len(machine_assets) * len(metric_types) * total_minutes
# 10 macchine * 3 metriche * 20.160 minuti = 604.800 record di metriche
```

#### Asset Monitorati per Performance
- **10 macchine** totali (VM, Container, Physical Host, Proxmox Node)
- **3 metriche** per macchina: `cpu_usage`, `memory_usage`, `io_wait`
- **Totale**: 604.800 record di metriche per 14 giorni

### 2. **Dati di Backup (per Resilience Analytics)**

#### Intervallo di Raccolta
- **Frequenza**: **GIORNALIERA** (1 volta al giorno)
- **Orario**: Tra le **01:00 e 04:00** (simulazione backup notturni)
- **Periodo Default**: **14 giorni** di dati storici

#### Calcolo Totale Dati Backup
```python
# Dal codice generate_backup_history():
machine_assets = 10  # VM, Container, Physical Host, Proxmox Node
days = 14
total_backups = machine_assets * days  # 10 * 14 = 140 record di backup
```

#### Dettagli Backup
- **Asset coinvolti**: Solo macchine (VM, Container, Physical Host, Proxmox Node)
- **Metrica generata**: `backup_status` (1.0 = successo, 0.0 = fallimento)
- **Success Rate per tipo**:
  - VM: 95% successo
  - Container: 92% successo  
  - Physical Host: 97% successo
  - Proxmox Node: 98% successo

### 3. **Dati di Polling/Availability**

#### Intervallo di Raccolta
- **Frequenza**: **MINUTO per MINUTO** (ogni 60 secondi)
- **Metriche**: 2 per asset (`availability` + `response_time`)
- **Periodo Default**: **14 giorni** di dati storici

#### Calcolo Totale Dati Polling
```python
# Include sia macchine che servizi
total_assets = len(INFRASTRUCTURE_ASSETS) + sum(len(asset.get("services", [])) for asset in INFRASTRUCTURE_ASSETS)
# 10 macchine + ~20 servizi = ~30 asset totali
total_polling = days * 24 * 60 * total_assets * 2  # *2 per availability + response_time
# 14 * 1440 * 30 * 2 = 1.209.600 record di polling
```

## Dati Six Sigma SPC (metrics_dashboard)

### 1. **Baseline Data Points**

#### Configurazione Baseline
```python
# Dal file sixsigma_utils.py:
GIORNI_BASELINE_CONFIG = 3  # 3 giorni per baseline
BASELINE_DATA_POINTS = GIORNI_BASELINE_CONFIG * 24 * 60  # 4.320 punti
```

#### Dettagli Baseline
- **Periodo baseline**: **3 giorni** (4.320 minuti)
- **Granularità**: **1 minuto**
- **Scopo**: Calcolare parametri statistici (CL, UCL, LCL) per carte di controllo
- **Metriche**: CPU, RAM, I/O Wait per ogni macchina

### 2. **Simulazione Real-Time**

#### Intervallo Simulazione
- **Frequenza visualizzazione**: Configurabile (1x, 2x, 3x velocità)
- **Granularità**: **1 punto ogni avanzamento** (simula 1 ora di dati reali)
- **Dati utilizzati**: Punti successivi ai BASELINE_DATA_POINTS

## Riepilogo Intervalli Temporali

### Tabella Riassuntiva

| **Tipo Dato** | **Frequenza Raccolta** | **Granularità** | **Periodo Default** | **Totale Record (14gg)** |
|----------------|------------------------|-----------------|---------------------|---------------------------|
| **Performance Metrics** | Ogni minuto | 1 minuto | 14 giorni | ~604.800 |
| **Backup Status** | Giornaliera | 1 giorno | 14 giorni | ~140 |
| **Polling/Availability** | Ogni minuto | 1 minuto | 14 giorni | ~1.209.600 |
| **Six Sigma Baseline** | Ogni minuto | 1 minuto | 3 giorni | ~4.320 |

### Totale Complessivo
- **Totale record generati**: ~1.818.860 per 14 giorni
- **Rate di inserimento**: ~1.000 record per batch (configurabile)
- **Tempo generazione**: Dipende dalle performance del sistema

## Pattern Temporali Realistici

### 1. **Pattern Performance CPU/RAM/I/O**

#### Orari Business (9:00-17:00)
- **CPU**: Picchi durante orari lavorativi
- **RAM**: Correlata al carico CPU
- **I/O**: Picchi durante backup notturni (01:00-04:00)

#### Pattern Specifici per Asset
- **DB Server**: Picchi CPU durante business hours
- **Web Server**: Alto carico durante business hours  
- **Backup Server**: Alto I/O durante notti (22:00-06:00)
- **Development Server**: Attività sporadica durante dev hours

### 2. **Pattern Backup**

#### Scheduling Realistico
```python
# Dal codice determine_backup_success():
backup_hour = random.choice([1, 2, 3, 4])  # Tra 1-4 AM
backup_minute = random.randint(0, 59)
```

#### Failure Patterns
- **Failure rate** basato su tipo asset
- **Pattern realistici**: Occasionali fallimenti casuali
- **No correlazioni complesse**: Implementazione semplificata

### 3. **Pattern Six Sigma**

#### Anomalie Simulate
- **Test 1**: Violazione limiti (UCL/LCL)
- **Test mR**: Variabilità eccessiva tra punti consecutivi
- **Test 4**: 7-9 punti consecutivi stesso lato media
- **Test 7**: 14 punti alternati (pattern oscillatorio)
- **Test 8**: 6 punti trend lineare crescente/decrescente

## Configurazione Tempi

### Parametri Configurabili

#### Storage Layer (`seed_database.py`)
```bash
python seed_database.py \
    --days 14 \                    # Giorni di dati da generare
    --batch-size 1000 \            # Record per batch
    --progress-interval 30 \       # Log progresso ogni 30 sec
    --checkpoint-interval 300      # Checkpoint ogni 5 min
```

#### Six Sigma (`sixsigma_utils.py`)
```python
GIORNI_BASELINE_CONFIG = 3         # Giorni per baseline
BASELINE_DATA_POINTS = 4320        # Punti baseline totali
```

#### Resilience Analytics
```python
self.simulation_hours = 168        # 1 settimana (168 ore)
```

## Considerazioni Performance

### 1. **Generazione Dati**
- **Batch size**: 1.000 record per inserimento
- **Progress logging**: Ogni 30 secondi
- **Checkpoint**: Ogni 5 minuti per recovery
- **Resumable**: Supporto per ripresa da checkpoint

### 2. **Utilizzo Memoria**
- **Pattern generator**: Mantiene stato per pattern realistici
- **Cache baseline**: Evita ricalcoli ripetuti
- **Batch processing**: Limita utilizzo memoria

### 3. **Scalabilità**
- **Asset illimitati**: Supporta qualsiasi numero di macchine
- **Periodo configurabile**: Da 1 giorno a mesi di dati
- **Parallel processing**: Batch insertion efficiente

## Conclusioni

Il sistema genera dati con **granularità al minuto** per le metriche di performance e polling, mentre i backup sono **giornalieri**. Questo simula realisticamente un ambiente di monitoraggio enterprise dove:

1. **Metriche sistema** vengono raccolte frequentemente (ogni minuto)
2. **Backup** vengono eseguiti giornalmente durante finestre notturne
3. **Baseline Six Sigma** utilizza 3 giorni di dati per stabilire parametri statistici
4. **Simulazioni resilience** analizzano 1 settimana (168 ore) di dati

La **frequenza minuto per minuto** per le metriche di performance è realistica per sistemi di monitoraggio enterprise, fornendo granularità sufficiente per rilevare anomalie e trend senza sovraccaricare il sistema di storage.