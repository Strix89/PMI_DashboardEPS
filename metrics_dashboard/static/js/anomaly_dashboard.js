/**
 * AnomalySNMP Dashboard JavaScript
 * Gestisce la simulazione tempo reale e le visualizzazioni grafiche
 * Integrato con anomaly_charts.js per color coding avanzato e gestione grafici
 * Task 5.2: Implementazione visualizzazioni grafiche completata
 */

// Variabili globali per la simulazione
let simulationRunning = false;
let currentOffset = 0;
let simulationInterval = null;

// Variabili per i grafici
let customGauge = null;
let temporalChart = null;
let temporalData = [];

// Contatori statistiche
let normalCount = 0;
let anomalyCount = 0;

// Contatori statistiche e accuratezza
let totalPredictions = 0;
let correctPredictions = 0;

// Classificazione anomalia: SOLO S-Score esattamente = 0.0 è anomalia
const ANOMALY_THRESHOLD = 0.0;

// Configurazione colori per zone S-Score
const SCORE_ZONE_COLORS = {
    excellent: { color: '#27ae60', threshold: 0.8, label: 'Normale (0.8-1.0)' },      // Verde
    good: { color: '#f39c12', threshold: 0.6, label: 'Buono (0.6-0.8)' },            // Giallo
    warning: { color: '#ff6b35', threshold: 0.4, label: 'Attenzione (0.4-0.6)' },    // Arancione
    critical: { color: '#e74c3c', threshold: 0.0, label: 'Critico (0.0-0.4)' }       // Rosso
};

// Alias per compatibilitÃ 
const SCORE_COLORS = SCORE_ZONE_COLORS;

// Funzione per ottenere il colore basato su S-Score
function getScoreZoneColor(score) {
    if (score >= 0.8) return SCORE_ZONE_COLORS.excellent.color;
    if (score >= 0.6) return SCORE_ZONE_COLORS.good.color;
    if (score >= 0.4) return SCORE_ZONE_COLORS.warning.color;
    return SCORE_ZONE_COLORS.critical.color;
}

/**
 * Inizializzazione della dashboard con controllo stato simulazione
 * Requirements: 6.1, 6.4, 8.4
 */
document.addEventListener('DOMContentLoaded', function () {
    console.log('ðŸš€ Inizializzazione AnomalySNMP Dashboard');

    // Registra plugin Chart.js
    if (typeof Chart !== 'undefined' && typeof annotationPlugin !== 'undefined') {
        Chart.register(annotationPlugin);
    }

    loadTheme();
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);

    initializeCharts();
    loadConfiguration();

    // Carica stato simulazione esistente
    loadSimulationStatus();

    // Controllo periodico dello stato (ogni 30 secondi)
    setInterval(checkSimulationStatus, 30000);

    console.log('âœ… Dashboard inizializzata con successo');
});

/**
 * Carica lo stato corrente della simulazione dal server
 */
async function loadSimulationStatus() {
    try {
        const response = await fetch('/anomaly_snmp/api/simulation_status');
        const result = await response.json();

        if (result.success) {
            const status = result.status;

            // Ripristina stato locale
            currentOffset = status.current_offset;

            // Aggiorna UI
            document.getElementById('current-offset').textContent = currentOffset;

            // Aggiorna statistiche se disponibili
            if (status.statistics) {
                normalCount = status.statistics.normal_count || 0;
                anomalyCount = status.statistics.anomaly_count || 0;
                updateStatistics();
            }

            // Aggiorna timeline info semplificato
            if (currentOffset > 0) {
                document.getElementById('timeline-info').textContent =
                    `Simulazione: Punto ${currentOffset}`;
            }

            console.log('ðŸ“Š Stato simulazione caricato:', status);

        } else {
            console.log('â„¹ï¸ Nessuno stato simulazione precedente trovato');
        }

    } catch (error) {
        console.warn('âš ï¸ Errore nel caricamento stato simulazione:', error);
    }
}

/**
 * Controllo periodico dello stato della simulazione
 */
async function checkSimulationStatus() {
    if (!simulationRunning) return; // Non controllare se non in esecuzione

    try {
        const response = await fetch('/anomaly_snmp/api/simulation_status');
        const result = await response.json();

        if (result.success) {
            const status = result.status;

            // Verifica sincronizzazione
            if (status.current_offset !== currentOffset) {
                console.log(`ðŸ”„ Sincronizzazione offset: locale=${currentOffset}, server=${status.current_offset}`);
                currentOffset = status.current_offset;
                document.getElementById('current-offset').textContent = currentOffset;
            }

            // Verifica se la simulazione Ã¨ ancora attiva lato server
            if (!status.is_running && simulationRunning) {
                console.log('â¸ï¸ Simulazione fermata lato server, sincronizzazione...');
                pauseSimulation();
            }

        }

    } catch (error) {
        console.warn('âš ï¸ Errore nel controllo stato simulazione:', error);
    }
}

/**
 * Gestione del tema
 */
function toggleTheme() {
    const body = document.body;
    const currentTheme = body.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    body.setAttribute('data-theme', newTheme);

    const icon = document.getElementById('theme-icon');
    icon.className = newTheme === 'light' ? 'fas fa-moon' : 'fas fa-sun';

    localStorage.setItem('theme', newTheme);

    // Aggiorna i grafici per il nuovo tema
    updateChartsTheme();

    console.log(`ðŸŽ¨ Tema cambiato a: ${newTheme}`);
}

function loadTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.body.setAttribute('data-theme', savedTheme);
    document.getElementById('theme-icon').className =
        savedTheme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
}

/**
 * Aggiornamento ora corrente
 */
