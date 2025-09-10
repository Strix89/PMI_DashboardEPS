/**
 * AnomalySNMP Dashboard JavaScript - Versione Modificata
 * Gestisce la simulazione tempo reale senza gauge, mostra solo Normale/Anomalia
 */

// Variabili globali per la simulazione
let simulationRunning = false;
let currentOffset = 0;
let simulationInterval = null;

// Variabili per i grafici
let temporalChart = null;
let temporalData = [];

// Contatori statistiche
let normalCount = 0;
let anomalyCount = 0;

// Contatori per accuratezza
let totalPredictions = 0;
let correctPredictions = 0;

/**
 * Inizializzazione della dashboard
 */
document.addEventListener('DOMContentLoaded', function () {
    console.log('🚀 Inizializzazione AnomalySNMP Dashboard (Versione Modificata)');

    // Registra plugin Chart.js
    if (typeof Chart !== 'undefined' && typeof annotationPlugin !== 'undefined') {
        Chart.register(annotationPlugin);
    }

    loadTheme();
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);

    initializeCharts();
    loadConfiguration();
    loadSimulationStatus();

    // Controllo periodico dello stato (ogni 30 secondi)
    setInterval(checkSimulationStatus, 30000);

    console.log('✅ Dashboard inizializzata con successo');
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
            currentOffset = status.current_offset;
            document.getElementById('current-offset').textContent = currentOffset;

            if (status.statistics) {
                normalCount = status.statistics.normal_count || 0;
                anomalyCount = status.statistics.anomaly_count || 0;
                updateStatistics();
            }

            if (currentOffset > 0) {
                document.getElementById('timeline-info').textContent =
                    `Simulazione: Punto ${currentOffset}`;
            }

            console.log('📊 Stato simulazione caricato:', status);
        }
    } catch (error) {
        console.warn('⚠️ Errore nel caricamento stato simulazione:', error);
    }
}

/**
 * Controllo periodico dello stato della simulazione
 */
