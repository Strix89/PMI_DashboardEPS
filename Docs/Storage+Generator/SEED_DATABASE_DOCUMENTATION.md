# Documentazione Completa: seed_database.py

## Indice
1. [Panoramica](#panoramica)
2. [Prerequisiti](#prerequisiti)
3. [Configurazione](#configurazione)
4. [Utilizzo Base](#utilizzo-base)
5. [Opzioni Avanzate](#opzioni-avanzate)
6. [Struttura Dati Generati](#struttura-dati-generati)
7. [Pattern di Performance](#pattern-di-performance)
8. [Esempi Pratici](#esempi-pratici)
9. [Troubleshooting](#troubleshooting)
10. [Monitoraggio e Logging](#monitoraggio-e-logging)

---

## Panoramica

Il script `seed_database.py` è uno strumento completo per popolare il database MongoDB con dati realistici di infrastruttura per scopi di testing e sviluppo. Genera:

- **10 macchine** diverse (VM, container, host fisici, nodi Proxmox)
- **20+ servizi** associati alle macchine
- **2 job di backup Acronis**
- **Metriche minute-by-minute** per 14 giorni (oltre 600.000 record)
- **Polling history** per calcoli di disponibilità (oltre 600.000 record)
- **Frequenza raccolta**: 1 record ogni minuto per ogni metrica e polling
- **Pattern di performance realistici** con variazioni temporali

### Caratteristiche Principali

✅ **Dati Realistici**: Pattern di CPU, memoria e I/O basati su scenari reali  
✅ **Polling History**: Cronologia di disponibilità per calcoli di uptime accurati  
✅ **Scalabilità**: Inserimento batch ottimizzato per grandi volumi di dati  
✅ **Resumable**: Possibilità di riprendere l'esecuzione in caso di interruzione  
✅ **Flessibilità**: Configurazione personalizzabile per diversi scenari  
✅ **Logging Dettagliato**: Monitoraggio completo del processo di generazione  

---

## Prerequisiti

### Dipendenze Software

```bash
# Python 3.8 o superiore
python --version

# Dipendenze Python (installate automaticamente con requirements.txt)
pip install pymongo python-dotenv
```

### Database MongoDB

```bash
# MongoDB deve essere in esecuzione e accessibile
# Verifica la connessione:
mongosh --eval "db.adminCommand('ping')"
```

### Struttura del Progetto

```
PMI_Dashboard/
├── storage_layer/
│   ├── mongodb_config.py      # ✅ Configurazione MongoDB
│   ├── storage_manager.py     # ✅ Gestione storage
│   ├── models.py             # ✅ Modelli dati
│   └── .env                  # ⚠️  File di configurazione (da creare)
├── seed_database.py          # 🎯 Script principale
└── requirements.txt          # ✅ Dipendenze
```

---

## Configurazione

### 1. Configurazione MongoDB

Crea il file `.env` nella directory `storage_layer/`:

```bash
# Copia il template
cp storage_layer/.env.example storage_layer/.env

# Modifica con i tuoi parametri
nano storage_layer/.env
```

**Configurazione Minima (Sviluppo Locale):**
```env
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DATABASE=pmi_infrastructure_dev
ENVIRONMENT=development
```

**Configurazione Produzione:**
```env
MONGODB_HOST=mongodb-prod.example.com
MONGODB_PORT=27017
MONGODB_DATABASE=pmi_infrastructure
MONGODB_USERNAME=pmi_user
MONGODB_PASSWORD=your_secure_password
MONGODB_SSL_ENABLED=true
ENVIRONMENT=production
```

### 2. Verifica Configurazione

```bash
# Test della connessione MongoDB
python -c "from storage_layer.mongodb_config import mongodb_config; print('✅ Connessione OK' if mongodb_config.test_connection() else '❌ Connessione FALLITA')"
```

---

## Utilizzo Base

### Comando Semplice

```bash
# Genera tutti i dati con configurazione di default
python seed_database.py
```

Questo comando:
- Crea 10 macchine + 20+ servizi + 2 job backup
- Genera 14 giorni di metriche (circa 600.000 record)
- Usa batch di 1000 record per l'inserimento
- Mostra progress bar dettagliato

### Output Tipico

```
🚀 Avvio generazione dati infrastruttura PMI Dashboard
📊 Configurazione: 10 macchine, 14 giorni, batch 1000

✅ Connessione MongoDB stabilita
🏗️  Creazione asset infrastruttura...
   ├── 10 macchine create
   ├── 22 servizi creati
   └── 2 job backup creati

📈 Generazione metriche temporali...
   ├── Periodo: 2025-01-26 → 2025-02-09
   ├── Metriche totali: 604,800
   └── Progress: [████████████████████] 100% (604,800/604,800)

✅ Generazione completata in 2m 34s
📊 Statistiche finali:
   ├── Asset totali: 34
   ├── Metriche inserite: 604,800
   └── Velocità media: 3,945 metriche/sec
```

---

## Opzioni Avanzate

### Parametri da Riga di Comando

```bash
# Mostra tutte le opzioni disponibili
python seed_database.py --help
```

### Opzioni Principali

| Parametro      | Descrizione                          | Default | Esempio             |
| -------------- | ------------------------------------ | ------- | ------------------- |
| `--days`       | Giorni di dati da generare           | 14      | `--days 30`         |
| `--batch-size` | Record per batch (ottimizzazione DB) | 1000    | `--batch-size 5000` |
| `--clean`      | Pulisce il database prima            | False   | `--clean`           |
| `--resume`     | Riprende esecuzione interrotta       | False   | `--resume`          |
| `--seed`       | Seed per riproducibilità             | Random  | `--seed 12345`      |
| `--log-level`  | Livello di logging                   | INFO    | `--log-level DEBUG` |
| `--quiet`      | Riduce output                        | False   | `--quiet`           |

### Esempi di Utilizzo Avanzato

```bash
# Genera 30 giorni di dati con batch grandi (più veloce)
python seed_database.py --days 30 --batch-size 5000

# Pulisce e rigenera tutto con seed fisso
python seed_database.py --skip-cleanup --seed 12345 --log-level DEBUG

# Solo asset senza metriche (veloce per test)
python seed_database.py --assets-only --days 7

# Riprende un'esecuzione interrotta
python seed_database.py --resume --log-level DEBUG
```

### 🚀 Ottimizzazione Batch Size

Il `--batch-size` controlla **quanti record vengono inseriti insieme** nel database per ottimizzare le performance:

#### Come Funziona
```
Generazione Dati (sempre 1/minuto):
┌─────────────────────────────────────────────────────────┐
│ Min 1: 30 record → Batch                               │
│ Min 2: 30 record → Batch (60 totali)                  │
│ Min 3: 30 record → Batch (90 totali)                  │
│ ...                                                     │
│ Min 34: 30 record → Batch (1020 totali)               │
│ → INSERISCE 1000 nel DB, rimangono 20 nel batch       │
└─────────────────────────────────────────────────────────┘
```

#### Scelta del Batch Size

| Batch Size | Velocità     | Memoria    | Uso Consigliato          |
| ---------- | ------------ | ---------- | ------------------------ |
| **500**    | Lenta        | Bassa      | Hardware limitato        |
| **1000**   | Media        | Media      | **Default - Bilanciato** |
| **5000**   | Veloce       | Alta       | Server potenti           |
| **10000**  | Molto veloce | Molto alta | Test performance         |

#### Esempi Pratici

```bash
# Hardware limitato (es. Raspberry Pi)
python seed_database.py --batch-size 500

# Sviluppo locale standard
python seed_database.py --batch-size 1000  # Default

# Server di produzione
python seed_database.py --batch-size 5000

# Test di performance massima
python seed_database.py --batch-size 10000 --days 90
```

#### Monitoraggio Performance

Il sistema mostra le performance del batch in tempo reale:
```
📈 Batch 1000/604800 completato (0.17%)
   ├── Velocità: 3,945 metriche/sec
   ├── Tempo batch: 0.25s
   └── ETA: 2m 15s
```

---

## Struttura Dati Generati

### Asset Infrastruttura

#### 1. Nodi Proxmox
```json
{
  "asset_id": "pve-node-01",
  "asset_type": "proxmox_node",
  "hostname": "PVE-HOST-01",
  "data": {
    "status": "running",
    "cpu_cores": 32,
    "memory_gb": 128,
    "storage_gb": 2000,
    "hypervisor_version": "7.4-3",
    "cluster_name": "production"
  }
}
```

#### 2. Macchine Virtuali
```json
{
  "asset_id": "vm-101",
  "asset_type": "vm",
  "hostname": "DB-SERVER-PROD",
  "data": {
    "status": "running",
    "cpu_cores": 8,
    "memory_gb": 32,
    "storage_gb": 500,
    "hypervisor": "pve-node-01",
    "os": "Ubuntu 22.04 LTS"
  }
}
```

#### 3. Container LXC
```json
{
  "asset_id": "ct-201",
  "asset_type": "container",
  "hostname": "CACHE-SERVER-01",
  "data": {
    "status": "running",
    "cpu_cores": 2,
    "memory_gb": 8,
    "container_type": "LXC",
    "os": "Ubuntu 22.04 LTS"
  }
}
```

#### 4. Host Fisici
```json
{
  "asset_id": "physical-01",
  "asset_type": "physical_host",
  "hostname": "BACKUP-SERVER-01",
  "data": {
    "status": "running",
    "cpu_cores": 16,
    "memory_gb": 64,
    "manufacturer": "Dell",
    "model": "PowerEdge R740",
    "location": "Datacenter Rack A1"
  }
}
```

### Servizi Associati

```json
{
  "asset_id": "svc-mysql-101",
  "asset_type": "service",
  "service_name": "MySQL Database",
  "data": {
    "parent_asset_id": "vm-101",
    "status": "running",
    "service_type": "database",
    "port": 3306
  }
}
```

### Job di Backup Acronis

```json
{
  "asset_id": "backup-job-001",
  "asset_type": "acronis_backup_job",
  "data": {
    "job_name": "Daily VM Backup",
    "status": "running",
    "schedule": "daily_2am",
    "target_assets": ["vm-101", "vm-102", "vm-103"],
    "backup_type": "incremental",
    "retention_days": 30
  }
}
```

### Metriche Temporali

Le metriche sono generate **ogni minuto** per ogni macchina:

```json
{
  "asset_id": "vm-101",
  "metric_name": "cpu_usage",
  "timestamp": "2025-02-09T10:30:00Z",  // Timestamp preciso al minuto
  "value": 67.5,
  "unit": "percentage",
  "tags": {
    "environment": "production",
    "asset_type": "vm"
  }
}
```

**Frequenza di raccolta simulata:**
- ⏱️ **1 record ogni minuto** per ogni metrica
- 📊 **3 metriche** per macchina (CPU, Memory, I/O)
- 🕐 **1440 record/giorno** per macchina (24h × 60min × 3 metriche)
- 📈 **604.800 record totali** per 10 macchine in 14 giorni

### Polling History per Disponibilità

La polling history è essenziale per calcolare l'availability (disponibilità) dei servizi e delle macchine:

```json
{
  "asset_id": "svc-mysql-101",
  "metric_name": "availability_status",
  "timestamp": "2025-02-09T10:30:00Z",
  "value": 100.0  // 100.0=up, 50.0=degraded, 0.0=down
}
```

```json
{
  "asset_id": "svc-mysql-101", 
  "metric_name": "response_time_ms",
  "timestamp": "2025-02-09T10:30:00Z",
  "value": 45.2  // Tempo di risposta in millisecondi
}
```

**Caratteristiche della Polling History:**
- ⏱️ **1 polling ogni minuto** per ogni asset (macchine + servizi)
- 📊 **2 metriche di polling** per asset (availability_status + response_time_ms)
- 🔍 **Simula downtime programmati** (manutenzioni notturne)
- 🚨 **Simula guasti casuali** (99.5% uptime per servizi, 99.9% per macchine)
- 📈 **Oltre 600.000 record di polling** per 32 asset in 14 giorni

**Stati di Disponibilità:**
- **100.0**: Servizio/macchina completamente operativo
- **50.0**: Servizio/macchina degradato (lento ma funzionante)
- **0.0**: Servizio/macchina non disponibile (down/timeout)

**Pattern di Downtime Realistici:**
- 🕐 **Manutenzioni programmate**: Servizi con downtime notturno (es. 23:00-01:00)
- 🔄 **Memory leak**: Degradazione graduale con reset settimanali
- 🎲 **Guasti casuali**: Failure rate realistici per tipo di asset
- 🔗 **Dipendenze**: Servizi ereditano lo stato della macchina host

### Backup History per RPO

La backup history è essenziale per calcolare RPO (Recovery Point Objective) e success rate dei backup:

```json
{
  "asset_id": "vm-101",
  "metric_name": "backup_status",
  "timestamp": "2025-09-03T02:15:00Z",
  "value": 1.0  // 1.0=success, 0.0=failed
}
```

**Caratteristiche della Backup History:**
- ⏰ **1 backup al giorno** per ogni macchina (ore notturne 1-4 AM)
- 📊 **Solo backup_status** (success/failed)
- 🎯 **RPO target configurabili** nel dashboard (non generati)
- 📈 **Success rate realistici** (92-98% per tipo di asset)
- 🕐 **Timestamp precisi** per calcolo actual RPO

**Success Rate per Tipo Asset:**
- **Proxmox nodes**: 98% (più affidabili)
- **Physical hosts**: 97%
- **VM**: 95%
- **Container**: 92% (più volatili)

**Pattern di Backup Realistici:**
- 🌙 **Orari notturni**: Backup schedulati tra 1-4 AM
- ⚠️ **Failure pattern**: Più fallimenti il lunedì e durante picchi di carico
- 🔄 **Memory leak impact**: Riduzione success rate per asset con problemi memoria
- 🎲 **Contention**: Riduzione success rate durante ore di picco (2-4 AM)

---

## Frequenza di Raccolta Dati

### Simulazione Real-Time

Il sistema simula un **monitoraggio real-time** con raccolta dati ogni minuto:

```
Timeline Esempio (vm-101):
┌─────────────────┬─────────┬─────────┬─────────┐
│ Timestamp       │ CPU %   │ Memory %│ I/O %   │
├─────────────────┼─────────┼─────────┼─────────┤
│ 10:00:00        │  65.2   │  45.1   │  12.3   │
│ 10:01:00        │  67.8   │  45.3   │  11.9   │ ← +1 minuto
│ 10:02:00        │  69.1   │  45.7   │  13.1   │ ← +1 minuto
│ 10:03:00        │  66.4   │  45.2   │  12.8   │ ← +1 minuto
│ ...             │  ...    │  ...    │  ...    │
└─────────────────┴─────────┴─────────┴─────────┘
```

### Calcolo Volume Dati

**Per 1 macchina:**
- 🕐 **1440 minuti/giorno** (24 ore × 60 minuti)
- 📊 **3 metriche/minuto** (CPU, Memory, I/O)
- 📈 **4.320 record/giorno** per macchina

**Per configurazione default (10 macchine + 22 servizi, 14 giorni):**

**Metriche Performance:**
- 🖥️ **10 macchine** × **3 metriche** × **1440 minuti** × **14 giorni**
- 📊 **604.800 record di metriche**

**Polling History:**
- 🔍 **32 asset totali** (10 macchine + 22 servizi) × **2 polling** × **1440 minuti** × **14 giorni**
- 📊 **645.120 record di polling**

**Backup History:**
- 💾 **10 macchine** × **1 backup status** × **14 giorni**
- 📊 **140 record di backup**

**Totale:**
- 📈 **1.250.060 record totali**
- 💾 **~93 MB** di dati nel database

### Granularità Temporale

```python
# Esempio di generazione timestamp
current_time = start_time
while current_time < end_time:
    # Genera metriche per questo minuto specifico
    for asset in assets:
        for metric_type in ['cpu_usage', 'memory_usage', 'io_wait']:
            create_metric(asset_id, metric_type, current_time, value)
    
    current_time += timedelta(minutes=1)  # Avanza di 1 minuto
```

### Pattern Minute-Level

I pattern di performance sono progettati per essere realistici anche a livello di minuto:

**Esempio - Picchi ogni 15 minuti:**
```python
if minute % 15 == 0:  # Spike ogni 15 minuti
    base_cpu = min(95.0, base_cpu + 25.0)
```

**Esempio - Variazioni graduali:**
```python
# Variazione sinusoidale durante le ore lavorative
base_cpu = 65.0 + 20.0 * math.sin((hour - 9) * math.pi / 8)
```

---

## Pattern di Performance

Il sistema genera 8 pattern di performance realistici:

### 1. `stable_with_io_spikes`
- **CPU**: Stabile ~15%, picchi I/O alle 3:00
- **Memoria**: Costante ~35%, aumenta durante I/O
- **I/O**: Picchi significativi alle 3:00 (backup)
- **Uso**: Server di storage, NAS

### 2. `cpu_spikes_business_hours`
- **CPU**: Alto 9-17 (65%+), basso fuori orario
- **Memoria**: Correlata al carico CPU
- **I/O**: Moderato durante orario lavorativo
- **Uso**: Database server, application server

### 3. `high_load_business_hours`
- **CPU**: Costantemente alto 9-17 (75%+)
- **Memoria**: Alta durante orario lavorativo
- **I/O**: Sostenuto durante il giorno
- **Uso**: Web server ad alto traffico

### 4. `memory_leak_pattern`
- **CPU**: Aumenta con la pressione memoria
- **Memoria**: Crescita graduale, reset settimanale
- **I/O**: Aumenta con swapping
- **Uso**: Applicazioni Java con memory leak

### 5. `volatile_load`
- **CPU**: Carico molto variabile, picchi casuali
- **Memoria**: Fluttuazioni significative
- **I/O**: Picchi imprevedibili
- **Uso**: Cache server, sistemi batch

### 6. `stable_low_load`
- **CPU**: Costantemente basso (~8%)
- **Memoria**: Stabile e bassa
- **I/O**: Minimo
- **Uso**: Sistemi di monitoraggio

### 7. `io_wait_nights`
- **CPU**: Alto durante la notte (backup)
- **Memoria**: Aumenta durante operazioni notturne
- **I/O**: Molto alto 22:00-06:00
- **Uso**: Server di backup

### 8. `development_pattern`
- **CPU**: Sporadico durante orario dev
- **Memoria**: Variabile con attività
- **I/O**: Picchi durante build/deploy
- **Uso**: Server di sviluppo, CI/CD

---

## Esempi Pratici

### Scenario 1: Setup Sviluppo Rapido

```bash
# Setup completo per sviluppo locale
python seed_database.py --days 7 --batch-size 2000 --log-level DEBUG
```

**Risultato**: Database pulito con 7 giorni di dati, perfetto per sviluppo e test.

### Scenario 2: Demo con Dati Consistenti

```bash
# Genera sempre gli stessi dati per demo
python seed_database.py --seed 42 --days 14 --clean
```

**Risultato**: Dati identici ad ogni esecuzione, ideale per demo e presentazioni.

### Scenario 3: Test di Performance

```bash
# Genera grandi volumi per test di performance
python seed_database.py --days 90 --batch-size 10000 --log-level DEBUG
```

**Risultato**: ~1.8M metriche per testare performance del sistema.

### Scenario 4: Ripristino dopo Interruzione

```bash
# L'esecuzione si è interrotta, riprendi da dove si era fermata
python seed_database.py --resume --log-level DEBUG
```

**Risultato**: Continua la generazione dal punto di interruzione.

### Scenario 5: Verifica senza Modifiche

```bash
# Solo asset per verificare configurazione (veloce)
python seed_database.py --assets-only --days 30 --log-level DEBUG
```

**Risultato**: Crea solo gli asset senza metriche né polling history.

### Scenario 6: Solo Polling History

```bash
# Genera solo la polling history per test di disponibilità
python seed_database.py --polling-only --days 7 --batch-size 5000
```

**Risultato**: Genera solo i dati di polling per calcoli di availability.

### Scenario 7: Solo Backup History

```bash
# Genera solo la backup history per test RPO
python seed_database.py --backup-only --days 14 --batch-size 1000
```

**Risultato**: Genera solo i dati di backup per calcoli di RPO e success rate.

---

## Troubleshooting

### Problemi Comuni

#### 1. Errore di Connessione MongoDB

**Sintomo:**
```
❌ ConnectionFailure: Impossibile connettersi a MongoDB
```

**Soluzioni:**
```bash
# Verifica che MongoDB sia in esecuzione
sudo systemctl status mongod

# Testa la connessione manualmente
mongosh --host localhost --port 27017

# Verifica la configurazione
cat storage_layer/.env
```

#### 2. Errore di Autenticazione

**Sintomo:**
```
❌ OperationFailure: Authentication failed
```

**Soluzioni:**
```bash
# Verifica credenziali nel file .env
grep MONGODB_USERNAME storage_layer/.env
grep MONGODB_PASSWORD storage_layer/.env

# Testa l'autenticazione manualmente
mongosh "mongodb://username:password@localhost:27017/database"
```

#### 3. Memoria Insufficiente

**Sintomo:**
```
❌ MemoryError: Unable to allocate memory
```

**Soluzioni:**
```bash
# Riduci la dimensione del batch
python seed_database.py --batch-size 500

# Riduci i giorni di dati
python seed_database.py --days 7

# Monitora l'uso della memoria
htop
```

#### 4. Spazio Disco Insufficiente

**Sintomo:**
```
❌ No space left on device
```

**Soluzioni:**
```bash
# Verifica spazio disponibile
df -h

# Pulisci il database esistente
python seed_database.py --clean

# Riduci il volume di dati
python seed_database.py --days 3
```

#### 5. Interruzione del Processo

**Sintomo:**
```
⚠️ Processo interrotto a metà generazione
```

**Soluzioni:**
```bash
# Riprendi dall'ultimo punto
python seed_database.py --resume

# Se il resume non funziona, ricomincia senza pulizia
python seed_database.py --skip-cleanup --log-level DEBUG
```

### Debug Avanzato

#### Abilitazione Logging Dettagliato

```bash
# Logging completo per debug
python seed_database.py --log-level DEBUG --log-file seed_debug.log
```

#### Verifica Stato Database

```python
# Script per verificare lo stato del database
from storage_layer.mongodb_config import mongodb_config

# Test connessione
print("Connessione:", mongodb_config.test_connection())

# Info server
print("Server Info:", mongodb_config.get_server_info())

# Statistiche database
print("DB Stats:", mongodb_config.get_database_stats())
```

#### Controllo Integrità Dati

```python
# Verifica i dati generati
from storage_layer.storage_manager import StorageManager

sm = StorageManager()

# Conta asset per tipo
assets = sm.get_all_assets()
for asset_type in set(a.asset_type for a in assets):
    count = len([a for a in assets if a.asset_type == asset_type])
    print(f"{asset_type}: {count}")

# Conta metriche per asset
for asset in assets[:5]:  # Prime 5 macchine
    metrics = sm.get_metrics_by_asset_id(asset.asset_id, limit=1)
    print(f"{asset.hostname}: {len(metrics)} metriche")
```

---

## Monitoraggio e Logging

### Livelli di Logging

Il sistema utilizza diversi livelli di logging:

- **DEBUG**: Dettagli tecnici completi
- **INFO**: Informazioni generali sul progresso
- **WARNING**: Situazioni anomale ma gestibili
- **ERROR**: Errori che impediscono il completamento

### File di Log

```bash
# I log vengono scritti in:
logs/seed_database_YYYYMMDD_HHMMSS.log

# Esempio di contenuto:
2025-02-09 10:30:15 INFO     Avvio generazione dati
2025-02-09 10:30:16 INFO     Connessione MongoDB stabilita
2025-02-09 10:30:17 INFO     Creazione 10 asset infrastruttura
2025-02-09 10:30:18 INFO     Creazione 22 servizi
2025-02-09 10:30:19 INFO     Inizio generazione metriche
2025-02-09 10:32:45 INFO     Batch 1000/604800 completato (0.17%)
```

### Monitoraggio Progress

Il sistema fornisce feedback in tempo reale:

```
📈 Generazione metriche temporali...
   ├── Asset corrente: vm-101 (DB-SERVER-PROD)
   ├── Metrica: cpu_usage
   ├── Timestamp: 2025-02-09 10:30:00
   ├── Progress: [████████████████████] 100%
   ├── Velocità: 3,945 metriche/sec
   ├── Tempo rimanente: 2m 15s
   └── ETA: 10:32:45
```

### Statistiche Finali

Al completamento, il sistema mostra statistiche dettagliate:

```
✅ Generazione completata con successo!

📊 Statistiche Finali:
   ├── Tempo totale: 2m 34s
   ├── Asset creati: 34 (10 macchine + 22 servizi + 2 backup)
   ├── Metriche inserite: 604,800
   ├── Velocità media: 3,945 metriche/sec
   ├── Dimensione database: 45.2 MB
   └── Periodo dati: 2025-01-26 → 2025-02-09

🎯 Database pronto per l'utilizzo!
```

---

## Conclusioni

Il script `seed_database.py` è uno strumento potente e flessibile per popolare il database con dati realistici. La sua configurazione modulare e le opzioni avanzate lo rendono adatto sia per sviluppo rapido che per test di performance su larga scala.

### Prossimi Passi

1. **Verifica i dati generati** usando il dashboard PMI
2. **Personalizza i pattern** modificando `INFRASTRUCTURE_ASSETS`
3. **Estendi le metriche** aggiungendo nuovi tipi di misurazioni
4. **Automatizza l'esecuzione** con cron job per refresh periodici

### Supporto

Per problemi o domande:
- Consulta la sezione [Troubleshooting](#troubleshooting)
- Verifica i log dettagliati con `--log-level DEBUG`
- Controlla la configurazione MongoDB
- Usa `--assets-only` per test veloci senza metriche

---

*Documentazione aggiornata: Febbraio 2025*  
*Versione script: 2.0*  
*Compatibilità: Python 3.8+, MongoDB 4.4+*