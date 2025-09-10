# Metrics Dashboard - Sistema di Monitoraggio Avanzato PMI Infrastructure

**Metrics Dashboard** è una web application Flask completa che fornisce tre moduli di monitoraggio avanzato per l'infrastruttura PMI: **Availability Analytics**, **Resilience Analytics** e **Six Sigma Statistical Process Control (SPC)**. Il sistema si connette a MongoDB per recuperare metriche operative e genera dashboard interattive per il monitoraggio in tempo reale della salute dei servizi, resilienza dei backup e controllo statistico dei processi.

## 🏗️ Architettura del Sistema

### **Componenti Principali**

1. **Flask Web Application** (`app.py`)
   - Server web principale con routing e API endpoints per tutti e tre i moduli
   - Gestione sessioni utente e configurazioni personalizzate
   - Job manager per analisi asincrone in background
   - Sistema di cache per performance ottimali

2. **Availability Analytics Module**
   - **Cumulative Availability Analyzer** (`utils/cumulative_availability_analyzer.py`)
     - Motore di calcolo delle metriche cumulative di disponibilità servizi
     - Algoritmo di scoring basato su error budget configurabili
   - **Availability Summary** (`utils/availability_summary.py`)
     - Modulo di aggregazione e riepilogo delle metriche di availability

3. **Resilience Analytics Module**
   - **Cumulative Resilience Analyzer** (`utils/cumulative_resilience_analyzer.py`)
     - Motore di analisi della resilienza dei sistemi di backup
     - Calcolo di RPO Compliance e Success Rate per backup jobs e asset
     - Scoring ponderato basato su parametri configurabili
   - **Backup Summary** (`utils/backup_summary.py`)
     - Modulo di aggregazione per metriche di backup e resilienza

4. **Six Sigma SPC Module** (NUOVO)
   - **Six Sigma Utilities** (`utils/sixsigma_utils.py`)
     - Motore Statistical Process Control con implementazione completa dei test SPC
     - Carte di controllo XmR (Individual & Moving Range)
     - 9 Test statistici implementati: Test 1, 2, 3, 4, 7, 8, mR, Saturazione
     - Sistema di baseline dinamico con ricalcolo automatico
   - **Six Sigma Frontend** (`static/sixsigma_script.js`)
     - Dashboard interattiva real-time con Chart.js
     - Simulazione temporale con controlli play/pause
     - Visualizzazione P-Score aggregato weighted

5. **Storage Layer Integration**
   - Integrazione con `storage_layer.storage_manager` per connettività MongoDB
   - Accesso a multiple collections: "assets", "metrics", "sixsigma_monitoring"
   - Sistema di configurazione persistente con MongoDB

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

### **Formula Cumulativa di Resilience**

Il sistema calcola la resilience dei backup utilizzando un approccio multi-metrica:

```
Resilience_Score = (w_RPO × RPO_Compliance) + (w_Success × Success_Rate)
```

**Dove:**
- `RPO_Compliance = max(0, 1 - (actual_RPO / target_RPO))`
- `Success_Rate = backup_riusciti_cumulativi / backup_totali_cumulativi`
- `w_RPO` = Peso per RPO Compliance (default: 60%)
- `w_Success` = Peso per Success Rate (default: 40%)

### **Formula Six Sigma P-Score** (NUOVO)

Il sistema calcola un Performance Score aggregato utilizzando pesi configurabili per macchina:

```
P_Score = (w_CPU × Score_CPU) + (w_RAM × Score_RAM) + (w_IO × Score_IO)
```

**Dove:**
- `Score_X` = Punteggio SPC per metrica (1.0 = In Controllo, 0.0 = Critico)
- `w_CPU` = Peso CPU (default: 40%)
- `w_RAM` = Peso RAM (default: 35%) 
- `w_IO` = Peso I/O Wait (default: 25%)
- `w_CPU + w_RAM + w_IO = 100%` (auto-bilanciamento)

**Test SPC Implementati:**

| Test | Nome | Score | Colore | Descrizione |
|------|------|-------|--------|-------------|
| **Test 1** | Violazione Limiti | 0.1 | 🔴 Rosso | Punto fuori UCL/LCL |
| **Test mR** | Variabilità Eccessiva | 0.2 | 🔴 Rosso | Moving Range > UCL_mR |
| **Saturazione** | Risorsa al Limite | 0.0 | 🔴 Rosso | Valore ≥ 100% |
| **Test 4** | Run Above/Below Centerline | 0.4 | 🟠 Arancione | 7-9 punti consecutivi stesso lato |
| **Test 7** | Oscillatory Trend | 0.4 | 🟠 Arancione | 14 punti alternanti sopra/sotto |
| **Test 8** | Linear Trend | 0.4 | 🟠 Arancione | 6 punti monotoni crescenti/decrescenti |
| **Test 2** | Pre-allarme Shift | 0.6 | 🟡 Giallo | 2 di 3 punti oltre 2σ |
| **Test 3** | Variabilità Aumentata | 0.7 | 🟡 Giallo | 4 di 5 punti oltre 1σ |
| **In Controllo** | Processo Stabile | 1.0 | 🟢 Verde | Tutti i test passati |

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

**Resilience Status:**
| Score Range | Status | Descrizione |
|-------------|---------|-------------|
| > 90% | **EXCELLENT** | Resilienza eccellente |
| 75% - 90% | **GOOD** | Resilienza buona |
| 60% - 75% | **ACCEPTABLE** | Resilienza accettabile |
| 40% - 60% | **CRITICAL** | Resilienza critica |
| < 40% | **SEVERE** | Resilienza severa |

**Six Sigma P-Score Status:**
| Score Range | Status | Descrizione |
|-------------|---------|-------------|
| > 0.8 | **EXCELLENT** | Performance eccellenti |
| 0.5 - 0.8 | **GOOD** | Performance buone |
| < 0.5 | **CRITICAL** | Performance critiche |

## 🔧 API Reference

### **Endpoints Modulo Availability**

#### **GET /** (Homepage)
Pagina di selezione tra i moduli analytics

#### **GET /availability/**
Dashboard principale di availability analytics
- **Template**: `availability_index.html`
- **Feature**: Selezione servizi e configurazione pesi

#### **GET /availability/config**
Interfaccia di configurazione parametri availability
- **Template**: `availability_config.html`
- **Feature**: Error budget e pesi di criticità

