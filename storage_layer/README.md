# Storage Layer - PMI Dashboard

## Panoramica

Il **Storage Layer** è il componente responsabile della gestione dei dati per il sistema PMI Dashboard. Fornisce un'interfaccia unificata per l'accesso ai dati di infrastruttura, metriche di performance e configurazioni di backup.

## Architettura

```
storage_layer/
├── mongodb_config.py      # 🔧 Configurazione MongoDB
├── storage_manager.py     # 📊 Gestione dati principale
├── models.py             # 📋 Modelli dati
├── exceptions.py         # ⚠️  Gestione errori
├── logging_config.py     # 📝 Configurazione logging
├── mongodb_utils.py      # 🛠️  Utilità MongoDB
├── .env.example          # 📄 Template configurazione
└── README.md            # 📖 Questa documentazione
```

## Installazione e Configurazione

### 1. Prerequisiti

```bash
# Python 3.8 o superiore
python --version

# MongoDB 4.4 o superiore
mongod --version

# Dipendenze Python
pip install pymongo python-dotenv
```

### 2. Configurazione MongoDB

```bash
# Copia il template di configurazione
cp storage_layer/.env.example storage_layer/.env

# Modifica la configurazione
nano storage_layer/.env
```

**Configurazione minima per sviluppo:**
```env
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DATABASE=pmi_infrastructure_dev
ENVIRONMENT=development
```

**Configurazione produzione:**
```env
MONGODB_HOST=mongodb-prod.example.com
MONGODB_PORT=27017
MONGODB_DATABASE=pmi_infrastructure
MONGODB_USERNAME=pmi_user
MONGODB_PASSWORD=your_secure_password
MONGODB_SSL_ENABLED=true
ENVIRONMENT=production
```

### 3. Test della Configurazione

```bash
# Test connessione MongoDB
python storage_layer/mongodb_utils.py --test-connection

# Mostra configurazione corrente
python storage_layer/mongodb_utils.py --show-config

# Crea indici ottimali
python storage_layer/mongodb_utils.py --create-indexes
```

## Utilizzo

### Connessione Base

```python
from storage_layer.mongodb_config import get_mongodb_client, get_mongodb_database

# Ottieni client MongoDB
client = get_mongodb_client()

# Ottieni database
db = get_mongodb_database()

# Test connessione
from storage_layer.mongodb_config import mongodb_config
if mongodb_config.test_connection():
    print("✅ Connessione OK")
```

### Storage Manager

```python
from storage_layer.storage_manager import StorageManager
from storage_layer.models import create_asset_document, create_metric_document
from datetime import datetime

# Inizializza storage manager
sm = StorageManager()

# Crea un asset
asset = create_asset_document(
    asset_id="vm-001",
    asset_type="vm",
    hostname="web-server-01",
    data={
        "status": "running",
        "cpu_cores": 4,
        "memory_gb": 16,
        "os": "Ubuntu 22.04"
    }
)

# Salva asset
sm.save_asset(asset)

# Crea una metrica
metric = create_metric_document(
    asset_id="vm-001",
    metric_name="cpu_usage",
    timestamp=datetime.utcnow(),
    value=75.5,
    unit="percentage"
)

# Salva metrica
sm.save_metric(metric)

# Recupera dati
assets = sm.get_all_assets()
metrics = sm.get_metrics_by_asset_id("vm-001", limit=100)
```

### Gestione Errori

```python
from storage_layer.exceptions import StorageManagerError

try:
    sm = StorageManager()
    assets = sm.get_all_assets()
except StorageManagerError as e:
    print(f"Errore storage: {e}")
except Exception as e:
    print(f"Errore generico: {e}")
```

## Modelli Dati

### Asset Document

```python
{
    "asset_id": "vm-001",           # ID univoco asset
    "asset_type": "vm",             # Tipo: vm, container, physical_host, etc.
    "hostname": "web-server-01",    # Nome host (opzionale)
    "service_name": None,           # Nome servizio (solo per servizi)
    "data": {                       # Dati specifici dell'asset
        "status": "running",
        "cpu_cores": 4,
        "memory_gb": 16,
        "os": "Ubuntu 22.04"
    },
    "created_at": "2025-02-09T10:30:00Z",
    "updated_at": "2025-02-09T10:30:00Z"
}
```

### Metric Document

