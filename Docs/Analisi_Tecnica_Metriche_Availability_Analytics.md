# Analisi Tecnica: Sistema di Calcolo Metriche Availability Analytics

## 📋 Panoramica del Sistema

Il modulo **Availability Analytics** del progetto `metrics_dashboard` implementa un sistema completo di monitoraggio e analisi cumulativa della disponibilità dei servizi IT. Il sistema utilizza una formula matematica sofisticata per calcolare score di availability basati su error budget configurabili, con supporto per analisi temporali e aggregazione ponderata multi-servizio.

## 🏗️ Architettura del Sistema

### Componenti Principali

#### 1. **Backend - Motore di Analisi** (`utils/cumulative_availability_analyzer.py`)
- **Funzione**: Calcolo score cumulativi, analisi temporale, aggregazione ponderata
- **Database**: MongoDB `infrastructure_monitoring.metrics` (collection availability_status)
- **Algoritmo**: Formula cumulativa con error budget e soglie di status

#### 2. **Frontend - Dashboard Interattiva** (`templates/availability_dashboard.html`)
- **Librerie**: ECharts per gauge semicircolari, Bootstrap per UI responsive
- **Visualizzazione**: Tachimetri per singoli servizi + gauge aggregato centrale
- **Controlli**: Timeline temporale, velocità simulazione, play/pause

#### 3. **JavaScript Engine** (`availability_dashboard.html` - script integrato)
- **Funzione**: Simulazione temporale, aggiornamento real-time, gestione stati
- **Comunicazione**: API REST con backend Flask
- **Features**: Sincronizzazione ora reale, controlli velocità, mapping nomi servizi

#### 4. **Generatore Dati** (`storage_layer/seed_database.py`)
- **Funzione**: Simulazione dati availability realistici con pattern di downtime
- **Frequenza**: Polling ogni minuto per tutti i servizi e macchine
- **Pattern**: Downtime programmato, degradazione graduale, failure casuali

#### 5. **Configurazione** (`templates/availability_config.html`)
- **Funzione**: Setup error budget personalizzati e pesi servizi
- **Validazione**: Auto-bilanciamento pesi, normalizzazione automatica
- **Workflow**: 3 step guidati (Error Budget → Pesi → Riepilogo)

## 🔬 Algoritmi di Calcolo

### Formula Cumulativa di Availability

Il sistema implementa una formula sofisticata per il calcolo del score di availability:

```python
def calculate_cumulative_score(cumulative_failures: int, eb_value: int) -> float:
    """
    Calcola il punteggio cumulativo usando la formula specificata.
    
    Formula:
    S(P_f, E_b) = 
    - 100% se P_f = 0                                    (Nessun fallimento)
    - 100% - (P_f/E_b × 50%) se 0 < P_f ≤ E_b           (Fallimenti sotto soglia)
    - max(0, 50% - ((P_f - E_b)/E_b × 50%)) se P_f > E_b (Fallimenti sopra soglia)
    
    Dove:
    - P_f = Numero di fallimenti cumulativi per servizio
    - E_b = Error Budget configurabile per tipo di servizio
    """
    if cumulative_failures == 0:
        return 1.0  # 100% - Perfetto
    
    elif 0 < cumulative_failures <= eb_value:
        # Degradazione lineare fino al 50%
        score = 1.0 - ((cumulative_failures / eb_value) * 0.5)
        return score
    
    else:  # cumulative_failures > eb_value
        # Degradazione accelerata sotto il 50%
        score = max(0.0, 0.5 - (((cumulative_failures - eb_value) / eb_value) * 0.5))
        return score
```

### Error Budget per Tipo di Servizio

Il sistema utilizza error budget differenziati per tipo di servizio:

