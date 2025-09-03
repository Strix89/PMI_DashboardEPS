# Polling History Implementation Summary

## Problema Risolto

Il seed database generava solo metriche di performance (CPU, memoria, I/O) ma mancava la **polling history** necessaria per calcolare la disponibilità (availability) dei servizi e delle macchine.

## Soluzione Implementata

### 1. Nuova Funzione: `generate_polling_history()`

Aggiunta al file `seed_database.py` per generare cronologia di polling realistica:

- **Frequenza**: 1 polling ogni minuto per ogni asset
- **Metriche generate**:
  - `availability_status`: 100.0 (UP), 50.0 (DEGRADED), 0.0 (DOWN)
  - `response_time_ms`: Tempo di risposta in millisecondi

### 2. Pattern di Disponibilità Realistici

#### Per i Servizi (`determine_service_availability()`):
- **Uptime target**: 99.5% (0.5% di downtime)
- **Downtime programmati**: Rispetta gli orari di manutenzione definiti
- **Degradazione graduale**: Servizi con pattern di memory leak
- **Dipendenze**: I servizi ereditano lo stato della macchina host

#### Per le Macchine (`determine_machine_availability()`):
- **Uptime target**: 99.9% (0.1% di downtime)
- **Pattern specifici**: Degradazione basata sui pattern di performance
- **Maggiore affidabilità**: Le macchine sono più stabili dei servizi

### 3. Tempi di Risposta Realistici (`generate_response_time()`)

Tempi di risposta differenziati per tipo di asset:
- **Servizi**: ~50ms (base)
- **Container**: ~30ms (più veloci)
- **VM**: ~100ms
- **Host fisici**: ~150ms
- **Nodi Proxmox**: ~200ms

Con variazioni basate su:
- **Stato di disponibilità**: Timeout (30s) se DOWN, lento se DEGRADED
- **Orario**: Più lento durante ore lavorative e operazioni notturne
- **Picchi casuali**: 5% di probabilità di spike di rete

### 4. Nuova Opzione CLI

Aggiunta l'opzione `--polling-only` per generare solo la polling history:

```bash
python seed_database.py --polling-only --days 7 --batch-size 1000
```

### 5. Integrazione nel Flusso Principale

La polling history viene generata automaticamente nel flusso completo:

1. **Creazione asset** (macchine e servizi)
2. **Generazione metriche** (CPU, memoria, I/O)
3. **🆕 Generazione polling history** (availability + response_time)
4. **Simulazione stati servizi**

## Risultati dei Test

### Test con `--polling-only --days 1`

- **77.760 record** generati in **4 secondi**
- **Velocità**: ~18.758 record/secondo
- **32 asset** × **2 metriche** × **1440 minuti** = dati completi

### Distribuzione Dati

- **38.880 metriche** `availability_status`
- **38.880 metriche** `response_time_ms`
- **Valori realistici**: UP (100.0), tempi di risposta variabili

## Benefici per il Dashboard

### 1. Calcoli di Availability Accurati

Ora è possibile calcolare:
- **Uptime percentuale** per periodo
- **MTTR** (Mean Time To Recovery)
- **MTBF** (Mean Time Between Failures)
- **SLA compliance**

### 2. Analisi Trend di Disponibilità

- **Grafici temporali** di availability
- **Correlazione** tra performance e disponibilità
- **Identificazione pattern** di downtime

### 3. Alerting Intelligente

- **Soglie dinamiche** basate su cronologia
- **Predizione guasti** basata su trend
- **Escalation automatica** per servizi critici

## Struttura Dati nel Database

### Esempio Availability Status
```json
{
  "timestamp": "2025-09-02T10:30:00Z",
  "meta": {
    "asset_id": "svc-mysql-101",
    "metric_name": "availability_status"
  },
  "value": 100.0  // UP
}
```

### Esempio Response Time
```json
{
  "timestamp": "2025-09-02T10:30:00Z",
  "meta": {
    "asset_id": "svc-mysql-101", 
    "metric_name": "response_time_ms"
  },
  "value": 45.2  // millisecondi
}
```

## Documentazione Aggiornata

- **SEED_DATABASE_DOCUMENTATION.md**: Aggiunta sezione polling history
- **Esempi di utilizzo**: Nuovi scenari con `--polling-only`
- **Calcoli volume dati**: Aggiornati per includere polling history

## Compatibilità

- **Backward compatible**: Non modifica dati esistenti
- **Opzionale**: Può essere disabilitata con opzioni CLI
- **Incrementale**: Si integra con il sistema di checkpoint esistente

## Prossimi Passi

1. **Dashboard Integration**: Utilizzare i dati di polling per grafici availability
2. **Alerting Rules**: Configurare soglie basate su availability_status
3. **Reporting**: Creare report SLA automatici
4. **Ottimizzazioni**: Indicizzazione specifica per query di availability

---

**Implementazione completata con successo!** ✅

La polling history è ora disponibile e pronta per essere utilizzata dal dashboard PMI per calcoli di disponibilità accurati e realistici.