```python
{
    "asset_id": "vm-001",           # Riferimento all'asset
    "metric_name": "cpu_usage",     # Nome metrica
    "timestamp": "2025-02-09T10:30:00Z",
    "value": 75.5,                  # Valore numerico
    "unit": "percentage",           # Unità di misura
    "tags": {                       # Tag aggiuntivi (opzionale)
        "environment": "production",
        "datacenter": "dc1"
    },
    "created_at": "2025-02-09T10:30:00Z"
}
```

## Utilità MongoDB

Il modulo `mongodb_utils.py` fornisce strumenti per la gestione del database:

### Test e Diagnostica

```bash
# Test connessione completo
python storage_layer/mongodb_utils.py --test-connection

# Statistiche database
python storage_layer/mongodb_utils.py --database-stats

# Test performance
python storage_layer/mongodb_utils.py --performance-test --duration 120
```

### Gestione Indici

```bash
# Crea indici ottimali
python storage_layer/mongodb_utils.py --create-indexes

# Mostra indici esistenti
python storage_layer/mongodb_utils.py --show-indexes
```

### Manutenzione

```bash
# Pulisci dati vecchi (30 giorni)
python storage_layer/mongodb_utils.py --cleanup-old-data --days 30

# Backup database
python storage_layer/mongodb_utils.py --backup-database /path/to/backup
```

## Configurazioni per Ambiente

### Sviluppo

```env
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DATABASE=pmi_infrastructure_dev
ENVIRONMENT=development
MONGODB_MAX_POOL_SIZE=50
MONGODB_LOG_LEVEL=DEBUG
```

### Test

```env
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DATABASE=pmi_infrastructure_test
ENVIRONMENT=testing
MONGODB_MAX_POOL_SIZE=10
MONGODB_LOG_LEVEL=DEBUG
```

### Produzione

```env
MONGODB_HOST=mongodb-cluster.example.com
MONGODB_PORT=27017
MONGODB_DATABASE=pmi_infrastructure
MONGODB_USERNAME=pmi_user
MONGODB_PASSWORD=secure_password
MONGODB_AUTH_SOURCE=admin
MONGODB_SSL_ENABLED=true
MONGODB_REPLICA_SET=rs0
ENVIRONMENT=production
MONGODB_MAX_POOL_SIZE=200
MONGODB_MIN_POOL_SIZE=20
MONGODB_LOG_LEVEL=WARNING
```

## Indici Ottimali

Il sistema crea automaticamente questi indici per performance ottimali:

### Collezione `assets`
- `asset_id` (unique) - Ricerca rapida per ID
- `asset_type` - Filtro per tipo asset
- `hostname` - Ricerca per hostname
- `asset_type + data.parent_asset_id` - Query servizi per parent

### Collezione `metrics`
- `asset_id + timestamp` - Query temporali per asset
- `metric_name` - Filtro per tipo metrica
- `asset_id + metric_name + timestamp` - Query specifiche ottimizzate
- `timestamp` (TTL 90 giorni) - Pulizia automatica dati vecchi

## Performance e Scalabilità

### Ottimizzazioni Implementate

1. **Batch Insert**: Inserimento metriche in batch per ridurre overhead
2. **Connection Pooling**: Pool di connessioni configurabile per ambiente
3. **Indici Ottimali**: Indici specifici per pattern di query comuni
4. **TTL Index**: Pulizia automatica dati vecchi
5. **Retry Logic**: Retry automatico per operazioni fallite

### Metriche di Performance Tipiche

- **Inserimento metriche**: 3,000-5,000 record/sec
- **Query asset**: 1,000-2,000 ops/sec
- **Query metriche temporali**: 500-1,000 ops/sec
- **Dimensione database**: ~45MB per 14 giorni di dati (10 macchine)

### Scalabilità

Il sistema è progettato per gestire:
- **Asset**: Fino a 10,000 macchine/servizi
- **Metriche**: Fino a 100M record (con TTL appropriato)
- **Throughput**: Fino a 10,000 metriche/sec con hardware adeguato

## Monitoraggio e Logging

### Configurazione Logging

```python
import logging
from storage_layer.logging_config import setup_logging

# Setup logging per l'applicazione
setup_logging(level=logging.INFO)

# Logger specifico per storage
logger = logging.getLogger('storage_layer')
logger.info("Operazione completata")
```

### Metriche di Sistema