```python
# Configurazione E_b per tipo di servizio (fallimenti attesi) - DEFAULT
default_service_eb_config = {
    "web_service": 5,      # Servizi web (nginx, apache)
    "database": 3,         # Database (mysql, redis, elasticsearch) - Più critici
    "application": 8,      # Applicazioni (tomcat, reporting)
    "backup": 10,          # Servizi di backup - Meno critici
    "monitoring": 4,       # Prometheus, grafana
    "mail": 6,             # Postfix, dovecot
    "ci_cd": 7,            # Jenkins, gitlab-runner
    "file_sharing": 5,     # NFS, SMB
    "default": 5           # Valore di default
}
```

### Formula Score Aggregato Ponderato

Il sistema calcola un Availability Score globale utilizzando pesi configurabili:

```python
def calculate_aggregated_score(services_data, service_weights):
    """
    Calcola score aggregato ponderato per tutti i servizi
    """
    total_weighted_score = 0
    total_weight = 0
    
    for service_name, service_data in services_data.items():
        score = service_data.get('final_score', 0)
        weight = service_weights.get(service_name, 1.0 / len(services_data))  # Default: peso uguale
        
        total_weighted_score += score * weight
        total_weight += weight
    
    aggregated_score = total_weighted_score / total_weight if total_weight > 0 else 0
    return aggregated_score
```

### Classificazione Status

Il sistema classifica i servizi in base al score calcolato:

```python
def determine_status_type(score: float) -> StatusType:
    """
    Determina il tipo di status basato sul punteggio.
    """
    if score < 0.5:        # < 50%
        return "CRITICAL"   # 🔴 Rosso
    elif score < 0.8:      # 50%-80%
        return "ATTENZIONE" # 🟡 Giallo
    else:                  # > 80%
        return "GOOD"       # 🟢 Verde
```

## 🗄️ Generazione Dati di Availability

### Simulazione Realistica nel Storage Layer

Il sistema genera dati di availability realistici attraverso `storage_layer/seed_database.py`:

```python
def generate_polling_history(storage_manager, pattern_generator, days=14):
    """
    Genera cronologia di polling per calcoli availability.
    
    Crea dati minuto-per-minuto per tutti i servizi e macchine,
    simulando pattern realistici di availability inclusi:
    - Downtime programmato
    - Failure casuali
    - Degradazione graduale
    - Dipendenze tra servizi
    """
    
    # Calcola range temporale
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=days)
    
    # Per ogni minuto nel range
    current_time = start_time
    while current_time < end_time:
        for asset in all_assets:
            # Determina status availability
            if asset_type == "service":
                availability_status = determine_service_availability(asset, current_time)
            else:
                availability_status = determine_machine_availability(asset, current_time)
            
            # Crea record metrica
            polling_metric = create_metric_document(
                timestamp=current_time,
                asset_id=asset_id,
                metric_name="availability_status",
                value=availability_status,  # 1.0 = UP, 0.0 = DOWN
            )
        
        current_time += timedelta(minutes=1)
```

### Pattern di Availability per Servizi

```python
def determine_service_availability(asset, timestamp, pattern_generator) -> float:
    """
    Determina status availability servizio basato su vari fattori.
    """
    service_def = asset.get("service_def", {})
    hour = timestamp.hour
    
    # 1. DOWNTIME PROGRAMMATO
    downtime_schedule = service_def.get("downtime_schedule")
    if downtime_schedule:
        start_hour = downtime_schedule["start_hour"]
        end_hour = downtime_schedule["end_hour"]
        
        # Gestisce downtime che attraversa mezzanotte
        if start_hour > end_hour:  # es. 23:00-01:00
            if hour >= start_hour or hour <= end_hour:
                return 0.0  # Servizio down per manutenzione
        else:  # Finestra normale
            if start_hour <= hour <= end_hour:
                return 0.0  # Servizio down per manutenzione
    
    # 2. PATTERN DI DEGRADAZIONE
    degradation_pattern = service_def.get("degradation_pattern")
    if degradation_pattern == "memory_pressure":
        # Simula degradazione graduale per problemi memoria
        days_since_epoch = (timestamp - datetime(2024, 1, 26, tzinfo=UTC)).days
        memory_pressure_cycle = days_since_epoch % 7  # Ciclo settimanale
        
        if memory_pressure_cycle >= 5:  # Giorni 5-6 della settimana
            degradation_chance = (memory_pressure_cycle - 4) * 0.4  # 40% giorno 5, 80% giorno 6
            if random.random() < degradation_chance:
                return 0.0  # Servizio down per memory pressure
    
    # 3. FAILURE CASUALI (Target 99.5% uptime)
    service_reliability = 0.995
    random_factor = hash(f"{asset['asset_id']}_{timestamp.hour}_{timestamp.minute}") % 10000 / 10000.0
    
    if random_factor > service_reliability:
        return 0.0  # Servizio down
    
    # Servizio funzionante normalmente
    return 1.0
```

