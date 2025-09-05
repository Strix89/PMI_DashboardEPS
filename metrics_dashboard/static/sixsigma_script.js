document.addEventListener('DOMContentLoaded', () => {
    // Riferimenti agli elementi HTML principali
    const machineSelector = document.getElementById('machine-selector');
    const scoreValueEl = document.getElementById('score-value');
    const anomalyLogEl = document.getElementById('anomaly-log');
    const pauseButton = document.getElementById('pause-button');
    const zoomToggle = document.getElementById('zoom-toggle');

    let simulationInterval = null;
    let timeUpdateInterval = null;
    let currentOffset = 1;
    let isPaused = false;
    let isZoomEnabled = true;
    const MAX_POINTS_ON_CHART = 40;
    const charts = {};
    let currentBaselines = {};
    
    // Contatori per le statistiche dei test
    let testStatistics = {
        test1: 0,    // Violazione Limite
        test2: 0,    // Zona A
        test3: 0,    // Zona B  
        test4: 0,    // Run Test
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

    // CORREZIONE: Variabile per tenere traccia della simulazione attualmente attiva
    let activeMachineId = null;

    /**
     * Crea o distrugge e ricrea un'istanza di Chart.js in modo sicuro.
     * @param {string} canvasId - L'ID dell'elemento <canvas>.
     * @param {object} config - La configurazione per il nuovo grafico.
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
     * @param {string} machineId - L'ID della macchina da monitorare.
     */
    function startSimulation(machineId) {
        if (simulationInterval) clearInterval(simulationInterval);
        if (timeUpdateInterval) clearInterval(timeUpdateInterval);
        
        // CORREZIONE: Imposta la macchina corrente come attiva
        activeMachineId = machineId;

        isPaused = false;
        pauseButton.textContent = 'Pausa';
        pauseButton.disabled = false;
        currentOffset = 1; 
        
        const scoreSpan = scoreValueEl.querySelector('span') || scoreValueEl;
        scoreSpan.textContent = '--';
        
        // Reset delle classi del performance score
        scoreValueEl.classList.remove('score-excellent', 'score-good', 'score-poor');
        scoreValueEl.classList.add('score-default');
        
        anomalyLogEl.innerHTML = '';
        
        // Reset delle statistiche
        resetTestStatistics();
        
        addLogMessage(`Caricamento baseline per ${machineId}...`);
        
        fetch(`/sixsigma/api/baseline/${machineId}`)
            .then(res => res.json())
            .then(baselines => {
                // CORREZIONE: Controlla se siamo ancora sulla stessa macchina prima di procedere
                if (machineId !== activeMachineId) return;

                currentBaselines = baselines; // Salva le baseline per il toggle zoom
                addLogMessage(`Baseline caricata. Avvio monitoraggio...`);
                setupCharts(baselines);
                
                simulationInterval = setInterval(() => {
                    if (!isPaused) {
                        fetchData(machineId);
                    }
                }, 1000);
                
                // Avvia il timer per aggiornare il tempo di simulazione
                timeUpdateInterval = setInterval(updateSimulationInfo, 1000);
            }).catch(err => {
                addLogMessage(`Errore caricamento baseline per ${machineId}: ${err}`, 'log-anomaly');
            });
    }

    /**
     * Configura tutti e 6 i grafici con i limiti di controllo corretti presi dalla baseline.
     * @param {object} baselines - L'oggetto contenente i parametri CL, UCL, LCL per ogni metrica.
     */
    function setupCharts(baselines) {
        for (const metrica of ['cpu', 'ram', 'io_wait']) {
            const b = baselines[metrica];
            if (!b) continue; // Salta se la baseline per una metrica non è disponibile

            // Configurazione Grafico X (Individui)
            let yMin, yMax;
            if (isZoomEnabled) {
                const marginY = Math.max(5, (b.ucl_x - b.lcl_x) * 0.1); // Margine del 10% o minimo 5
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
                            ucl: { type: 'line', yMin: b.ucl_x, yMax: b.ucl_x, borderColor: 'rgba(255, 99, 132, 0.8)', borderWidth: 2, label: { content: `UCL=${b.ucl_x}`, display: true, position: 'start', color: 'red', font: {size: 10} } },
                            lcl: { type: 'line', yMin: b.lcl_x, yMax: b.lcl_x, borderColor: 'rgba(255, 99, 132, 0.8)', borderWidth: 2, label: { content: `LCL=${b.lcl_x}`, display: true, position: 'start', color: 'red', font: {size: 10} } },
                            cl: { type: 'line', yMin: b.cl_x, yMax: b.cl_x, borderColor: 'rgba(75, 192, 192, 0.8)', borderWidth: 1, borderDash: [6, 6], label: { content: `CL=${b.cl_x}`, display: true, position: 'center', color: 'green', font: {size: 10} } }
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
                            ucl_mr: { type: 'line', yMin: b.ucl_mr, yMax: b.ucl_mr, borderColor: 'rgba(255, 159, 64, 0.8)', borderWidth: 2, label: { content: `UCL_mR=${b.ucl_mr}`, display: true, position: 'start', color: 'orange', font: {size: 10} } }
                        }}
                    }
                }
            });
        }
    }

    /**
     * Funzione chiamata a intervalli per recuperare il prossimo punto dato dal backend.
     * @param {string} machineId - L'ID della macchina corrente.
     */
    function fetchData(machineId) {
        // CORREZIONE: Se l'utente ha cambiato macchina, non fare nulla.
        if (machineId !== activeMachineId) {
            return;
        }

        fetch(`/sixsigma/api/data/${machineId}/${currentOffset}`)
            .then(response => response.ok ? response.json() : Promise.reject('Fine dei dati di simulazione.'))
            .then(data => {
                // CORREZIONE: Controlla di nuovo prima di aggiornare la UI
                if (machineId === activeMachineId) {
                    updateDashboard(data);
                    currentOffset = data.next_offset;
                }
            })
            .catch(error => {
                if (machineId === activeMachineId) {
                    addLogMessage(error.toString(), 'log-anomaly');
                    clearInterval(simulationInterval);
                    pauseButton.disabled = true;
                }
            });
    }

    /**
     * Aggiorna tutti gli elementi della dashboard con i nuovi dati ricevuti.
     * @param {object} data - L'oggetto JSON restituito dall'API.
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
        
        // Incrementa il contatore dei punti analizzati (3 metriche per punto temporale)
        pointsAnalyzed += 3;
        updateSimulationInfo();

        for (const metrica of ['cpu', 'ram', 'io_wait']) {
            const chartX = charts[`${metrica}Chart`];
            const chartMr = charts[`${metrica}MrChart`];
            // CORREZIONE: Se i grafici non sono ancora pronti, non fare nulla
            if (!chartX || !chartMr) continue;

            const valoreX = data.metrics[`${metrica}_percent`];
            const valoreMr = data.moving_ranges[metrica];
            const stato = data.stati[metrica];

            // Aggiorna le statistiche per ogni metrica
            updateTestStatistics(stato);

            // Determina se il punto ha anomalie (qualsiasi stato diverso da "In Controllo")
            const hasAnomaly = stato !== 'In Controllo';
            const hasVariabilityAnomaly = stato.includes('Alta Variabilità');

            updateChart(chartX, timestamp, valoreX, hasAnomaly);
            updateChart(chartMr, timestamp, valoreMr, hasVariabilityAnomaly);

            if (stato !== 'In Controllo') {
                const testType = getTestType(stato);
                const message = `[${timestamp}] ${machineSelector.value} -> ${metrica.toUpperCase()} - ${stato} (Val: ${valoreX}%) ${testType}`;
                addLogMessage(message, 'log-anomaly');
            }
        }
    }

    /**
     * Helper per aggiornare un singolo grafico.
     * @param {Chart} chart - L'istanza di Chart.js da aggiornare.
     */
    function updateChart(chart, label, value, isAnomaly) {
        chart.data.labels.push(label);
        chart.data.datasets[0].data.push(value);
        
        // Gestisci i colori dei punti
        const pointColors = chart.data.datasets[0].pointBackgroundColor || [];
        const pointBorderColors = chart.data.datasets[0].pointBorderColor || [];
        const pointRadii = chart.data.datasets[0].pointRadius || [];
        const pointBorderWidths = chart.data.datasets[0].pointBorderWidth || [];
        
        if (isAnomaly) {
            pointColors.push('#dc3545');           // Rosso per anomalie
            pointBorderColors.push('#ffffff');     // Bordo bianco per contrasto
            pointRadii.push(6);                    // Punto più grande
            pointBorderWidths.push(2);             // Bordo più spesso
        } else {
            pointColors.push(chart.data.datasets[0].borderColor);
            pointBorderColors.push('#ffffff');
            pointRadii.push(4);                    // Dimensione normale
            pointBorderWidths.push(1);             // Bordo normale
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
    
    function addLogMessage(message, className = '') {
        const p = document.createElement('p');
        p.textContent = `> ${message}`;
        if(className) p.className = className;
        anomalyLogEl.prepend(p);
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
        if (stato.includes('Violazione Limite')) {
            testStatistics.test1++;
        } else if (stato.includes('Zona A')) {
            testStatistics.test2++;
        } else if (stato.includes('Zona B')) {
            testStatistics.test3++;
        } else if (stato.includes('Run Test')) {
            testStatistics.test4++;
        } else if (stato.includes('Stratificazione')) {
            testStatistics.test6++;
        } else if (stato.includes('Oscillatorio')) {
            testStatistics.test7++;
        } else if (stato.includes('Trend Lineare')) {
            testStatistics.test8++;
        } else if (stato.includes('Alta Variabilità')) {
            testStatistics.testmr++;
        } else if (stato.includes('Saturazione')) {
            testStatistics.testsat++;
        } else if (stato === 'In Controllo') {
            testStatistics.testok++;
        }
        updateTestStatisticsDisplay();
    }
    
    function updateTestStatisticsDisplay() {
        document.getElementById('test1-count').textContent = testStatistics.test1;
        document.getElementById('test2-count').textContent = testStatistics.test2;
        document.getElementById('test3-count').textContent = testStatistics.test3;
        document.getElementById('test4-count').textContent = testStatistics.test4;
        document.getElementById('test6-count').textContent = testStatistics.test6;
        document.getElementById('test7-count').textContent = testStatistics.test7;
        document.getElementById('test8-count').textContent = testStatistics.test8;
        document.getElementById('testmr-count').textContent = testStatistics.testmr;
        document.getElementById('testsat-count').textContent = testStatistics.testsat;
        document.getElementById('testok-count').textContent = testStatistics.testok;
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
        if (stato.includes('Violazione Limite')) return '[SPC-1]';
        if (stato.includes('Zona A')) return '[SPC-2]';
        if (stato.includes('Zona B')) return '[SPC-3]';
        if (stato.includes('Run Test')) return '[SPC-4]';
        if (stato.includes('Stratificazione')) return '[SPC-6]';
        if (stato.includes('Oscillatorio')) return '[SPC-7]';
        if (stato.includes('Trend Lineare')) return '[SPC-8]';
        if (stato.includes('Alta Variabilità')) return '[mR]';
        if (stato.includes('Saturazione')) return '[SAT]';
        return '';
    }

    /**
     * Carica e aggiorna le statistiche dei test di stabilità.
     * @param {string} machineId - L'ID della macchina corrente.
     */
});
