# Analisi Tecnica - Metriche di Resilience Analytics

## Panoramica Generale

Il modulo **Resilience Analytics** del `metrics_dashboard` è progettato per analizzare e monitorare la resilienza dei backup e la capacità di recovery dell'infrastruttura IT. Il sistema calcola metriche di resilienza basate su **RPO Compliance** e **Success Rate** per backup jobs e asset individuali, fornendo una simulazione ora per ora per una settimana completa (168 ore).

## Architettura del Sistema

### Struttura dei File

#### Backend (Python)
- **`metrics_dashboard/app.py`**: Applicazione Flask principale con route per resilience
- **`metrics_dashboard/utils/cumulative_resilience_analyzer.py`**: Motore di calcolo delle metriche di resilience
- **`metrics_dashboard/output/`**: Directory contenente i file JSON generati dalle analisi

#### Frontend (HTML/JavaScript)
- **`metrics_dashboard/templates/resilience_index.html`**: Pagina di selezione analisi esistenti o nuova generazione
- **`metrics_dashboard/templates/resilience_config.html`**: Interfaccia di configurazione pesi e RPO
- **`metrics_dashboard/templates/resilience_dashboard.html`**: Dashboard di visualizzazione in tempo reale

#### File di Output
- **`metrics_dashboard/output/resilience_analysis_YYYYMMDD_HHMMSS.json`**: File JSON contenenti i risultati delle analisi

## Calcolo delle Metriche di Resilience

### 1. Metriche Fondamentali

#### RPO Compliance (Recovery Point Objective Compliance)
```python
def calculate_rpo_compliance(self, last_successful_backup: Optional[datetime], 
                           current_time: datetime, target_rpo_hours: int) -> float:
    """
    Calcola la RPO Compliance.
    Formula: max(0, 1 - (actual_RPO / target_RPO))
    """
    if last_successful_backup is None:
        return 1.0  # Nessun backup ancora riuscito = compliance perfetta (100%)
    
    # Calcola actual RPO in ore
    time_diff = current_time - last_successful_backup
    actual_rpo_hours = time_diff.total_seconds() / 3600
    
    # Se actual_rpo_hours è negativo (backup nel futuro), considera RPO = 0
    if actual_rpo_hours < 0:
        actual_rpo_hours = 0
    
    # Formula: max(0, 1 - (actual_RPO / target_RPO))
    rpo_compliance = max(0.0, min(1.0, 1.0 - (actual_rpo_hours / target_rpo_hours)))
    return rpo_compliance
```

**Spiegazione RPO Compliance:**
- **Target RPO**: Tempo massimo accettabile tra backup consecutivi (configurabile per asset/job)
- **Actual RPO**: Tempo effettivo trascorso dall'ultimo backup riuscito
- **Punteggio**: 1.0 = perfetto (backup entro target), 0.0 = critico (RPO superato)

#### Success Rate
```python
def calculate_success_rate(self, total_successful: int, total_attempted: int) -> float:
    """
    Calcola il Success Rate cumulativo.
    """
    if total_attempted == 0:
        return 1.0  # Default al 100% se non ci sono ancora tentativi
    
    return total_successful / total_attempted
```

**Spiegazione Success Rate:**
- **Percentuale di backup completati con successo** sul totale dei tentativi
- **Calcolo cumulativo**: considera tutti i backup dall'inizio della simulazione
- **Punteggio**: 1.0 = 100% successi, 0.0 = 0% successi

### 2. Resilience Score Finale

```python
def calculate_resilience_score(self, rpo_compliance: float, success_rate: float,
                             weights: Dict[str, float]) -> float:
    """
    Calcola il punteggio finale di resilienza.
    Formula: (w_rpo × RPO_Compliance) + (w_success × Success_Rate)
    """
    w_rpo = weights.get('w_rpo', 0.6)      # Peso RPO Compliance (default 60%)
    w_success = weights.get('w_success', 0.4)  # Peso Success Rate (default 40%)
    
    return (w_rpo * rpo_compliance) + (w_success * success_rate)
```

