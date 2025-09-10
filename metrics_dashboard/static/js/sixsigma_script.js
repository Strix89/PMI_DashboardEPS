document.addEventListener('DOMContentLoaded', () => {
    // Riferimenti agli elementi HTML principali
    const machineSelector = document.getElementById('machine-selector');
    const scoreValueEl = document.getElementById('score-value');
    
    // Log separati per ogni metrica
    const cpuLogEl = document.getElementById('cpu-log');
    const ramLogEl = document.getElementById('ram-log');
    const ioLogEl = document.getElementById('io-log');
    
    const pauseButton = document.getElementById('pause-button');
    const zoomToggle = document.getElementById('zoom-toggle');

    let simulationInterval = null;
    let timeUpdateInterval = null;
    let currentOffset = 1;
    let isPaused = false;
    let isZoomEnabled = true;
    const MAX_POINTS_ON_CHART = 20;  // Allineato con history_limit del backend
    const charts = {};
    let currentBaselines = {};
    
    // Contatori per le statistiche dei test
    let testStatistics = {
        test1: 0,    // Violazione Limite
        test2: 0,    // Zona A
        test3: 0,    // Zona B  
        test4: 0,    // Run Test
        test5: 0,    // 6 su 8
        test6: 0,    // Stratificazione
        test7: 0,    // Trend Oscillatorio
        test8: 0,    // Trend Lineare
        testmr: 0,   // Alta Variabilità mR
        testsat: 0,  // Saturazione Risorsa
        testok: 0    // In Controllo
    };
    
    // Contatori per la simulazione
    let simulationStartTime = null;
    let pointsAnalyzed = 0;

    // Variabile per tenere traccia della simulazione attualmente attiva
    let activeMachineId = null;
    
    // 🔶 GESTIONE RICALCOLO BASELINE ESTESA
    let recalculateCounters = {};
    let isRecalculating = {};
    let pausedCharts = {};  // Nuovo: traccia i grafici in pausa
    const RECALCULATE_WAIT_POINTS = 20;  // Ridotto a 20 punti per ricalcolo più veloce

    /**
     * Aggiorna la visualizzazione dei pesi per la macchina corrente
     */
    function updateWeightsDisplay(machineId) {
        const machineNameEl = document.getElementById('current-machine-name');
        const weightCpuEl = document.getElementById('weight-cpu');
        const weightRamEl = document.getElementById('weight-ram');
        const weightIoWaitEl = document.getElementById('weight-io-wait');
        
        if (machineNameEl) {
            machineNameEl.textContent = machineId;
        }
        
        fetch(`/sixsigma/api/weights/${machineId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const weights = data.weights;
                    if (weightCpuEl) weightCpuEl.textContent = `${Math.round(weights.cpu * 100)}%`;
                    if (weightRamEl) weightRamEl.textContent = `${Math.round(weights.ram * 100)}%`;
                    if (weightIoWaitEl) weightIoWaitEl.textContent = `${Math.round(weights.io_wait * 100)}%`;
                } else {
                    console.error('Errore nel caricamento pesi:', data.message);
                    // Valori di default in caso di errore
                    if (weightCpuEl) weightCpuEl.textContent = '40%';
                    if (weightRamEl) weightRamEl.textContent = '35%';
                    if (weightIoWaitEl) weightIoWaitEl.textContent = '25%';
                }
            })
            .catch(error => {
                console.error('Errore nella richiesta pesi:', error);
                // Valori di default in caso di errore
                if (weightCpuEl) weightCpuEl.textContent = '40%';
                if (weightRamEl) weightRamEl.textContent = '35%';
                if (weightIoWaitEl) weightIoWaitEl.textContent = '25%';
            });
    }

    /**
     * Crea o distrugge e ricrea un'istanza di Chart.js in modo sicuro.
     */
    function createChart(canvasId, config) {
        if (charts[canvasId]) {
            charts[canvasId].destroy();
        }
        
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error(`Elemento canvas con ID "${canvasId}" non trovato.`);
            return;
        }
        const ctx = canvas.getContext('2d');
        charts[canvasId] = new Chart(ctx, config);
    }

    // --- Inizializzazione dell'Applicazione ---

    fetch('/sixsigma/api/macchine')
        .then(response => response.json())
        .then(macchine => {
            machineSelector.innerHTML = '';
            macchine.forEach(m => {
                const option = new Option(m, m);
                machineSelector.appendChild(option);
            });
            if (macchine.length > 0) startSimulation(macchine[0]);
        });

    machineSelector.addEventListener('change', (event) => startSimulation(event.target.value));
    pauseButton.addEventListener('click', () => {
        isPaused = !isPaused;
        pauseButton.textContent = isPaused ? 'Riprendi' : 'Pausa';
    });
    
    zoomToggle.addEventListener('change', (event) => {
        isZoomEnabled = event.target.checked;
        if (Object.keys(currentBaselines).length > 0) {
            setupCharts(currentBaselines);
        }
    });

    /**
     * Funzione principale che avvia/riavvia la simulazione per una macchina specifica.
     */
    function startSimulation(machineId) {
        if (simulationInterval) clearInterval(simulationInterval);
        if (timeUpdateInterval) clearInterval(timeUpdateInterval);
        
        activeMachineId = machineId;
        isPaused = false;
        pauseButton.textContent = 'Pausa';
        pauseButton.disabled = false;
        currentOffset = 1; 
        
        // Aggiorna la visualizzazione dei pesi per la macchina selezionata
        updateWeightsDisplay(machineId);
        
        // Reset contatori ricalcolo
        recalculateCounters = {};
        isRecalculating = {};
        pausedCharts = {};  // Reset dei grafici in pausa
        
        // Reset automatico del backend per evitare stati bloccati
        for (const metrica of ['cpu', 'ram', 'io_wait']) {
            fetch(`/sixsigma/api/resume_chart/${machineId}/${metrica}`)
                .catch(err => console.log(`Info: Reset ${metrica} non necessario`));
        }
        
        const scoreSpan = scoreValueEl.querySelector('span') || scoreValueEl;
        scoreSpan.textContent = '--';
        
        // Reset delle classi del performance score
        scoreValueEl.classList.remove('score-excellent', 'score-good', 'score-poor');
        scoreValueEl.classList.add('score-default');
        
        // Pulisci tutti i log separati
        cpuLogEl.innerHTML = '';
        ramLogEl.innerHTML = '';
        ioLogEl.innerHTML = '';
        
        // Reset delle statistiche
        resetTestStatistics();
        
        // Messaggio di chiarimento sui log
        addLogMessage('cpu', `🔍 INIZIO MONITORAGGIO - I log mostrano solo TEST FALLITI`);
        addLogMessage('ram', `🔍 INIZIO MONITORAGGIO - I log mostrano solo TEST FALLITI`);
        addLogMessage('io_wait', `🔍 INIZIO MONITORAGGIO - I log mostrano solo TEST FALLITI`);
        
        addLogMessage('cpu', `Caricamento baseline per ${machineId}...`);
        
        fetch(`/sixsigma/api/baseline/${machineId}`)
            .then(res => res.json())
            .then(baselines => {
                if (machineId !== activeMachineId) return;

                currentBaselines = baselines;
                addLogMessage('general', `Baseline caricata. Avvio monitoraggio...`);
                setupCharts(baselines);
                
                simulationInterval = setInterval(() => {
                    if (!isPaused) {
                        fetchData(machineId);
                    }
                }, 1000);
                
                timeUpdateInterval = setInterval(updateSimulationInfo, 1000);
            }).catch(err => {
                addLogMessage('general', `Errore caricamento baseline per ${machineId}: ${err}`, 'log-anomaly');
            });
    }

    /**
     * 🔄 RICREA SOLO I GRAFICI DI UNA SPECIFICA METRICA
     */
    function setupChartsForMetric(metrica, baseline) {
        const b = baseline;
        if (!b) return;

        // Configurazione Grafico X (Individui)
        let yMin, yMax;
        if (isZoomEnabled) {
            const marginY = Math.max(5, (b.ucl_x - b.lcl_x) * 0.1);
            yMin = Math.max(0, b.lcl_x - marginY);
            yMax = Math.min(100, b.ucl_x + marginY);
        } else {
            yMin = 0;
            yMax = 105;
        }
        
        createChart(`${metrica}Chart`, {
            type: 'line',
            data: { 
                labels: [], 
                datasets: [{ 
                    label: 'Valore', 
                    data: [], 
                    borderColor: '#007bff', 
                    tension: 0.1, 
                    pointRadius: [],
                    pointBackgroundColor: [],
                    pointBorderColor: [],
                    pointBorderWidth: []
                }] 
            },
            options: {
                scales: { y: { min: yMin, max: yMax } },
                plugins: {
                    legend: { display: false },
                    annotation: { annotations: {
                        ucl: { 
                            type: 'line', 
                            yMin: b.ucl_x, 
                            yMax: b.ucl_x, 
                            borderColor: 'rgba(255, 99, 132, 0.8)', 
                            borderWidth: 2, 
                            label: { 
                                content: `UCL=${b.ucl_x}`, 
                                display: true, 
                                position: 'start', 
                                color: 'red', 
                                font: {size: 10} 
                            } 
                        },
                        lcl: { 
                            type: 'line', 
                            yMin: b.lcl_x, 
                            yMax: b.lcl_x, 
                            borderColor: 'rgba(255, 99, 132, 0.8)', 
                            borderWidth: 2, 
                            label: { 
                                content: `LCL=${b.lcl_x}`, 
                                display: true, 
                                position: 'start', 
                                color: 'red', 
                                font: {size: 10} 
                            } 
                        },
                        cl: { 
                            type: 'line', 
                            yMin: b.cl_x, 
                            yMax: b.cl_x, 
                            borderColor: 'rgba(75, 192, 192, 0.8)', 
                            borderWidth: 1, 
                            borderDash: [6, 6], 
                            label: { 
                                content: `CL=${b.cl_x}`, 
                                display: true, 
                                position: 'center', 
                                color: 'green', 
                                font: {size: 10} 
                            } 
                        }
                    }}
                }
            }
        });
        
        // Configurazione Grafico mR (Moving Range)
        createChart(`${metrica}MrChart`, {
            type: 'line',
            data: { 
                labels: [], 
                datasets: [{ 
                    label: 'Moving Range', 
                    data: [], 
                    borderColor: '#6c757d', 
                    tension: 0.1, 
                    pointRadius: [],
                    pointBackgroundColor: [],
                    pointBorderColor: [],
                    pointBorderWidth: []
                }] 
            },
            options: {
                scales: { y: { min: 0 } },
                plugins: {
                    legend: { display: false },
                    annotation: { annotations: {
                        ucl_mr: { 
                            type: 'line', 
                            yMin: b.ucl_mr, 
                            yMax: b.ucl_mr, 
                            borderColor: 'rgba(255, 159, 64, 0.8)', 
                            borderWidth: 2, 
                            label: { 
                                content: `UCL_mR=${b.ucl_mr}`, 
                                display: true, 
                                position: 'start', 
                                color: 'orange', 
                                font: {size: 10} 
                            } 
                        }
                    }}
                }
            }
        });
    }
    /**
     * Configura tutti i grafici con i limiti di controllo corretti.
     */
    function setupCharts(baselines) {
        for (const metrica of ['cpu', 'ram', 'io_wait']) {
            const b = baselines[metrica];
            if (!b) continue;
            setupChartsForMetric(metrica, b);
        }
    }

    /**
     * Funzione chiamata a intervalli per recuperare il prossimo punto dato dal backend.
     */
    function fetchData(machineId) {
        if (machineId !== activeMachineId) {
            return;
        }

        fetch(`/sixsigma/api/data/${machineId}/${currentOffset}`)
            .then(response => response.ok ? response.json() : Promise.reject('Fine dei dati di simulazione.'))
            .then(data => {
                if (machineId === activeMachineId) {
                    updateDashboard(data);
                    currentOffset = data.next_offset;
                }
            })
            .catch(error => {
                if (machineId === activeMachineId) {
                    addLogMessage('general', error.toString(), 'log-anomaly');
                    clearInterval(simulationInterval);
                    pauseButton.disabled = true;
                }
            });
    }

    /**
     * Aggiorna tutti gli elementi della dashboard con i nuovi dati ricevuti.
     */
    function updateDashboard(data) {
        const scoreSpan = scoreValueEl.querySelector('span') || scoreValueEl;
        scoreSpan.textContent = data.p_score.toFixed(3);
        
        // Rimuove tutte le classi di score esistenti
        scoreValueEl.classList.remove('score-excellent', 'score-good', 'score-poor', 'score-default');
        
        // Applica la classe appropriata basata sul valore del performance score
        if (data.p_score > 0.8) {
            scoreValueEl.classList.add('score-excellent');
        } else if (data.p_score > 0.5) {
            scoreValueEl.classList.add('score-good');
        } else {
            scoreValueEl.classList.add('score-poor');
        }
        
        const timestamp = new Date(data.timestamp).toLocaleTimeString('it-IT');
        
        // Incrementa il contatore dei punti analizzati
        pointsAnalyzed += 3;
        updateSimulationInfo();

        for (const metrica of ['cpu', 'ram', 'io_wait']) {
            const chartX = charts[`${metrica}Chart`];
            const chartMr = charts[`${metrica}MrChart`];
            
            if (!chartX || !chartMr) continue;

            const valoreX = data.metrics[`${metrica}_percent`];
            const valoreMr = data.moving_ranges[metrica];
            const stato = data.stati[metrica];
            const testFallito = data.test_falliti[metrica];
            const isPuntoCritico = data.punti_critici[metrica];
            const puntiCoinvolti = data.punti_coinvolti[metrica] || [];

            // Aggiorna le statistiche per ogni metrica
            updateTestStatistics(stato);

            // 🔶 GESTIONE SPECIALE PER GRAFICI IN PAUSA (Test 4/7/8 in ricalcolo)
            if (pausedCharts[metrica]) {
                // Se il grafico è in pausa, continua il conteggio per il ricalcolo
                recalculateCounters[metrica]++;
                
                console.log(`🔍 DEBUG ${metrica}: Counter=${recalculateCounters[metrica]}/${RECALCULATE_WAIT_POINTS}, Paused=${pausedCharts[metrica]}`);
                
                if (recalculateCounters[metrica] >= RECALCULATE_WAIT_POINTS) {
                    addLogMessage(metrica, `[BASELINE] 🔄 Raggiunto limite ${RECALCULATE_WAIT_POINTS} misurazioni - Avvio ricalcolo...`, 'log-baseline');
                    triggerBaselineRecalculation(metrica, timestamp);
                } else {
                    // Log ridotti: solo ogni 10 punti per evitare spam
                    if (recalculateCounters[metrica] % 10 === 0) {
                        const remaining = RECALCULATE_WAIT_POINTS - recalculateCounters[metrica];
                        addLogMessage(metrica, `[BASELINE] ⏳ Raccolta dati... ${remaining} rimanenti`, 'log-baseline');
                    }
                }
                
                // Non aggiornare le statistiche durante la pausa (tranne che per il penalty score che è gestito dal backend)
                continue; // Skip aggiornamento grafico se è in pausa
            }

            // 🔶 GESTIONE INIZIALE PER TEST 4, TEST 7 e TEST 8: PRIMO RILEVAMENTO
            if (testFallito === "Test 4" || testFallito === "Test 7" || testFallito === "Test 8") {
                handleTestWithBaslineRecalc(metrica, testFallito, puntiCoinvolti, timestamp, valoreX, valoreMr);
                continue; // Skip normale aggiornamento grafico
            }

            // � GESTIONE TEST 2 e TEST 3: ALLERTA ZONE (Colorazione Gialla)
            if (testFallito === "Test 2" || testFallito === "Test 3") {
                handleZoneTests(metrica, testFallito, puntiCoinvolti, timestamp, valoreX, valoreMr);
                continue; // Skip normale aggiornamento grafico
            }

            // �🔴 LOGICA DI COLORAZIONE NORMALE (Test 1, mR, Saturazione)
            let pointColorX = '#007bff';  // Blu normale
            let pointColorMr = '#17a2b8'; // Teal normale
            let radiusX = 4, radiusMr = 4;
            let borderWidthX = 1, borderWidthMr = 1;
            
            // Test 1 su Grafico X: Violazione Limite
            if (testFallito === "Test 1") {
                pointColorX = '#ff0000';  // Rosso
                radiusX = 8;
                borderWidthX = 3;
            }
            
            // Test mR su Grafico mR: Alta Variabilità
            if (testFallito === "Test mR") {
                pointColorMr = '#ff0000';  // Rosso
                radiusMr = 8;
                borderWidthMr = 3;
            }
            
            // Test Saturazione: Rosso su entrambi i grafici
            if (testFallito === "Saturazione") {
                pointColorX = '#ff0000';
                radiusX = 8;
                borderWidthX = 3;
            }

            // Aggiorna i grafici con la colorazione specifica
            updateChartSpecific(chartX, timestamp, valoreX, pointColorX, radiusX, borderWidthX);
            updateChartSpecific(chartMr, timestamp, valoreMr, pointColorMr, radiusMr, borderWidthMr);

            // 📝 LOG SOLO PER TEST FALLITI (no "In Controllo")
            if (stato !== "✅ In Controllo") {
                let message = `[${timestamp}] ${stato}`;
                
                if (data.dettagli_anomalie[metrica]) {
                    const dettagli = data.dettagli_anomalie[metrica];
                    message += ` | ${dettagli.descrizione}`;
                    
                    if (dettagli.teoria) {
                        message += ` | TEORIA: ${dettagli.teoria}`;
                    }
                }
                
                addLogMessage(metrica, message, 'log-anomaly');
            }
            // ✅ NON logghiamo più i processi "In Controllo" per ridurre il rumore
        }
    }

    /**
     * Aggiorna un grafico con controllo specifico di colore, raggio e bordo
     */
    function updateChartSpecific(chart, timestamp, value, pointColor, pointRadius, borderWidth) {
        const dataset = chart.data.datasets[0];
        
        // Aggiungi nuovo punto
        chart.data.labels.push(timestamp);
        dataset.data.push(value);
        dataset.pointBackgroundColor.push(pointColor);
        dataset.pointBorderColor.push(pointColor === '#ff0000' ? '#ffffff' : pointColor);
        dataset.pointRadius.push(pointRadius);
        dataset.pointBorderWidth.push(borderWidth);
        
        // Mantieni solo gli ultimi MAX_POINTS_ON_CHART punti
        if (chart.data.labels.length > MAX_POINTS_ON_CHART) {
            chart.data.labels.shift();
            dataset.data.shift();
            dataset.pointBackgroundColor.shift();
            dataset.pointBorderColor.shift();
            dataset.pointRadius.shift();
            dataset.pointBorderWidth.shift();
        }
        
        chart.update('none');
    }

    /**
     * 🔶 GESTIONE PRIMO RILEVAMENTO TEST 4, TEST 7 e TEST 8: Pausa + Colorazione Retroattiva
     */
    function handleTestWithBaslineRecalc(metrica, testFallito, puntiCoinvolti, timestamp, valoreX, valoreMr) {
        const chartX = charts[`${metrica}Chart`];
        const chartMr = charts[`${metrica}MrChart`];
        
        // 🟠 PRIMO RILEVAMENTO: Aggiungi punto corrente e pausa grafico
        
        // Aggiungi il punto corrente normalmente
        updateChartSpecific(chartX, timestamp, valoreX, '#007bff', 4, 1);
        updateChartSpecific(chartMr, timestamp, valoreMr, '#17a2b8', 4, 1);
        
        // 🟠 COLORA RETROATTIVAMENTE I PUNTI COINVOLTI
        applyRetroactiveColoring(chartX, puntiCoinvolti, '#ffa500', 7, 2); // Arancione
        
        // 🛑 PAUSA IL GRAFICO (sia frontend che backend)
        pausedCharts[metrica] = true;
        recalculateCounters[metrica] = 1; // Inizia il conteggio da 1
        
        // Notifica il backend della pausa
        fetch(`/sixsigma/api/pause_chart/${activeMachineId}/${metrica}`)
            .then(response => response.json())
            .then(result => {
                console.log(`✅ Backend notificato pausa per ${metrica}:`, result);
            })
            .catch(err => {
                console.error('❌ Errore pausa chart:', err);
                addLogMessage(metrica, `[ERRORE] Problema comunicazione backend per pausa`, 'log-anomaly');
            });
        
        // Messaggi personalizzati per ogni test basati sulla teoria
        let shiftMessage = '';
        if (testFallito === 'Test 4') {
            shiftMessage = `[${testFallito}] 🟠 RUN RILEVATO - ${puntiCoinvolti.length} punti consecutivi stesso lato | prestazioni processo cambiate`;
        } else if (testFallito === 'Test 7') {
            shiftMessage = `[${testFallito}] 🟠 OSCILLAZIONE RILEVATA - ${puntiCoinvolti.length} punti alternanti | tendenza sistematica non normale`;
        } else if (testFallito === 'Test 8') {
            shiftMessage = `[${testFallito}] 🟠 TREND RILEVATO - ${puntiCoinvolti.length} punti monotoni | causa eccezionale in atto`;
        } else {
            shiftMessage = `[${testFallito}] 🟠 ANOMALIA RILEVATA - ${puntiCoinvolti.length} punti coinvolti | pattern statistico`;
        }
        
        addLogMessage(metrica, shiftMessage, 'log-anomaly');
        addLogMessage(metrica, `[BASELINE] ⏸️ GRAFICO IN PAUSA - Attendo ${RECALCULATE_WAIT_POINTS} misurazioni per ricalcolo baseline...`, 'log-baseline');
        
        console.log(`🔍 DEBUG ${metrica}: PRIMO RILEVAMENTO ${testFallito}, Counter inizializzato a 1/${RECALCULATE_WAIT_POINTS}`);
    }

    /**
     * 🎨 APPLICA COLORAZIONE RETROATTIVA AI PUNTI COINVOLTI
     */
    function applyRetroactiveColoring(chart, relativeIndices, color, radius, borderWidth) {
        const dataset = chart.data.datasets[0];
        const totalPoints = dataset.pointBackgroundColor.length;
        
        relativeIndices.forEach(relativeIndex => {
            const absoluteIndex = totalPoints + relativeIndex; // relativeIndex è negativo
            if (absoluteIndex >= 0 && absoluteIndex < totalPoints) {
                dataset.pointBackgroundColor[absoluteIndex] = color;
                dataset.pointBorderColor[absoluteIndex] = '#ffffff';
                dataset.pointRadius[absoluteIndex] = radius;
                dataset.pointBorderWidth[absoluteIndex] = borderWidth;
            }
        });
        
        chart.update('none');
    }

    /**
     * Gestisce il processo di ricalcolo della baseline
     */
    function handleRecalculateBaseline(data, timestamp) {
        for (const metrica of ['cpu', 'ram', 'io_wait']) {
            // Controlla se c'è un test che richiede ricalcolo baseline
            if (data.warning_levels[metrica] === 'warning' && 
                data.dettagli_anomalie[metrica] && 
                data.dettagli_anomalie[metrica].test_fallito.match(/Test [4578]/)) {
                
                if (!recalculateCounters[metrica]) {
                    recalculateCounters[metrica] = 0;
                    isRecalculating[metrica] = true;  // Inizia subito la pausa
                    addLogMessage(metrica, `[BASELINE] ⏸️ PAUSA VISUALIZZAZIONE - Rilevato ${data.dettagli_anomalie[metrica].test_fallito}. Attendo ${RECALCULATE_WAIT_POINTS} misurazioni per ricalcolo baseline...`, 'log-baseline');
                }
                
                recalculateCounters[metrica]++;
                
                if (recalculateCounters[metrica] >= RECALCULATE_WAIT_POINTS) {
                    triggerBaselineRecalculation(metrica, timestamp);
                } else {
                    const remaining = RECALCULATE_WAIT_POINTS - recalculateCounters[metrica];
                    if (recalculateCounters[metrica] % 5 === 0) {  // Log ogni 5 punti
                        addLogMessage(metrica, `[BASELINE] ⏳ Raccolgo nuovi dati... ${remaining} misurazioni rimanenti`, 'log-baseline');
                    }
                }
            }
        }
    }

    /**
     * Avvia il ricalcolo della baseline per una metrica
     */
    function triggerBaselineRecalculation(metrica, timestamp) {
        addLogMessage(metrica, `[BASELINE] 🔄 Avvio ricalcolo baseline con nuovi dati...`, 'log-baseline');
        console.log(`🔄 Avvio ricalcolo baseline per ${metrica}`);
        
        fetch(`/sixsigma/api/recalculate_baseline/${activeMachineId}/${metrica}`)
            .then(response => {
                console.log(`📡 Response status per ${metrica}:`, response.status);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(result => {
                console.log(`📊 Risultato ricalcolo per ${metrica}:`, result);
                
                if (result.success) {
                    // Aggiorna la baseline corrente
                    currentBaselines[metrica] = result.new_baseline;
                    
                    addLogMessage(metrica, `[BASELINE] ✅ RICALCOLO COMPLETATO - Aggiornamento grafico...`, 'log-success');
                    
                    // 🔄 RICREA SOLO I GRAFICI DELLA METRICA SPECIFICA (non tutti!)
                    setupChartsForMetric(metrica, result.new_baseline);
                    
                    addLogMessage(metrica, `[BASELINE] ✅ NUOVI LIMITI - CL=${result.new_baseline.cl_x.toFixed(1)}, UCL=${result.new_baseline.ucl_x.toFixed(1)}, LCL=${result.new_baseline.lcl_x.toFixed(1)}`, 'log-success');
                    addLogMessage(metrica, `[BASELINE] ▶️ GRAFICO RIATTIVATO - Monitoraggio ripreso`, 'log-success');
                    
                    // 🟢 RIPRISTINA IL GRAFICO (sia frontend che backend)
                    recalculateCounters[metrica] = 0;
                    pausedCharts[metrica] = false;  // Riattiva il grafico
                    
                    // Notifica il backend della riattivazione
                    fetch(`/sixsigma/api/resume_chart/${activeMachineId}/${metrica}`)
                        .then(resumeResponse => resumeResponse.json())
                        .then(resumeResult => {
                            console.log(`✅ Backend notificato resume per ${metrica}:`, resumeResult);
                        })
                        .catch(err => console.error('Errore resume chart:', err));
                        
                } else {
                    addLogMessage(metrica, `[ERRORE] ❌ Fallimento ricalcolo baseline: ${result.message}`, 'log-anomaly');
                    console.error(`❌ Errore ricalcolo ${metrica}:`, result.message);
                    
                    // Riattiva comunque per evitare blocco permanente
                    pausedCharts[metrica] = false;
                    fetch(`/sixsigma/api/resume_chart/${activeMachineId}/${metrica}`)
                        .catch(err => console.error('Errore resume chart dopo fallimento:', err));
                }
            })
            .catch(error => {
                addLogMessage(metrica, `[ERRORE] ❌ Errore comunicazione ricalcolo baseline: ${error.message}`, 'log-anomaly');
                console.error(`❌ Errore fetch ricalcolo ${metrica}:`, error);
                
                // Riattiva comunque per evitare blocco permanente
                pausedCharts[metrica] = false;
                fetch(`/sixsigma/api/resume_chart/${activeMachineId}/${metrica}`)
                    .catch(err => console.error('Errore resume chart dopo errore:', err));
            });
    }

    /**
     * Determina il colore del punto basato sul warning level
     */
    function getPointColor(warningLevel, stato) {
        switch (warningLevel) {
            case 'critical': return 'red';      // Test 1, mR, Saturazione
            case 'warning': return 'orange';    // Test 2-8 (test statistici)
            case 'pending': return 'yellow';    // Pre-allarmi
            default: return 'blue';             // Normale
        }
    }

    /**
     * Applica colorazione retroattiva ai punti precedenti
     */
    function applyRetroactiveColoring(chart, indices, color) {
        const colors = chart.data.datasets[0].pointBackgroundColor;
        const currentLength = colors.length;
        
        indices.forEach(relativeIndex => {
            const absoluteIndex = currentLength + relativeIndex;
            if (absoluteIndex >= 0 && absoluteIndex < currentLength) {
                colors[absoluteIndex] = color;
            }
        });
        
        chart.update('none');
    }

    /**
     * Helper per aggiornare un singolo grafico.
     */
    function updateChart(chart, label, value, pointColor, isTransition = false) {
        chart.data.labels.push(label);
        chart.data.datasets[0].data.push(value);
        
        // Gestisci i colori dei punti
        const pointColors = chart.data.datasets[0].pointBackgroundColor || [];
        const pointBorderColors = chart.data.datasets[0].pointBorderColor || [];
        const pointRadii = chart.data.datasets[0].pointRadius || [];
        const pointBorderWidths = chart.data.datasets[0].pointBorderWidth || [];
        
        // Colore del punto
        pointColors.push(pointColor);
        
        // Stile del punto
        if (pointColor === 'red') {
            pointBorderColors.push('#ffffff');
            pointRadii.push(6);
            pointBorderWidths.push(2);
        } else if (pointColor === 'yellow') {
            pointBorderColors.push('#000000');
            pointRadii.push(5);
            pointBorderWidths.push(2);
        } else {
            pointBorderColors.push('#ffffff');
            pointRadii.push(4);
            pointBorderWidths.push(1);
        }
        
        // Stile linea durante transizione
        if (isTransition) {
            chart.data.datasets[0].borderDash = [5, 5];
        } else {
            chart.data.datasets[0].borderDash = [];
        }
        
        chart.data.datasets[0].pointBackgroundColor = pointColors;
        chart.data.datasets[0].pointBorderColor = pointBorderColors;
        chart.data.datasets[0].pointRadius = pointRadii;
        chart.data.datasets[0].pointBorderWidth = pointBorderWidths;
        
        // Rimuovi i punti più vecchi se superi il limite
        if (chart.data.labels.length > MAX_POINTS_ON_CHART) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
            pointColors.shift();
            pointBorderColors.shift();
            pointRadii.shift();
            pointBorderWidths.shift();
        }
        chart.update('none');
    }
    
    function addLogMessage(metrica, message, className = '') {
        const p = document.createElement('p');
        p.textContent = `> ${message}`;
        if(className) p.className = className;
        
        // Seleziona il log appropriato basato sulla metrica
        let targetLog;
        switch(metrica) {
            case 'cpu':
                targetLog = cpuLogEl;
                break;
            case 'ram':
                targetLog = ramLogEl;
                break;
            case 'io_wait':
                targetLog = ioLogEl;
                break;
            default:
                // Per messaggi generali, aggiungi a tutti i log
                targetLog = cpuLogEl;
                const p2 = p.cloneNode(true);
                const p3 = p.cloneNode(true);
                ramLogEl.prepend(p2);
                ioLogEl.prepend(p3);
                break;
        }
        
        targetLog.prepend(p);
    }
    
    function resetTestStatistics() {
        Object.keys(testStatistics).forEach(key => {
            testStatistics[key] = 0;
        });
        pointsAnalyzed = 0;
        simulationStartTime = new Date();
        updateTestStatisticsDisplay();
        updateSimulationInfo();
    }
    
    function updateTestStatistics(stato) {
        // Contatori per tutti i test implementati
        if (stato.includes('Test 1')) {
            testStatistics.test1++;
        } else if (stato.includes('Test 4')) {
            testStatistics.test4++;
        } else if (stato.includes('Test 7')) {
            testStatistics.test7++;
        } else if (stato.includes('Test 8')) {
            testStatistics.test8++;
        } else if (stato.includes('Test mR')) {
            testStatistics.testmr++;
        } else if (stato.includes('Saturazione')) {
            testStatistics.testsat++;
        } else if (stato === '✅ In Controllo') {
            testStatistics.testok++;
        }
        updateTestStatisticsDisplay();
    }
    
    function updateTestStatisticsDisplay() {
        // Aggiorna solo gli elementi che esistono realmente nell'HTML
        const test1El = document.getElementById('test1-count');
        const test4El = document.getElementById('test4-count');
        const test7El = document.getElementById('test7-count');
        const test8El = document.getElementById('test8-count');
        const testmrEl = document.getElementById('testmr-count');
        const testsatEl = document.getElementById('testsat-count');
        const testokEl = document.getElementById('testok-count');
        
        if (test1El) test1El.textContent = testStatistics.test1;
        if (test4El) test4El.textContent = testStatistics.test4;
        if (test7El) test7El.textContent = testStatistics.test7;
        if (test8El) test8El.textContent = testStatistics.test8;
        if (testmrEl) testmrEl.textContent = testStatistics.testmr;
        if (testsatEl) testsatEl.textContent = testStatistics.testsat;
        if (testokEl) testokEl.textContent = testStatistics.testok;
        
        // Non tentiamo di aggiornare gli elementi non implementati per evitare errori
    }
    
    function updateSimulationInfo() {
        document.getElementById('points-analyzed').textContent = pointsAnalyzed;
        
        if (simulationStartTime) {
            const elapsed = Math.floor((new Date() - simulationStartTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            document.getElementById('simulation-time').textContent = 
                `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
    }
    
    function getTestType(stato) {
        if (stato.includes('Test 1')) return '[SPC-1]';
        if (stato.includes('Test 2')) return '[SPC-2]';
        if (stato.includes('Test 3')) return '[SPC-3]';
        if (stato.includes('Test 4')) return '[SPC-4]';
        if (stato.includes('Test 5')) return '[SPC-5]';
        if (stato.includes('Test 6')) return '[SPC-6]';
        if (stato.includes('Test 7')) return '[SPC-7]';
        if (stato.includes('Test 8')) return '[SPC-8]';
        if (stato.includes('Alta Variabilità')) return '[mR]';
        if (stato.includes('Saturazione')) return '[SAT]';
        return '';
    }
    
    // 🔧 FUNZIONE DEBUG: Sblocca tutti i grafici in pausa
    window.unlockAllCharts = function() {
        console.log('🔧 DEBUG: Sblocco forzato di tutti i grafici');
        
        for (const metrica of ['cpu', 'ram', 'io_wait']) {
            if (pausedCharts[metrica]) {
                console.log(`🔓 Sblocco grafico ${metrica}`);
                
                pausedCharts[metrica] = false;
                recalculateCounters[metrica] = 0;
                
                // Notifica il backend
                fetch(`/sixsigma/api/resume_chart/${activeMachineId}/${metrica}`)
                    .then(response => response.json())
                    .then(result => {
                        console.log(`✅ Backend notificato resume per ${metrica}:`, result);
                        addLogMessage(metrica, `[DEBUG] 🔓 SBLOCCO MANUALE - Grafico riattivato`, 'log-success');
                    })
                    .catch(err => {
                        console.error('Errore sblocco chart:', err);
                        addLogMessage(metrica, `[DEBUG] ❌ Errore sblocco manuale`, 'log-anomaly');
                    });
            }
        }
        
        // Ricarica solo i grafici necessari
        if (Object.keys(currentBaselines).length > 0) {
            setupCharts(currentBaselines);
            addLogMessage('cpu', `[DEBUG] 🔄 Grafici ricaricati dopo sblocco manuale`, 'log-success');
        }
    };

    /**
     * 🟡 GESTIONE TEST ZONE (Test 2 e Test 3): Colorazione Gialla sui punti coinvolti
     * 
     * @param {string} metrica - Nome della metrica
     * @param {string} testName - Nome del test fallito ("Test 2" o "Test 3")
     * @param {Array} puntiCoinvolti - Indici relativi dei punti coinvolti
     * @param {string} timestamp - Timestamp corrente
     * @param {number} valoreX - Valore X corrente
     * @param {number} valoreMr - Valore mR corrente
     */
    function handleZoneTests(metrica, testName, puntiCoinvolti, timestamp, valoreX, valoreMr) {
        console.log(`🟡 Zone Test rilevato: ${testName} per ${metrica}`);
        
        const chartX = charts[`${metrica}Chart`];
        const chartMr = charts[`${metrica}MrChart`];
        
        if (!chartX || !chartMr) return;

        // Aggiungi il punto corrente ai grafici con colore normale
        updateChartSpecific(chartX, timestamp, valoreX, '#007bff', 4, 1);  // Blu normale
        updateChartSpecific(chartMr, timestamp, valoreMr, '#17a2b8', 4, 1); // Teal normale

        // Applica colorazione gialla retroattiva sui punti coinvolti
        applyRetroactiveColoring(chartX, puntiCoinvolti, '#ffff99'); // Giallo chiaro
        
        // Log del rilevamento
        addLogMessage(metrica, 
            `[${testName}] 🟡 Allerta Zone: ${puntiCoinvolti.length} punti coinvolti`, 
            'log-warning'
        );
        
        chartX.update('none');
        chartMr.update('none');
    }
});
