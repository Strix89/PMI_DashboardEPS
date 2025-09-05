# Metrics Dashboard - Sistema di Monitoraggio Availability e Resilience

**Metrics Dashboard** è una web application Flask avanzata che fornisce analisi cumulativa e monitoraggio real-time delle metriche di **availability** e **resilience** per servizi infrastrutturali e sistemi di backup. Il sistema connette a MongoDB per recuperare metriche operative e genera dashboard interattive per il monitoraggio della salute dei servizi e della resilienza dei backup.

## 🏗️ Architettura del Sistema

### **Componenti Principali**

1. **Flask Web Application** (`app.py`)
   - Server web principale con routing e API endpoints per entrambi i moduli
   - Gestione sessioni utente e configurazioni personalizzate
   - Job manager per analisi asincrone in background per availability e resilience

2. **Availability Analytics**
   - **Cumulative Availability Analyzer** (`utils/cumulative_availability_analyzer.py`)
     - Motore di calcolo delle metriche cumulative di disponibilità servizi
     - Algoritmo di scoring basato su error budget configurabili
   - **Availability Summary** (`utils/availability_summary.py`)
     - Modulo di aggregazione e riepilogo delle metriche di availability

3. **Resilience Analytics** (NUOVO)
   - **Cumulative Resilience Analyzer** (`utils/cumulative_resilience_analyzer.py`)
     - Motore di analisi della resilienza dei sistemi di backup
     - Calcolo di RPO Compliance e Success Rate per backup jobs e asset
     - Scoring ponderato basato su parametri configurabili
   - **Backup Summary** (`utils/backup_summary.py`)
     - Modulo di aggregazione per metriche di backup e resilienza

4. **Storage Layer Integration**
   - Integrazione con `storage_layer.storage_manager` per connettività MongoDB
   - Accesso a collection "assets", "metrics" e dati di backup del database PMI

## 🔬 Algoritmi di Scoring

### **Formula Cumulativa di Availability**

Il sistema implementa un algoritmo sofisticato per il calcolo del score di availability:

```
S(P_f, E_b) = 
- 100% se P_f = 0                                    (Nessun fallimento)
- 100% - (P_f/E_b × 50%) se 0 < P_f ≤ E_b           (Fallimenti sotto soglia)
- max(0, 50% - ((P_f - E_b)/E_b × 50%)) se P_f > E_b (Fallimenti sopra soglia)
```

**Dove:**
- `P_f` = Numero di fallimenti cumulativi per servizio
- `E_b` = Error Budget configurabile per tipo di servizio

### **Formula Cumulativa di Resilience** (NUOVO)

Il sistema calcola la resilience dei backup utilizzando un approccio multi-metrica:

```
Resilience_Score = (w_RPO × RPO_Compliance) + (w_Success × Success_Rate)
```

**Dove:**
- `RPO_Compliance = max(0, 1 - (actual_RPO / target_RPO))`
- `Success_Rate = backup_riusciti_cumulativi / backup_totali_cumulativi`
- `w_RPO` = Peso per RPO Compliance (default: 60%)
- `w_Success` = Peso per Success Rate (default: 40%)

**Target RPO Default per Tipo Asset:**
- Virtual Machines: 24 ore
- Container: 12 ore
- Server Fisici: 48 ore
- Nodi Proxmox: 24 ore
- Backup Jobs Acronis: 24 ore

### **Classificazione Status**

**Availability Status:**
| Score Range | Status | Descrizione |
|-------------|---------|-------------|
| < 50% | **CRITICAL** | Servizio in stato critico |
| 50% - 80% | **ATTENZIONE** | Servizio degradato |
| > 80% | **GOOD** | Servizio operativo |