### 3. Livelli di Resilience

```python
class ResilienceLevel(Enum):
    EXCELLENT = "EXCELLENT"      # > 90%
    GOOD = "GOOD"               # 75% - 90%
    ACCEPTABLE = "ACCEPTABLE"    # 60% - 75%
    CRITICAL = "CRITICAL"       # 40% - 60%
    SEVERE = "SEVERE"           # < 40%

def determine_resilience_level(self, score: float) -> ResilienceLevel:
    """Determina il livello di resilienza basato sul punteggio."""
    if score >= 0.9:    return ResilienceLevel.EXCELLENT
    elif score >= 0.75: return ResilienceLevel.GOOD
    elif score >= 0.6:  return ResilienceLevel.ACCEPTABLE
    elif score >= 0.4:  return ResilienceLevel.CRITICAL
    else:               return ResilienceLevel.SEVERE
```

## Configurazione del Sistema

### 1. Target RPO (Recovery Point Objective)

#### Configurazione Default per Tipo Asset
```python
self.default_rpo_config = {
    "vm": 24,                    # Virtual Machines - 24 ore
    "container": 12,             # Container - 12 ore  
    "physical_host": 48,         # Server fisici - 48 ore
    "proxmox_node": 24,         # Nodi Proxmox - 24 ore
    "acronis_backup_job": 24,   # Backup job Acronis - 24 ore
    "default": 24               # Valore di default
}
```

#### Configurazione Personalizzata
- **Asset RPO Targets**: RPO specifici per singoli asset
- **Backup Job RPO Targets**: RPO specifici per singoli backup jobs
- **Configurabile tramite interfaccia web** in `resilience_config.html`

### 2. Pesi delle Metriche

#### Configurazione Default
```python
self.default_weights = {
    "w_rpo": 0.6,      # Peso per RPO Compliance (60%)
    "w_success": 0.4   # Peso per Success Rate (40%)
}
```

#### Configurazione Personalizzata
- **Asset Weights**: Pesi specifici per singoli asset
- **Backup Job Weights**: Pesi specifici per singoli backup jobs
- **Vincolo**: La somma dei pesi deve essere sempre 1.0 (100%)

## Simulazione e Analisi

### 1. Periodo di Simulazione
- **Durata fissa**: 168 ore (1 settimana completa)
- **Granularità**: Calcolo ora per ora
- **Periodo**: Ultima settimana dei dati disponibili nel database

### 2. Processo di Simulazione per Singola Entità

```python
def simulate_entity_resilience(self, entity_id: str, entity_type: str, 
                             start_time: datetime, is_backup_job: bool = False):
    """
    Simula la resilienza di un'entità ora per ora per una settimana.
    """
    results = []
    
    # Ottieni configurazioni per questa entità
    target_rpo_hours = self.get_target_rpo_hours(entity_id, entity_type, is_backup_job)
    weights = self.get_weights(entity_id, is_backup_job)
    
    # Ottieni tutte le metriche di backup per l'intera finestra
    all_metrics = self.get_backup_metrics_for_entity(entity_id, start_time, end_time)
    
    # Inizializza contatori cumulativi
    total_backups_attempted = 0
    total_backups_successful = 0
    last_successful_backup = None
    
    # Simula ora per ora
    for hour in range(168):  # 168 ore = 1 settimana
        current_time = start_time + timedelta(hours=hour)
        
        # Controlla se ci sono nuovi backup in quest'ora
        for metric in all_metrics:
            if current_time <= metric_time < hour_end:
                total_backups_attempted += 1
                
                # Gestisce metriche di backup (0/1 o oggetti complessi)
                if backup_successful:
                    total_backups_successful += 1
                    last_successful_backup = metric_time
        
        # Calcola le metriche per quest'ora
        rpo_compliance = self.calculate_rpo_compliance(
            last_successful_backup, current_time, target_rpo_hours
        )
        success_rate = self.calculate_success_rate(
            total_backups_successful, total_backups_attempted
        )
        resilience_score = self.calculate_resilience_score(
            rpo_compliance, success_rate, weights
        )
        resilience_level = self.determine_resilience_level(resilience_score)
        
        # Salva risultato per quest'ora
        results.append({
            "timestamp": current_time.isoformat(),
            "hour": hour,
            "rpo_compliance": round(rpo_compliance, 4),
            "success_rate": round(success_rate, 4),
            "resilience_score": round(resilience_score, 4),
            "resilience_level": resilience_level.value,
            "total_backups_attempted": total_backups_attempted,
            "total_backups_successful": total_backups_successful,
            "actual_rpo_hours": actual_rpo_hours,
            "target_rpo_hours": target_rpo_hours
        })
    
    return results, config_used
```