#### **POST /availability/start_analysis**
Avvio analisi cumulativa availability
- **Payload**: JSON con configurazione servizi
- **Response**: Job ID per tracking progress
- **Background**: Subprocess per analisi pesanti

#### **GET /availability/analysis_progress/\<job_id>**
Monitoraggio progress analisi asincrona
- **Response**: JSON con status, percentage, logs

#### **GET /availability/dashboard/\<analysis_file>**
Dashboard con risultati analisi
- **Template**: `availability_dashboard.html`
- **Chart**: Tachimetri semicircolari per servizi

### **Endpoints Modulo Resilience**

#### **GET /resilience/**
Dashboard principale di resilience analytics
- **Template**: `resilience_index.html`
- **Feature**: Selezione asset e configurazione RPO

#### **GET /resilience/config**
Interfaccia di configurazione parametri resilience
- **Template**: `resilience_config.html`
- **Feature**: Target RPO e pesi metriche

#### **POST /resilience/start_analysis**
Avvio analisi cumulativa resilience
- **Payload**: JSON con configurazione asset/jobs
- **Response**: Job ID per tracking progress
- **Background**: Subprocess per simulazione settimanale

#### **GET /resilience/analysis_progress/\<job_id>**
Monitoraggio progress analisi asincrona
- **Response**: JSON con status, percentage, logs

#### **GET /resilience/dashboard/\<analysis_file>**
Dashboard con risultati analisi
- **Template**: `resilience_dashboard.html`
- **Chart**: Grafici a ciambetta e indicatori circolari

### **Endpoints Modulo Six Sigma SPC**

#### **GET /sixsigma/**
Pagina di selezione macchina per SPC monitoring
- **Template**: `sixsigma_index.html`
- **Feature**: Theme toggle e selezione asset

#### **GET /sixsigma/config**
Interfaccia di configurazione pesi metriche
- **Template**: `sixsigma_config.html`
- **Feature**: Auto-balancing sliders per CPU/RAM/I/O

#### **POST /sixsigma/save_weights**
Salvataggio configurazione pesi
- **Payload**: JSON con weights e machine name
- **Response**: Success/error status
- **Storage**: MongoDB collection `sixsigma_weights_config`

#### **GET /sixsigma/get_weights/\<machine_name>**
Recupero pesi configurati per macchina
- **Response**: JSON con CPU, RAM, I/O weights
- **Fallback**: Valori default (33.33% each) se non configurato

#### **GET /sixsigma/dashboard/\<machine_name>**
Dashboard SPC real-time
- **Template**: `sixsigma_dashboard.html`
- **Feature**: Chart XmR interattivi con statistical tests

#### **GET /sixsigma/get_metrics/\<machine_name>**
Recupero metriche storiche per analisi SPC
- **Response**: JSON con timestamp, CPU, RAM, I/O data
- **Filter**: Ultimi 3 giorni per baseline calculation

#### **POST /sixsigma/monitor_data**
Elaborazione nuovo punto dati SPC
- **Payload**: JSON con machine_name e metric value
- **Response**: Detailed SPC analysis con test results
- **Process**: 9 test statistici + P-Score calculation

#### **GET /sixsigma/test/demo**
Endpoint di test per validazione implementazione
- **Response**: JSON con test results e baseline stats
- **Usage**: Development e debugging

### **Database Collections**

#### **pmi_infrastructure.assets**
```json
{
  "_id": ObjectId,
  "hostname": "string",
  "tipo": "vm|container|nodo_proxmox|server_fisico",
  "ip": "string",
  "stato_operativo": "attivo|manutenzione|disattivato",
  "criticita": "alta|media|bassa"
}
```

#### **pmi_infrastructure.metrics**
```json
{
  "_id": ObjectId,
  "asset_id": ObjectId,
  "timestamp": ISODate,
  "cpu_percent": Number,
  "ram_percent": Number,
  "iowait_percent": Number,
  "services": [
    {
      "name": "string",
      "status": "active|inactive|failed",
      "uptime": Number
    }
  ]
}
```

#### **sixsigma_monitoring.sixsigma_weights_config**
```json
{
  "_id": ObjectId,
  "machine_name": "string",
  "weights": {
    "cpu": Number,    // 0-100
    "ram": Number,    // 0-100
    "io": Number      // 0-100
  },
  "created_at": ISODate,
  "updated_at": ISODate
}
```

#### **sixsigma_monitoring.metrics_advanced_test**
```json
{
  "_id": ObjectId,
  "machine_name": "string",
  "timestamp": ISODate,
  "metric_type": "cpu|ram|io",
  "value": Number,
  "baseline_stats": {
    "cl": Number,
    "ucl": Number,
    "lcl": Number,
    "ucl_mr": Number,
    "sigma": Number
  },
  "test_results": {
    "test1": Boolean,
    "test2": Boolean,
    "test3": Boolean,
    "test4": Boolean,
    "test8": Boolean,
    "testmr": Boolean,
    "saturazione": Boolean
  },
  "p_score": Number
}
```

## ⚙️ Setup e Installazione

### **1. Requisiti di Sistema**
```bash
# Sistema Operativo
Windows 10/11 or Linux/macOS

# Python Version
Python 3.8+

# MongoDB
MongoDB 4.4+ with replica set (for change streams)

# Storage Requirements
Minimum 2GB for application + logs
```

### **2. Dipendenze Python**
```bash
# Core Dependencies
pip install flask==2.3.3
pip install pymongo==4.5.0
pip install python-dotenv==1.0.0
pip install numpy==1.24.3
pip install matplotlib==3.7.2

# Additional Dependencies  
pip install requests==2.31.0
pip install jinja2==3.1.2
pip install werkzeug==2.3.7

# Or install all at once
pip install -r requirements.txt
```

### **3. Configurazione MongoDB**

#### **Setup Database pmi_infrastructure**
```javascript
// MongoDB Shell Commands
use pmi_infrastructure

// Crea collections con indexes
db.assets.createIndex({"hostname": 1})
db.assets.createIndex({"tipo": 1})
db.assets.createIndex({"stato_operativo": 1})

db.metrics.createIndex({"asset_id": 1, "timestamp": -1})
db.metrics.createIndex({"timestamp": -1})
```