**Resilience Status:** (NUOVO)
| Score Range | Status | Descrizione |
|-------------|---------|-------------|
| > 90% | **EXCELLENT** | Resilienza eccellente |
| 75% - 90% | **GOOD** | Resilienza buona |
| 60% - 75% | **ACCEPTABLE** | Resilienza accettabile |
| 40% - 60% | **CRITICAL** | Resilienza critica |
| < 40% | **SEVERE** | Resilienza severa |

```
metrics_dashboard/
├── app.py                          # Flask application server principale
├── run.py                          # Script di avvio dell'applicazione
├── requirements.txt                # Dipendenze Python specifiche
├── config.py                       # Configurazioni globali (se presente)
├── .env                           # Variabili d'ambiente di produzione
├── .env.example                   # Template per configurazione
├── __init__.py                    # Package initialization
├── templates/                     # Template HTML Jinja2
│   ├── base.html                 # Template base (se presente)
│   ├── index.html                # Pagina principale di selezione modulo
│   # AVAILABILITY MODULE
│   ├── availability_index.html   # Pagina selezione analisi availability
│   ├── availability_config.html  # Interfaccia configurazione availability
│   └── availability_dashboard.html # Dashboard real-time availability
│   # RESILIENCE MODULE (NUOVO)
│   ├── resilience_index.html     # Pagina selezione analisi resilience  
│   ├── resilience_config.html    # Interfaccia configurazione resilience
│   └── resilience_dashboard.html # Dashboard real-time resilience
├── static/                       # Assets statici (CSS, JS, immagini)
│   ├── css/
│   │   └── style.css            # Fogli di stile custom
│   └── js/
│       ├── configuration.js      # Logic configurazione frontend
│       ├── dashboard.js          # Logic dashboard interattiva
│       └── theme.js              # Gestione tema chiaro/scuro
├── utils/                        # Moduli di utility e business logic
│   # AVAILABILITY ANALYTICS
│   ├── cumulative_availability_analyzer.py  # Core analyzer engine availability
│   ├── availability_summary.py              # Summary aggregator availability
│   # RESILIENCE ANALYTICS (NUOVO)
│   ├── cumulative_resilience_analyzer.py    # Core analyzer engine resilience
│   └── backup_summary.py                    # Summary aggregator backup/resilience
├── output/                       # Directory per output JSON generati
│   ├── cumulative_availability_analysis_*.json  # Report availability
│   └── resilience_analysis_*.json               # Report resilience (NUOVO)
└── __pycache__/                  # Cache Python compilato
```

## 🚀 Funzionalità Principali

### **Modulo Availability**

#### **1. Configurazione Dinamica dei Parametri**
- **Selezione Servizi**: Recupero automatico da collection MongoDB "assets"
- **Error Budget Personalizzabili**: Configurazione soglie per ogni servizio
- **Pesi di Criticità**: Definizione dell'impatto di ogni servizio sull'health score aggregato

#### **2. Analisi Cumulativa in Background**
- **Job Manager Asincrono**: Esecuzione di task lunghi senza bloccare l'interfaccia
- **Progress Tracking**: Monitoraggio dello stato di avanzamento delle analisi
- **Subprocess Execution**: Invocazione del cumulative analyzer come processo separato
- **Error Handling**: Gestione completa degli errori durante l'analisi

#### **3. Dashboard Real-time Interattiva**
- **Tachimetri Semicircolari**: Visualizzazione percentuale availability per servizio
- **Health Score Aggregato**: Calcolo ponderato basato su criticità configurate
- **Timeline Navigation**: Controlli play/pause per scorrimento temporale dei dati
- **Status Indicators**: Codifica a colori per stato operativo (Critical/Attenzione/Good)

### **Modulo Resilience** (NUOVO)

#### **1. Configurazione Avanzata RPO e Pesi**
- **Target RPO Personalizzabili**: Configurazione obiettivi RPO per asset e backup jobs
- **Pesi Metriche Configurabili**: Bilanciamento tra RPO Compliance e Success Rate
- **Selezione Asset e Backup Jobs**: Recupero automatico da MongoDB con filtri per tipo
- **Configurazione per Tipo Asset**: VM, Container, Server Fisici, Nodi Proxmox