### 3. Calcolo Score Aggregato

Il sistema calcola un punteggio aggregato considerando tutti gli asset e backup jobs:

```python
# Calcola il summary aggregato
total_entities = 0
aggregated_score_sum = 0.0

# Raccoglie i punteggi finali da individual assets (inclusi backup jobs)
for asset_id, asset_data in analysis_result["individual_assets"].items():
    if asset_data["simulation_data"]:
        final_score = asset_data["simulation_data"][-1]["resilience_score"]
        aggregated_score_sum += final_score
        total_entities += 1

# Calcola il punteggio aggregato (media semplice)
aggregated_score = aggregated_score_sum / total_entities if total_entities > 0 else 0.0
```

## Struttura Dati di Output

### File JSON Generato

```json
{
  "simulation_period": {
    "start": "2025-08-28T05:00:00",
    "end": "2025-09-04T04:00:00", 
    "total_hours": 168
  },
  "configuration": {
    "default_target_rpo_hours": {
      "vm": 24,
      "container": 12,
      "physical_host": 48,
      "proxmox_node": 24,
      "acronis_backup_job": 24,
      "default": 24
    },
    "default_weights": {
      "w_rpo": 0.6,
      "w_success": 0.4
    },
    "resilience_thresholds": {
      "excellent": 0.9,
      "good": 0.75,
      "acceptable": 0.6,
      "critical": 0.4
    },
    "custom_asset_rpo_targets": {},
    "custom_backup_job_rpo_targets": {},
    "custom_asset_weights": {},
    "custom_backup_job_weights": {},
    "has_custom_config": true
  },
  "individual_assets": {
    "backup-job-001": {
      "hostname": "Daily VM Backup",
      "asset_type": "acronis_backup_job",
      "job_name": "Daily VM Backup",
      "description": "Backup job Daily VM Backup",
      "destination": "Unknown",
      "backup_path": "Unknown", 
      "schedule": "daily_2am",
      "backup_type": "incremental",
      "simulation_data": [
        {
          "timestamp": "2025-08-28T05:00:00",
          "hour": 0,
          "rpo_compliance": 1.0,
          "success_rate": 1.0,
          "resilience_score": 1.0,
          "resilience_level": "EXCELLENT",
          "total_backups_attempted": 0,
          "total_backups_successful": 0,
          "actual_rpo_hours": 0.0,
          "target_rpo_hours": 24
        },
        // ... 167 ore successive
      ],
      "config_used": {
        "target_rpo_hours": 24,
        "weights": {"w_rpo": 0.6, "w_success": 0.4},
        "rpo_source": "custom",
        "weights_source": "custom"
      }
    }
    // ... altri asset
  },
  "summary": {
    "total_entities": 12,
    "aggregated_score": 0.85,
    "aggregated_status": "GOOD",
    "simulation_hours": 168
  }
}
```

## Frontend e Visualizzazione

### 1. Route Flask per Resilience