#### **Setup Database sixsigma_monitoring**
```javascript
// MongoDB Shell Commands  
use sixsigma_monitoring

// Crea collections con indexes
db.sixsigma_weights_config.createIndex({"machine_name": 1}, {"unique": true})
db.metrics_advanced_test.createIndex({"machine_name": 1, "timestamp": -1})
db.metrics_advanced_test.createIndex({"timestamp": -1})
```

### **4. Configurazione Environment**

#### **File .env di Produzione**
```bash
# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB_INFRASTRUCTURE=pmi_infrastructure
MONGODB_DB_SIXSIGMA=sixsigma_monitoring

# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-secret-key-here

# Application Settings
HOST=0.0.0.0
PORT=5000
WORKERS=4

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/application.log
```

### **5. Struttura Directory di Installazione**
```
PMI_DashboardEPS/
├── metrics_dashboard/           # Applicazione principale
│   ├── app.py                  # Flask server
│   ├── requirements.txt        # Dipendenze
│   ├── .env                   # Configurazione produzione
│   └── ...                    # Altri file applicazione
├── storage_layer/              # Layer di accesso dati
│   ├── storage_manager.py     # MongoDB connection manager
│   ├── models.py              # Data models
│   └── ...                    # Altri file storage
├── logs/                      # Directory log applicazione
└── venv/                      # Virtual environment Python
```

### **6. Avvio dell'Applicazione**

#### **Modalità Development**
```bash
# Attiva virtual environment
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Installa dipendenze
pip install -r requirements.txt

# Avvia in modalità development
python app.py
# O usando il run script
python run.py
```

#### **Modalità Production**
```bash
# Usando Gunicorn (Linux/macOS)
gunicorn --bind 0.0.0.0:5000 --workers 4 app:app

# Usando Waitress (Windows)
pip install waitress
waitress-serve --host=0.0.0.0 --port=5000 app:app

# Come servizio systemd (Linux)
sudo systemctl start metrics-dashboard
sudo systemctl enable metrics-dashboard
```

## 🚀 Workflow Operativo

### **1. Utilizzo Modulo Availability**

#### **Step 1: Configurazione Iniziale**
1. Accedi a `http://localhost:5000/availability/config`
2. Seleziona i servizi da monitorare dalla lista automatica
3. Configura Error Budget personalizzati per ogni servizio
4. Imposta pesi di criticità (distribuzione 100%)
5. Salva configurazione

#### **Step 2: Avvio Analisi**
1. Vai su `http://localhost:5000/availability/`
2. Clicca "Avvia Analisi Cumulativa"
3. Monitora progress tramite progress bar
4. Attendi completamento (dipende da volume dati)

#### **Step 3: Visualizzazione Dashboard**
1. Al completamento, redirect automatico a dashboard
2. Analizza tachimetri semicircolari per ogni servizio
3. Verifica Health Score aggregato ponderato
4. Usa controlli timeline per navigazione temporale

### **2. Utilizzo Modulo Resilience**

#### **Step 1: Configurazione RPO e Pesi**
1. Accedi a `http://localhost:5000/resilience/config`
2. Seleziona asset e backup jobs da monitorare
3. Configura target RPO personalizzati per tipo
4. Imposta bilanciamento tra RPO Compliance e Success Rate
5. Salva configurazione

#### **Step 2: Avvio Analisi Settimanale**
1. Vai su `http://localhost:5000/resilience/`
2. Clicca "Avvia Analisi Resilience"
3. Il sistema simula 168 ore (1 settimana)
4. Monitora progress dell'analisi

#### **Step 3: Dashboard Resilience**
1. Visualizza grafico a ciambella aggregato
2. Analizza indicatori circolari per singoli asset
3. Verifica distribuzione livelli resilience
4. Naviga timeline per andamento storico

### **3. Utilizzo Modulo Six Sigma SPC**

#### **Step 1: Configurazione Pesi Macchina**
1. Accedi a `http://localhost:5000/sixsigma/`
2. Seleziona macchina/asset da monitorare
3. Vai su "Configura Pesi" per la macchina selezionata
4. Usa auto-balancing sliders per CPU/RAM/I/O Wait
5. Salva configurazione (persiste in MongoDB)

#### **Step 2: Monitoring SPC Real-time**
1. Accedi a dashboard `http://localhost:5000/sixsigma/dashboard/<machine>`
2. I grafici XmR si popolano automaticamente
3. Monitora P-Score aggregato e test statistici
4. Usa controlli play/pause per simulazione temporale

#### **Step 3: Analisi Anomalie**
1. Osserva colori dei punti (Verde/Giallo/Arancione/Rosso)
2. Leggi log dettagliati per ogni metrica
3. Verifica contatori test statistici
4. Analizza pattern e trend nei grafici XmR

## 🔍 Algoritmi e Logica di Business

### **Statistical Process Control (SPC) Engine**

#### **Baseline Calculation Algorithm**
```python
def calcola_baseline(dati_storici):
    """
    Calcola parametri baseline da ultimi 3 giorni di dati
    Implementa teoria XmR Control Charts
    """
    # Individual Chart (X)
    media = np.mean(dati_storici)
    
    # Moving Range Chart (mR)  
    moving_ranges = [abs(dati_storici[i] - dati_storici[i-1]) 
                    for i in range(1, len(dati_storici))]
    mr_mean = np.mean(moving_ranges)
    
    # Calcola limiti di controllo
    ucl = media + (2.66 * mr_mean)  # Upper Control Limit
    lcl = media - (2.66 * mr_mean)  # Lower Control Limit
    if lcl < 0: lcl = 0             # Non negativi per %
    
    ucl_mr = 3.27 * mr_mean         # UCL per Moving Range
    sigma = mr_mean / 1.128         # Stima sigma processo
    
    return media, ucl, lcl, ucl_mr, sigma
```