### Pattern di Availability per Macchine

```python
def determine_machine_availability(asset, timestamp, pattern_generator) -> float:
    """
    Determina status availability macchina basato su pattern performance.
    """
    pattern = asset.get("performance_pattern", "stable_low_load")
    
    # Macchine generalmente più affidabili dei servizi (99.9% uptime)
    machine_reliability = 0.999
    random_factor = hash(f"{asset['asset_id']}_{timestamp.hour}_{timestamp.minute}") % 10000 / 10000.0
    
    if random_factor > machine_reliability:
        return 0.0  # Macchina down
    
    # Controlli specifici per pattern
    if pattern == "memory_leak_pattern":
        # Maggiore probabilità failure durante memory pressure
        days_since_epoch = (timestamp - datetime(2024, 1, 26, tzinfo=UTC)).days
        memory_pressure = min(1.0, (days_since_epoch % 7) / 7.0)
        
        if memory_pressure > 0.8 and random.random() < 0.01:  # 1% chance durante alta pressione
            return 0.0
    
    elif pattern == "volatile_load":
        # Failure occasionali per spike di carico
        spike_factor = hash(f"{asset['asset_id']}_load_{timestamp.hour}_{timestamp.minute // 5}") % 100
        if spike_factor < 2:  # 2% probabilità failure legato al carico
            return 0.0
    
    # Macchina funzionante normalmente
    return 1.0
```

## 🎨 Sistema di Visualizzazione

### Gauge Semicircolari ECharts

Il frontend utilizza ECharts per creare tachimetri semicircolari per ogni servizio:

```javascript
// Configurazione gauge ECharts per singolo servizio
function createServiceGauge(serviceData) {
    const gaugeOption = {
        series: [{
            type: 'gauge',
            startAngle: 180,
            endAngle: 0,
            center: ['50%', '75%'],
            radius: '90%',
            min: 0,
            max: 100,
            splitNumber: 8,
            axisLine: {
                lineStyle: {
                    width: 6,
                    color: [
                        [0.5, '#e74c3c'],    // 0-50%: Rosso (CRITICAL)
                        [0.8, '#f39c12'],    // 50-80%: Arancione (ATTENZIONE)
                        [1, '#27ae60']       // 80-100%: Verde (GOOD)
                    ]
                }
            },
            pointer: {
                icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
                length: '12%',
                width: 20,
                offsetCenter: [0, '-60%'],
                itemStyle: {
                    color: 'auto'
                }
            },
            axisTick: {
                length: 12,
                lineStyle: {
                    color: 'auto',
                    width: 2
                }
            },
            splitLine: {
                length: 20,
                lineStyle: {
                    color: 'auto',
                    width: 5
                }
            },
            axisLabel: {
                color: '#464646',
                fontSize: 20,
                distance: -60,
                formatter: function (value) {
                    return value + '%';
                }
            },
            title: {
                offsetCenter: [0, '-20%'],
                fontSize: 20
            },
            detail: {
                fontSize: 30,
                offsetCenter: [0, '-35%'],
                valueAnimation: true,
                formatter: function (value) {
                    return Math.round(value) + '%';
                },
                color: 'auto'
            },
            data: [{
                value: serviceData.final_score * 100,
                name: serviceData.service_name
            }]
        }]
    };
    
    return gaugeOption;
}
```