async function checkSimulationStatus() {
    if (!simulationRunning) return;

    try {
        const response = await fetch('/anomaly_snmp/api/simulation_status');
        const result = await response.json();

        if (result.success) {
            const status = result.status;

            if (status.current_offset !== currentOffset) {
                console.log(`🔄 Sincronizzazione offset: locale=${currentOffset}, server=${status.current_offset}`);
                currentOffset = status.current_offset;
                document.getElementById('current-offset').textContent = currentOffset;
            }

            if (!status.is_running && simulationRunning) {
                console.log('⏸️ Simulazione fermata lato server, sincronizzazione...');
                pauseSimulation();
            }
        }
    } catch (error) {
        console.warn('⚠️ Errore nel controllo stato simulazione:', error);
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
    updateChartsTheme();

    console.log(`🎨 Tema cambiato a: ${newTheme}`);
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
 * Inizializzazione dei grafici (solo temporale, senza gauge)
 */
function initializeCharts() {
    console.log('📊 Inizializzazione grafici...');
    initializeTemporalChart();
    console.log('✅ Grafici inizializzati');
}

/**
 * Inizializza il grafico temporale per l'andamento delle predizioni
 */
function initializeTemporalChart() {
    const ctx = document.getElementById('temporal-chart').getContext('2d');

    temporalChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Predizioni',
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
                            const value = context.parsed.y;
                            const label = temporalData[index] ? temporalData[index].label : 'Unknown';
                            const prediction = temporalData[index] ? temporalData[index].prediction : 'Unknown';

                            return [
                                `Predizione: ${prediction}`,
                                `Etichetta reale: ${label}`,
                                `Valore: ${value === 1 ? 'Normale' : 'Anomalia'}`
                            ];
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    min: -1.5,
                    max: 1.5,
                    ticks: {
                        callback: function (value) {
                            if (value === 1) return 'Normale';
                            if (value === -1) return 'Anomalia';
                            return '';
                        }
                    },
                    title: {
                        display: true,
                        text: 'Predizione Isolation Forest',
                        font: {
                            weight: 'bold'
                        }
                    },
                    grid: {
                        color: function (context) {
                            if (context.tick.value === 1) return '#27ae60';
                            if (context.tick.value === -1) return '#e74c3c';
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

    console.log('📈 Grafico temporale inizializzato');
}

/**
 * Caricamento configurazione dal server
 */
async function loadConfiguration() {
    try {
        console.log('⚙️ Caricamento configurazione...');
        const response = await fetch('/anomaly_snmp/api/get_config');
        const data = await response.json();

        if (data.success) {
            const config = data.config;
            document.getElementById('config-contamination').textContent =
                (config.contamination * 100).toFixed(1) + '%';
            document.getElementById('config-train-split').textContent =
                (config.train_split * 100).toFixed(0) + '%';

            // Aggiorna dataset report solo se il DOM è pronto
            if (document.readyState === 'complete' || document.readyState === 'interactive') {
                updateDatasetReport(config);
            } else {
                document.addEventListener('DOMContentLoaded', () => updateDatasetReport(config));
            }

            document.getElementById('timeline-info').textContent =
                `Configurazione: Contamination ${(config.contamination * 100).toFixed(1)}%, Train Split ${(config.train_split * 100).toFixed(0)}%`;

            console.log('✅ Configurazione caricata:', config);
        } else {
            console.error('❌ Errore nel caricamento configurazione:', data.error);
        }
    } catch (error) {
        console.error('❌ Errore di connessione configurazione:', error);
    }
}

/**
 * Aggiorna il resoconto del dataset con logica SMOTE corretta
 * 
 * FLUSSO CORRETTO:
 * 1. Dataset originale: 600 normali + 4398 anomalie
 * 2. Separo: Prendo solo i 600 normali
 * 3. SMOTE: Applico SMOTE ai 600 normali per raggiungere target contamination
 * 4. Training split: 80% dei normali post-SMOTE per training
 * 5. Test set: 20% normali post-SMOTE + TUTTE le 4398 anomalie (shufflati)
 */
function updateDatasetReport(config) {
    const trainSplit = config.train_split || 0.7;
    const contamination = config.contamination || 0.05;
    
    // DEBUG: Log dei parametri ricevuti
    console.log('🔍 DEBUG updateDatasetReport:');
    console.log('   • config ricevuto:', config);
    console.log('   • trainSplit:', trainSplit);
    console.log('   • contamination:', contamination);

    const normalOriginal = 600;
    const anomalyOriginal = 4398;
    const totalOriginal = normalOriginal + anomalyOriginal;

    // STEP 1: SMOTE sui 600 normali originali
    // Il contamination si riferisce al test set finale
    // Formula: anomalie / (normali_test + anomalie) = contamination
    // Quindi: normali_test = anomalie * (1 - contamination) / contamination
    const normalsNeededInTest = Math.floor(anomalyOriginal * (1 - contamination) / contamination);
    
    // STEP 2: Calcolo quanti normali totali servono considerando il train_split
    // Se normali_test = smote_total * (1 - train_split), allora:
    // smote_total = normali_test / (1 - train_split)
    const smoteTarget = Math.floor(normalsNeededInTest / (1 - trainSplit));
    
    // STEP 3: Training split sui normali post-SMOTE
    const normalTraining = Math.floor(smoteTarget * trainSplit);
    
    // STEP 4: Test set = normali rimanenti + tutte le anomalie
    const normalTest = smoteTarget - normalTraining;
    const anomalyTest = anomalyOriginal;
    const totalTest = normalTest + anomalyTest;

    // Dataset post-SMOTE (solo normali aumentati)
    const totalSmote = smoteTarget;

    // Aggiorna UI con controlli di sicurezza
    const updateElement = (id, value) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        } else {
            console.warn(`Elemento ${id} non trovato nel DOM`);
        }
    };

    // Dataset Originale
    updateElement('dataset-normal-original', normalOriginal.toLocaleString());
    updateElement('dataset-anomaly-original', anomalyOriginal.toLocaleString());
    updateElement('dataset-total-original', totalOriginal.toLocaleString());

    // Dataset Post-SMOTE (solo normali aumentati)
    updateElement('dataset-normal-smote', smoteTarget.toLocaleString());
    updateElement('dataset-total-smote', totalSmote.toLocaleString());

    // Training Set (solo normali post-SMOTE)
    updateElement('training-normal-count', normalTraining.toLocaleString());
    updateElement('training-total-count', normalTraining.toLocaleString());

    // Test Set (normali rimanenti + tutte le anomalie)
    updateElement('test-normal-count', normalTest.toLocaleString());
    updateElement('test-anomaly-count', anomalyTest.toLocaleString());
    updateElement('test-total-count', totalTest.toLocaleString());

    console.log('📊 Resoconto dataset aggiornato');
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
 * Avvia simulazione
 */
async function startSimulation() {
    simulationRunning = true;
    document.getElementById('simulation-btn').innerHTML = '<i class="fas fa-pause"></i> <span>Pausa</span>';

    simulationInterval = setInterval(fetchNextDataPoint, 1000);
    await controlSimulation('play');

    console.log('▶️ Simulazione avviata');
}

/**
 * Pausa simulazione
 */
async function pauseSimulation() {
    simulationRunning = false;
    document.getElementById('simulation-btn').innerHTML = '<i class="fas fa-play"></i> <span>Play</span>';

    if (simulationInterval) {
        clearInterval(simulationInterval);
        simulationInterval = null;
    }

    await controlSimulation('pause');
    console.log('⏸️ Simulazione in pausa');
}

/**
 * Reset simulazione
 */
async function resetSimulation() {
    console.log('🔄 Reset simulazione...');
    pauseSimulation();

    try {
        const response = await fetch('/anomaly_snmp/api/reset_simulation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (result.success) {
            currentOffset = 0;
            temporalData = [];
            normalCount = 0;
            anomalyCount = 0;

            // Reset contatori accuratezza
            resetAccuracyCounters();

            // Reset grafici
            temporalChart.data.labels = [];
            temporalChart.data.datasets[0].data = [];
            temporalChart.data.datasets[0].pointBackgroundColor = [];
            temporalChart.update();

            updateDetectionStatus('waiting', 'In attesa...', 'Avvia la simulazione per iniziare il rilevamento');
            updateStatistics();

            // Reset timeline info
            document.getElementById('timeline-info').textContent = 'Simulazione: Pronta per iniziare';

            document.getElementById('timeline-info').textContent = 'Simulazione: Pronta per iniziare';

            console.log('✅ Simulazione resettata con successo');
        } else {
            console.error('❌ Errore nel reset:', result.error);
            showErrorMessage('Errore nel reset della simulazione');
        }
    } catch (error) {
        console.error('❌ Errore di connessione durante reset:', error);
        showErrorMessage('Errore di connessione durante il reset');
    }
}

/**
 * Controllo simulazione con API
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
            console.log(`✅ Azione ${action} eseguita con successo`);
            return result;
        } else {
            console.error(`❌ Errore nell'azione ${action}:`, result.error);
            return null;
        }
    } catch (error) {
        console.error(`❌ Errore di connessione per azione ${action}:`, error);
        return null;
    }
}

/**
 * Fetch del prossimo punto dati
 */
async function fetchNextDataPoint() {
    try {
        const response = await fetch(`/anomaly_snmp/api/get_next_point/${currentOffset}`);
        const result = await response.json();

        if (result.success) {
            const data = result.data;
            currentOffset = result.next_offset || (currentOffset + 1);

            // Aggiorna visualizzazioni
            updateDashboard(data);
            updateTemporalChart(data);
            updateStatistics();

            // Gestione fine dataset
            if (!result.has_more_data) {
                console.log('📊 Fine del dataset raggiunta');
                pauseSimulation();
                showEndOfDatasetMessage();
                return;
            }

            console.log(`📊 Punto dati ${data.offset}: Predizione=${data.classification}, Label=${data.real_label}`);
        } else {
            console.error('❌ Errore nel fetch dati:', result.error);
            pauseSimulation();
            showErrorMessage(result.error);
        }
    } catch (error) {
        console.error('❌ Errore di connessione:', error);
        pauseSimulation();
        showErrorMessage('Errore di connessione al server');
    }
}

/**
 * Aggiornamento dashboard principale
 */
function updateDashboard(data) {
    // Aggiorna status di rilevamento
    if (data.is_anomaly) {
        updateDetectionStatus('anomaly', 'ANOMALIA RILEVATA', 'Il modello ha identificato un comportamento anomalo');
    } else {
        updateDetectionStatus('normal', 'COMPORTAMENTO NORMALE', 'Il modello ha identificato un comportamento normale');
    }

    // Aggiorna solo il timeline info con informazioni generali
    document.getElementById('timeline-info').textContent = 
        `Simulazione: Punto ${data.offset} - ${data.classification}`;

    // Aggiorna contatori basati sulle PREDIZIONI del modello (non etichette reali)
    if (data.is_anomaly) {
        anomalyCount++;  // Incrementa quando il modello PREDICE un'anomalia
    } else {
        normalCount++;   // Incrementa quando il modello PREDICE normale
    }

    // Calcola accuratezza
    totalPredictions++;
    
    // Verifica se la predizione è corretta
    const predictionCorrect = (
        (data.is_anomaly && data.real_label === 'Anomaly') ||
        (data.is_normal && data.real_label === 'Normal')
    );
    
    if (predictionCorrect) {
        correctPredictions++;
    }

    // Aggiorna display accuratezza
    updateAccuracyDisplay();

    // Aggiorna confronto predizione vs realtà
    updatePredictionComparison(data, predictionCorrect);
}

/**
 * Aggiorna lo status di rilevamento
 */
function updateDetectionStatus(type, text, description) {
    const statusIcon = document.getElementById('status-icon');
    const statusText = document.getElementById('status-text');
    const statusDescription = document.getElementById('status-description');
    const scoreCard = document.getElementById('anomaly-score-card');

    // Rimuovi classi precedenti
    scoreCard.classList.remove('card-normal', 'card-anomaly', 'card-waiting');
    statusIcon.classList.remove('status-normal', 'status-anomaly', 'status-waiting');

    // Applica nuove classi e contenuto
    switch (type) {
        case 'normal':
            scoreCard.classList.add('card-normal');
            statusIcon.classList.add('status-normal');
            statusIcon.innerHTML = '<i class="fas fa-check-circle"></i>';
            break;
        case 'anomaly':
            scoreCard.classList.add('card-anomaly');
            statusIcon.classList.add('status-anomaly');
            statusIcon.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
            break;
        case 'waiting':
        default:
            scoreCard.classList.add('card-waiting');
            statusIcon.classList.add('status-waiting');
            statusIcon.innerHTML = '<i class="fas fa-question-circle"></i>';
            break;
    }

    statusText.textContent = text;
    statusDescription.textContent = description;
}

/**
 * Aggiornamento grafico temporale
 */
function updateTemporalChart(data) {
    const maxPoints = 50;

    // Aggiungi nuovo punto
    temporalData.push({
        offset: data.offset,
        prediction: data.prediction,
        label: data.real_label,
        timestamp: data.timestamp,
        classification: data.classification
    });

    // Mantieni solo gli ultimi punti
    if (temporalData.length > maxPoints) {
        temporalData.shift();
    }

    // Aggiorna chart data
    temporalChart.data.labels = temporalData.map(d => d.offset);
    temporalChart.data.datasets[0].data = temporalData.map(d => d.prediction);

    // Color coding: verde per normale (1), rosso per anomalia (-1)
    temporalChart.data.datasets[0].pointBackgroundColor = temporalData.map(d =>
        d.prediction === 1 ? '#27ae60' : '#e74c3c'
    );

    temporalChart.update('active');
}

/**
 * Aggiornamento statistiche
 */
function updateStatistics() {
    document.getElementById('normal-count').textContent = normalCount;
    document.getElementById('anomaly-count').textContent = anomalyCount;

    const total = normalCount + anomalyCount;
    if (total > 0) {
        const normalPerc = ((normalCount / total) * 100).toFixed(1);
        const anomalyPerc = ((anomalyCount / total) * 100).toFixed(1);

        document.getElementById('normal-count').title = `${normalPerc}% del totale`;
        document.getElementById('anomaly-count').title = `${anomalyPerc}% del totale`;
    }
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
 * Aggiorna tema dei grafici
 */
function updateChartsTheme() {
    if (temporalChart) {
        temporalChart.update();
    }
}

/**
 * Aggiorna il display dell'accuratezza
 */
function updateAccuracyDisplay() {
    const accuracyElement = document.getElementById('model-accuracy');
    const accuracyDisplayElement = document.getElementById('model-accuracy-display');
    
    if (totalPredictions === 0) {
        accuracyElement.textContent = '--';
        accuracyDisplayElement.className = 'accuracy-display';
        return;
    }

    const accuracy = (correctPredictions / totalPredictions) * 100;
    accuracyElement.textContent = `${accuracy.toFixed(1)}% (${correctPredictions}/${totalPredictions})`;

    // Aggiorna colore basato sull'accuratezza
    accuracyDisplayElement.classList.remove('accuracy-excellent', 'accuracy-good', 'accuracy-poor');
    
    if (accuracy >= 85) {
        accuracyDisplayElement.classList.add('accuracy-excellent');
    } else if (accuracy >= 70) {
        accuracyDisplayElement.classList.add('accuracy-good');
    } else {
        accuracyDisplayElement.classList.add('accuracy-poor');
    }
}

/**
 * Aggiorna il confronto tra predizione e realtà
 */
function updatePredictionComparison(data, isCorrect) {
    const comparisonElement = document.getElementById('prediction-comparison');
    
    const predictionText = data.classification;
    const realText = data.real_label === 'Normal' ? 'Normale' : 'Anomalia';
    
    let html = `
        <div class="row">
            <div class="col-6">
                <strong>Predizione IF:</strong><br>
                <span class="${data.is_anomaly ? 'text-danger' : 'text-success'}">${predictionText}</span>
            </div>
            <div class="col-6">
                <strong>Etichetta Reale:</strong><br>
                <span class="${data.real_label === 'Normal' ? 'text-success' : 'text-danger'}">${realText}</span>
            </div>
        </div>
        <div class="row mt-2">
            <div class="col-12 text-center">
                <span class="badge ${isCorrect ? 'bg-success' : 'bg-danger'}">
                    ${isCorrect ? '✓ Predizione Corretta' : '✗ Predizione Errata'}
                </span>
            </div>
        </div>
    `;
    
    comparisonElement.innerHTML = html;
}

/**
 * Reset dei contatori accuratezza
 */
function resetAccuracyCounters() {
    totalPredictions = 0;
    correctPredictions = 0;
    updateAccuracyDisplay();
    
    const comparisonElement = document.getElementById('prediction-comparison');
    comparisonElement.innerHTML = '<small class="text-muted">Avvia simulazione per vedere il confronto</small>';
}