#### **Test Statistici Implementation**
```python
def esegui_test_spc(valore, dati_recenti, baseline):
    """
    Esegue tutti i test SPC su nuovo punto dati
    """
    test_results = {}
    
    # Test 1: Violazione Limiti
    test_results['test1'] = (valore > baseline['ucl'] or 
                           valore < baseline['lcl'])
    
    # Test 2: Pre-allarme Shift (2 di 3 punti oltre 2σ)
    if len(dati_recenti) >= 3:
        zone_a_violations = sum(1 for v in dati_recenti[-3:] 
                               if abs(v - baseline['cl']) > 2*baseline['sigma'])
        test_results['test2'] = zone_a_violations >= 2
    
    # Test 3: Variabilità Aumentata (4 di 5 punti oltre 1σ)
    if len(dati_recenti) >= 5:
        zone_b_violations = sum(1 for v in dati_recenti[-5:] 
                               if abs(v - baseline['cl']) > baseline['sigma'])
        test_results['test3'] = zone_b_violations >= 4
    
    # Test 4: Run Above/Below Centerline (7-9 punti stesso lato)
    for run_length in [9, 8, 7]:
        if len(dati_recenti) >= run_length:
            above_mean = all(v > baseline['cl'] for v in dati_recenti[-run_length:])
            below_mean = all(v < baseline['cl'] for v in dati_recenti[-run_length:])
            if above_mean or below_mean:
                test_results['test4'] = True
                break
    
    # Test 7: Oscillatory Trend (14 punti alternanti)
    if len(dati_recenti) >= 14:
        last_14 = dati_recenti[-14:]
        pattern1 = all((last_14[i] < last_14[i+1] if i % 2 == 0 else last_14[i] > last_14[i+1])
                      for i in range(13))
        pattern2 = all((last_14[i] > last_14[i+1] if i % 2 == 0 else last_14[i] < last_14[i+1])
                      for i in range(13))
        test_results['test7'] = pattern1 or pattern2
    
    # Test 8: Linear Trend (6 punti monotoni)
    if len(dati_recenti) >= 6:
        increasing = all(dati_recenti[i] < dati_recenti[i+1] 
                        for i in range(-6, -1))
        decreasing = all(dati_recenti[i] > dati_recenti[i+1] 
                        for i in range(-6, -1))
        test_results['test8'] = increasing or decreasing
    
    return test_results
```

### **Weighted P-Score Algorithm**
```python
def calcola_p_score_pesato(scores_metriche, pesi):
    """
    Calcola P-Score aggregato usando pesi configurabili
    """
    p_score = (pesi['cpu']/100.0 * scores_metriche['cpu'] +
               pesi['ram']/100.0 * scores_metriche['ram'] + 
               pesi['io']/100.0 * scores_metriche['io'])
    
    return round(p_score, 3)

def converti_test_a_score(test_results):
    """
    Converte risultati test SPC in score numerico
    """
    if test_results['saturazione']: return 0.0
    if test_results['test1']: return 0.1
    if test_results['testmr']: return 0.2
    if test_results['test4'] or test_results['test8']: return 0.4
    if test_results['test2']: return 0.6
    if test_results['test3']: return 0.7
    return 1.0  # In controllo
```

### **Resilience Score Algorithm**
```python
def calcola_resilience_score(rpo_compliance, success_rate, pesi):
    """
    Combina RPO Compliance e Success Rate con pesi configurabili
    """
    # Normalizza RPO Compliance
    rpo_norm = max(0, min(1, rpo_compliance))
    
    # Calcola score finale
    resilience_score = (pesi['rpo']/100.0 * rpo_norm + 
                       pesi['success']/100.0 * success_rate)
    
    return round(resilience_score * 100, 2)  # Percentuale
```

## 🛠️ Troubleshooting e Best Practices

### **Common Issues e Soluzioni**

#### **1. Problemi di Connessione MongoDB**
```bash
# Verifica connessione MongoDB
mongo --eval "db.runCommand('ping')"

# Controlla status replica set (necessario per change streams)
mongo --eval "rs.status()"

# Se replica set non configurato
mongo --eval "rs.initiate()"
```

#### **2. Errori di Dipendenze Python**
```bash
# Reinstalla dipendenze pulite
pip uninstall -r requirements.txt -y
pip install -r requirements.txt

# Problemi con numpy/matplotlib
pip install --upgrade numpy matplotlib

# Per Windows con problemi compilazione
pip install --only-binary=all numpy matplotlib
```

#### **3. Problemi Performance Dashboard**
```bash
# Ottimizza queries MongoDB con explain
db.metrics.explain("executionStats").find({
    "timestamp": {$gte: ISODate("2024-01-01")}
}).sort({"timestamp": -1}).limit(1000)

# Aggiungi indexes per performance
db.metrics.createIndex({"asset_id": 1, "timestamp": -1})
db.metrics.createIndex({"timestamp": -1})
```

#### **4. Memory Issues con Analisi Grandi**
```python
# Configura pagination per dataset grandi
BATCH_SIZE = 1000
cursor = db.metrics.find().batch_size(BATCH_SIZE)

# Usa streaming per file JSON grandi
import ijson
parser = ijson.parse(open('large_analysis.json', 'rb'))
```

### **Best Practices Operative**

#### **1. Gestione Baseline SPC**
- **Ricalcolo Automatico**: Il sistema ricalcola baseline quando detect shift sistematici
- **Minimum Data Points**: Almeno 20 punti per baseline affidabile
- **Historical Window**: Usa 3 giorni di storia (72 ore) per baseline stabile
- **Validation**: Controlla baseline dopo manutenzioni o modifiche HW/SW

#### **2. Configurazione Pesi Metriche**
- **CPU Intensive Apps**: Peso CPU 50-60%, RAM 25-30%, I/O 15-20%
- **Database Systems**: Peso I/O 40-50%, RAM 30-35%, CPU 15-25%  
- **Web Servers**: Peso bilanciato 33% ciascuno
- **Monitoring**: Ricalibra pesi basandosi su historical patterns

#### **3. Thresholds e Alerting**
```python
# Configurazione alert per P-Score
ALERT_THRESHOLDS = {
    'critical': 0.3,    # P-Score < 30% = Alert immediato
    'warning': 0.6,     # P-Score < 60% = Warning
    'good': 0.8         # P-Score > 80% = Performance buone
}

# Alert su test pattern specifici
PATTERN_ALERTS = {
    'trend_degradation': ['test8'],      # Linear Trend negativo
    'process_shift': ['test4'],          # Run Above/Below Centerline
    'oscillatory_behavior': ['test7'],   # Oscillatory Trend sistematico
    'high_variability': ['testmr'],      # Variabilità eccessiva
    'saturation': ['saturazione']        # Risorse sature
}
```