```python
@app.route('/resilience')
def resilience_index():
    """Pagina iniziale resilience con selezione file JSON o generazione"""

@app.route('/resilience/config')  
def resilience_config():
    """Pagina di configurazione per generare nuovo file JSON resilience"""

@app.route('/resilience/dashboard')
def resilience_dashboard():
    """Pagina dashboard resilience con i risultati"""

@app.route('/resilience/load_json/<filename>')
def resilience_load_json(filename):
    """Carica un file JSON esistente per la dashboard resilience"""

@app.route('/resilience/get_dashboard_data')
def resilience_get_dashboard_data():
    """API per ottenere i dati del dashboard resilience"""

@app.route('/resilience/start_analysis', methods=['POST'])
def resilience_start_analysis():
    """Avvia l'analisi resilience"""

@app.route('/resilience/analysis_progress')
def resilience_analysis_progress():
    """Verifica il progresso dell'analisi resilience"""
```

### 2. Interfaccia di Configurazione (`resilience_config.html`)

#### Step 1: Configurazione Pesi Globali
- **Controlli per pesi RPO Compliance e Success Rate**
- **Applicazione globale** con possibilità di personalizzazione individuale
- **Validazione**: somma pesi deve essere 1.0

#### Step 2: Target RPO per Backup Jobs
- **Configurazione RPO in ore** per ogni backup job
- **Valori suggeriti**: 24h (giornaliero), 12h (bi-giornaliero), 4h (critico)
- **Applicazione rapida** con personalizzazione individuale

#### Step 3: Riepilogo e Avvio
- **Visualizzazione configurazione finale**
- **Avvio analisi** con progress tracking

### 3. Dashboard di Visualizzazione (`resilience_dashboard.html`)

#### Componenti Principali

1. **Score Aggregato - Grafico a Torta**
   ```javascript
   // Grafico ECharts con score aggregato in tempo reale
   const option = {
       series: [{
           name: 'Resilience Score',
           type: 'pie',
           radius: ['40%', '70%'],
           data: [
               {
                   value: scorePercentage,
                   name: 'Resilience',
                   itemStyle: { color: getColorByLevel(score) }
               },
               {
                   value: remainingPercentage,
                   name: 'Mancante',
                   itemStyle: { color: '#ecf0f1', opacity: 0.3 }
               }
           ]
       }]
   };
   ```

2. **Asset Individuali**
   ```javascript
   // Card per ogni asset con metriche in tempo reale
   function createEntityCard(entityId, entityData, type) {
       return `
           <div class="entity-card card asset-card mb-3">
               <div class="card-body p-3">
                   <h6>${hostname}</h6>
                   <small>${entityId} • ${assetType}</small>
                   
                   <!-- Metriche in tempo reale -->
                   <div class="row">
                       <div class="col-6">
                           <small>Ultimo Backup:</small>
                           <span id="${entityId}-last-success">Mai</span>
                       </div>
                       <div class="col-6">
                           <small>Target RPO:</small>
                           <span id="${entityId}-target-rpo">--</span>
                       </div>
                   </div>
                   
                   <!-- Score e livello -->
                   <div class="text-end">
                       <span class="metric-badge" id="${entityId}-score">--</span>
                       <span class="metric-badge" id="${entityId}-level">--</span>
                   </div>
               </div>
           </div>
       `;
   }
   ```

3. **Controlli Timeline**
   ```javascript
   // Controlli per navigazione temporale
   - Play/Pause automatico
   - Slider per navigazione manuale  
   - Controllo velocità (1x, 2x, 3x)
   - Reset timeline
   ```

#### Aggiornamento Dati in Tempo Reale

```javascript
function updateDashboard() {
    // Calcola score aggregato per l'ora corrente
    let totalScore = 0;
    let totalEntities = 0;

    // Aggiorna asset individuali
    Object.entries(dashboardData.individual_assets || {}).forEach(([assetId, assetData]) => {
        const simulation = assetData.simulation_data;
        if (simulation && simulation[currentHour]) {
            const hourData = simulation[currentHour];
            const score = hourData.resilience_score || 0;
            const level = hourData.resilience_level || 'UNKNOWN';
            
            // Aggiorna UI per questo asset
            updateAssetUI(assetId, hourData);
            
            totalScore += score;
            totalEntities++;
        }
    });

    // Aggiorna score aggregato
    const aggregatedScore = totalEntities > 0 ? (totalScore / totalEntities) : 0;
    const aggregatedLevel = getResilienceLevel(aggregatedScore);
    
    // Aggiorna grafico e display
    updateTimelineChart(aggregatedScore);
    updateAggregatedDisplay(aggregatedScore, aggregatedLevel);
}
```