#### **2. Analisi Resilience Cumulativa**
- **Simulazione Settimanale**: Analisi ora per ora per 168 ore (1 settimana)
- **RPO Compliance Calculation**: Monitoraggio deviazioni dai target RPO configurati
- **Success Rate Tracking**: Calcolo percentuale successo backup cumulativo
- **Weighted Scoring**: Combinazione ponderata delle metriche con pesi configurabili

#### **3. Dashboard Resilience Interattiva**
- **Grafico a Ciambella Aggregato**: Visualizzazione distribuzione livelli di resilience
- **Indicatori Circolari**: Score resilience per singolo asset/backup job
- **Timeline Temporale**: Navigazione cronologica dell'andamento resilience
- **Status Colorati**: Classificazione visiva (Excellent/Good/Acceptable/Critical/Severe)

#### **4. Gestione File JSON di Output**
- **Selezione File Esistenti**: Caricamento analisi resilience precedenti
- **Report Strutturati**: File JSON con configurazione, timeline e metriche dettagliate
- **Timestamp Automatico**: Nomenclatura file con data/ora generazione
- **Persistenza Configurazione**: Salvataggio parametri per riuso futuro

### **4. Integrazione Storage Layer**
- **MongoDB Connection**: Accesso diretto al database PMI infrastructure
- **AssetDocument Models**: Utilizzo di modelli strutturati per asset management
- **Metrics Collection**: Query ottimizzate per recupero metriche operative

## 🛠️ Installazione e Configurazione

### **Prerequisiti Sistema**
```powershell
# Windows PowerShell - Verifica Python
python --version  # Richiede Python 3.8+

# Verifica MongoDB in esecuzione
# MongoDB deve essere accessibile con dati nelle collection "assets" e "metrics"
```

### **Setup Ambiente di Sviluppo**
```powershell
# Navigazione alla directory
cd C:\Users\tomma\Desktop\PMI_DashboardEPS\metrics_dashboard

# Installazione dipendenze
pip install -r requirements.txt

# Configurazione variabili d'ambiente
copy .env.example .env
# Modificare .env con i parametri corretti
```

### **Configurazione Database (.env)**
```env
# MongoDB Configuration
MONGODB_CONNECTION_STRING=mongodb://localhost:27017
MONGODB_DATABASE_NAME=pmi_infrastructure

# Flask Configuration
FLASK_SECRET_KEY=metrics-dashboard-secret-2025
FLASK_ENV=production

# Default Parameters
DEFAULT_ERROR_BUDGET=5
```

### **Avvio Applicazione**
```powershell
# Avvio del server Flask
python app.py

# Oppure usando lo script di run
python run.py
```

**🌐 Accesso Web**: `http://localhost:5001`

## 💻 Workflow Operativo Dettagliato

### **Selezione Modulo**

**Pagina Principale** (`http://localhost:5001`)
- **Availability Module**: Monitoraggio disponibilità servizi infrastrutturali
- **Resilience Module**: Analisi resilienza backup e RPO compliance

### **Availability Workflow**

#### **Phase 1: Configurazione Availability**

1. **Accesso Pagina Availability** (`/availability`)
   - Selezione tra file JSON esistenti o nuova configurazione
   - Routing verso template `availability_index.html`

2. **Recupero Servizi Disponibili**
   - **Endpoint**: `GET /get_services`
   - **Logic**: Query MongoDB collection "assets" per recupero lista servizi
   - **Output**: JSON con service_id, display_name, service_type per ogni servizio

3. **Configurazione Parametri** (`/availability/config`)
   - **Error Budget**: Impostazione soglie fallimenti per ogni servizio
   - **Service Weights**: Definizione criticità/impatto per health score aggregato
   - **Validation**: Controlli real-time su range valori (error budget 1-50, weights 1-10)