#### **4. Data Retention Policy**
```javascript
// MongoDB TTL indexes per data retention
db.metrics.createIndex(
    {"timestamp": 1}, 
    {expireAfterSeconds: 7776000}  // 90 giorni
)

db.metrics_advanced_test.createIndex(
    {"timestamp": 1},
    {expireAfterSeconds: 2592000}  // 30 giorni
)
```

### **Maintenance Tasks**

#### **Daily Operations**
```bash
# 1. Backup configurazioni
mongodump --db sixsigma_monitoring --collection sixsigma_weights_config

# 2. Verifica log errors
grep "ERROR" logs/application.log | tail -20

# 3. Controllo disk space
df -h /var/log/metrics_dashboard/

# 4. Health check endpoints
curl http://localhost:5000/sixsigma/test/demo
```

#### **Weekly Operations**  
```bash
# 1. Restart applicazione per memory cleanup
sudo systemctl restart metrics-dashboard

# 2. Analizza performance queries
mongo sixsigma_monitoring --eval "db.setProfilingLevel(2)"

# 3. Backup complete database
mongodump --db pmi_infrastructure --db sixsigma_monitoring

# 4. Update baseline cache se necessario
python utils/maintenance_scripts.py --update-baselines
```

### **Security Considerations**

#### **1. MongoDB Security**
```javascript
// Crea utente applicazione con privilegi minimi
use admin
db.createUser({
    user: "metrics_app",
    pwd: "secure_password",
    roles: [
        {role: "readWrite", db: "pmi_infrastructure"},
        {role: "readWrite", db: "sixsigma_monitoring"}
    ]
})
```

#### **2. Flask Security Headers**
```python
# app.py security headers
@app.after_request
def after_request(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response
```

## 📋 Conclusioni e Sviluppi Futuri

### **Sistema Attuale - Capabilities**
✅ **Three-Module Analytics Platform**: Availability, Resilience, Six Sigma SPC
✅ **Real-time SPC Monitoring**: 9 test statistici con XmR control charts  
✅ **Weighted Scoring Systems**: Configurabile via MongoDB persistence
✅ **Interactive Dashboards**: Chart.js con timeline navigation
✅ **Asynchronous Processing**: Background jobs per analisi pesanti
✅ **MongoDB Integration**: Multiple databases con ottimizzazioni
✅ **Responsive UI**: Bootstrap con theme dark/light support

### **Roadmap Tecnica Futura**
🔄 **Machine Learning Integration**: Predictive analytics su trend SPC
🔄 **API Authentication**: JWT tokens per sicurezza endpoints
🔄 **Real-time Notifications**: WebSocket per alert immediati
🔄 **Export Capabilities**: PDF/Excel reports generation
🔄 **Multi-tenancy**: Support per multiple PMI environments
🔄 **Advanced Analytics**: MTTR, MTBF, availability forecasting

---

**Documentazione aggiornata:** `{{ current_date }}`
**Versione Sistema:** `v2.1.0 - Six Sigma SPC Integration`
**Autore:** PMI Infrastructure Team
**Repository:** `metrics_dashboard/`

```
metrics_dashboard/
├── app.py                          # Flask application server principale
├── run.py                          # Script di avvio dell'applicazione
├── requirements.txt                # Dipendenze Python specifiche
├── .env                           # Variabili d'ambiente di produzione
├── .env.example                   # Template per configurazione
├── __init__.py                    # Package initialization
├── templates/                     # Template HTML Jinja2
│   ├── index.html                # Pagina principale selezione modulo
│   # AVAILABILITY MODULE
│   ├── availability_index.html   # Pagina selezione analisi availability
│   ├── availability_config.html  # Interfaccia configurazione availability
│   └── availability_dashboard.html # Dashboard real-time availability
│   # RESILIENCE MODULE
│   ├── resilience_index.html     # Pagina selezione analisi resilience  
│   ├── resilience_config.html    # Interfaccia configurazione resilience
│   └── resilience_dashboard.html # Dashboard real-time resilience
│   # SIX SIGMA SPC MODULE (NUOVO)
│   ├── sixsigma_index.html       # Pagina selezione Six Sigma (tema dark/light)
│   ├── sixsigma_config.html      # Configurazione pesi metriche per macchina
│   └── sixsigma_dashboard.html   # Dashboard SPC real-time con test statistici
├── static/                       # Assets statici (CSS, JS, immagini)
│   └── sixsigma_script.js        # Logic frontend Six Sigma (Chart.js, SPC)
├── utils/                        # Moduli di utility e business logic
│   # AVAILABILITY ANALYTICS
│   ├── cumulative_availability_analyzer.py  # Core analyzer engine availability
│   ├── availability_summary.py              # Summary aggregator availability
│   # RESILIENCE ANALYTICS
│   ├── cumulative_resilience_analyzer.py    # Core analyzer engine resilience
│   ├── backup_summary.py                    # Summary aggregator backup/resilience
│   # SIX SIGMA SPC ANALYTICS (NUOVO)
│   ├── sixsigma_utils.py                    # Core SPC engine con test statistici
│   └── generate_metrics_spc.py              # Generatore dati SPC per testing
├── output/                       # Directory per output JSON generati
│   ├── cumulative_availability_analysis_*.json  # Report availability
│   ├── resilience_analysis_*.json               # Report resilience
│   └── verify_and_enhance_analysis.py           # Utility validazione
└── __pycache__/                  # Cache Python compilato
```

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
- **Error Budget Personalizzabili**: Configurazione soglie fallimenti per ogni servizio
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

### **Modulo Resilience**

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

### **Modulo Six Sigma SPC** (NUOVO)

#### **1. Configurazione Pesi Metriche per Macchina**
- **Auto-Balancing Sliders**: Slider automatici che mantengono 100% totale
- **Pesi Personalizzabili**: CPU, RAM, I/O Wait configurabili per ogni macchina
- **Persistenza MongoDB**: Salvataggio configurazione in collection `sixsigma_weights_config`
- **Cache Performance**: Sistema di cache per accesso rapido ai pesi configurati
- **Fallback Intelligente**: Valori di default se configurazione non trovata

