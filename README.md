# EPS+ (Enhanced PMI System Plus)
## Sistema di Monitoraggio per Infrastrutture IT Ibride delle PMI

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-4.x-brightgreen.svg)](https://www.mongodb.com/)

---

## 📖 Abstract

Le Piccole e Medie Imprese (PMI) affrontano notevoli sfide nella gestione di infrastrutture IT ibride, principalmente a causa della mancanza di visibilità unificata su sistemi eterogenei. Questa tesi, in collaborazione con l'azienda **Evolumia**, propone la progettazione e lo sviluppo parziale di **EPS+**, un sistema di monitoraggio open source. 

L'obiettivo di EPS+ è **integrare dati frammentati** da diverse fonti (come Proxmox VE, Acronis Cyber Protect e dispositivi di rete monitorati via SNMP), per rilevare proattivamente le anomalie tramite machine learning e calcolare un **"health score" aggregato**. Questo punteggio, basato su metriche di performance, availability e resilience, offre una valutazione immediata e intuitiva dello stato dell'infrastruttura.

Dato che gli ambienti PMI sono eterogenei e spesso privi di dati etichettati, il progetto si concentra su un **approccio non supervisionato**. Il nucleo sperimentale si basa sull'algoritmo **Isolation Forest**, convalidato su dataset SNMP-MIB e su dati generati. Il confronto con benchmark supervisionati (come Random Forest e kNN) ha dimostrato l'efficienza di Isolation Forest nel modellare la "normalità" senza la necessità di etichette, mantenendo performance in termini di accuratezza e velocità di elaborazione.

Il sistema esplora anche un approccio più avanzato con **autoencoder basati su GRU** per l'analisi di pattern sequenziali, dimostrando potenzialità di sviluppo future. In questo contesto, Isolation Forest agisce come un passo strategico iniziale: identifica le anomalie in tempo reale e accumula dati validati che possono essere usati per addestrare modelli più complessi.

---

## 🗂️ Struttura della Repository

Questa repository contiene l'implementazione completa del sistema EPS+, organizzata in moduli funzionali:

```
PMI_DashboardEPS/
│
├── 📊 pmi_dashboard/              # Dashboard principale Flask
│   ├── proxmox/                   # Integrazione Proxmox VE
│   │   ├── api_client.py         # Client API Proxmox
│   │   ├── models.py             # Modelli dati Proxmox
│   │   └── routes.py             # Endpoint REST Proxmox
│   ├── acronis/                   # Integrazione Acronis Cyber Protect
│   │   ├── api_client.py         # Client API Acronis
│   │   ├── config_manager.py     # Gestione configurazione
│   │   ├── models.py             # Modelli dati Acronis
│   │   └── routes.py             # Endpoint REST Acronis
│   ├── static/                    # Risorse statiche (CSS, JS, immagini)
│   ├── templates/                 # Template HTML Jinja2
│   ├── data/                      # Dati applicazione
│   ├── logs/                      # File di log
│   ├── app.py                     # Applicazione Flask principale
│   ├── config.py                  # Configurazione applicazione
│   └── logging_config.py          # Configurazione logging
│
├── 📈 metrics_dashboard/          # Dashboard analisi metriche e ML
│   ├── anomaly_snmp/             # Sistema rilevamento anomalie
│   │   ├── monitoring.py         # Monitoraggio metriche
│   │   ├── routes.py             # API anomaly detection
│   │   ├── exceptions.py         # Gestione eccezioni
│   │   ├── logging_config.py     # Logging specifico
│   │   └── utils/                # Utility per ML
│   ├── Datasets/                  # Dataset per training/testing
│   ├── output/                    # Output elaborazioni
│   ├── static/                    # Risorse frontend
│   ├── templates/                 # Template visualizzazione
│   ├── utils/                     # Utility generiche
│   ├── app.py                     # Applicazione metriche
│   └── run.py                     # Script avvio
│
├── 🌐 network_discovery/          # Sistema scoperta e monitoring rete
│   ├── scanners/                  # Scanner SNMP
│   ├── core/                      # Logica core
│   ├── config/                    # Configurazioni SNMP
│   ├── results/                   # Risultati scan
│   ├── utils/                     # Utility rete
│   └── main.py                    # Entry point
│
├── 💾 storage_layer/              # Layer persistenza MongoDB
│   ├── models.py                  # Modelli dati MongoDB
│   ├── storage_manager.py         # Gestione storage
│   ├── mongodb_config.py          # Configurazione MongoDB
│   ├── mongodb_utils.py           # Utility MongoDB
│   ├── seed_database.py           # Popolamento DB test
│   ├── exceptions.py              # Eccezioni storage
│   ├── logging_config.py          # Logging storage
│   └── logs/                      # Log storage
│
├── 📚 Docs/                       # Documentazione completa
│   ├── Acronis/                   # Doc integrazione Acronis
│   ├── FlaskAppProxmox/          # Doc integrazione Proxmox
│   ├── NetworkDiscovery/         # Doc network discovery
│   ├── Storage+Generator/        # Doc storage layer
│   ├── Metrics_Dashboard_Complete_Guide.md
│   ├── Report_Analisi_Tecnica_Metrics_Dashboard.md
│   ├── Analisi_Tecnica_*.md      # Analisi tecniche dettagliate
│   └── README.md                  # Indice documentazione
│
├── 📄 requirements.txt            # Dipendenze Python
├── 🎓 Tesi.pdf                   # Tesi di laurea completa
├── 🔧 Crazy_Caesar.py            # Utility cifrario Cesare
└── 📖 README.md                  # Questo file
```

---

## 🔍 Cosa Troverai nella Repository

### 1. **PMI Dashboard** (`pmi_dashboard/`)
Dashboard web principale costruita con Flask che aggrega e visualizza dati da tutte le sorgenti.

**Componenti principali:**
- **Proxmox Integration**: API client per interrogare Proxmox VE, modelli dati per VM/Container/Storage, endpoint REST per frontend
- **Acronis Integration**: API client OAuth2 per Acronis Cyber Protect, gestione configurazione multi-tenant, modelli per backup e protezione dati
- **Web Interface**: Template responsive per visualizzazione dashboard, static assets (CSS/JS/immagini), sistema di routing Flask
- **Logging System**: Configurazione logging multi-livello, file di log rotativi, monitoraggio eventi applicazione

**Tecnologie utilizzate:**
- Flask 3.0
- Jinja2 templates
- RESTful API design
- OAuth2 authentication

### 2. **Metrics Dashboard** (`metrics_dashboard/`)
Modulo specializzato nell'analisi delle metriche e nel rilevamento anomalie tramite machine learning.

**Componenti principali:**
- **Anomaly Detection**: Implementazione Isolation Forest per rilevamento anomalie non supervisionato, sistema di monitoring metriche real-time, gestione threshold dinamici
- **Dataset Management**: Dataset SNMP-MIB reali, dati sintetici per testing, pipeline preprocessing
- **Analytics Engine**: Calcolo metriche Performance/Availability/Resilience, generazione Health Score, analisi trend temporali
- **Visualization**: Dashboard metriche interattive

**Algoritmi implementati:**
- Isolation Forest (principale)
- Statistical Process Control (SPC)

### 3. **Network Discovery** (`network_discovery/`)
Sistema di scoperta automatica della rete e monitoraggio dispositivi tramite SNMP.

**Componenti principali:**
- **SNMP Scanners**: Scanner multi-threaded per subnet, supporto SNMP v1/v2c/v3, auto-discovery dispositivi
- **Device Management**: Inventory dispositivi di rete, raccolta OID SNMP-MIB standard, categorizzazione automatica
- **Configuration**: File YAML per configurazione SNMP, gestione community strings, timeout e retry logic

**Dispositivi supportati:**
- Router, Switch, Firewall
- Server Linux/Windows
- Storage NAS/SAN
- Access Point WiFi
- Stampanti di rete

### 4. **Storage Layer** (`storage_layer/`)
Layer di astrazione per la persistenza dati su MongoDB, con modelli dati ottimizzati per time-series.

**Componenti principali:**
- **Data Models**: Schema Mongoose-like per Python, modelli per Infrastructure/Backups/Polling/Anomalies, validazione dati
- **Storage Manager**: CRUD operations con error handling, query builder con aggregation pipeline, gestione connessioni e pooling
- **Database Seeding**: Script generazione dati di test, dataset realistici per sviluppo, fixture per unit testing
- **MongoDB Utilities**: Helper per operazioni comuni, ottimizzazione indici, gestione time-series collections

**Collections MongoDB:**
- `infrastructure_metrics`: Metriche infrastruttura
- `backup_history`: Cronologia backup
- `polling_data`: Dati polling SNMP
- `anomaly_records`: Anomalie rilevate
- `health_scores`: Punteggi salute sistema

### 5. **Documentazione** (`Docs/`)
Documentazione tecnica completa e approfondita del sistema.

**Contenuti:**
- **Guide Complete**: Metrics Dashboard Complete Guide (2581+ righe), guida architettura sistema PMI
- **Analisi Tecniche**: Analisi metriche Performance SPC, analisi Availability Analytics, analisi Resilience Analytics, analisi tempi raccolta dati
- **Documentazione Moduli**: API documentation per ogni modulo, guide installazione e configurazione, esempi di utilizzo, reference architecture

### 6. **Tesi Completa** (`Tesi.pdf`)
Documento di tesi di laurea completo con tutti i dettagli teorici, implementativi e sperimentali del progetto.

---

## � Calcolo degli Score dei Tre Pilastri

Il sistema EPS+ calcola un **Health Score aggregato** basato su tre pilastri fondamentali: **Performance**, **Availability** e **Resilience**. Ciascun pilastro utilizza formule e metodologie specifiche per valutare lo stato dell'infrastruttura IT.

### 🎯 1. Performance Score (SPC - Statistical Process Control)

Il **Performance Score** si basa sul metodo **Six Sigma** con carte di controllo **XmR (Individual and Moving Range)** per monitorare metriche come CPU, Memory e Disk I/O.

#### Metodologia

1. **Fase Baseline**: Raccolta di 3 giorni di dati (GIORNI_BASELINE_CONFIG = 3) per calcolare i parametri statistici:
   - **CL (Central Line)**: Media dei valori baseline
   - **UCL (Upper Control Limit)**: CL + 2.66 × MR_medio
   - **LCL (Lower Control Limit)**: max(0, CL - 2.66 × MR_medio)
   - **UCL_MR**: 3.268 × MR_medio

2. **Fase Monitoring**: Applicazione di **8 test SPC** su nuovi dati per rilevare anomalie:

   | Test | Descrizione | Score | Livello |
   |------|-------------|-------|---------|
   | **Test 1** | Violazione limiti (UCL/LCL) | 0.1 | 🔴 CRITICO |
   | **Test mR** | Variabilità eccessiva (MR > UCL_MR) | 0.2 | 🔴 CRITICO |
   | **Test Saturazione** | Risorsa al 100% | 0.0 | 🔴 CRITICO |
   | **Test 4** | 7-9 punti consecutivi stesso lato CL | 0.4 | 🟠 ATTENZIONE |
   | **Test 7** | 14 punti oscillatori alternati | 0.4 | 🟠 ATTENZIONE |
   | **Test 8** | 6 punti trend lineare crescente/decrescente | 0.4 | 🟠 ATTENZIONE |
   | **Test 2** | 2 su 3 punti oltre 2σ | 0.5 | 🟡 WARNING |
   | **Test 3** | 4 su 5 punti oltre 1σ | 0.6 | 🟡 WARNING |

3. **Score Finale**:
   - **1.0** = Processo in controllo (normale)
   - **0.0-0.6** = Anomalia rilevata (gravità dipende dal test fallito)

#### Formula Esempio (Test 1):
```python
if valore > UCL:
    score = 0.1  # CRITICO
    dettaglio = "Valore supera Upper Control Limit"
elif valore < LCL:
    score = 0.1  # CRITICO
    dettaglio = "Valore sotto Lower Control Limit"
else:
    score = 1.0  # OK
```

**Implementazione**: `metrics_dashboard/utils/sixsigma_utils.py`

---

### 🟢 2. Availability Score

Il **Availability Score** misura la disponibilità cumulativa dei servizi IT utilizzando una formula basata su **fallimenti cumulativi** e **error budget**.

#### Formula Base

$$
S(P_f, E_b) = \begin{cases}
100\% & \text{se } P_f = 0 \\
100\% - \left(\frac{P_f}{E_b} \times 50\%\right) & \text{se } 0 < P_f \leq E_b \\
\max\left(0, 50\% - \left(\frac{P_f - E_b}{E_b} \times 50\%\right)\right) & \text{se } P_f > E_b
\end{cases}
$$

Dove:
- **P_f** = Fallimenti cumulativi del servizio nel periodo
- **E_b** = Error Budget (soglia fallimenti attesi per tipo servizio)

#### Error Budget per Tipo Servizio

| Tipo Servizio | E_b (default) | Esempio |
|---------------|---------------|---------|
| **Database** | 3 | MySQL, Redis, Elasticsearch |
| **Monitoring** | 4 | Prometheus, Grafana |
| **Web Service** | 5 | Nginx, Apache |
| **File Sharing** | 5 | NFS, SMB |
| **Mail** | 6 | Postfix, Dovecot |
| **CI/CD** | 7 | Jenkins, GitLab Runner |
| **Application** | 8 | Tomcat, Reporting |
| **Backup** | 10 | Backup services |
| **Default** | 5 | Altri servizi |

#### Soglie di Classificazione

| Range Score | Status | Descrizione |
|-------------|--------|-------------|
| **< 50%** | 🔴 CRITICAL | Servizio gravemente compromesso |
| **50% - 80%** | 🟡 ATTENZIONE | Servizio degradato, richiede intervento |
| **> 80%** | 🟢 GOOD | Servizio operativo e stabile |

#### Esempio di Calcolo

**Scenario**: Web Service con E_b = 5

1. **P_f = 0**: Score = 100% ✅ (nessun fallimento)
2. **P_f = 2**: Score = 100% - (2/5 × 50%) = **80%** 🟡
3. **P_f = 5**: Score = 100% - (5/5 × 50%) = **50%** 🟡
4. **P_f = 8**: Score = max(0, 50% - ((8-5)/5 × 50%)) = **20%** 🔴

```python
def calculate_cumulative_score(cumulative_failures, eb_value):
    if cumulative_failures == 0:
        return 1.0  # 100%
    elif 0 < cumulative_failures <= eb_value:
        return 1.0 - ((cumulative_failures / eb_value) * 0.5)
    else:
        return max(0.0, 0.5 - (((cumulative_failures - eb_value) / eb_value) * 0.5))
```

**Implementazione**: `metrics_dashboard/utils/cumulative_availability_analyzer.py`

---

### 🛡️ 3. Resilience Score

Il **Resilience Score** valuta la capacità dell'infrastruttura di backup di rispettare gli obiettivi di **RPO (Recovery Point Objective)** e mantenere un'alta **Success Rate**.

#### Formula Ponderata

$$
\text{Resilience Score} = (w_{RPO} \times \text{RPO Compliance}) + (w_{Success} \times \text{Success Rate})
$$

**Pesi di default**:
- **w_RPO = 0.6** (60%) - Peso RPO Compliance
- **w_Success = 0.4** (40%) - Peso Success Rate

#### 1. RPO Compliance

Misura quanto i backup rispettano gli obiettivi RPO definiti.

$$
\text{RPO Compliance} = \max\left(0, 1 - \frac{\text{RPO Attuale}}{\text{RPO Target}}\right)
$$

**RPO Target di Default**:

| Asset Type | RPO Target | Descrizione |
|------------|------------|-------------|
| **VM** | 24h | Macchine virtuali |
| **Container** | 12h | Container Docker/LXC |
| **Physical** | 48h | Server fisici |
| **Proxmox** | 24h | Hypervisor Proxmox |

**Esempio**:
- Target RPO = 24h, Attuale = 20h → Compliance = max(0, 1 - 20/24) = **16.7%** ⚠️
- Target RPO = 24h, Attuale = 10h → Compliance = max(0, 1 - 10/24) = **58.3%** 🟡
- Target RPO = 24h, Attuale = 2h → Compliance = max(0, 1 - 2/24) = **91.7%** ✅

#### 2. Success Rate

Percentuale di backup completati con successo sul totale.

$$
\text{Success Rate} = \frac{\text{Backup Riusciti Cumulativi}}{\text{Backup Totali Cumulativi}}
$$

**Esempio**:
- 90 backup riusciti su 100 totali → Success Rate = **90%** ✅
- 70 backup riusciti su 100 totali → Success Rate = **70%** 🟡
- 40 backup riusciti su 100 totali → Success Rate = **40%** 🔴

#### Score Finale e Classificazione

| Resilience Score | Livello | Emoji | Descrizione |
|------------------|---------|-------|-------------|
| **> 90%** | EXCELLENT | 🟢 | Sistema backup altamente resiliente |
| **75% - 90%** | GOOD | 🟢 | Resilienza buona, pochi miglioramenti necessari |
| **60% - 75%** | ACCEPTABLE | 🟡 | Resilienza accettabile, richiede attenzione |
| **40% - 60%** | CRITICAL | 🟠 | Resilienza critica, intervento urgente |
| **< 40%** | SEVERE | 🔴 | Sistema backup gravemente compromesso |

#### Esempio Completo di Calcolo

**Scenario**:
- **RPO Attuale**: 16h (Target: 24h)
- **Backup Riusciti**: 85 su 100
- **Pesi**: w_RPO = 0.6, w_Success = 0.4

**Calcolo**:
1. RPO Compliance = max(0, 1 - 16/24) = **0.333** (33.3%)
2. Success Rate = 85/100 = **0.85** (85%)
3. Resilience Score = (0.6 × 0.333) + (0.4 × 0.85) = 0.200 + 0.340 = **0.540** (54%)
4. **Livello**: CRITICAL 🟠 (necessita intervento)

```python
def calculate_resilience_score(rpo_actual, rpo_target, success_count, total_count, 
                                w_rpo=0.6, w_success=0.4):
    rpo_compliance = max(0, 1 - (rpo_actual / rpo_target))
    success_rate = success_count / total_count if total_count > 0 else 0
    resilience_score = (w_rpo * rpo_compliance) + (w_success * success_rate)
    return resilience_score
```

**Implementazione**: `metrics_dashboard/utils/cumulative_resilience_analyzer.py`

---

### 🏆 Aggregazione Health Score Globale

L'**Health Score aggregato** finale può essere calcolato come media ponderata dei tre pilastri:

$$
\text{Health Score} = w_P \times \text{Performance} + w_A \times \text{Availability} + w_R \times \text{Resilience}
$$

Dove:
- **w_P, w_A, w_R** = Pesi configurabili per ciascun pilastro (default: equamente distribuiti)
- Ogni score è normalizzato tra 0.0 e 1.0

**Esempio con pesi uguali (1/3 ciascuno)**:
- Performance = 0.9 (90%)
- Availability = 0.75 (75%)
- Resilience = 0.54 (54%)
- **Health Score** = (0.9 + 0.75 + 0.54) / 3 = **0.73** (73%) 🟡

Questo approccio fornisce una **visione unificata e quantitativa** dello stato di salute dell'intera infrastruttura IT.

---

## �🚀 Quick Start

### Prerequisiti
```bash
# Sistema
- Python 3.8+
- MongoDB 4.x o 5.x
- Git

# Opzionali (per funzionalità complete)
- Proxmox VE server
- Acronis Cyber Protect account
- Dispositivi SNMP-enabled
```

### Installazione
```bash
# 1. Clone repository
git clone https://github.com/Strix89/PMI_DashboardEPS.git
cd PMI_DashboardEPS

# 2. Ambiente virtuale
python -m venv env
.\env\Scripts\activate  # Windows
# source env/bin/activate  # Linux/Mac

# 3. Installa dipendenze
pip install -r requirements.txt

# 4. Configura MongoDB (deve essere in esecuzione)
# mongodb://localhost:27017/

# 5. (Opzionale) Inizializza database con dati test
python storage_layer/seed_database.py

# 6. Avvia PMI Dashboard
cd pmi_dashboard
python app.py
# Apri browser: http://localhost:5000

# 7. (In un nuovo terminale) Avvia Metrics Dashboard
cd metrics_dashboard
python run.py
# Apri browser: http://localhost:5001

# 8. (Opzionale) Avvia Network Discovery
cd network_discovery
python main.py
```

### Configurazione Base

**File `.env` per ogni modulo:**

```bash
# pmi_dashboard/.env
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
PROXMOX_HOST=proxmox.example.com
PROXMOX_USER=root@pam
ACRONIS_CLIENT_ID=your-client-id
ACRONIS_CLIENT_SECRET=your-secret

# metrics_dashboard/.env
FLASK_APP=app.py
FLASK_ENV=development
MONGODB_URI=mongodb://localhost:27017/pmi_dashboard

# storage_layer/.env
MONGODB_URI=mongodb://localhost:27017/pmi_dashboard
MONGODB_DATABASE=pmi_dashboard
```

---

## 📊 Tecnologie Utilizzate

### Backend
- **Flask 3.0**: Framework web principale
- **PyMongo 4.x**: Driver MongoDB
- **PyYAML**: Parsing configurazioni
- **python-dotenv**: Gestione variabili ambiente
- **psutil**: Monitoring sistema
- **cryptography**: Sicurezza dati

### Machine Learning
- **scikit-learn**: Isolation Forest, preprocessing
- **imbalanced-learn**: Gestione dataset sbilanciati
- **numpy/pandas**: Manipolazione dati
- **joblib**: Serializzazione modelli

### Network & Monitoring
- **pysnmp**: Protocollo SNMP
- **python-nmap**: Network scanning
- **netaddr**: Manipolazione indirizzi IP

### Visualization
- **plotly**: Grafici interattivi
- **Flask-SocketIO**: Real-time updates
- **Jinja2**: Template engine

### Database
- **MongoDB**: Database principale NoSQL
- **mongomock**: Testing senza MongoDB

---

## 📚 Documentazione Estesa

Per informazioni dettagliate, consulta:

- **[Docs/README.md](./Docs/README.md)** - Indice completo documentazione
- **[Docs/Metrics_Dashboard_Complete_Guide.md](./Docs/Metrics_Dashboard_Complete_Guide.md)** - Guida completa sistema
- **[Docs/Report_Analisi_Tecnica_Metrics_Dashboard.md](./Docs/Report_Analisi_Tecnica_Metrics_Dashboard.md)** - Report tecnico
- **[Tesi.pdf](./Tesi.pdf)** - Documento tesi completo

### Documentazione per Modulo

| Modulo | Path Documentazione | Contenuti |
|--------|-------------------|-----------|
| **Proxmox** | `Docs/FlaskAppProxmox/` | API, Architecture, Installation, Config |
| **Acronis** | `Docs/Acronis/` | API, Configuration, User Guide |
| **Network** | `Docs/NetworkDiscovery/` | API Reference, Architecture, Examples |
| **Storage** | `Docs/Storage+Generator/` | Schema DB, Metrics, Seeding |

---

## 🤝 Contributi

Contributi, issue e feature request sono benvenuti! Sentiti libero di controllare la [issues page](https://github.com/Strix89/PMI_DashboardEPS/issues).

---

## 📄 Licenza

Questo progetto è sviluppato come parte di una tesi di laurea in collaborazione con Evolumia.

---

## 👤 Autore

**Tommaso**
- GitHub: [@Strix89](https://github.com/Strix89)
- Progetto: Tesi di Laurea Magistrale
- Partner: Evolumia

---

## 🎓 Citazione

```bibtex
@mastersthesis{eps_plus_2024,
  author = {Tommaso},
  title = {EPS+: Sistema di Monitoraggio Open Source per Infrastrutture IT Ibride delle PMI},
  school = {Università degli Studi},
  year = {2024},
  note = {In collaborazione con Evolumia}
}
```

---

<div align="center">

**Made with ❤️ for the PMI Community**

</div>