### Gauge Aggregato Centrale

```javascript
// Gauge principale per score aggregato di sistema
function initializeAggregatedGauge() {
    const aggregatedGauge = echarts.init(document.getElementById('aggregated-gauge'));
    
    const option = {
        series: [{
            type: 'gauge',
            startAngle: 180,
            endAngle: 0,
            center: ['50%', '75%'],
            radius: '90%',
            min: 0,
            max: 100,
            splitNumber: 10,
            axisLine: {
                lineStyle: {
                    width: 8,
                    color: [
                        [0.5, '#FF6B6B'],    // Critico
                        [0.8, '#FFD93D'],    // Attenzione  
                        [1, '#6BCF7F']       // Buono
                    ]
                }
            },
            pointer: {
                icon: 'path://M2090.36389,615.30999 L2090.36389,615.30999 C2091.48372,615.30999 2092.40383,616.194028 2092.44859,617.312956 L2096.90698,728.755929 C2097.05155,732.369577 2094.1393,735.416212 2090.5256,735.416212 L2090.5256,735.416212 C2086.91190,735.416212 2083.99965,732.369577 2084.14422,728.755929 L2088.60261,617.312956 C2088.64737,616.194028 2089.56748,615.30999 2090.68731,615.30999 Z',
                length: '75%',
                width: 16,
                offsetCenter: [0, '5%'],
                itemStyle: {
                    color: '#C23531'
                }
            },
            data: [{
                value: 0,
                name: 'System Availability'
            }]
        }]
    };
    
    aggregatedGauge.setOption(option);
    echartsInstances['aggregated'] = aggregatedGauge;
}
```

### Colorazione Dinamica Status

```javascript
// Sistema di colorazione basato su score
function getStatusColor(score) {
    if (score >= 0.8) {
        return {
            color: '#27ae60',      // Verde
            class: 'good',
            text: 'GOOD'
        };
    } else if (score >= 0.5) {
        return {
            color: '#f39c12',      // Arancione
            class: 'attenzione', 
            text: 'ATTENZIONE'
        };
    } else {
        return {
            color: '#e74c3c',      // Rosso
            class: 'critical',
            text: 'CRITICAL'
        };
    }
}

// Applicazione colori ai badge di status
function updateServiceStatus(serviceName, score, status) {
    const statusBadge = document.querySelector(`#service-${serviceName} .status-badge`);
    const statusInfo = getStatusColor(score);
    
    statusBadge.className = `status-badge ${statusInfo.class}`;
    statusBadge.textContent = statusInfo.text;
    statusBadge.style.backgroundColor = statusInfo.color;
}
```

## 🌐 API e Comunicazione

### Endpoints Principali

#### **GET /availability/**
```json
// Response: Pagina selezione file JSON esistenti o generazione nuova analisi
{
    "template": "availability_index.html",
    "json_files": [
        {
            "filename": "cumulative_availability_analysis_20250109_143022.json",
            "analysis_timestamp": "2025-01-09T14:30:22.123456",
            "analysis_dates": ["2025-01-08"],
            "total_services": 17
        }
    ],
    "has_files": true
}
```

#### **GET /availability/config**
```json
// Response: Pagina configurazione parametri
{
    "template": "availability_config.html", 
    "default_config": {
        "error_budget": 5
    }
}
```

#### **POST /availability/start_analysis**
```json
// Request: Configurazione per avvio analisi
{
    "service_error_budgets": {
        "Proxmox Web Interface": 3,
        "MySQL Database": 2,
        "Nginx Web Server": 5
    },
    "service_weights": {
        "Proxmox Web Interface": 0.25,
        "MySQL Database": 0.35,
        "Nginx Web Server": 0.40
    },
    "dashboard_type": "availability"
}