function updateCurrentTime() {
    const now = new Date();
    document.getElementById('current-time').textContent = now.toLocaleTimeString();
}

/**
 * Inizializzazione dei grafici
 */
function initializeCharts() {
    console.log('ðŸ“Š Inizializzazione grafici...');
    initializeGaugeChart();
    initializeTemporalChart();
    console.log('âœ… Grafici inizializzati');
}

/**
 * Inizializza il gauge chart personalizzato per visualizzare l'S-Score
 */
function initializeGaugeChart() {
    const isDark = document.body.getAttribute('data-theme') === 'dark';

    customGauge = new AnomalyGauge('anomaly-gauge', {
        size: 300,
        thickness: 25,
        label: '',
        textColor: isDark ? '#f0f0f0' : '#2c3e50',
        backgroundColor: isDark ? '#404040' : '#ecf0f1',
        colorZones: [
            { min: 0.0, max: 0.4, color: '#e74c3c', label: 'Critico' },
            { min: 0.4, max: 0.6, color: '#ff6b35', label: 'Attenzione' },
            { min: 0.6, max: 0.8, color: '#f39c12', label: 'Buono' },
            { min: 0.8, max: 1.0, color: '#27ae60', label: 'Eccellente' }
        ]
    });

    console.log('ðŸŽ¯ Custom gauge inizializzato');
}

/**
 * Inizializza il grafico temporale per l'andamento S-Score
 */
function initializeTemporalChart() {
    const ctx = document.getElementById('temporal-chart').getContext('2d');

    temporalChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'S-Score',
                data: [],
                borderColor: '#ff8c00',
                backgroundColor: 'rgba(255, 140, 0, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: [],
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: '#ff8c00',
                    borderWidth: 1,
                    callbacks: {
                        title: function (context) {
                            const index = context[0].dataIndex;
                            if (temporalData[index]) {
                                const timestamp = new Date(temporalData[index].timestamp);
                                return `Punto ${temporalData[index].offset} - ${timestamp.toLocaleTimeString()}`;
                            }
                            return 'Punto dati';
                        },
                        label: function (context) {
                            const index = context.dataIndex;
                            const score = context.parsed.y;
                            const label = temporalData[index] ? temporalData[index].label : 'Unknown';

                            return [
                                `S-Score: ${(score * 100).toFixed(1)}%`,
                                `Etichetta reale: ${label}`,
                                `Livello: ${getScoreLevel(score)}`
                            ];
                        }
                    }
                },
                annotation: {
                    annotations: {
                        excellentLine: {
                            type: 'line',
                            yMin: 0.8,
                            yMax: 0.8,
                            borderColor: SCORE_COLORS.excellent.color,
                            borderWidth: 2,
                            borderDash: [5, 5],
                            label: {
                                content: 'Eccellente (80%)',
                                enabled: true,
                                position: 'end'
                            }
                        },
                        goodLine: {
                            type: 'line',
                            yMin: 0.6,
                            yMax: 0.6,
                            borderColor: SCORE_COLORS.good.color,
                            borderWidth: 2,
                            borderDash: [5, 5],
                            label: {
                                content: 'Buono (60%)',
                                enabled: true,
                                position: 'end'
                            }
                        },
                        warningLine: {
                            type: 'line',
                            yMin: 0.4,
                            yMax: 0.4,
                            borderColor: SCORE_COLORS.warning.color,
                            borderWidth: 2,
                            borderDash: [5, 5],
                            label: {
                                content: 'Attenzione (40%)',
                                enabled: true,
                                position: 'end'
                            }
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 1.0,
                    ticks: {
                        callback: function (value) {
                            return (value * 100).toFixed(0) + '%';
                        }
                    },
                    title: {
                        display: true,
                        text: 'S-Score (%)',
                        font: {
                            weight: 'bold'
                        }
                    },
                    grid: {
                        color: function (context) {
                            // Highlight threshold lines
                            if (context.tick.value === 0.8) return SCORE_COLORS.excellent.color + '40';
                            if (context.tick.value === 0.6) return SCORE_COLORS.good.color + '40';
                            if (context.tick.value === 0.4) return SCORE_COLORS.warning.color + '40';
                            return '#e0e0e0';
                        }
                    }
                },
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Offset Punti Dati',
                        font: {
                            weight: 'bold'
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            animation: {
                duration: 300
            }
        }
    });

    console.log('ðŸ“ˆ Grafico temporale inizializzato con threshold lines');
}

/**
 * Caricamento configurazione dal server
 */
async function loadConfiguration() {
    try {
        console.log('âš™ï¸ Caricamento configurazione...');
        const response = await fetch('/anomaly_snmp/api/get_config');
        const data = await response.json();

        if (data.success) {
            const config = data.config;
            document.getElementById('config-contamination').textContent =
                (config.contamination * 100).toFixed(1) + '%';
            document.getElementById('config-train-split').textContent =
                (config.train_split * 100).toFixed(0) + '%';

            // NUOVO: Aggiorna resoconto dataset
            updateDatasetReportCorrect(config);

            document.getElementById('timeline-info').textContent =
                `Configurazione: Contamination ${(config.contamination * 100).toFixed(1)}%, Train Split ${(config.train_split * 100).toFixed(0)}%`;

            console.log('âœ… Configurazione caricata:', config);
        } else {
            console.error('âŒ Errore nel caricamento configurazione:', data.error);
        }
    } catch (error) {
        console.error('âŒ Errore di connessione configurazione:', error);
    }
}

/**
 * NUOVO: Aggiorna il resoconto del dataset basato sulla configurazione
 */