```python
from storage_layer.mongodb_config import mongodb_config

# Statistiche database
stats = mongodb_config.get_database_stats()
print(f"Documenti: {stats.get('objects', 0):,}")
print(f"Dimensione: {stats.get('dataSize', 0)} bytes")

# Info server
server_info = mongodb_config.get_server_info()
print(f"Versione MongoDB: {server_info.get('version')}")
```

## Backup e Ripristino

### Backup Automatico

```bash
# Backup completo
python storage_layer/mongodb_utils.py --backup-database /backup/pmi_$(date +%Y%m%d)

# Script cron per backup giornaliero
0 2 * * * /usr/bin/python /path/to/storage_layer/mongodb_utils.py --backup-database /backup/pmi_$(date +\%Y\%m\%d)
```

### Ripristino

```bash
# Ripristino da backup
mongorestore --host localhost:27017 --db pmi_infrastructure /backup/pmi_20250209/pmi_infrastructure
```

## Troubleshooting

### Problemi Comuni

#### 1. Errore di Connessione
```bash
# Verifica MongoDB in esecuzione
sudo systemctl status mongod

# Test connessione manuale
mongosh --host localhost --port 27017
```

#### 2. Errore Autenticazione
```bash
# Verifica credenziali
grep MONGODB_USERNAME storage_layer/.env
grep MONGODB_PASSWORD storage_layer/.env

# Test autenticazione
mongosh "mongodb://username:password@localhost:27017/database"
```

#### 3. Performance Lente
```bash
# Verifica indici
python storage_layer/mongodb_utils.py --show-indexes

# Crea indici mancanti
python storage_layer/mongodb_utils.py --create-indexes

# Test performance
python storage_layer/mongodb_utils.py --performance-test
```

#### 4. Spazio Disco
```bash
# Verifica spazio
df -h

# Pulizia dati vecchi
python storage_layer/mongodb_utils.py --cleanup-old-data --days 30
```

### Debug Avanzato

```python
# Abilita logging dettagliato
import logging
logging.getLogger('pymongo').setLevel(logging.DEBUG)

# Test connessione con dettagli
from storage_layer.mongodb_config import MongoDBConfig
config = MongoDBConfig()
print("Config:", config.config)
print("Connection String:", config.get_connection_string())
```

## Sicurezza

### Best Practices Implementate

1. **Autenticazione**: Username/password configurabili
2. **SSL/TLS**: Supporto crittografia in transito
3. **Autorizzazione**: Database-level permissions
4. **Connection Limits**: Pool size limitato
5. **Timeout**: Timeout configurabili per prevenire hang
6. **Sanitization**: Rimozione credenziali dai log

### Configurazione Sicura

```env
# Produzione sicura
MONGODB_SSL_ENABLED=true
MONGODB_SSL_CERT_PATH=/path/to/client.pem
MONGODB_SSL_CA_PATH=/path/to/ca.pem
MONGODB_AUTH_SOURCE=admin
MONGODB_RETRY_WRITES=true
```

## Estensioni Future

### Funzionalità Pianificate

1. **Sharding**: Supporto per cluster MongoDB sharded
2. **Read Replicas**: Bilanciamento letture su replica set
3. **Aggregation Pipeline**: Query complesse ottimizzate
4. **Time Series**: Collezioni time-series native MongoDB 5.0+
5. **Change Streams**: Notifiche real-time per modifiche dati

### API Estese

```python
# Aggregazioni avanzate (futuro)
sm.get_metrics_aggregated(
    asset_ids=["vm-001", "vm-002"],
    metric_names=["cpu_usage", "memory_usage"],
    aggregation="avg",
    interval="1h",
    start_time=datetime.utcnow() - timedelta(days=7)
)

# Query geografiche (futuro)
sm.get_assets_by_location(
    datacenter="dc1",
    rack="A1"
)
```

## Supporto

Per problemi o domande:

1. **Verifica configurazione**: `python storage_layer/mongodb_utils.py --test-connection`
2. **Consulta log**: File di log in `logs/` directory
3. **Test performance**: `python storage_layer/mongodb_utils.py --performance-test`
4. **Documentazione completa**: Vedi `../Docs/Storage+Generator/SEED_DATABASE_DOCUMENTATION.md`

---

*Documentazione Storage Layer - Febbraio 2025*  
*Versione: 2.0*  
*Compatibilità: Python 3.8+, MongoDB 4.4+*