## Integrazione con Storage Layer

### 1. Connessione Database
```python
# Inizializza storage manager
storage_manager = StorageManager(
    connection_string=args.connection_string,
    database_name=args.database_name
)
storage_manager.connect()
```

### 2. Recupero Dati Backup
```python
def get_backup_metrics_for_entity(self, entity_id: str, 
                                start_time: datetime, end_time: datetime):
    """Ottiene le metriche di backup per un'entità in un intervallo di tempo."""
    try:
        metrics = self.storage_manager.get_metrics(
            asset_id=entity_id,
            metric_name="backup_status",
            start_time=start_time,
            end_time=end_time
        )
        
        # Ordina per timestamp
        metrics.sort(key=lambda x: x.get('timestamp', datetime.min))
        return metrics
    except Exception as e:
        self.logger.error(f"Errore nel recuperare metriche per {entity_id}: {e}")
        return []
```

### 3. Tipi di Asset Supportati
- **Backup Jobs Acronis**: `asset_type="acronis_backup_job"`
- **Virtual Machines**: `asset_type="vm"`
- **Container**: `asset_type="container"`
- **Physical Hosts**: `asset_type="physical_host"`
- **Proxmox Nodes**: `asset_type="proxmox_node"`

## Esecuzione e Deployment

### 1. Avvio Analyzer da Linea di Comando
```bash
python metrics_dashboard/utils/cumulative_resilience_analyzer.py \
    --connection-string "mongodb://localhost:27017" \
    --database-name "infrastructure_monitoring" \
    --config-file "config.json" \
    --output-file "resilience_analysis.json"
```

### 2. Avvio Dashboard Web
```bash
python metrics_dashboard/run.py
# Accesso: http://localhost:5001/resilience
```

### 3. Parametri di Configurazione
- **Connection String**: Stringa connessione MongoDB
- **Database Name**: Nome database metriche
- **Config File**: File JSON con configurazione personalizzata
- **Output File**: File JSON risultati (auto-generato se omesso)

## Considerazioni Tecniche

### 1. Performance
- **Simulazione 168 ore**: Calcolo efficiente ora per ora
- **Cache configurazioni**: Evita riletture ripetute
- **Batch processing**: Recupero metriche in blocco per periodo

### 2. Scalabilità
- **Asset illimitati**: Supporta qualsiasi numero di asset/backup jobs
- **Configurazione flessibile**: RPO e pesi personalizzabili per entità
- **Output JSON**: Formato standard per integrazione

### 3. Robustezza
- **Gestione errori**: Fallback per dati mancanti
- **Validazione input**: Controllo parametri configurazione
- **Logging dettagliato**: Tracciamento operazioni e errori

### 4. Estensibilità
- **Nuove metriche**: Facilmente aggiungibili al calcolo resilience
- **Nuovi asset types**: Supporto configurabile per nuovi tipi
- **Custom weights**: Sistema pesi completamente personalizzabile

## Conclusioni

Il sistema **Resilience Analytics** fornisce una soluzione completa per il monitoraggio della resilienza dei backup, combinando:

1. **Calcoli matematici precisi** per RPO Compliance e Success Rate
2. **Configurazione flessibile** di target RPO e pesi metriche  
3. **Simulazione temporale dettagliata** ora per ora
4. **Visualizzazione interattiva** con dashboard web responsive
5. **Integrazione robusta** con storage layer MongoDB
6. **Output standardizzato** in formato JSON per analisi successive

Il sistema permette di identificare rapidamente problematiche di backup, ottimizzare le strategie di recovery e mantenere alta la resilienza dell'infrastruttura IT attraverso metriche quantitative e visualizzazioni intuitive.