function updateDatasetReport(config) {
    const trainSplit = config.train_split || 0.7;
    const contamination = config.contamination || 0.05;

    // Calcoli basati sui dati reali
    const normalOriginal = 600;
    const anomalyOriginal = 4398;
    const totalOriginal = normalOriginal + anomalyOriginal;

    // Training set (solo normali)
    const normalTraining = Math.floor(normalOriginal * trainSplit);
    const smoteTarget = Math.floor(normalTraining / (1 - contamination));
    const smoteGenerated = smoteTarget - normalTraining;

    // Test set
    const normalTest = normalOriginal - normalTraining;
    const anomalyTest = anomalyOriginal; // Usa tutte le anomalie reali
    const totalTest = normalTest + anomalyTest;

    // Dataset Post-SMOTE
    const totalSmote = smoteTarget + anomalyOriginal;

    // Aggiorna UI - Dataset Originale
    document.getElementById('dataset-normal-original').textContent = normalOriginal.toLocaleString();
    document.getElementById('dataset-anomaly-original').textContent = anomalyOriginal.toLocaleString();
    document.getElementById('dataset-total-original').textContent = totalOriginal.toLocaleString();

    // Dataset Post-SMOTE
    document.getElementById('dataset-normal-smote').textContent = smoteTarget.toLocaleString();
    document.getElementById('dataset-anomaly-smote').textContent = anomalyOriginal.toLocaleString();
    document.getElementById('dataset-total-smote').textContent = totalSmote.toLocaleString();

    // Training Set (solo normali)
    document.getElementById('training-normal-count').textContent = normalTraining.toLocaleString();
    // training-anomaly-count rimosso dal template
    document.getElementById('training-total-count').textContent = normalTraining.toLocaleString();

    // Test Set
    document.getElementById('test-normal-count').textContent = normalTest.toLocaleString();
    document.getElementById('test-anomaly-count').textContent = anomalyTest.toLocaleString();
    document.getElementById('test-total-count').textContent = totalTest.toLocaleString();

    // Rilevamento Anomalie
    // detected-anomalies rimosso dal template
    // theoretical-anomalies rimosso dal template
    // detection-accuracy rimosso dal template

    // Progress bar rimossa dal template

    console.log('ðŸ“Š Resoconto dataset aggiornato:', {
        original: { normal: normalOriginal, anomaly: anomalyOriginal, total: totalOriginal },
        postSmote: { normal: smoteTarget, anomaly: anomalyOriginal, total: totalSmote },
        training: { normal: normalTraining, anomaly: 0, total: normalTraining },
        test: { normal: normalTest, anomaly: anomalyTest, total: totalTest }
    });
}

/**
 * Controlli della simulazione
 */
function toggleSimulation() {
    if (simulationRunning) {
        pauseSimulation();
    } else {
        startSimulation();
    }
}

/**
 * Avvia simulazione con sincronizzazione server
 * Requirements: 6.4, 6.5
 */
async function startSimulation() {
    simulationRunning = true;
    document.getElementById('simulation-btn').innerHTML = '<i class="fas fa-pause"></i> <span>Pausa</span>';
    document.getElementById('real-time-indicator').style.animation = 'pulse 1s infinite';

    // Intervallo fisso: 1 secondo per punto
    simulationInterval = setInterval(fetchNextDataPoint, 1000);

    // Sincronizza con server
    await controlSimulation('play');

    console.log(`â–¶ï¸ Simulazione avviata (velocitÃ : ${1}x)`);
}

/**
 * Pausa simulazione con sincronizzazione server
 * Requirements: 6.4, 6.5
 */
async function pauseSimulation() {
    simulationRunning = false;
    document.getElementById('simulation-btn').innerHTML = '<i class="fas fa-play"></i> <span>Play</span>';
    document.getElementById('real-time-indicator').style.animation = 'none';

    if (simulationInterval) {
        clearInterval(simulationInterval);
        simulationInterval = null;
    }

    // Sincronizza con server
    await controlSimulation('pause');

    console.log('â¸ï¸ Simulazione in pausa');
}

/**
 * Reset simulazione con chiamata API
 * Requirements: 6.1, 6.4
 */
async function resetSimulation() {
    console.log('ðŸ”„ Reset simulazione...');

    pauseSimulation();

    try {
        // Chiamata API per reset lato server
        const response = await fetch('/anomaly_snmp/api/reset_simulation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (result.success) {
            // Reset stato locale
            currentOffset = 0;
            temporalData = [];
            normalCount = 0;
            anomalyCount = 0;
            totalPredictions = 0;
            correctPredictions = 0;

            // Reset grafici
            temporalChart.data.labels = [];
            temporalChart.data.datasets[0].data = [];
            temporalChart.data.datasets[0].pointBackgroundColor = [];
            temporalChart.update();

            updateGauge(0);
            updateStatistics();

            // Reset display
            document.getElementById('current-timestamp').textContent = '--';
            document.getElementById('current-offset').textContent = '0';
            document.getElementById('current-label').textContent = '--';
            document.getElementById('current-score').textContent = '--';
            document.getElementById('model-accuracy').textContent = '--';

            // Reset timeline info
            document.getElementById('timeline-info').textContent = 'Simulazione: Pronta per iniziare';

            console.log('âœ… Simulazione resettata con successo');

        } else {
            console.error('âŒ Errore nel reset:', result.error);
            showErrorMessage('Errore nel reset della simulazione');
        }

    } catch (error) {
        console.error('âŒ Errore di connessione durante reset:', error);
        showErrorMessage('Errore di connessione durante il reset');
    }
}