#### **Phase 2: Esecuzione Analisi Availability**

1. **Avvio Job di Analisi**
   - **Endpoint**: `POST /start_analysis`
   - **Payload**: Configurazione JSON con parametri utente
   - **Analysis Type**: `"availability"`
   - **Logic**: `AnalysisJobManager.start_analysis()` crea thread separato

2. **Background Processing**
   - **File Temporaneo**: Creazione `temp_config.json` con configurazione
   - **Subprocess Call**: Esecuzione `cumulative_availability_analyzer.py` 
   - **Command Line**: 
     ```
     python utils/cumulative_availability_analyzer.py 
     --connection-string mongodb://localhost:27017 
     --database-name pmi_infrastructure 
     --config-file temp_config.json
     ```

### **Resilience Workflow** (NUOVO)

#### **Phase 1: Configurazione Resilience**

1. **Accesso Pagina Resilience** (`/resilience`)
   - Selezione tra file JSON resilience esistenti o nuova configurazione
   - Routing verso template `resilience_index.html`
   - Lista file `resilience_analysis_*.json` disponibili

2. **Recupero Asset e Backup Jobs**
   - **Endpoint**: `GET /get_services` (per asset)
   - **Endpoint**: `GET /get_backup_jobs` (per backup jobs Acronis)
   - **Logic**: Query MongoDB per asset con backup e backup jobs configurati

3. **Configurazione Parametri Resilience** (`/resilience/config`)
   - **Target RPO**: Configurazione obiettivi RPO in ore per ogni asset/backup job
   - **Metric Weights**: Bilanciamento w_RPO (60%) e w_Success (40%)
   - **Asset Selection**: Selezione asset da includere nell'analisi
   - **Validation**: Controlli su range RPO (1-168 ore) e pesi (0.0-1.0)

#### **Phase 2: Esecuzione Analisi Resilience**

1. **Avvio Job di Analisi Resilience**
   - **Endpoint**: `POST /start_analysis`
   - **Analysis Type**: `"resilience"`
   - **Payload**: Configurazione con target RPO e pesi personalizzati

2. **Background Processing Resilience**
   - **Subprocess Call**: Esecuzione `cumulative_resilience_analyzer.py`
   - **Simulazione**: 168 ore (1 settimana) di analisi cumulativa
   - **Output**: File `resilience_analysis_YYYYMMDD_HHMMSS.json`

#### **Phase 3: Algoritmo Resilience Core**

1. **RPO Compliance Calculation**
   ```python
   RPO_Compliance = max(0, 1 - (actual_RPO / target_RPO))
   ```
   - **Actual RPO**: Tempo trascorso dall'ultimo backup riuscito
   - **Target RPO**: Obiettivo configurato per asset/backup job

2. **Success Rate Tracking**
   ```python
   Success_Rate = backup_riusciti_cumulativi / backup_totali_cumulativi
   ```

3. **Weighted Resilience Score**
   ```python
   Resilience = (w_RPO × RPO_Compliance) + (w_Success × Success_Rate)
   ```

4. **Status Classification**
   - **EXCELLENT** (>90%): Resilienza eccellente
   - **GOOD** (75-90%): Resilienza buona  
   - **ACCEPTABLE** (60-75%): Resilienza accettabile
   - **CRITICAL** (40-60%): Resilienza critica
   - **SEVERE** (<40%): Resilienza severa

#### **Phase 4: Dashboard Resilience Visualization**

1. **Data Retrieval** (`/resilience/get_dashboard_data`)
   - Parsing JSON resilience e trasformazione per frontend
   - Calcolo aggregati per grafico a ciambella

2. **Visualizzazioni Interattive**
   - **Donut Chart**: Distribuzione livelli resilience aggregati
   - **Circular Indicators**: Score individuale per asset/backup job
   - **Timeline Navigation**: Scorrimento temporale 168 ore
   - **Status Indicators**: Codifica colori per livelli resilience