#### **2. Statistical Process Control Engine**
- **Carte di Controllo XmR**: Individual & Moving Range charts con limiti dinamici
- **9 Test SPC Completi**: Implementazione completa dei test statistici industriali
- **Baseline Dinamico**: Calcolo automatico CL, UCL, LCL da dati storici (3 giorni)
- **Ricalcolo Automatico**: Trigger per ricalcolo baseline quando detectati shift sistematici
- **Zone Sigma**: Calcolo zone 1σ, 2σ, 3σ per test avanzati

#### **3. Test Statistici Implementati**

**Test di Priorità Critica (Score 0.0-0.2):**
- **Test 1 - Violazione Limiti**: Punto fuori UCL/LCL (Score: 0.1)
- **Test mR - Variabilità Eccessiva**: Moving Range > UCL_mR (Score: 0.2)  
- **Saturazione - Risorsa al Limite**: Valore ≥ 100% utilizzo (Score: 0.0)

**Test di Pattern Sistematico (Score 0.4):**
- **Test 4 - Run Above/Below Centerline**: 7-9 punti consecutivi stesso lato media
- **Test 7 - Oscillatory Trend**: 14 punti alternanti sopra/sotto precedente ⭐ **NUOVO**
- **Test 8 - Linear Trend**: 6 punti monotoni crescenti/decrescenti

**Test di Pre-allarme (Score 0.6-0.7):**
- **Test 2 - Pre-allarme Shift**: 2 di 3 punti oltre 2σ dalla media
- **Test 3 - Variabilità Aumentata**: 4 di 5 punti oltre 1σ dalla media

#### **5. Teoria Test 7 - Oscillatory Trend** ⭐ **NUOVO**

Il **Test 7 - Oscillatory Trend Test** rileva comportamenti oscillatori sistematici nel processo che non sono attribuibili a variazione normale. Questo test ricerca 14 successive osservazioni che si alternano sopra e sotto rispetto alla precedente.

**Pattern Rilevati:**
```
Pattern 1 (Crescente-Decrescente):
p1 < p2 > p3 < p4 > p5 < p6 > p7 < p8 > p9 < p10 > p11 < p12 > p13 < p14

Pattern 2 (Decrescente-Crescente):  
p1 > p2 < p3 > p4 < p5 > p6 < p7 > p8 < p9 > p10 < p11 > p12 < p13 > p14
```

**Significato Statistico:**
- **Probabilità**: La probabilità che 14 punti si alternino casualmente è estremamente bassa (< 0.01%)
- **Causa**: Indica una tendenza sistematica nel processo non attribuibile a comportamento normale
- **Impatto**: Suggerisce instabilità ciclica o interferenze periodiche nel sistema

**Comportamento Sistema:**
- **Rilevamento**: Grafico si blocca, 14 punti coinvolti vengono colorati
- **Ricalcolo Baseline**: Attende 20 nuove misurazioni prima di ricalcolare limiti
- **Score**: 0.4 (stesso livello di Test 4 e Test 8)
- **Colore**: 🟠 Arancione (warning level)

#### **4. Dashboard SPC Real-time**
- **Grafici XmR Separati**: CPU, RAM, I/O Wait con Chart.js interattivi
- **P-Score Aggregato**: Visualizzazione centrale con classificazione colorata
- **Simulazione Temporale**: Timeline con controlli play/pause (2 secondi/punto)
- **Log Dettagliati**: Separati per metrica con descrizione anomalie e teoria SPC
- **Statistiche Test**: Contatori aggiornati in tempo reale per ogni test
- **Zoom Dinamico**: Opzione zoom automatico per visualizzazione ottimale
- **Gestione Pause**: Sistema pause/resume per grafici con anomalie critiche

#### **5. Visualizzazione Pesi Correnti**
- **Sezione Pesi Macchina**: Mostra i pesi utilizzati per calcolo P-Score
- **Aggiornamento Automatico**: Quando si cambia macchina, i pesi si aggiornano
- **Badge Colorati**: CPU (blu), RAM (verde), I/O Wait (giallo) per identificazione
- **Informazioni Tooltips**: Spiegazione ruolo pesi nel calcolo finale

#### **6. Sistema di Cache e Performance**
- **Baseline Cache**: Cache dei parametri baseline calcolati per performance
- **Pause Charts Cache**: Gestione grafici in pausa per anomalie
- **Weights Cache**: Cache pesi configurazioni per accesso rapido
- **Recalculate Counters**: Gestione intelligente dei trigger di ricalcolo

### **4. Integrazione Storage Layer**
- **MongoDB Connection**: Accesso a multiple database (pmi_infrastructure, sixsigma_monitoring)
- **AssetDocument Models**: Utilizzo di modelli strutturati per asset management
- **Collection Multiple**: assets, metrics, sixsigma_weights_config, metrics_advanced_test
- **Query Ottimizzate**: Recupero efficiente di metriche con filtri temporali

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
-
--

## 🤖 AnomalySNMP Module - Sistema di Rilevamento Anomalie SNMP

**AnomalySNMP** è un modulo avanzato di rilevamento anomalie per dati di rete SNMP che combina **Isolation Forest** con **Statistical Process Control (SPC)** per identificare comportamenti anomali in tempo reale attraverso un **S-Score ibrido** innovativo.

### 🎯 Caratteristiche Principali

- 🤖 **Machine Learning**: Isolation Forest per detection unsupervised
- 📊 **S-Score Ibrido**: Formula matematica interpretabile [0,1]
- ⚡ **Tempo Reale**: Simulazione con controlli velocità 1x-10x
- 🎨 **Visualizzazione**: Gauge, grafici temporali, zone colore
- 📈 **Accuratezza**: Calcolo predizioni corrette in tempo reale
- 🔄 **SMOTE**: Bilanciamento dataset con oversampling

### 🏗️ Architettura AnomalySNMP

```
anomaly_snmp/
├── routes.py                    # Controller Flask
├── exceptions.py                # Gestione errori
├── logging_config.py            # Sistema logging
├── monitoring.py                # Monitoraggio performance
└── utils/
    ├── ml_engine.py             # Motore Isolation Forest
    └── data_processor.py        # Preprocessing dati
```

### 📊 Dataset SNMP-MIB

```
File: Datasets/snmp_mib_dataset.csv
- 4,998 record totali
- 600 record Normal (12%)
- 4,398 record Anomaly (88%)
- 8 feature SNMP per record
```