/**
 * Controlli velocitÃ  simulazione con sincronizzazione server
 * Requirements: 6.4, 6.5
 */
async function changeSpeed(speed) {
    const oldSpeed = simulationSpeed;
    simulationSpeed = parseInt(speed);

    // Aggiorna UI immediatamente per responsiveness
    document.getElementById('speed-slider').value = speed;
    document.getElementById('speed-display').textContent = speed + 'x';

    // Aggiorna intervallo locale
    if (simulationRunning) {
        clearInterval(simulationInterval);
        simulationInterval = setInterval(fetchNextDataPoint, Math.max(100, 1000 / simulationSpeed));
    }

    try {
        // Sincronizza con server
        const response = await fetch('/anomaly_snmp/api/simulation_control', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'set_speed',
                speed: speed
            })
        });

        const result = await response.json();

        if (result.success) {
            console.log(`âš¡ VelocitÃ  cambiata a: ${speed}x (sincronizzata con server)`);
        } else {
            console.warn('âš ï¸ Errore sincronizzazione velocitÃ :', result.error);
            // Mantieni il cambio locale anche se la sincronizzazione fallisce
        }

    } catch (error) {
        console.warn('âš ï¸ Errore di connessione per sincronizzazione velocitÃ :', error);
        // Mantieni il cambio locale
    }
}

function updateSpeed(speed) {
    changeSpeed(parseInt(speed));
}

/**
 * Controllo avanzato simulazione con API
 */
async function controlSimulation(action, params = {}) {
    try {
        const response = await fetch('/anomaly_snmp/api/simulation_control', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: action,
                ...params
            })
        });

        const result = await response.json();

        if (result.success) {
            console.log(`âœ… Azione ${action} eseguita con successo`);

            // Aggiorna stato locale basato sulla risposta
            if (result.simulation_state) {
                updateSimulationState(result.simulation_state);
            }

            return result;
        } else {
            console.error(`âŒ Errore nell'azione ${action}:`, result.error);
            return null;
        }

    } catch (error) {
        console.error(`âŒ Errore di connessione per azione ${action}:`, error);
        return null;
    }
}

/**
 * Fetch del prossimo punto dati con gestione avanzata dello stato
 * Requirements: 6.4, 6.5, 8.4
 */
async function fetchNextDataPoint() {
    try {
        const response = await fetch(`/anomaly_snmp/api/get_next_point/${currentOffset}`);
        const result = await response.json();

        if (result.success) {
            const data = result.data;
            // CORREZIONE: Aggiorna currentOffset PRIMA di usarlo
            currentOffset = result.next_offset || (currentOffset + 1);

            // Aggiorna visualizzazioni
            updateDashboard(data);
            updateTemporalChart(data);
            updateStatistics();
            updateSimulationProgress(data);

            // Gestione fine dataset
            if (!result.has_more_data) {
                console.log('ðŸ“Š Fine del dataset raggiunta');
                pauseSimulation();
                showEndOfDatasetMessage();
                return;
            }

            // Aggiorna stato simulazione locale
            if (result.simulation_state) {
                updateSimulationState(result.simulation_state);
            }

            console.log(`ðŸ“Š Punto dati ${data.offset}: S-Score=${(data.s_score * 100).toFixed(1)}%, Label=${data.real_label}, Fase=${data.metadata?.phase || 'unknown'}`);

        } else {
            console.error('âŒ Errore nel fetch dati:', result.error);
            pauseSimulation();
            showErrorMessage(result.error);
        }

    } catch (error) {
        console.error('âŒ Errore di connessione:', error);
        pauseSimulation();
        showErrorMessage('Errore di connessione al server');
    }
}

/**
 * Aggiorna lo stato della simulazione basato sulla risposta del server
 */
function updateSimulationState(serverState) {
    // Velocità fissa rimossa - nessun aggiornamento necessario
}

/**
 * Mostra messaggio di fine dataset
 */
function showEndOfDatasetMessage() {
    const timelineInfo = document.getElementById('timeline-info');
    timelineInfo.innerHTML = `
        <i class="fas fa-check-circle text-success me-2"></i>
        Simulazione completata - Fine dataset raggiunta
    `;

    // Mostra statistiche finali
    const total = normalCount + anomalyCount;
    if (total > 0) {
        const normalPerc = ((normalCount / total) * 100).toFixed(1);
        const anomalyPerc = ((anomalyCount / total) * 100).toFixed(1);

        setTimeout(() => {
            timelineInfo.innerHTML += `<br><small class="text-muted">
                Totale processati: ${total} punti (${normalPerc}% normali, ${anomalyPerc}% anomalie)
            </small>`;
        }, 1000);
    }
}

/**
 * Mostra messaggio di errore
 */
function showErrorMessage(message) {
    const timelineInfo = document.getElementById('timeline-info');
    timelineInfo.innerHTML = `
        <i class="fas fa-exclamation-triangle text-warning me-2"></i>
        Errore: ${message}
    `;
}

/**
 * Aggiornamento dashboard principale
 */
function updateDashboard(data) {
    // Aggiorna gauge e score
    updateGauge(data.s_score);

    // Aggiorna timestamp e offset
    const timestamp = new Date(data.timestamp);
    document.getElementById('current-timestamp').textContent = timestamp.toLocaleTimeString();
    document.getElementById('current-offset').textContent = data.offset;

    // Aggiorna etichetta e score correnti
    document.getElementById('current-label').textContent = data.real_label;
    document.getElementById('current-score').textContent = (data.s_score * 100).toFixed(1) + '%';

    // Feature display rimossa

    // Aggiorna contatori
    if (data.real_label === 'Normal') {
        normalCount++;
    } else {
        anomalyCount++;
    }
}