### **Gestione Comune (Entrambi i Moduli)**

#### **Progress Monitoring**
- **Endpoint**: `GET /job_status`
- **Status Types**: `idle`, `running`, `completed`, `error`
- **Progress**: Percentuale 0-100% con step intermedi

#### **File Management**
- **Output Directory**: `metrics_dashboard/output/`
- **Availability Files**: `cumulative_availability_analysis_*.json`
- **Resilience Files**: `resilience_analysis_*.json`
- **Load Existing**: Caricamento file precedenti tramite interfaccia web
   - **Update Frequency**: Default 60 secondi configurabile
   - **Controls**: Play/Pause, Reset, Speed multiplier

3. **UI Components**
   - **Tachimetri**: Gauge semicircolari con colore basato su status
   - **Health Score**: Valore aggregato in evidenza
   - **Service Cards**: Dettagli per ogni servizio (failures, error budget, weight)

## 🔧 API Endpoints Completa
| Endpoint | Metodo | Parametri | Descrizione | Response |
|----------|--------|-----------|-------------|----------|
| `/` | GET | - | Pagina di configurazione iniziale | HTML template |
| `/get_services` | GET | - | Lista servizi da MongoDB collection "assets" | `{success: bool, services: [...]}` |
| `/start_analysis` | POST | `config: JSON` | Avvia job di analisi asincrono | `{success: bool, message: string}` |
| `/job_status` | GET | - | Status corrente del job di analisi | `{status: string, progress: int, result: {...}}` |
| `/dashboard` | GET | - | Pagina dashboard con risultati | HTML template (redirect se no data) |
| `/get_dashboard_data` | GET | - | Dati formattati per dashboard frontend | `{success: bool, services: {...}, aggregated_health_score: float}` |
| `/reset_config` | GET | - | Reset configurazione e redirect | Redirect to index |

## ⚙️ Moduli Core e Classi

### **app.py - Flask Application**

**Classi principali:**

- **`AnalysisJobManager`**: 
  - Gestione job asincroni con threading
  - Status tracking (`idle`, `running`, `completed`, `error`)
  - Progress monitoring con percentuali
  - Result storage per dashboard consumption

**Configurazione:**
- **Database Config**: Connection string e database name da variabili d'ambiente
- **Session Management**: Flask session per configurazione utente persistente
- **Logging**: Structured logging per debug e monitoring

### **cumulative_availability_analyzer.py - Core Engine**

**Classi principali:**

- **`CumulativeAvailabilityAnalyzer`**:
  - **`__init__(storage_manager, config)`**: Inizializzazione con storage e config personalizzata
  - **`analyze_random_day()`**: Selezione casuale giorno e esecuzione analisi
  - **`run_cumulative_analysis(date, services)`**: Core algorithm per calcolo score
  - **`calculate_score(failures, error_budget)`**: Implementazione formula matematica

**Configurazioni Default:**
```python
default_service_eb_config = {
    "web_service": 5,      # Servizi web (nginx, apache)
    "database": 3,         # Database (mysql, redis)
    "application": 8,      # Applicazioni (tomcat, reporting)
    "backup": 10,          # Servizi di backup
    "monitoring": 4,       # Prometheus, grafana
    "mail": 6,             # Postfix, dovecot
    "ci_cd": 7,            # Jenkins, gitlab-runner
    "file_sharing": 5,     # NFS, SMB
    "default": 5           # Fallback value
}
```

**Algoritmo Timeline:**
1. **Time Range Extraction**: Recupero min/max timestamp dal giorno selezionato
2. **Failure Aggregation**: Conteggio cumulativo fallimenti per timestamp
3. **Score Evolution**: Calcolo score progressivo applicando formula matematica
4. **Status Classification**: Mapping percentuale → status enum