### 🤖 Algoritmo di Rilevamento

#### 1. Preprocessing e Bilanciamento
```python
# Normalizzazione feature
X_normalized = (X - μ) / σ  # Media=0, Std=1

# Split Train/Test
train_split = 0.7  # Configurabile
normal_train = 420  # 70% dei normali
normal_test = 180   # 30% dei normali
anomaly_test = 4,398  # Tutte le anomalie

# Bilanciamento SMOTE
contamination = 0.05  # 5% anomalie attese
target_normal = anomaly_test * (1-contamination) / contamination
# target_normal = 4,398 * 0.95 / 0.05 = 83,562
smote_needed = target_normal - 600 = 82,962
```

#### 2. Training Isolation Forest
```python
from sklearn.ensemble import IsolationForest

model = IsolationForest(
    contamination=0.05,    # 5% anomalie attese
    n_estimators=100,      # 100 alberi
    max_samples='auto',    # Campioni automatici
    random_state=42        # Riproducibilità
)

# Training SOLO su dati normali (inclusi SMOTE)
model.fit(X_train_normal_only)
```

#### 3. Calcolo Baseline Statistica
```python
# Score grezzi da Isolation Forest
raw_scores = model.decision_function(X_train_normal)
# Range tipico: [-0.15, 0.08]

# Normalizzazione Min-Max [0,1]
norm_scores = (raw_scores - min) / (max - min)

# Baseline per S-Score
baseline = {
    'mu_normal': np.mean(norm_scores),     # ≈ 0.7
    'sigma_normal': np.std(norm_scores),   # ≈ 0.1
    'min_raw': min(raw_scores),            # Per normalizzazione futura
    'max_raw': max(raw_scores)             # Per normalizzazione futura
}
```

### 📐 Formula S-Score AnomalySNMP

Il sistema utilizza una formula matematica ibrida per convertire gli score dell'Isolation Forest in un valore interpretabile:

```
S(s_new) = {
    1.0                                           se s_new ≤ μ_normal
    max(0, 1 - (s_new - μ_normal)/(3·σ_normal))  se s_new > μ_normal
}
```

**Esempi Numerici** (μ_normal=0.7, σ_normal=0.1):
```
s_new = 0.6  → S-Score = 1.0   (≤ μ_normal) - Perfettamente normale
s_new = 0.7  → S-Score = 1.0   (= μ_normal) - Normale
s_new = 0.8  → S-Score = 0.67  (decadimento lineare) - Attenzione
s_new = 0.9  → S-Score = 0.33  (decadimento lineare) - Warning
s_new = 1.0  → S-Score = 0.0   (anomalia massima) - ANOMALIA
```

### 🎯 Classificazione Anomalie

```javascript
// REGOLA: Solo S-Score esattamente = 0.0 è anomalia
const ANOMALY_THRESHOLD = 0.0;
const predictedLabel = (s_score === 0.0) ? 'Anomaly' : 'Normal';
```

### 🎨 Zone Colore S-Score

| S-Score Range | Zona | Colore | Stato | Descrizione |
|---------------|------|--------|-------|-------------|
| **0.8 - 1.0** | Excellent | 🟢 Verde | Normale | Sistema stabile |
| **0.6 - 0.8** | Good | 🟡 Giallo | Buono | Leggera deviazione |
| **0.4 - 0.6** | Warning | 🟠 Arancione | Attenzione | Comportamento sospetto |
| **0.0 - 0.4** | Critical | 🔴 Rosso | Critico | Possibile anomalia |
| **= 0.0** | Anomaly | 🚨 Rosso | **ANOMALIA** | **Anomalia dichiarata** |

### 🔧 API Endpoints AnomalySNMP

#### **GET /anomaly_snmp/configure**
Pagina di configurazione del modello AnomalySNMP
- **Template**: `anomaly_configure.html`
- **Feature**: Impostazione contamination e train_split

#### **POST /anomaly_snmp/train**
Training del modello Isolation Forest
- **Payload**: JSON con parametri configurazione
- **Process**: 
  1. Preprocessing dataset SNMP-MIB
  2. SMOTE oversampling
  3. Training Isolation Forest
  4. Calcolo baseline statistica
  5. Salvataggio artifacts in sessione
- **Response**: Redirect a dashboard

#### **GET /anomaly_snmp/dashboard**
Dashboard simulazione tempo reale
- **Template**: `anomaly_dashboard.html`
- **Feature**: 
  - Gauge circolare S-Score
  - Grafico temporale con zone colore
  - Controlli simulazione (Play/Pause/Velocità)
  - Statistiche accuratezza in tempo reale

#### **GET /anomaly_snmp/api/get_next_point/\<int:offset>**
API per ottenere prossimo punto dati simulazione
- **Response**: JSON con:
  ```json
  {
    "success": true,
    "data": {
      "s_score": 0.85,
      "real_label": "Normal",
      "timestamp": "2025-01-09T10:30:00",
      "offset": 42
    },
    "next_offset": 43,
    "has_more_data": true
  }
  ```

#### **POST /anomaly_snmp/api/simulation_control**
Controllo simulazione (play/pause/velocità)
- **Payload**: 
  ```json
  {
    "action": "play|pause|set_speed",
    "speed": 5  // Solo per set_speed
  }
  ```

#### **POST /anomaly_snmp/api/reset_simulation**
Reset completo simulazione
- **Response**: Conferma reset con statistiche azzerate

### 🎮 Interfaccia Dashboard AnomalySNMP

#### 1. **Anomaly Score Card**
- **Gauge Circolare**: Visualizza S-Score 0-100%
- **Colore Dinamico**: Verde/Giallo/Arancione/Rosso
- **Percentuale**: S-Score in formato percentuale

#### 2. **Control Panel**
- **Play/Pause**: Controllo simulazione tempo reale
- **Velocità**: Slider 1x-10x + bottoni rapidi (1x, 2x, 5x)
- **Timeline**: Informazioni punto corrente
- **Reset**: Azzera simulazione completamente

#### 3. **Grafico Temporale**
- **Andamento S-Score**: Timeline con colori zone
- **50 punti**: Mantiene ultimi 50 per performance
- **Legenda**: Zone colore con soglie interpretative