/**
 * Aggiornamento gauge chart con color coding dinamico
 */
function updateGauge(score) {
    const percentage = Math.round(score * 100);

    // Aggiorna custom gauge con animazione
    if (customGauge) {
        customGauge.setValue(score, true);
    }

    // Determina colore e classe basati su score
    const { color, cardClass } = getScoreColorAndClass(score);

    // Aggiorna score display
    document.getElementById('score-percentage').textContent = percentage + '%';

    // Aggiorna colore card con transizione smooth
    const scoreCard = document.getElementById('anomaly-score-card');
    scoreCard.className = `anomaly-score-card ${cardClass}`;
}

/**
 * Aggiornamento grafico temporale con color coding per punti
 */
function updateTemporalChart(data) {
    const maxPoints = 50; // Mantieni solo gli ultimi 50 punti per performance

    // Aggiungi nuovo punto
    temporalData.push({
        offset: data.offset,
        score: data.s_score,
        label: data.real_label,
        timestamp: data.timestamp
    });

    // Mantieni solo gli ultimi punti
    if (temporalData.length > maxPoints) {
        temporalData.shift();
    }

    // Aggiorna chart data
    temporalChart.data.labels = temporalData.map(d => d.offset);
    temporalChart.data.datasets[0].data = temporalData.map(d => d.score);

    // Color coding dinamico dei punti basato su zone S-Score
    temporalChart.data.datasets[0].pointBackgroundColor = temporalData.map(d =>
        getScoreZoneColor(d.score)
    );

    // Aggiorna con animazione smooth
    temporalChart.update('active');
}

// Feature SNMP display rimossa come richiesto

// Funzione generateFeaturesHTMLFallback rimossa

/**
 * Aggiornamento statistiche
 */
function updateStatistics() {
    document.getElementById('normal-count').textContent = normalCount;
    document.getElementById('anomaly-count').textContent = anomalyCount;

    // Aggiorna percentuali se ci sono dati
    const total = normalCount + anomalyCount;
    if (total > 0) {
        const normalPerc = ((normalCount / total) * 100).toFixed(1);
        const anomalyPerc = ((anomalyCount / total) * 100).toFixed(1);

        document.getElementById('normal-count').title = `${normalPerc}% del totale`;
        document.getElementById('anomaly-count').title = `${anomalyPerc}% del totale`;
    }
}

/**
 * Aggiornamento progresso simulazione
 */
function updateSimulationProgress(data) {
    // Progress bar rimossa - funzione semplificata

    // Progress bar rimossa dal template

    // Progress text rimosso dal template

    // Aggiorna timeline info con informazioni piÃ¹ dettagliate
    const timelineInfo = document.getElementById('timeline-info');
    if (timelineInfo) {
        timelineInfo.textContent = `Simulazione: Punto ${currentOffset}`;
    }
}

/**
 * Aggiornamento tema per i grafici
 */
function updateChartsTheme() {
    const isDark = document.body.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#f0f0f0' : '#2c3e50';
    const gridColor = isDark ? '#404040' : '#e0e0e0';

    // Aggiorna custom gauge
    if (customGauge) {
        customGauge.updateTheme(isDark);
    }

    // Aggiorna temporal chart
    if (temporalChart) {
        temporalChart.options.scales.x.ticks.color = textColor;
        temporalChart.options.scales.y.ticks.color = textColor;
        temporalChart.options.scales.x.grid.color = gridColor;
        temporalChart.options.scales.y.grid.color = gridColor;
        temporalChart.options.scales.x.title.color = textColor;
        temporalChart.options.scales.y.title.color = textColor;
        temporalChart.update();
    }

    console.log(`ðŸŽ¨ Tema grafici aggiornato: ${isDark ? 'dark' : 'light'}`);
}

/**
 * Utility functions
 */

/**
 * Determina colore e classe CSS basati su S-Score
 * Utilizza AnomalyChartUtils se disponibile, altrimenti fallback
 */
function getScoreColorAndClass(score) {
    if (typeof AnomalyChartUtils !== 'undefined') {
        return AnomalyChartUtils.getScoreColorAndClass(score);
    }

    // Fallback al metodo originale
    if (score >= SCORE_COLORS.excellent.threshold) {
        return { color: SCORE_COLORS.excellent.color, cardClass: 'score-excellent' };
    } else if (score >= SCORE_COLORS.good.threshold) {
        return { color: SCORE_COLORS.good.color, cardClass: 'score-good' };
    } else if (score >= SCORE_COLORS.warning.threshold) {
        return { color: SCORE_COLORS.warning.color, cardClass: 'score-warning' };
    } else {
        return { color: SCORE_COLORS.critical.color, cardClass: 'score-critical' };
    }
}

/**
 * Ottieni livello testuale basato su S-Score
 * Utilizza AnomalyChartUtils se disponibile, altrimenti fallback
 */
function getScoreLevel(score) {
    if (typeof AnomalyChartUtils !== 'undefined') {
        return AnomalyChartUtils.getScoreLevel(score);
    }

    // Fallback al metodo originale
    if (score >= SCORE_COLORS.excellent.threshold) {
        return SCORE_COLORS.excellent.label;
    } else if (score >= SCORE_COLORS.good.threshold) {
        return SCORE_COLORS.good.label;
    } else if (score >= SCORE_COLORS.warning.threshold) {
        return SCORE_COLORS.warning.label;
    } else {
        return SCORE_COLORS.critical.label;
    }
}

/**
 * Navigazione
 */