### **Storage Layer Integration**

**Dipendenze:**
- **`storage_layer.storage_manager.StorageManager`**: Connection manager MongoDB
- **`storage_layer.models.AssetDocument`**: Modello strutturato per asset
- **`storage_layer.exceptions.StorageManagerError`**: Error handling specifico

**Query Patterns:**
```python
# Recupero servizi
assets = storage_manager.get_all_assets()

# Query metriche per giorno specifico
pipeline = [
    {"$match": {"timestamp": {"$gte": start_date, "$lt": end_date}}},
    {"$sort": {"timestamp": 1}},
    {"$group": {"_id": "$service_id", "metrics": {"$push": "$$ROOT"}}}
]
```

## 🎨 Frontend Architecture

### **Templates Structure**

1. **`index.html`** - Landing page con navigation
2. **`config.html`** - Multi-step configuration wizard
3. **`dashboard.html`** - Real-time monitoring interface

### **JavaScript Components**

1. **`configuration.js`**:
   - Form validation real-time
   - AJAX calls per service loading
   - Progress tracking durante analisi
   - Error handling user-friendly

2. **`dashboard.js`**:
   - Gauge rendering per tachimetri
   - Timeline management con play/pause controls
   - Real-time data updates via polling
   - Theme switching light/dark

3. **`theme.js`**:
   - CSS custom properties management
   - Local storage per persistenza tema
   - Dynamic color scheme switching

### **CSS Architecture**

- **CSS Custom Properties**: Theming con variabili CSS
- **Responsive Design**: Mobile-first approach
- **Component-based**: Modularità per riutilizzo
- **Animation**: Smooth transitions per user experience

## 📋 Formato Output JSON

### **Struttura File Generato**

Il `cumulative_availability_analyzer.py` genera file JSON nella directory `output/` con questa struttura:

```json
{
  "analysis_timestamp": "2025-09-04T10:30:00Z",
  "analysis_dates": ["2025-09-01"],
  "configuration": {
    "service_error_budgets": {"service1": 5, "service2": 3},
    "service_weights": {"service1": 8, "service2": 6}
  },
  "services": {
    "service1": {
      "service_id": "nginx_web",
      "error_budget": 5,
      "weight": 8,
      "final_score": 85.6,
      "final_status": "GOOD",
      "total_failures": 2,
      "detailed_metrics": [
        {
          "timestamp": "2025-09-01T08:00:00Z",
          "cumulative_failures": 0,
          "score": 1.0,
          "status_type": "GOOD"
        },
        {
          "timestamp": "2025-09-01T08:15:00Z", 
          "cumulative_failures": 1,
          "score": 0.90,
          "status_type": "GOOD"
        }
      ]
    }
  },
  "summary": {
    "aggregated_score": 87.3,
    "total_services": 12,
    "services_by_status": {
      "GOOD": 8,
      "ATTENZIONE": 3,
      "CRITICAL": 1
    }
  }
}
```

## 🔍 Configurazione Avanzata e Troubleshooting

### **Variabili d'Ambiente (.env)**

```env
# MongoDB Configuration
MONGODB_CONNECTION_STRING=mongodb://localhost:27017
MONGODB_DATABASE_NAME=pmi_infrastructure

# Flask Application  
FLASK_SECRET_KEY=metrics-dashboard-secret-key-2025
FLASK_ENV=development  # o production
FLASK_DEBUG=True       # per development

# Application Defaults
DEFAULT_ERROR_BUDGET=5

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/metrics_dashboard.log

# Performance Settings
MAX_ANALYSIS_TIMEOUT=300  # 5 minuti timeout per analisi
DASHBOARD_UPDATE_INTERVAL=60000  # 60 secondi in millisecondi
```

### **Personalizzazione Algoritmi**