// Response: Job ID per tracking
{
    "success": true,
    "job_id": "availability_analysis_20250109_143022"
}
```

#### **GET /availability/analysis_progress**
```json
// Response: Stato progresso analisi
{
    "status": "running",        // "idle", "running", "completed", "error"
    "progress": 75,             // Percentuale completamento
    "result": null              // Risultato se completato
}
```

#### **GET /availability/get_dashboard_data**
```json
// Response: Dati completi per dashboard
{
    "success": true,
    "services": {
        "Proxmox Web Interface": {
            "service_id": "svc-pveproxy-01",
            "error_budget": 3,
            "weight": 0.25,
            "days_analyzed": 1,
            "total_failures": 2,
            "final_score": 0.6667,
            "final_status": "ATTENZIONE",
            "timeline": [
                {
                    "timestamp": "2025-01-08T00:00:00",
                    "score": 1.0,
                    "status_type": "GOOD",
                    "cumulative_failures": 0,
                    "current_value": 1.0
                },
                {
                    "timestamp": "2025-01-08T00:01:00", 
                    "score": 0.8333,
                    "status_type": "GOOD",
                    "cumulative_failures": 1,
                    "current_value": 0.0
                }
            ]
        }
    },
    "summary": {
        "total_services": 17,
        "aggregated_score": 0.8234,
        "aggregated_status": "GOOD",
        "total_days_analyzed": 1
    },
    "aggregated_score": 0.8234
}
```

#### **GET /get_services**
```json
// Response: Lista servizi disponibili per configurazione
{
    "success": true,
    "services": [
        {
            "id": "507f1f77bcf86cd799439011",
            "name": "Proxmox Web Interface",
            "description": "Servizio Proxmox Web Interface", 
            "status": "active",
            "type": "web_service"
        },
        {
            "id": "507f1f77bcf86cd799439012",
            "name": "MySQL Database",
            "description": "Servizio MySQL Database",
            "status": "active", 
            "type": "database"
        }
    ]
}
```

## 🔄 Workflow Operativo

### Processo di Analisi Completo

#### **Step 1: Configurazione**
1. **Accesso**: `/availability/config`
2. **Error Budget**: Configurazione fallimenti attesi per servizio
3. **Pesi Servizi**: Distribuzione importanza relativa (somma = 100%)
4. **Validazione**: Auto-bilanciamento e controlli coerenza

#### **Step 2: Generazione Analisi**
1. **Avvio Job**: Subprocess `cumulative_availability_analyzer.py`
2. **Selezione Giorno**: Giorno casuale con dati availability
3. **Calcolo Score**: Formula cumulativa per ogni servizio
4. **Aggregazione**: Score ponderato globale di sistema

#### **Step 3: Visualizzazione Dashboard**
1. **Caricamento Dati**: API `/availability/get_dashboard_data`
2. **Rendering Gauge**: ECharts per servizi individuali + aggregato
3. **Timeline**: Navigazione temporale con controlli velocità
4. **Real-time**: Sincronizzazione con ora corrente

### Simulazione Temporale

```javascript
// Logica di simulazione temporale nel frontend
function startRealTimeUpdates() {
    updateInterval = setInterval(() => {
        if (isRealTimeActive && !isPaused) {
            // Avanza timeline
            currentTimelineIndex++;
            
            if (currentTimelineIndex >= maxTimelineIndex) {
                currentTimelineIndex = 0; // Loop
            }
            
            // Aggiorna dashboard
            updateDashboard();
            updateTimelineInfo();
        }
    }, updateSpeed / speedMultiplier);
}

// Controlli velocità simulazione
function setSpeed(multiplier) {
    speedMultiplier = multiplier;
    document.getElementById('speed-display').textContent = `${multiplier}x`;
    
    // Riavvia interval con nuova velocità
    if (updateInterval) {
        clearInterval(updateInterval);
        startRealTimeUpdates();
    }
}

