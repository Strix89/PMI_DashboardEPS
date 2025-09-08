# AnomalySNMP Dashboard - Documentazione Completa

## 📋 Indice
1. [Panoramica Sistema](#panoramica-sistema)
2. [Architettura](#architettura)
3. [Algoritmo di Rilevamento](#algoritmo-di-rilevamento)
4. [Interfaccia Utente](#interfaccia-utente)
5. [API Backend](#api-backend)
6. [Configurazione](#configurazione)
7. [Utilizzo](#utilizzo)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Panoramica Sistema

**AnomalySNMP** è un sistema avanzato di rilevamento anomalie per dati di rete SNMP che combina **Isolation Forest** con **Statistical Process Control (SPC)** per identificare comportamenti anomali in tempo reale attraverso un **S-Score ibrido** innovativo.

### Caratteristiche Principali
- 🤖 **Machine Learning**: Isolation Forest per detection unsupervised
- 📊 **S-Score Ibrido**: Formula matematica interpretabile [0,1]
- ⚡ **Tempo Reale**: Simulazione con controlli velocità 1x-10x
- 🎨 **Visualizzazione**: Gauge, grafici temporali, zone colore
- 📈 **Accuratezza**: Calcolo predizioni corrette in tempo reale
- 🔄 **SMOTE**: Bilanciamento dataset con oversampling

---

## 🏗️ Architettura

### Struttura File
```
metrics_dashboard/
├── anomaly_snmp/                    # Modulo principale
│   ├── routes.py                    # Controller Flask
│   ├── exceptions.py                # Gestione errori
│   ├── logging_config.py            # Sistema logging
│   ├── monitoring.py                # Monitoraggio performance
│   └── utils/
│       ├── ml_engine.py             # Motore Isolation Forest
│       └── data_processor.py        # Preprocessing dati
├── templates/
│   ├── anomaly_configure.html       # Pagina configurazione
│   └── anomaly_dashboard.html       # Dashboard principale
├── static/js/
│   ├── anomaly_dashboard.js         # Logica frontend
│   ├── anomaly_charts.js            # Gestione grafici
│   └── anomaly_gauge.js             # Gauge circolare
├── Datasets/
│   └── snmp_mib_dataset.csv         # Dataset SNMP-MIB
└── README.md                        # Questa documentazione
```

### Flusso Dati
```
Dataset → Preprocessing → Training IF → Baseline → S-Score → Simulazione → Dashboard
```

---

## 🤖 Algoritmo di Rilevamento

### 1. Dataset SNMP-MIB
```
File: Datasets/snmp_mib_dataset.csv
- 4,998 record totali
- 600 record Normal (12%)
- 4,398 record Anomaly (88%)
- 8 feature SNMP per record
```

### 2. Preprocessing
```python
# Normalizzazione feature
X_normalized = (X - μ) / σ  # Media=0, Std=1

# Split Train/Test
train_split = 0.7  # Configurabile
normal_train = 420  # 70% dei normali
normal_test = 180   # 30% dei normali
anomaly_test = 4,398  # Tutte le anomalie
```

### 3. Bilanciamento SMOTE
```python
# Calcolo target per contamination
contamination = 0.05  # 5% anomalie attese
target_normal = anomaly_test * (1-contamination) / contamination
# target_normal = 4,398 * 0.95 / 0.05 = 83,562

# SMOTE genera record sintetici
smote_needed = target_normal - 600 = 82,962
```

### 4. Training Isolation Forest
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

### 5. Calcolo Baseline Statistica
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

### 6. Formula S-Score
```
S(s_new) = {
    1.0                                           se s_new ≤ μ_normal
    max(0, 1 - (s_new - μ_normal)/(3·σ_normal))  se s_new > μ_normal
}
```

**Esempi Numerici** (μ_normal=0.7, σ_normal=0.1):
```
s_new = 0.6  → S-Score = 1.0   (≤ μ_normal)
s_new = 0.7  → S-Score = 1.0   (= μ_normal)
s_new = 0.8  → S-Score = 0.67  (decadimento lineare)
s_new = 0.9  → S-Score = 0.33  (decadimento lineare)
s_new = 1.0  → S-Score = 0.0   (anomalia massima)
```

### 7. Classificazione Anomalie
```javascript
// REGOLA: Solo S-Score esattamente = 0.0 è anomalia
const ANOMALY_THRESHOLD = 0.0;
const predictedLabel = (s_score === 0.0) ? 'Anomaly' : 'Normal';
```

---

## 🎨 Interfaccia Utente

### Dashboard Principale (`anomaly_dashboard.html`)

#### 1. Anomaly Score Card
- **Gauge Circolare**: Visualizza S-Score 0-100%
- **Colore Dinamico**: Verde/Giallo/Arancione/Rosso
- **Percentuale**: S-Score in formato percentuale

#### 2. Control Panel
- **Play/Pause**: Controllo simulazione
- **Velocità**: Slider 1x-10x + bottoni rapidi
- **Timeline**: Informazioni punto corrente
- **Reset**: Azzera simulazione

#### 3. Grafico Temporale
- **Andamento S-Score**: Timeline con colori zone
- **50 punti**: Mantiene ultimi 50 per performance
- **Legenda**: Zone colore con soglie

#### 4. Resoconto Dataset
- **Dataset Originale**: 600 Normal, 4,398 Anomaly
- **Post-SMOTE**: Dati bilanciati
- **Training Set**: Solo normali
- **Test Set**: Normali + Anomalie

#### 5. Statistiche Simulazione
- **Contatori**: Punti normali/anomalie processati
- **Configurazione**: Contamination, Train Split
- **Punto Corrente**: Etichetta reale/predetta
- **Accuratezza**: % predizioni corrette

### Zone Colore S-Score
```javascript
const SCORE_ZONES = {
    excellent: [0.8, 1.0],  // Verde - Normale
    good: [0.6, 0.8],       // Giallo - Buono
    warning: [0.4, 0.6],    // Arancione - Attenzione  
    critical: [0.0, 0.4]    // Rosso - Critico/Anomalia
};
```

---

## 🔧 API Backend

### Route Principali

#### 1. Configurazione
```python
@anomaly_snmp_bp.route('/configure')
def configure():
    """Pagina configurazione modello"""
    # Mostra form per contamination e train_split
```

#### 2. Training
```python
@anomaly_snmp_bp.route('/train', methods=['POST'])
def train_model():
    """Training del modello Isolation Forest"""
    # 1. Preprocessing dataset
    # 2. SMOTE oversampling
    # 3. Training Isolation Forest
    # 4. Calcolo baseline
    # 5. Salvataggio in sessione
```

#### 3. Dashboard
```python
@anomaly_snmp_bp.route('/dashboard')
def dashboard():
    """Dashboard simulazione"""
    # Verifica configurazione e artifacts
```

#### 4. API Simulazione
```python
@anomaly_snmp_bp.route('/api/get_next_point/<int:offset>')
def get_next_point(offset):
    """Ottiene prossimo punto dati"""
    # Genera punto on-demand con seed
    # Calcola S-Score
    # Restituisce dati JSON
```

#### 5. Controlli Simulazione
```python
@anomaly_snmp_bp.route('/api/simulation_control', methods=['POST'])
def simulation_control():
    """Controllo play/pause/velocità"""
    # Gestisce azioni simulazione
```

### Gestione Sessione
```python
session['anomaly_snmp'] = {
    'config': {
        'contamination': 0.05,
        'train_split': 0.7,
        'dataset_name': 'SNMP-MIB Dataset'
    },
    'dataset_stats': {
        'normal_original': 600,
        'anomaly_original': 4398,
        'test_set_total': 29686
    },
    'model_artifacts': {
        'baseline': {...},
        'test_set_seed': 1234
    }
}
```

---

## ⚙️ Configurazione

### Parametri Principali

#### 1. Contamination (0.01-0.1)
- **Default**: 0.05 (5%)
- **Significato**: Percentuale anomalie attese nel dataset
- **Impatto**: Influenza sensibilità del modello

#### 2. Train Split (0.5-0.9)
- **Default**: 0.7 (70%)
- **Significato**: Percentuale dati per training
- **Impatto**: Bilanciamento training/test

#### 3. Soglia Anomalia
- **Valore**: S-Score = 0.0
- **Significato**: Solo score esattamente zero è anomalia
- **Logica**: Massima precisione, minima sensibilità

### Configurazione Avanzata
```python
# ml_engine.py
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

---

## 🚀 Utilizzo

### 1. Configurazione Iniziale
1. Accedi a `/anomaly_snmp/configure`
2. Imposta **Contamination** (es: 0.05)
3. Imposta **Train Split** (es: 0.7)
4. Clicca **"Avvia Training"**

### 2. Training del Modello
- Il sistema processa automaticamente:
  - Caricamento dataset SNMP-MIB
  - Preprocessing e normalizzazione
  - Oversampling SMOTE
  - Training Isolation Forest
  - Calcolo baseline statistica

### 3. Dashboard Simulazione
1. Accedi automaticamente alla dashboard
2. **Play**: Avvia simulazione tempo reale
3. **Velocità**: Regola 1x-10x con slider
4. **Osserva**: S-Score, colori, accuratezza
5. **Reset**: Riavvia simulazione

### 4. Interpretazione Risultati

#### S-Score
- **1.0**: Perfettamente normale (Verde)
- **0.8-0.6**: Normale con attenzione (Giallo)
- **0.6-0.4**: Comportamento sospetto (Arancione)
- **0.4-0.0**: Critico (Rosso)
- **0.0**: 🚨 **ANOMALIA DICHIARATA**

#### Accuratezza
- **Etichetta Reale**: Dal dataset originale
- **Etichetta Predetta**: Solo se S-Score = 0.0
- **Accuratezza**: % predizioni corrette

---

## 🔍 Troubleshooting

### Problemi Comuni

#### 1. Errore "Sessione non trovata"
```
Causa: Sessione Flask scaduta
Soluzione: Rifare configurazione e training
```

#### 2. Simulazione non avanza
```
Causa: Endpoint API non risponde
Verifica: Console browser per errori JavaScript
Soluzione: Ricaricare pagina
```

#### 3. Grafico non si aggiorna
```
Causa: Chart.js non inizializzato
Verifica: Librerie caricate correttamente
Soluzione: Hard refresh (Ctrl+F5)
```

#### 4. Accuratezza sempre 100%
```
Causa: Soglia troppo restrittiva (S-Score = 0.0)
Spiegazione: È normale, poche anomalie hanno score esatto 0.0
```

### Debug JavaScript
```javascript
// Console browser
console.log('Simulation running:', simulationRunning);
console.log('Current offset:', currentOffset);
console.log('Accuracy:', correctPredictions, '/', totalPredictions);
```

### Debug Python
```python
# routes.py
logger.info(f"S-Score calcolato: {s_score}")
logger.info(f"Baseline: {baseline}")
```

---

## 📊 Metriche Performance

### Timing Simulazione
- **1x**: 1 punto/secondo
- **2x**: 2 punti/secondo  
- **5x**: 5 punti/secondo
- **10x**: 10 punti/secondo

### Memoria
- **Dataset**: ~5MB (4,998 record)
- **Modello**: ~50MB (Isolation Forest)
- **Sessione**: ~1MB (baseline + metadata)

### Scalabilità
- **Max punti grafico**: 50 (performance)
- **Max dati temporali**: 100 (memoria)
- **Concurrent users**: Limitato da sessioni Flask

---

## 🔬 Validazione Scientifica

### Formula S-Score
- **Base teorica**: Statistical Process Control
- **Range**: [0,1] sempre garantito
- **Interpretabilità**: Lineare e intuitiva
- **Robustezza**: Normalizzazione Min-Max

### Isolation Forest
- **Algoritmo**: Unsupervised anomaly detection
- **Principio**: Path length in alberi casuali
- **Vantaggi**: Efficiente, scalabile
- **Limitazioni**: Sensibile a parametri

### Validazione Risultati
- **Ground Truth**: Etichette dataset originale
- **Metrica**: Accuratezza predizioni
- **Baseline**: Confronto con soglie alternative

---

## 📝 Note Sviluppo

### Versioning
- **v1.0**: Implementazione base
- **v1.1**: Correzioni bug JavaScript
- **v1.2**: Ottimizzazioni performance
- **v2.0**: Sistema attuale completo

### TODO Future
- [ ] Soglie anomalia configurabili
- [ ] Export risultati CSV/JSON
- [ ] Modelli ML alternativi
- [ ] Real-time SNMP data ingestion
- [ ] Alerting system
- [ ] Multi-tenant support

### Contributi
Per contribuire al progetto:
1. Fork repository
2. Crea feature branch
3. Implementa modifiche
4. Test completi
5. Pull request con documentazione

---

## 📞 Supporto

Per supporto tecnico o domande:
- **Documentazione**: Questo README
- **Logs**: Console browser + logs Python
- **Debug**: Modalità sviluppo Flask
- **Issues**: Repository GitHub

---

**© 2025 AnomalySNMP Dashboard - Sistema Avanzato di Rilevamento Anomalie SNMP**