**Error Budget per Tipo di Servizio:**
```python
# In cumulative_availability_analyzer.py
default_service_eb_config = {
    "web_service": 5,       # Servizi HTTP/HTTPS
    "database": 3,          # DB critici (bassa tolleranza errori)
    "application": 8,       # App server (tolleranza media)
    "backup": 10,           # Backup job (alta tolleranza)  
    "monitoring": 4,        # Sistemi monitoring (criticità alta)
    "mail": 6,              # Mail server (tolleranza media)
    "ci_cd": 7,             # CI/CD pipeline (tolleranza media-alta)
    "file_sharing": 5,      # File server (tolleranza media)
    "default": 5            # Fallback per servizi non classificati
}
```

**Soglie Status Classification:**
```python
status_thresholds = {
    "critical": 0.5,       # < 50% = CRITICAL
    "attenzione": 0.8      # 50%-80% = ATTENZIONE, > 80% = GOOD
}
```

### **Performance Tuning**

**MongoDB Query Optimization:**
- **Indexing**: Ensure indexes on `timestamp`, `service_id`, `status` fields
- **Aggregation Pipeline**: Utilizzo di `$match` early per ridurre dataset
- **Connection Pooling**: Storage manager con connection reuse

**Flask Application:**
- **Threading**: `threaded=True` per job background
- **Session Storage**: File system vs Redis per session scalabili
- **Template Caching**: Jinja2 cache per template rendering

## 🚨 Error Handling e Logging

### **Exception Management**

1. **Storage Layer Errors**:
   - `StorageManagerError`: Errori connessione MongoDB
   - Auto-retry mechanism per connection failures
   - Graceful degradation se servizi non disponibili

2. **Analysis Errors**:
   - Timeout handling per analisi lunghe
   - Partial results se alcuni servizi falliscono
   - Memory management per dataset grandi

3. **Frontend Error Handling**:
   - User-friendly error messages
   - Automatic retry per network errors
   - Progress indication durante recovery

### **Logging Strategy**

```python
# Structured logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/metrics_dashboard.log', encoding='utf-8')
    ]
)

# Log levels per component
logger.setLevel(logging.DEBUG)  # Development
logger.setLevel(logging.INFO)   # Production
logger.setLevel(logging.ERROR)  # Critical only
```

## � Security Considerations

### **Data Security**

- **Session Management**: Flask session con secret key sicura
- **Input Validation**: Sanitization di tutti gli input utente
- **SQL/NoSQL Injection**: Utilizzo di parametrized queries
- **XSS Protection**: Auto-escape nei template Jinja2

### **Network Security**

- **HTTPS Enforcement**: Configurazione SSL per production
- **CORS Policy**: Restriction degli origin permessi
- **Rate Limiting**: Protection contro brute force
- **Authentication**: Integration con sistemi enterprise (LDAP, AD)

## � Monitoring e Metrics

### **Application Metrics**

- **Response Times**: Monitoring endpoint performance
- **Error Rates**: Tracking di fallimenti per endpoint
- **Memory Usage**: Monitoring Python process memory
- **Database Connections**: Pool utilization tracking

### **Business Metrics**

- **Analysis Frequency**: Numero di analisi availability e resilience per giorno/ora
- **Service Coverage**: Percentuale servizi monitorati per availability
- **Backup Coverage**: Percentuale asset con backup monitorati per resilience (NUOVO)
- **RPO Compliance**: Tracking compliance ai target RPO configurati (NUOVO)
- **User Engagement**: Utilizzo dashboard availability vs resilience
- **Data Quality**: Completezza dati availability e backup metrics

## 🧪 Testing e Quality Assurance

### **Unit Testing**

```powershell
# Esecuzione test suite
python -m pytest tests/ -v

# Coverage report
python -m pytest --cov=metrics_dashboard --cov-report=html
```

### **Integration Testing**

- **MongoDB Integration**: Test con database di test
- **Flask App Testing**: Test endpoints con client di test
- **Frontend Testing**: Selenium per UI testing
- **Performance Testing**: Load testing con locust