// Sincronizzazione con ora reale
function syncWithCurrentTime() {
    const now = new Date();
    let bestMatchIndex = 0;
    
    // Cerca nel primo servizio per determinare range temporale
    const firstService = Object.values(dashboardData.services)[0];
    if (firstService && firstService.timeline) {
        const currentHour = now.getHours();
        const currentMinute = now.getMinutes();
        
        // Trova orario corrispondente nei dati storici
        firstService.timeline.forEach((item, index) => {
            if (item.timestamp) {
                const itemTime = new Date(item.timestamp);
                const itemHour = itemTime.getHours();
                const itemMinute = itemTime.getMinutes();
                
                const timeDiff = Math.abs(
                    (currentHour * 60 + currentMinute) - 
                    (itemHour * 60 + itemMinute)
                );
                
                if (timeDiff < minTimeDiff) {
                    minTimeDiff = timeDiff;
                    bestMatchIndex = index;
                }
            }
        });
    }
    
    currentTimelineIndex = bestMatchIndex;
}
```

## 🗄️ Struttura Database

### Collection: infrastructure_monitoring.metrics

```javascript
// Documento metrica availability
{
    "_id": ObjectId("..."),
    "timestamp": ISODate("2025-01-08T10:30:00.000Z"),
    "meta": {
        "asset_id": "svc-pveproxy-01",
        "metric_name": "availability_status",
        "source": "polling_system",
        "tags": {
            "service_type": "web_service",
            "criticality": "high"
        }
    },
    "value": 1.0,                    // 1.0 = UP, 0.0 = DOWN
    "unit": "status",
    "created_at": ISODate("2025-01-08T10:30:00.000Z")
}
```

### Collection: infrastructure_monitoring.assets

```javascript
// Documento asset servizio
{
    "_id": ObjectId("..."),
    "asset_id": "svc-pveproxy-01",
    "asset_type": "service",
    "name": "Proxmox Web Interface",
    "service_name": "Proxmox Web Interface",
    "hostname": "proxmox-01.local",
    "status": "active",
    "type": "web_service",
    "data": {
        "service_type": "web_service",
        "port": 8006,
        "protocol": "https",
        "dependencies": ["proxmox-node-01"]
    },
    "service_def": {
        "service_name": "pveproxy",
        "service_type": "web_service",
        "port": 8006,
        "downtime_schedule": {
            "start_hour": 2,
            "end_hour": 3,
            "description": "Manutenzione notturna"
        },
        "degradation_pattern": null
    },
    "created_at": ISODate("2025-01-08T00:00:00.000Z"),
    "updated_at": ISODate("2025-01-08T00:00:00.000Z")
}
```

## 📊 File Coinvolti

### **Backend**
- `app.py` - Server Flask principale con API endpoints availability
- `utils/cumulative_availability_analyzer.py` - Motore calcolo score cumulativi
- `utils/availability_summary.py` - Modulo aggregazione e statistiche
- `storage_layer/storage_manager.py` - Gestione connessioni MongoDB
- `storage_layer/seed_database.py` - Generatore dati availability realistici

### **Frontend**
- `templates/availability_index.html` - Pagina selezione file JSON
- `templates/availability_config.html` - Configurazione error budget e pesi
- `templates/availability_dashboard.html` - Dashboard principale con gauge
- `static/css/` - Stili CSS per temi chiaro/scuro
- JavaScript integrato nei template per logica frontend

### **Configurazione**
- `.env` - Configurazione database e parametri applicazione
- `requirements.txt` - Dipendenze Python (Flask, PyMongo, NumPy)

## 🎯 Casi d'Uso e Scenari

### Scenario 1: Servizio Perfetto (Score 100%)
1. **Condizione**: Nessun fallimento rilevato (P_f = 0)
2. **Calcolo**: S(0, E_b) = 100%
3. **Visualizzazione**: Gauge verde, badge "GOOD"
4. **Timeline**: Tutti i punti a 1.0 (UP)

### Scenario 2: Servizio in Degradazione (Score 75%)
1. **Condizione**: 2 fallimenti con E_b = 8
2. **Calcolo**: S(2, 8) = 100% - (2/8 × 50%) = 87.5%
3. **Visualizzazione**: Gauge verde chiaro, badge "GOOD"
4. **Timeline**: Maggioranza punti UP con alcuni DOWN

### Scenario 3: Servizio Critico (Score 25%)
1. **Condizione**: 15 fallimenti con E_b = 5
2. **Calcolo**: S(15, 5) = max(0, 50% - ((15-5)/5 × 50%)) = 0%
3. **Visualizzazione**: Gauge rosso, badge "CRITICAL"
4. **Timeline**: Molti punti DOWN consecutivi

### Scenario 4: Configurazione Pesi Personalizzata
1. **Setup**: Database MySQL peso 50%, Web Server peso 30%, Backup peso 20%
2. **Calcolo**: Score_aggregato = (0.9×0.5) + (0.8×0.3) + (0.6×0.2) = 0.81
3. **Risultato**: Sistema "GOOD" nonostante backup degradato
4. **Rationale**: Database critico ha peso maggiore

## 🔧 Configurazione e Personalizzazione

### Parametri Configurabili

```python
# Error Budget per tipo servizio
DEFAULT_SERVICE_EB_CONFIG = {
    "web_service": 5,      # Servizi web standard
    "database": 3,         # Database più critici
    "application": 8,      # Applicazioni meno critiche
    "backup": 10,          # Backup tollerano più failure
    "monitoring": 4,       # Monitoring importante
    "mail": 6,             # Mail servizi medi
    "ci_cd": 7,            # CI/CD meno critici
    "file_sharing": 5,     # File sharing standard
    "default": 5           # Fallback
}