function goToConfig() {
    if (simulationRunning) {
        if (confirm('La simulazione Ã¨ in corso. Vuoi interromperla e tornare alla configurazione?')) {
            pauseSimulation();
            window.location.href = '/anomaly_snmp/configure';
        }
    } else {
        window.location.href = '/anomaly_snmp/configure';
    }
}

/**
 * Funzioni di utilitÃ  aggiuntive per la simulazione
 */

/**
 * Salta a un offset specifico nella simulazione
 */
async function jumpToOffset(offset) {
    if (offset < 0) {
        showErrorMessage('Offset deve essere positivo');
        return;
    }

    const result = await controlSimulation('jump_to_offset', { offset: offset });

    if (result) {
        currentOffset = offset;
        document.getElementById('current-offset').textContent = offset;
        console.log(`ðŸŽ¯ Saltato all'offset ${offset}`);

        // Se la simulazione Ã¨ in corso, fetch il punto corrente
        if (simulationRunning) {
            await fetchNextDataPoint();
        }
    }
}

/**
 * Gestione keyboard shortcuts per la simulazione
 */
document.addEventListener('keydown', function (event) {
    // Solo se non stiamo digitando in un input
    if (event.target.tagName.toLowerCase() === 'input') return;

    switch (event.key) {
        case ' ': // Spacebar per play/pause
            event.preventDefault();
            toggleSimulation();
            break;
        case 'r': // R per reset
            if (event.ctrlKey) {
                event.preventDefault();
                resetSimulation();
            }
            break;
        case '1':
        case '2':
        case '3':
        case '4':
        case '5':
            // Numeri 1-5 per velocitÃ 
            event.preventDefault();
            changeSpeed(parseInt(event.key));
            break;
    }
});

/**
 * Gestione visibilitÃ  pagina per pausare simulazione quando non visibile
 */
document.addEventListener('visibilitychange', function () {
    if (document.hidden && simulationRunning) {
        console.log('ðŸ“± Pagina nascosta, pausa simulazione per risparmiare risorse');
        pauseSimulation();
    }
});

/**
 * Gestione errori di rete con retry automatico
 */
let retryCount = 0;
const maxRetries = 3;

async function fetchWithRetry(url, options = {}, retries = maxRetries) {
    try {
        const response = await fetch(url, options);
        retryCount = 0; // Reset counter on success
        return response;
    } catch (error) {
        if (retries > 0) {
            retryCount++;
            console.log(`ðŸ”„ Tentativo ${retryCount}/${maxRetries} fallito, riprovo in 2 secondi...`);
            await new Promise(resolve => setTimeout(resolve, 2000));
            return fetchWithRetry(url, options, retries - 1);
        } else {
            throw error;
        }
    }
}

/**
 * Mostra notifica toast per feedback utente
 */