## 📈 Scalability e Performance

### **Horizontal Scaling**

- **Load Balancing**: Multiple Flask instances con nginx
- **Database Sharding**: MongoDB sharding per dataset grandi
- **Caching Layer**: Redis per caching risultati analisi
- **CDN**: Delivery ottimizzata per static assets

### **Vertical Optimization**

- **Database Indexing**: Compound indexes per query complex
- **Memory Management**: Garbage collection tuning Python
- **Connection Pooling**: MongoDB connection pool optimization
- **Async Processing**: Celery per job heavy background

## 📖 Integration Points

### **PMI Dashboard EPS Ecosystem**

1. **Storage Layer**: Shared MongoDB access con altri componenti
2. **Asset Management**: Utilizzo modelli comuni per asset con estensione backup data
3. **Network Discovery**: Correlation con network topology data
4. **Proxmox Integration**: Metriche infrastructure da Proxmox API con backup correlation
5. **Acronis Integration**: Backup status correlation e RPO tracking per resilience (NUOVO)

### **External Systems**

- **Monitoring Systems**: Prometheus metrics export per availability e resilience
- **Alerting**: Integration con PagerDuty, Slack per alerting su threshold availability/RPO
- **Ticketing**: JIRA integration per incident management e backup failures  
- **Reporting**: Export data per business intelligence tools con metriche resilience
- **Backup Systems**: API integration con Acronis e altri backup vendor (NUOVO)

---

## � Riepilogo Funzionalità Resilience Module

Il **Modulo Resilience** rappresenta un'estensione completa del Metrics Dashboard che introduce il monitoraggio avanzato della resilienza dei sistemi di backup. Le caratteristiche principali includono:

### **Caratteristiche Distintive**

✅ **Analisi RPO Compliance**: Monitoraggio automatico della conformità ai Recovery Point Objective configurati  
✅ **Multi-Asset Support**: Supporto per VM, Container, Server Fisici, Nodi Proxmox e Backup Jobs Acronis  
✅ **Weighted Scoring**: Sistema di punteggio ponderato configurabile tra RPO e Success Rate  
✅ **Timeline Analysis**: Analisi cumulativa su 168 ore (1 settimana) con granularità oraria  
✅ **Interactive Dashboard**: Visualizzazioni interattive con grafici a ciambella e indicatori circolari  
✅ **Custom Configuration**: Target RPO e pesi personalizzabili per ogni asset/backup job  
✅ **Status Classification**: 5 livelli di resilience (Excellent/Good/Acceptable/Critical/Severe)  
✅ **JSON Export**: Report strutturati con configurazione e metriche dettagliate  

### **Casi d'Uso Tipici**

🎯 **Compliance Monitoring**: Verifica conformità ai SLA di backup aziendali  
🎯 **Risk Assessment**: Identificazione asset con resilience inadeguata  
🎯 **Capacity Planning**: Analisi trend per dimensionamento backup infrastructure  
🎯 **SLA Reporting**: Generazione report per management e audit  
🎯 **Preventive Maintenance**: Early warning per degradation backup performance  

---

## �👨‍💻 Development Guidelines

### **Code Style**
- **PEP 8**: Python code formatting standard
- **Type Hints**: Utilizzo typing per better code documentation  
- **Docstrings**: Documentation completa per functions e classes
- **Error Messages**: User-friendly messages con technical details in logs

### **Git Workflow**
- **Feature Branches**: Separate branch per ogni feature
- **Code Review**: Pull request review requirement
- **Testing**: Automated testing in CI/CD pipeline
- **Documentation**: README update per ogni major change

---

**🏢 Sviluppato per PMI Dashboard EPS Infrastructure Monitoring**  
**🚀 Version 2.0 - Production Ready con Resilience Module**  
**📊 Dual Module Architecture: Availability + Resilience Analytics**