# Soglie classificazione status
STATUS_THRESHOLDS = {
    "critical": 0.5,       # < 50% = CRITICAL
    "attenzione": 0.8      # 50%-80% = ATTENZIONE, > 80% = GOOD
}

# Configurazione simulazione temporale
SIMULATION_CONFIG = {
    "base_update_speed": 60000,    # 1 minuto base
    "max_speed_multiplier": 500,   # Velocità massima 500x
    "sync_with_real_time": True,   # Sincronizza con ora reale
    "loop_timeline": True          # Loop automatico timeline
}
```

### Personalizzazione Error Budget

```javascript
// Configurazione dinamica error budget nel frontend
function updateGlobalErrorBudget() {
    const globalValue = document.getElementById('error-budget-input').value;
    const serviceInputs = document.querySelectorAll('.error-budget-service');
    
    serviceInputs.forEach(input => {
        input.value = globalValue;
    });
    
    console.log('Error Budget aggiornati a', globalValue, 'per tutti i servizi');
}

// Validazione pesi servizi
function updateWeights() {
    let totalWeight = 0;
    const weights = document.querySelectorAll('.service-weight');
    
    weights.forEach(weight => {
        totalWeight += parseFloat(weight.value);
    });
    
    // Controllo somma = 1.0
    const isValid = Math.abs(totalWeight - 1.0) < 0.001;
    document.getElementById('weights-next-btn').disabled = !isValid;
    
    // Aggiorna progress bar
    const percentage = Math.min(100, totalWeight * 100);
    document.getElementById('weights-progress').style.width = `${percentage}%`;
}
```

## 📈 Metriche e KPI

### Performance Indicators

| Metrica | Descrizione | Range | Interpretazione |
|---------|-------------|-------|-----------------|
| **Availability Score** | Score cumulativo servizio | 0.0 - 1.0 | > 0.8 Buono, 0.5-0.8 Attenzione, < 0.5 Critico |
| **Aggregated Score** | Score ponderato sistema | 0.0 - 1.0 | Availability complessiva infrastruttura |
| **Error Budget Utilization** | % budget consumato | 0% - ∞ | > 100% indica superamento soglia |
| **Service Uptime** | % tempo operativo | 0% - 100% | Uptime grezzo senza error budget |

### Statistiche Dashboard

```javascript
// Calcolo statistiche real-time
function calculateDashboardStats(servicesData) {
    const stats = {
        total_services: Object.keys(servicesData).length,
        services_good: 0,
        services_attention: 0, 
        services_critical: 0,
        avg_score: 0,
        min_score: 1.0,
        max_score: 0.0
    };
    
    let totalScore = 0;
    
    Object.values(servicesData).forEach(service => {
        const score = service.final_score;
        totalScore += score;
        
        // Aggiorna min/max
        stats.min_score = Math.min(stats.min_score, score);
        stats.max_score = Math.max(stats.max_score, score);
        
        // Classifica per status
        if (score >= 0.8) {
            stats.services_good++;
        } else if (score >= 0.5) {
            stats.services_attention++;
        } else {
            stats.services_critical++;
        }
    });
    
    stats.avg_score = totalScore / stats.total_services;
    return stats;
}
```

## 🚀 Deployment e Scalabilità

### Requisiti di Sistema

- **CPU**: 2+ cores per analisi cumulativa
- **RAM**: 4GB+ per cache dati e calcoli
- **Storage**: 20GB+ per dati storici MongoDB
- **Network**: Connessione stabile per polling real-time

### Ottimizzazioni Performance

```python
# Ottimizzazioni query MongoDB
def get_metrics_optimized(asset_id, start_time, end_time):
    """
    Query ottimizzata con indici composti
    """
    # Indice: {"meta.asset_id": 1, "meta.metric_name": 1, "timestamp": -1}
    query_filter = {
        "meta.asset_id": asset_id,
        "meta.metric_name": "availability_status",
        "timestamp": {"$gte": start_time, "$lte": end_time}
    }
    
    # Proiezione per ridurre trasferimento dati
    projection = {
        "timestamp": 1,
        "value": 1,
        "_id": 0
    }
    
    return collection.find(query_filter, projection).sort("timestamp", 1)