#### 4. **Resoconto Dataset**
- **Dataset Originale**: 600 Normal, 4,398 Anomaly
- **Post-SMOTE**: Dati bilanciati per training
- **Training Set**: Solo record normali
- **Test Set**: Normali + Anomalie per simulazione

#### 5. **Statistiche Simulazione**
- **Contatori**: Punti normali/anomalie processati
- **Configurazione**: Contamination, Train Split
- **Punto Corrente**: Etichetta reale vs predetta
- **Accuratezza**: % predizioni corrette (Real vs Predicted)

### ⚙️ Configurazione AnomalySNMP

#### Parametri Principali

| Parametro | Range | Default | Descrizione |
|-----------|-------|---------|-------------|
| **Contamination** | 0.01-0.1 | 0.05 | % anomalie attese nel dataset |
| **Train Split** | 0.5-0.9 | 0.7 | % dati per training |
| **Soglia Anomalia** | Fisso | 0.0 | Solo S-Score = 0.0 è anomalia |

#### Configurazione Avanzata
```python
# Parametri Isolation Forest
ISOLATION_FOREST_PARAMS = {
    'n_estimators': 100,
    'max_samples': 'auto',
    'contamination': 0.05,
    'random_state': 42,
    'n_jobs': -1
}

# Parametri SMOTE
SMOTE_PARAMS = {
    'random_state': 42,
    'k_neighbors': 5
}
```

### 📊 Metriche Performance AnomalySNMP

#### Timing Simulazione
- **1x**: 1 punto/secondo (tempo reale)
- **2x**: 2 punti/secondo
- **5x**: 5 punti/secondo
- **10x**: 10 punti/secondo (massima velocità)

#### Accuratezza Sistema
- **Etichetta Reale**: Dal dataset SNMP-MIB originale
- **Etichetta Predetta**: Basata su soglia S-Score = 0.0
- **Metrica**: % predizioni corrette in tempo reale
- **Visualizzazione**: Frazione (es: 85.2% - 23/27)

#### Memoria e Performance
- **Dataset**: ~5MB (4,998 record SNMP)
- **Modello**: ~50MB (Isolation Forest + baseline)
- **Sessione**: ~1MB (artifacts + metadata)
- **Max punti grafico**: 50 (ottimizzazione performance)

### 🔍 Troubleshooting AnomalySNMP

#### Problemi Comuni

| Problema | Causa | Soluzione |
|----------|-------|-----------|
| **Sessione non trovata** | Sessione Flask scaduta | Rifare configurazione e training |
| **Simulazione non avanza** | Endpoint API non risponde | Verificare console browser |
| **Grafico non aggiorna** | Chart.js non inizializzato | Hard refresh (Ctrl+F5) |
| **Accuratezza sempre 100%** | Soglia troppo restrittiva | Normale, poche anomalie = 0.0 |

#### Debug JavaScript
```javascript
// Console browser per debug
console.log('Simulation running:', simulationRunning);
console.log('Current offset:', currentOffset);
console.log('Accuracy:', correctPredictions, '/', totalPredictions);
```

### 🔬 Validazione Scientifica AnomalySNMP

#### Formula S-Score
- **Base teorica**: Statistical Process Control + Isolation Forest
- **Range**: [0,1] sempre garantito
- **Interpretabilità**: Lineare e intuitiva
- **Robustezza**: Normalizzazione Min-Max per stabilità

#### Isolation Forest
- **Algoritmo**: Unsupervised anomaly detection
- **Principio**: Path length in alberi casuali
- **Vantaggi**: Efficiente, scalabile, no etichette
- **Limitazioni**: Sensibile a parametri contamination

#### Validazione Risultati
- **Ground Truth**: Etichette dataset SNMP-MIB originale
- **Metrica**: Accuratezza predizioni binarie
- **Baseline**: Confronto con soglie alternative
- **Interpretazione**: Solo S-Score = 0.0 massimizza precisione
---


## 🚀 Utilizzo Completo Sistema

### **Workflow Availability Analytics**
1. Accedi a `/availability/`
2. Seleziona servizi da monitorare
3. Configura error budget in `/availability/config`
4. Avvia analisi cumulativa
5. Visualizza dashboard con tachimetri

### **Workflow Resilience Analytics**
1. Accedi a `/resilience/`
2. Seleziona asset/jobs da analizzare
3. Configura target RPO in `/resilience/config`
4. Avvia analisi settimanale
5. Visualizza dashboard con grafici circolari

### **Workflow Six Sigma SPC**
1. Accedi a `/sixsigma/`
2. Seleziona macchina da monitorare
3. Configura pesi metriche in `/sixsigma/config`
4. Avvia monitoraggio real-time
5. Visualizza carte di controllo XmR

### **Workflow AnomalySNMP**
1. Accedi a `/anomaly_snmp/configure`
2. Imposta contamination e train_split
3. Avvia training Isolation Forest
4. Accedi automaticamente alla dashboard
5. Controlla simulazione tempo reale con S-Score

---

## 📞 Supporto e Contributi

### **Supporto Tecnico**
- **Documentazione**: Questo README completo
- **Logs**: Console browser + logs Python Flask
- **Debug**: Modalità sviluppo con `FLASK_ENV=development`
- **Monitoring**: Endpoint `/health` per status sistema

### **Contributi**
Per contribuire al progetto:
1. Fork repository
2. Crea feature branch (`git checkout -b feature/AmazingFeature`)
3. Implementa modifiche con test
4. Commit (`git commit -m 'Add AmazingFeature'`)
5. Push (`git push origin feature/AmazingFeature`)
6. Apri Pull Request con documentazione

### **Roadmap Futuro**
- [ ] **AnomalySNMP**: Soglie anomalia configurabili
- [ ] **AnomalySNMP**: Export risultati CSV/JSON
- [ ] **AnomalySNMP**: Real-time SNMP data ingestion
- [ ] **Six Sigma**: Alerting system per violazioni SPC
- [ ] **Availability**: Integrazione con sistemi ticketing
- [ ] **Resilience**: Predizione failure backup jobs
- [ ] **Sistema**: Multi-tenant support
- [ ] **Sistema**: API REST complete per tutti i moduli

---

**© 2025 Metrics Dashboard - Sistema Completo di Monitoraggio PMI Infrastructure**
*Availability Analytics • Resilience Analytics • Six Sigma SPC • AnomalySNMP Detection*