function showToast(message, type = 'info') {
    // Crea elemento toast se non esiste
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
        `;
        document.body.appendChild(toastContainer);
    }

    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show`;
    toast.style.cssText = `
        margin-bottom: 10px;
        min-width: 300px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;

    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    toastContainer.appendChild(toast);

    // Auto-remove dopo 5 secondi
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 5000);
}

// Export per testing (se necessario)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getScoreColorAndClass,
        getScoreLevel,
        SCORE_COLORS,
        jumpToOffset,
        fetchWithRetry,
        showToast
    };
}
/**
 * NUOVO: Aggiornamento statistiche
 */
function updateStatistics() {
    document.getElementById('normal-count').textContent = normalCount;
    document.getElementById('anomaly-count').textContent = anomalyCount;

    // Aggiorna accuratezza
    const accuracyElement = document.getElementById('model-accuracy');
    if (accuracyElement && totalPredictions > 0) {
        const accuracy = (correctPredictions / totalPredictions * 100).toFixed(1);
        accuracyElement.textContent = `${accuracy}% (${correctPredictions}/${totalPredictions})`;
    } else if (accuracyElement) {
        accuracyElement.textContent = '--';
    }
}

/**
 * RIMOSSO: Funzione updateDetectionStatistics non piÃ¹ necessaria
 * Gli elementi detected-anomalies, detection-accuracy sono stati rimossi dal template
 */

// Funzione duplicata rimossa - usa quella sopra che prende i dati dal server

/**
 * NUOVO: Aggiorna i contatori basati sull'etichetta del punto dati
 */
function updateCounters(realLabel) {
    if (realLabel === 'Normal') {
        normalCount++;
    } else if (realLabel === 'Anomaly') {
        anomalyCount++;
    }
}

/**
 * NUOVO: Aggiornamento dashboard principale
 */
function updateDashboard(data) {
    // Aggiorna gauge e score
    updateGauge(data.s_score);

    // Aggiorna timestamp e offset
    const timestamp = new Date(data.timestamp);
    document.getElementById('current-timestamp').textContent = timestamp.toLocaleTimeString();
    document.getElementById('current-offset').textContent = data.offset || currentOffset;

    // Calcola predizione del sistema: SOLO S-Score = 0.0 è anomalia
    const predictedLabel = data.s_score === ANOMALY_THRESHOLD ? 'Anomaly' : 'Normal';
    const isCorrect = predictedLabel === data.real_label;

    // Aggiorna contatori accuratezza
    totalPredictions++;
    if (isCorrect) correctPredictions++;

    // Aggiorna etichette nel pannello
    const currentLabelElement = document.getElementById('current-label');
    if (currentLabelElement) {
        const correctIcon = isCorrect ? '✅' : '❌';
        currentLabelElement.innerHTML = `
            <div><strong>Reale:</strong> <span class="badge bg-${data.real_label === 'Normal' ? 'success' : 'danger'}">${data.real_label}</span></div>
            <div><strong>Predetta:</strong> <span class="badge bg-${predictedLabel === 'Normal' ? 'success' : 'danger'}">${predictedLabel}</span> ${correctIcon}</div>
        `;
    }

    document.getElementById('current-score').textContent = (data.s_score * 100).toFixed(1) + '%';

    // Aggiorna accuratezza
    const accuracy = totalPredictions > 0 ? (correctPredictions / totalPredictions * 100).toFixed(1) : 0;
    document.getElementById('model-accuracy').textContent = `${accuracy}% (${correctPredictions}/${totalPredictions})`;

    // Aggiorna contatori basati sull'etichetta reale
    updateCounters(data.real_label);

    // Log dettagliato della predizione
    const predictionStatus = isCorrect ? '✅' : '❌';
    const anomalyStatus = data.s_score === 0.0 ? '🚨 ANOMALIA' : '✅ NORMALE';
    console.log(`📊 Punto ${data.offset || currentOffset}: ${anomalyStatus} | S-Score=${(data.s_score * 100).toFixed(1)}% | Real: ${data.real_label} | Predicted: ${predictedLabel} ${predictionStatus}`);

    // Aggiorna colore della card score basato sul valore
    updateScoreCardColor(data.s_score);
}

// Seconda funzione updateFeaturesDisplay rimossa

/**
 * NUOVO: Aggiorna il colore della card score basato sul valore S-Score
 */
function updateScoreCardColor(score) {
    const scoreCard = document.getElementById('anomaly-score-card');
    const scorePercentage = document.getElementById('score-percentage');

    if (scoreCard && scorePercentage) {
        // Rimuovi classi di colore esistenti
        scoreCard.classList.remove('score-excellent', 'score-good', 'score-warning', 'score-critical');

        // Aggiungi classe basata sul punteggio
        if (score >= 0.8) {
            scoreCard.style.background = 'linear-gradient(135deg, #27ae60, #2ecc71)';
        } else if (score >= 0.6) {
            scoreCard.style.background = 'linear-gradient(135deg, #f39c12, #e67e22)';
        } else if (score >= 0.4) {
            scoreCard.style.background = 'linear-gradient(135deg, #ff6b35, #e55a2b)';
        } else {
            scoreCard.style.background = 'linear-gradient(135deg, #e74c3c, #c0392b)';
        }

        // Aggiorna percentuale
        scorePercentage.textContent = (score * 100).toFixed(1) + '%';
    }
}

/**
 * NUOVO: Aggiorna il gauge chart
 */
function updateGauge(score) {
    if (customGauge) {
        customGauge.setValue(score, true); // true per animazione
    }
}

/**
 * NUOVO: Aggiorna il grafico temporale
 */
function updateTemporalChart(data) {
    if (!temporalChart) return;

    const score = data.s_score;
    const label = data.real_label;

    // Usa indice sequenziale invece di offset per garantire ordinamento
    const sequentialIndex = temporalChart.data.labels.length + 1;

    // Aggiungi punto al grafico con indice sequenziale
    temporalChart.data.labels.push(sequentialIndex);
    temporalChart.data.datasets[0].data.push(score);

    // Colore basato sulla zona S-Score
    const pointColor = getScoreZoneColor(score);
    temporalChart.data.datasets[0].pointBackgroundColor.push(pointColor);

    // Mantieni solo gli ultimi 50 punti per performance
    if (temporalChart.data.labels.length > 50) {
        temporalChart.data.labels.shift();
        temporalChart.data.datasets[0].data.shift();
        temporalChart.data.datasets[0].pointBackgroundColor.shift();
    }

    // Aggiorna il grafico
    temporalChart.update('none'); // Nessuna animazione per performance

    // Salva nei dati temporali con indice sequenziale
    temporalData.push({
        sequentialIndex: sequentialIndex,
        offset: data.offset || currentOffset,
        score: score,
        label: label,
        timestamp: data.timestamp
    });

    // Mantieni solo gli ultimi 100 punti nei dati
    if (temporalData.length > 100) {
        temporalData.shift();
    }
}

/**
 * NUOVO: Aggiorna il resoconto del dataset con LOGICA CORRETTA
 */
function updateDatasetReportCorrect(config) {
    const trainSplit = config.train_split || 0.7;
    const contamination = config.contamination || 0.05;

    // Dataset originale
    const normalOriginal = 600;
    const anomalyOriginal = 4398;
    const totalOriginal = normalOriginal + anomalyOriginal;

    // LOGICA CORRETTA:
    // 1. Oversampling sui normali fino a raggiungere rapporto contamination
    // Formula: anomalie / (normali_oversampled + anomalie) = contamination
    // Risolviamo: normali_oversampled = anomalie * (1 - contamination) / contamination
    const targetNormalOversampled = Math.floor(anomalyOriginal * (1 - contamination) / contamination);
    const smoteGenerated = Math.max(0, targetNormalOversampled - normalOriginal);
    const totalNormalOversampled = normalOriginal + smoteGenerated;

    // 2. Training/Test split sui normali bilanciati
    const normalTraining = Math.floor(totalNormalOversampled * trainSplit);
    const normalTest = totalNormalOversampled - normalTraining;

    // 3. Test set = normali rimanenti + TUTTE le anomalie
    const anomalyTest = anomalyOriginal;  // Tutte le 4398 anomalie
    const totalTest = normalTest + anomalyTest;

    // Dataset Post-SMOTE
    const totalSmote = totalNormalOversampled + anomalyOriginal;

    // Aggiorna UI - Dataset Originale
    document.getElementById('dataset-normal-original').textContent = normalOriginal.toLocaleString();
    document.getElementById('dataset-anomaly-original').textContent = anomalyOriginal.toLocaleString();
    document.getElementById('dataset-total-original').textContent = totalOriginal.toLocaleString();

    // Dataset Post-SMOTE
    document.getElementById('dataset-normal-smote').textContent = totalNormalOversampled.toLocaleString();
    document.getElementById('dataset-anomaly-smote').textContent = anomalyOriginal.toLocaleString();
    document.getElementById('dataset-total-smote').textContent = totalSmote.toLocaleString();

    // Training Set (solo normali)
    document.getElementById('training-normal-count').textContent = normalTraining.toLocaleString();
    // training-anomaly-count rimosso dal template
    document.getElementById('training-total-count').textContent = normalTraining.toLocaleString();

    // Test Set
    document.getElementById('test-normal-count').textContent = normalTest.toLocaleString();
    document.getElementById('test-anomaly-count').textContent = anomalyTest.toLocaleString();
    document.getElementById('test-total-count').textContent = totalTest.toLocaleString();

    // Rilevamento Anomalie
    // detected-anomalies rimosso dal template
    // theoretical-anomalies rimosso dal template
    // detection-accuracy rimosso dal template

    // Progress bar rimossa dal template

    console.log('ðŸ“Š Resoconto dataset aggiornato (LOGICA CORRETTA):', {
        oversampling: {
            original: normalOriginal,
            target: targetNormalOversampled,
            smote: smoteGenerated,
            total: totalNormalOversampled
        },
        training: { normal: normalTraining },
        test: { normal: normalTest, anomaly: anomalyTest, total: totalTest },
        contamination_achieved: (anomalyOriginal / (totalNormalOversampled + anomalyOriginal) * 100).toFixed(1) + '%'
    });
}


/**
 * NUOVO: Aggiorna i dati del dashboard con dichiarazione anomalia
 */
function updateDashboardData(data) {
    // Aggiorna S-Score e gauge
    updateGauge(data.s_score);
    updateScoreCardColor(data.s_score);

    // Aggiorna timestamp
    document.getElementById('current-timestamp').textContent =
        new Date(data.timestamp).toLocaleTimeString();
    document.getElementById('current-offset').textContent = data.offset;

    // Aggiorna etichette nel pannello statistiche
    const currentLabelElement = document.getElementById('current-label');
    const currentScoreElement = document.getElementById('current-score');

    if (currentLabelElement) {
        currentLabelElement.textContent = data.real_label;
    }

    if (currentScoreElement) {
        currentScoreElement.textContent = (data.s_score * 100).toFixed(1) + '%';
    }

    // DICHIARAZIONE ANOMALIA basata su S-Score
    const timelineInfo = document.getElementById('timeline-info');
    if (timelineInfo) {
        let statusMessage, statusIcon, statusClass;

        if (data.s_score >= 0.8) {
            statusMessage = 'SISTEMA NORMALE';
            statusIcon = '✅';
            statusClass = 'text-success';
        } else if (data.s_score >= 0.6) {
            statusMessage = 'ATTENZIONE - Deviazione rilevata';
            statusIcon = '⚠️';
            statusClass = 'text-warning';
        } else if (data.s_score >= 0.4) {
            statusMessage = 'WARNING - Comportamento anomalo';
            statusIcon = '🟠';
            statusClass = 'text-warning';
        } else {
            statusMessage = 'ANOMALIA CRITICA - Intervento richiesto';
            statusIcon = '🚨';
            statusClass = 'text-danger';
        }

        timelineInfo.innerHTML = `
            <div class="${statusClass}">
                <strong>${statusIcon} ${statusMessage}</strong>
            </div>
            <small class="text-muted">
                S-Score: ${(data.s_score * 100).toFixed(1)}% | Punto: ${data.offset} | ${new Date(data.timestamp).toLocaleTimeString()}
            </small>
        `;
    }

    // Log con dichiarazione anomalia
    let logStatus;
    if (data.s_score < 0.4) {
        logStatus = '🚨 ANOMALIA CRITICA';
    } else if (data.s_score < 0.6) {
        logStatus = '🟠 WARNING';
    } else if (data.s_score < 0.8) {
        logStatus = '⚠️ ATTENZIONE';
    } else {
        logStatus = '✅ NORMALE';
    }

    // Aggiorna contatori basati su S-Score
    if (data.s_score < 0.4) {
        criticalAnomalies++;
    } else if (data.s_score < 0.6) {
        warningPoints++;
    } else if (data.s_score < 0.8) {
        attentionPoints++;
    } else {
        normalPoints++;
    }

    // Aggiorna statistiche
    updateStatistics();

    console.log(`📊 Punto ${data.offset}: ${logStatus} | S-Score=${(data.s_score * 100).toFixed(1)}% | Real: ${data.real_label}`);
}

/**
 * Reset del grafico temporale
 */
function resetTemporalChart() {
    if (temporalChart) {
        temporalChart.data.labels = [];
        temporalChart.data.datasets[0].data = [];
        temporalChart.data.datasets[0].pointBackgroundColor = [];
        temporalChart.update();
    }

    // Reset dati temporali
    temporalData = [];

    console.log('📊 Grafico temporale resettato');
}

/**
 * Reset completo simulazione
 */
function resetSimulation() {
    // Reset contatori
    normalCount = 0;
    anomalyCount = 0;
    currentOffset = 0;

    // Reset grafico
    resetTemporalChart();

    // Reset statistiche
    updateStatistics();

    // Pausa simulazione
    pauseSimulation();

    console.log('🔄 Simulazione resettata completamente');
}