# Cache per baseline e configurazioni
availability_cache = {
    "service_configs": {},     # Cache configurazioni servizi
    "error_budgets": {},       # Cache error budget
    "analysis_results": {}     # Cache risultati analisi
}
```

### Monitoraggio Sistema

```python
# Logging strutturato per debugging
logger.info(f"Analisi avviata per {len(services)} servizi")
logger.info(f"Giorno selezionato: {random_date.strftime('%Y-%m-%d')}")
logger.info(f"Score aggregato finale: {aggregated_score:.4f}")

# Metriche performance
analysis_metrics = {
    "services_analyzed": len(services),
    "total_data_points": sum(len(s.get('timeline', [])) for s in services.values()),
    "analysis_duration": time.time() - start_time,
    "memory_usage": psutil.Process().memory_info().rss / 1024 / 1024  # MB
}
```

## 📋 Conclusioni

Il sistema Availability Analytics implementato nel progetto `metrics_dashboard` rappresenta una soluzione completa e sofisticata per il monitoraggio della disponibilità dei servizi IT. Le caratteristiche principali includono:

### Punti di Forza
- **Formula Matematica Rigorosa**: Algoritmo cumulativo con error budget personalizzabili
- **Visualizzazione Avanzata**: Gauge ECharts semicircolari con colorazione dinamica
- **Simulazione Realistica**: Generazione dati con pattern di downtime programmato e failure casuali
- **Configurazione Flessibile**: Error budget e pesi personalizzabili per tipo servizio
- **Timeline Interattiva**: Navigazione temporale con controlli velocità e sincronizzazione real-time

### Applicazioni Pratiche
- Monitoraggio SLA e compliance availability
- Analisi impatto downtime su business continuity
- Ottimizzazione allocazione risorse IT
- Identificazione servizi critici e pattern failure
- Reporting availability per management

### Valore Aggiunto
Il sistema trasforma il monitoraggio availability tradizionale in un approccio analitico avanzato, fornendo score quantitativi basati su error budget configurabili e permettendo analisi comparative tra servizi con criticità diverse attraverso aggregazione ponderata.