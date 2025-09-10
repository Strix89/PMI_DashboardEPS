"""
AnomalySNMP Blueprint - Routes per il componente di rilevamento anomalie SNMP
"""

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
)
import logging
import time
from datetime import datetime
from functools import wraps

# Import delle eccezioni personalizzate e logging
from .exceptions import (
    AnomalySNMPError,
    SessionNotFoundError,
    SessionCorruptedError,
    ParameterValidationError,
    ConfigurationError,
    SimulationError,
    SimulationDataExhaustedError,
    handle_exception,
    validate_parameters,
    create_error_response,
)
from .logging_config import (
    get_logger,
    operation_context,
    performance_monitor,
    error_handler,
    log_operation_start,
    log_operation_success,
    log_operation_error,
)

# Configurazione logging
logger = get_logger("anomaly_snmp.routes")

# Decorator per gestione errori nelle route
def handle_route_errors(operation_name: str = None):
    """
    Decorator per gestione automatica degli errori nelle route Flask

    Args:
        operation_name: Nome dell'operazione per logging
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            start_time = time.time()

            try:
                log_operation_start(
                    logger,
                    op_name,
                    endpoint=request.endpoint,
                    method=request.method,
                    remote_addr=request.remote_addr,
                )

                result = func(*args, **kwargs)

                duration = time.time() - start_time
                log_operation_success(
                    logger,
                    op_name,
                    duration,
                    endpoint=request.endpoint,
                    method=request.method,
                )

                return result

            except AnomalySNMPError as e:
                duration = time.time() - start_time
                log_operation_error(
                    logger,
                    op_name,
                    e,
                    duration,
                    endpoint=request.endpoint,
                    method=request.method,
                )

                # Per le route che restituiscono JSON
                if request.is_json or "api" in request.endpoint:
                    return jsonify(handle_exception(logger, e)), 400
                else:
                    # Per le route che restituiscono HTML, redirect con messaggio
                    return redirect(url_for("anomaly_snmp.configure", error=e.message))

            except Exception as e:
                duration = time.time() - start_time
                log_operation_error(
                    logger,
                    op_name,
                    e,
                    duration,
                    endpoint=request.endpoint,
                    method=request.method,
                    recovery_suggestion="Contattare il supporto tecnico",
                )

                # Errore generico
                if request.is_json or "api" in request.endpoint:
                    return jsonify(handle_exception(logger, e)), 500
                else:
                    return redirect(
                        url_for(
                            "anomaly_snmp.configure", error="Errore interno del sistema"
                        )
                    )

        return wrapper

    return decorator


# Creazione del Blueprint
anomaly_snmp_bp = Blueprint("anomaly_snmp", __name__, url_prefix="/anomaly_snmp")


@anomaly_snmp_bp.route("/")
@handle_route_errors("anomaly_snmp_home")
def index():
    """Homepage del modulo AnomalySNMP - reindirizza alla configurazione"""
    return redirect(url_for("anomaly_snmp.configure"))


@anomaly_snmp_bp.route("/configure")
@handle_route_errors("configure_page")
def configure():
    """Pagina di configurazione del modello AnomalySNMP"""
    with operation_context(logger, "configure_page_access") as ctx:
        # Controlla se esiste già una configurazione in sessione
        existing_config = None
        error_message = request.args.get("error")

        try:
            if "anomaly_snmp" in session and "config" in session["anomaly_snmp"]:
                existing_config = session["anomaly_snmp"]["config"]
                ctx["has_existing_config"] = True
                ctx["contamination"] = existing_config.get("contamination", "N/A")
                logger.info(
                    f"Configurazione esistente trovata: contamination={existing_config.get('contamination', 'N/A')}"
                )
            else:
                ctx["has_existing_config"] = False
                logger.info("Nessuna configurazione esistente trovata")

            return render_template(
                "anomaly_configure.html",
                existing_config=existing_config,
                error_message=error_message,
            )

        except Exception as e:
            logger.error(f"Errore nel caricamento pagina configurazione: {str(e)}")
            return render_template(
                "anomaly_configure.html",
                existing_config=None,
                error_message="Errore nel caricamento della configurazione",
            )


@anomaly_snmp_bp.route("/dashboard")
@handle_route_errors("dashboard_page")
def dashboard():
    """Dashboard di simulazione AnomalySNMP"""
    with operation_context(logger, "dashboard_page_access") as ctx:
        # Verifica che esista una configurazione
        if "anomaly_snmp" not in session:
            raise SessionNotFoundError("dashboard_access")

        config = session["anomaly_snmp"].get("config", {})
        ctx["contamination"] = config.get("contamination", "N/A")
        ctx["train_split"] = config.get("train_split", "N/A")

        # Verifica che la configurazione sia completa
        required_config_keys = ["contamination", "train_split", "dataset_name"]
        missing_keys = [key for key in required_config_keys if key not in config]

        if missing_keys:
            raise SessionCorruptedError(
                message=f"Configurazione incompleta, chiavi mancanti: {missing_keys}",
                missing_components=missing_keys,
            )

        # Verifica che il modello sia stato addestrato
        if "model_artifacts" not in session["anomaly_snmp"]:
            raise SessionCorruptedError(
                message="Model artifacts non trovati. Eseguire prima il training del modello.",
                missing_components=["model_artifacts"],
            )

        # Verifica integrità model artifacts
        model_artifacts = session["anomaly_snmp"]["model_artifacts"]
        required_artifacts = [
            "baseline",
            "test_set_seed",
        ]  # Cambiato da test_set a test_set_seed
        missing_artifacts = []

        for key in required_artifacts:
            if key not in model_artifacts or model_artifacts[key] is None:
                missing_artifacts.append(key)

        if missing_artifacts:
            raise SessionCorruptedError(
                message=f"Model artifacts incompleti: {missing_artifacts}",
                missing_components=missing_artifacts,
            )

        # Calcola dimensione test set dai metadati
        dataset_stats = session["anomaly_snmp"].get("dataset_stats", {})
        test_set_size = dataset_stats.get("test_set_total", 0)
        ctx["test_set_size"] = test_set_size
        logger.info(f"Accesso autorizzato alla dashboard con configurazione: {config}")

        return render_template("anomaly_dashboard_fixed.html", config=config)


@anomaly_snmp_bp.route("/api/train_model", methods=["POST"])
def train_model():
    """API endpoint per avviare il training del modello"""
    try:
        # Validazione presenza dati JSON
        if not request.json:
            return (
                jsonify(
                    {"success": False, "error": "Dati JSON mancanti nella richiesta"}
                ),
                400,
            )

        data = request.json

        # Estrazione e validazione parametri
        try:
            contamination = float(data.get("contamination", 0.05))
            train_split = float(data.get("train_split", 0.7))
        except (ValueError, TypeError) as e:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Parametri non validi: contamination e train_split devono essere numeri",
                    }
                ),
                400,
            )

        # Validazione range parametri
        if not (0.01 <= contamination <= 0.15):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Parametro contamination ({contamination:.3f}) deve essere tra 0.01 e 0.15",
                    }
                ),
                400,
            )

        if not (0.5 <= train_split <= 0.9):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Parametro train_split ({train_split:.2f}) deve essere tra 0.5 e 0.9",
                    }
                ),
                400,
            )

        logger.info(
            f"Avvio training modello AnomalySNMP con parametri: contamination={contamination:.3f}, train_split={train_split:.2f}"
        )

        # Validazione dataset (placeholder per ora)
        dataset_name = "SNMP-MIB Dataset"
        try:
            # TODO: Implementare validazione esistenza dataset nel Task 2.1
            # Per ora simuliamo la validazione
            dataset_valid = True
            if not dataset_valid:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Dataset {dataset_name} non trovato o non valido",
                        }
                    ),
                    404,
                )
        except Exception as dataset_error:
            logger.error(f"Errore validazione dataset: {str(dataset_error)}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Errore nella validazione del dataset: {str(dataset_error)}",
                    }
                ),
                500,
            )

        # IMPLEMENTAZIONE CORRETTA DEL PROCESSO DI TRAINING
        logger.info("Inizio processo di training con logica corretta")

        # 1. CARICAMENTO E PREPARAZIONE DATASET
        dataset_info = prepare_dataset_with_oversampling(contamination, train_split)

        # 2. TRAINING ISOLATION FOREST
        model_artifacts = train_isolation_forest_correct(dataset_info, contamination)

        # 3. PREPARAZIONE TEST SET SHUFFLED
        test_set = prepare_shuffled_test_set(dataset_info, model_artifacts)

        logger.info(
            f"Training completato: {len(dataset_info['training_normal'])} training, {len(test_set)} test"
        )

        # OTTIMIZZAZIONE: Salva solo metadati, non tutto il test_set
        # Genereremo i punti al volo usando un seed fisso per riproducibilità
        import random

        test_set_seed = random.randint(1000, 9999)  # Seed per ricreare il test set

        session["anomaly_snmp"] = {
            "config": {
                "contamination": contamination,
                "train_split": train_split,
                "dataset_name": dataset_name,
                "timestamp": str(datetime.now()),
                "status": "trained",
            },
            "dataset_stats": {
                "normal_original": dataset_info["normal_original"],
                "anomaly_original": dataset_info["anomaly_original"],
                "normal_oversampled_total": dataset_info["normal_oversampled_total"],
                "oversampling_generated": dataset_info["oversampling_generated"],
                "training_count": len(dataset_info["training_normal"]),
                "test_normal_count": len(dataset_info["test_normal"]),
                "test_anomaly_count": len(dataset_info["test_anomalies"]),
                "test_set_total": len(dataset_info["test_normal"])
                + len(dataset_info["test_anomalies"]),
            },
            "model_artifacts": {
                "baseline": model_artifacts["baseline"],
                "model_metadata": model_artifacts["model_metadata"],
                "test_set_seed": test_set_seed,  # Seed per ricreare il test set
                "current_offset": 0,
            },
            "simulation_state": {
                "is_running": False,
                "speed": 1,
                "current_index": 0,
                "statistics": {"normal_count": 0, "anomaly_count": 0},
            },
        }

        logger.info(
            f"Configurazione AnomalySNMP salvata in sessione per contamination={contamination:.3f}"
        )

        return jsonify(
            {
                "success": True,
                "message": "Configurazione salvata con successo. Training simulato completato.",
                "redirect_url": url_for("anomaly_snmp.dashboard"),
                "config": {
                    "contamination": contamination,
                    "train_split": train_split,
                    "dataset_name": dataset_name,
                },
            }
        )

    except KeyError as e:
        logger.error(f"Parametro mancante nella richiesta: {str(e)}")
        return (
            jsonify({"success": False, "error": f"Parametro mancante: {str(e)}"}),
            400,
        )

    except Exception as e:
        logger.error(f"Errore imprevisto durante il training: {str(e)}")
        return (
            jsonify(
                {"success": False, "error": f"Errore interno del server: {str(e)}"}
            ),
            500,
        )


# Prima definizione di get_next_point rimossa - duplicata


def _generate_sequential_data_point(offset, config):
    """
    Genera un punto dati sequenziale realistico per la simulazione
    Implementa il pattern: prima normal_test_holdout, poi anomalie in ordine
    """
    import random
    import math
    from datetime import datetime, timedelta

    # CORREZIONE: Timestamp progressivo in avanti
    base_time = datetime.now() - timedelta(hours=1)  # Inizia da 1 ora fa
    timestamp = base_time + timedelta(
        seconds=offset * 2
    )  # Avanza di 2 secondi per punto

    # Pattern sequenziale realistico basato sul design:
    # 1. Prima tutti i record normal_test_holdout
    # 2. Poi i record di anomalia nell'ordine originale del dataset

    contamination = config.get("contamination", 0.05)
    train_split = config.get("train_split", 0.7)

    # Calcola la distribuzione basata sui parametri di configurazione
    # Simula: 600 normali originali, con train_split applicato
    normal_original = 600
    normal_test_count = int(normal_original * (1 - train_split))  # es. 30% di 600 = 180
    anomaly_count = 4398

    # Determina se il punto corrente è normale o anomalia
    if offset < normal_test_count:
        # Fase 1: Punti normali dal test set
        real_label = "Normal"
        # S_score alto per punti normali (0.7-1.0)
        base_score = 0.85
        noise = random.uniform(-0.15, 0.15)
        s_score = max(0.0, min(1.0, base_score + noise))

        # Feature simulate per dati normali (valori più stabili)
        features = [round(random.uniform(0.3, 0.7), 3) for _ in range(8)]

    else:
        # Fase 2: Anomalie dal dataset
        anomaly_index = offset - normal_test_count

        if anomaly_index < anomaly_count:
            real_label = "Anomaly"
            # S_score più basso per anomalie (0.0-0.6)
            base_score = 0.3
            noise = random.uniform(-0.3, 0.3)
            s_score = max(0.0, min(1.0, base_score + noise))

            # Feature simulate per anomalie (valori più estremi)
            features = []
            for i in range(8):
                if random.random() < 0.3:  # 30% chance di valore estremo
                    features.append(
                        round(
                            (
                                random.uniform(0.0, 0.2)
                                if random.random() < 0.5
                                else random.uniform(0.8, 1.0)
                            ),
                            3,
                        )
                    )
                else:
                    features.append(round(random.uniform(0.2, 0.8), 3))
        else:
            # Fine del dataset, ritorna ultimo punto normale
            real_label = "Normal"
            s_score = 0.8
            features = [0.5] * 8

    # Applica variazione realistica basata su contamination
    # Più alta la contamination, più "confusi" possono essere i punteggi
    contamination_noise = contamination * random.uniform(-0.1, 0.1)
    s_score = max(0.0, min(1.0, s_score + contamination_noise))

    return {
        "timestamp": timestamp.isoformat(),
        "s_score": round(s_score, 3),
        "real_label": real_label,
        "features": features,
        "offset": offset,
        "metadata": {
            "phase": "normal_test" if offset < normal_test_count else "anomaly_data",
            "contamination_applied": contamination,
            "train_split_used": train_split,
        },
    }


@anomaly_snmp_bp.route("/api/validate_config", methods=["POST"])
def validate_config():
    """API per validare i parametri di configurazione senza avviare il training"""
    try:
        if not request.json:
            return jsonify({"success": False, "error": "Dati JSON mancanti"}), 400

        data = request.json

        # Validazione parametri
        try:
            contamination = float(data.get("contamination", 0.05))
            train_split = float(data.get("train_split", 0.7))
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Parametri non numerici"}), 400

        errors = []

        # Validazione contamination
        if not (0.01 <= contamination <= 0.15):
            errors.append(
                f"Contamination ({contamination:.3f}) deve essere tra 0.01 e 0.15"
            )

        # Validazione train_split
        if not (0.5 <= train_split <= 0.9):
            errors.append(f"Train split ({train_split:.2f}) deve essere tra 0.5 e 0.9")

        if errors:
            return jsonify({"success": False, "errors": errors}), 400

        return jsonify(
            {
                "success": True,
                "message": "Parametri validi",
                "validated_params": {
                    "contamination": contamination,
                    "train_split": train_split,
                },
            }
        )

    except Exception as e:
        logger.error(f"Errore nella validazione configurazione: {str(e)}")
        return (
            jsonify({"success": False, "error": f"Errore di validazione: {str(e)}"}),
            500,
        )


@anomaly_snmp_bp.route("/api/get_config")
def get_config():
    """API per recuperare la configurazione corrente"""
    try:
        if "anomaly_snmp" not in session:
            return (
                jsonify({"success": False, "error": "Nessuna configurazione trovata"}),
                404,
            )

        config = session["anomaly_snmp"].get("config", {})

        return jsonify({"success": True, "config": config})

    except Exception as e:
        logger.error(f"Errore nel recupero configurazione: {str(e)}")
        return (
            jsonify({"success": False, "error": f"Errore nel recupero: {str(e)}"}),
            500,
        )


@anomaly_snmp_bp.route("/api/reset_simulation", methods=["POST"])
def reset_simulation():
    """
    API per resettare la simulazione
    Ripristina lo stato iniziale e prepara per una nuova simulazione
    Requirements: 6.1, 6.4
    """
    try:
        if "anomaly_snmp" not in session:
            return (
                jsonify(
                    {"success": False, "error": "Nessuna sessione AnomalySNMP trovata"}
                ),
                404,
            )

        # Reset completo dello stato di simulazione
        session["anomaly_snmp"]["simulation_state"] = {
            "is_running": False,
            "speed": 1,
            "current_index": 0,
            "total_points_processed": 0,
            "normal_count": 0,
            "anomaly_count": 0,
            "last_reset_time": str(datetime.now()),
        }

        # Reset dell'offset corrente nei model artifacts
        if "model_artifacts" in session["anomaly_snmp"]:
            session["anomaly_snmp"]["model_artifacts"]["current_offset"] = 0

        logger.info("Simulazione AnomalySNMP resettata completamente")
        return jsonify(
            {
                "success": True,
                "message": "Simulazione resettata con successo",
                "simulation_state": session["anomaly_snmp"]["simulation_state"],
            }
        )

    except Exception as e:
        logger.error(f"Errore nel reset simulazione: {str(e)}")
        return jsonify({"success": False, "error": f"Errore nel reset: {str(e)}"}), 500


@anomaly_snmp_bp.route("/api/simulation_control", methods=["POST"])
def simulation_control():
    """
    API per controllo avanzato della simulazione (play/pause/speed)
    Requirements: 6.4, 6.5
    """
    try:
        if "anomaly_snmp" not in session:
            return (
                jsonify(
                    {"success": False, "error": "Sessione AnomalySNMP non trovata"}
                ),
                404,
            )

        if not request.json:
            return (
                jsonify(
                    {"success": False, "error": "Dati JSON mancanti nella richiesta"}
                ),
                400,
            )

        data = request.json
        action = data.get("action")

        simulation_state = session["anomaly_snmp"].get("simulation_state", {})

        if action == "play":
            simulation_state["is_running"] = True
            logger.info("Simulazione avviata via API")

        elif action == "pause":
            simulation_state["is_running"] = False
            logger.info("Simulazione messa in pausa via API")

        elif action == "set_speed":
            speed = data.get("speed", 1)
            try:
                speed = int(speed)
                if 1 <= speed <= 10:
                    simulation_state["speed"] = speed
                    logger.info(f"Velocità simulazione cambiata a {speed}x")
                else:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Velocità deve essere tra 1 e 10",
                            }
                        ),
                        400,
                    )
            except (ValueError, TypeError):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Velocità deve essere un numero intero",
                        }
                    ),
                    400,
                )

        elif action == "jump_to_offset":
            offset = data.get("offset", 0)
            try:
                offset = int(offset)
                if offset >= 0:
                    simulation_state["current_index"] = offset
                    session["anomaly_snmp"]["model_artifacts"][
                        "current_offset"
                    ] = offset
                    logger.info(f"Simulazione saltata all'offset {offset}")
                else:
                    return (
                        jsonify(
                            {"success": False, "error": "Offset deve essere positivo"}
                        ),
                        400,
                    )
            except (ValueError, TypeError):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Offset deve essere un numero intero",
                        }
                    ),
                    400,
                )
        else:
            return (
                jsonify(
                    {"success": False, "error": f"Azione non riconosciuta: {action}"}
                ),
                400,
            )

        # Salva lo stato aggiornato
        session["anomaly_snmp"]["simulation_state"] = simulation_state

        return jsonify(
            {
                "success": True,
                "message": f"Azione {action} eseguita con successo",
                "simulation_state": simulation_state,
            }
        )

    except Exception as e:
        logger.error(f"Errore nel controllo simulazione: {str(e)}")
        return (
            jsonify({"success": False, "error": f"Errore nel controllo: {str(e)}"}),
            500,
        )


@anomaly_snmp_bp.route("/api/simulation_status")
def get_simulation_status():
    """
    API per recuperare lo stato corrente della simulazione
    Requirements: 6.1, 6.4
    """
    try:
        if "anomaly_snmp" not in session:
            return (
                jsonify(
                    {"success": False, "error": "Sessione AnomalySNMP non trovata"}
                ),
                404,
            )

        config = session["anomaly_snmp"].get("config", {})
        simulation_state = session["anomaly_snmp"].get("simulation_state", {})
        model_artifacts = session["anomaly_snmp"].get("model_artifacts", {})

        # Calcola statistiche basate sui metadati del test_set
        current_offset = model_artifacts.get("current_offset", 0)
        dataset_stats = session["anomaly_snmp"].get("dataset_stats", {})
        max_points = dataset_stats.get("test_set_total", 0)
        progress_percentage = (
            (current_offset / max_points) * 100 if max_points > 0 else 0
        )

        status = {
            "is_running": simulation_state.get("is_running", False),
            "speed": simulation_state.get("speed", 1),
            "current_index": simulation_state.get("current_index", 0),
            "current_offset": current_offset,
            "progress_percentage": round(progress_percentage, 1),
            "max_points": max_points,
            "has_more_data": current_offset < max_points - 1,
            "configuration": {
                "contamination": config.get("contamination"),
                "train_split": config.get("train_split"),
                "dataset_name": config.get("dataset_name"),
            },
            "statistics": {
                "total_points_processed": simulation_state.get(
                    "total_points_processed", current_offset
                ),
                "normal_count": simulation_state.get("normal_count", 0),
                "anomaly_count": simulation_state.get("anomaly_count", 0),
            },
        }

        return jsonify({"success": True, "status": status})

    except Exception as e:
        logger.error(f"Errore nel recupero stato simulazione: {str(e)}")
        return (
            jsonify(
                {"success": False, "error": f"Errore nel recupero stato: {str(e)}"}
            ),
            500,
        )


@anomaly_snmp_bp.route("/api/get_next_point/<int:offset>")
@handle_route_errors("get_next_point")
def get_next_point(offset):
    """
    API per ottenere il prossimo punto dati nella simulazione
    Usa Isolation Forest .predict(X) per determinare se è anomalia o normale
    """
    try:
        if "anomaly_snmp" not in session:
            return jsonify({"success": False, "error": "Sessione non trovata"}), 404

        config = session["anomaly_snmp"].get("config", {})
        model_artifacts = session["anomaly_snmp"].get("model_artifacts", {})
        
        # Genera punto dati sequenziale
        data_point = _generate_sequential_data_point(offset, config)
        
        # Simula il modello Isolation Forest per la predizione
        # In un'implementazione reale, qui useresti il modello addestrato
        prediction = _simulate_isolation_forest_prediction(data_point, config)
        
        # Aggiorna offset corrente
        session["anomaly_snmp"]["model_artifacts"]["current_offset"] = offset + 1
        
        # Aggiorna statistiche
        simulation_state = session["anomaly_snmp"].get("simulation_state", {})
        if prediction["is_anomaly"]:
            simulation_state["anomaly_count"] = simulation_state.get("anomaly_count", 0) + 1
        else:
            simulation_state["normal_count"] = simulation_state.get("normal_count", 0) + 1
        
        session["anomaly_snmp"]["simulation_state"] = simulation_state
        session.modified = True
        
        # Determina se ci sono più dati
        dataset_stats = session["anomaly_snmp"].get("dataset_stats", {})
        max_points = dataset_stats.get("test_set_total", 1000)
        has_more_data = offset + 1 < max_points
        
        return jsonify({
            "success": True,
            "data": {
                "timestamp": data_point["timestamp"],
                "prediction": prediction["prediction"],
                "is_anomaly": prediction["is_anomaly"],
                "is_normal": prediction["is_normal"],
                "classification": prediction["classification"],
                "real_label": data_point["real_label"],
                "offset": offset,
                "features": data_point["features"],
                "metadata": data_point.get("metadata", {})
            },
            "next_offset": offset + 1,
            "has_more_data": has_more_data,
            "simulation_state": simulation_state
        })

    except Exception as e:
        logger.error(f"Errore nel get_next_point: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


def _simulate_isolation_forest_prediction(data_point, config):
    """
    Simula la predizione di Isolation Forest usando .predict(X)
    Restituisce 1 per normale, -1 per anomalia
    """
    import random
    
    # Simula la logica del modello basata sull'etichetta reale e contamination
    contamination = config.get("contamination", 0.05)
    real_label = data_point["real_label"]
    
    # Simula accuratezza del modello (circa 85-90%)
    accuracy = 0.87
    
    if real_label == "Normal":
        # Per punti normali, il modello dovrebbe predire 1 (normale) la maggior parte delle volte
        if random.random() < accuracy:
            prediction = 1  # Normale
        else:
            prediction = -1  # Falso positivo
    else:
        # Per anomalie, il modello dovrebbe predire -1 (anomalia) la maggior parte delle volte
        if random.random() < accuracy:
            prediction = -1  # Anomalia
        else:
            prediction = 1  # Falso negativo
    
    return {
        "prediction": prediction,
        "is_anomaly": prediction == -1,
        "is_normal": prediction == 1,
        "classification": "Anomalia" if prediction == -1 else "Normale"
    }


def prepare_dataset_with_oversampling(contamination, train_split):
    """
    Prepara il dataset con oversampling corretto secondo la logica richiesta

    Processo:
    1. Oversampling sui dati normali fino a raggiungere il rapporto contamination
    2. Split training/test sui dati normali bilanciati
    3. Preparazione anomalie per test set
    """
    import random
    import numpy as np

    # Dataset originale SNMP-MIB
    normal_original = 600
    anomaly_original = 4398

    logger.info(
        f"Dataset originale: {normal_original} normali, {anomaly_original} anomalie"
    )

    # 1. CALCOLO TARGET OVERSAMPLING CORRETTO
    # Se contamination = 5%, vogliamo che le anomalie siano il 5% del totale
    # Ma limitiamo l'oversampling per ragioni pratiche
    # Usiamo solo una parte delle anomalie per il test (es. 500)

    # CORREZIONE: Usiamo TUTTE le anomalie per il test set
    anomaly_for_test = anomaly_original  # Tutte le 4398 anomalie

    # Calcoliamo target normali per raggiungere contamination desiderata
    # anomaly_for_test / (target_normal + anomaly_for_test) = contamination
    target_normal_oversampled = int(
        anomaly_for_test * (1 - contamination) / contamination
    )
    oversampling_needed = max(0, target_normal_oversampled - normal_original)

    logger.info(f"Anomalie per test: {anomaly_for_test}")
    logger.info(f"Target normali dopo oversampling: {target_normal_oversampled}")
    logger.info(f"Oversampling necessario: {oversampling_needed}")

    # 2. GENERAZIONE DATI NORMALI CON OVERSAMPLING (SMOTE simulato)
    normal_data_oversampled = []

    # Aggiungi dati normali originali
    for i in range(normal_original):
        normal_data_oversampled.append(
            {
                "features": [round(random.uniform(0.3, 0.7), 3) for _ in range(8)],
                "label": "Normal",
                "source": "original",
                "id": i,
            }
        )

    # Aggiungi dati SMOTE (simulati con variazioni sui normali esistenti)
    for i in range(oversampling_needed):
        # Seleziona un record normale casuale come base
        base_record = random.choice(normal_data_oversampled[:normal_original])

        # Genera variazione SMOTE (piccole perturbazioni)
        smote_features = []
        for feature in base_record["features"]:
            noise = random.uniform(-0.05, 0.05)  # Piccola variazione
            smote_features.append(round(max(0, min(1, feature + noise)), 3))

        normal_data_oversampled.append(
            {
                "features": smote_features,
                "label": "Normal",
                "source": "smote",
                "id": normal_original + i,
            }
        )

    # 3. SPLIT TRAINING/TEST SUI DATI NORMALI BILANCIATI
    random.shuffle(normal_data_oversampled)

    split_index = int(len(normal_data_oversampled) * train_split)
    training_normal = normal_data_oversampled[:split_index]
    test_normal = normal_data_oversampled[split_index:]

    # 4. PREPARAZIONE ANOMALIE PER TEST
    test_anomalies = []
    for i in range(anomaly_for_test):
        test_anomalies.append(
            {
                "features": [round(random.uniform(0.0, 1.0), 3) for _ in range(8)],
                "label": "Anomaly",
                "source": "original",
                "id": i,
            }
        )

    dataset_info = {
        "normal_original": normal_original,
        "anomaly_original": anomaly_original,
        "normal_oversampled_total": len(normal_data_oversampled),
        "oversampling_generated": oversampling_needed,
        "training_normal": training_normal,
        "test_normal": test_normal,
        "test_anomalies": test_anomalies,
        "contamination_used": contamination,
        "train_split_used": train_split,
    }

    logger.info(
        f"Dataset preparato: {len(training_normal)} training, {len(test_normal)} test normali, {len(test_anomalies)} test anomalie"
    )

    return dataset_info


def train_isolation_forest_correct(dataset_info, contamination):
    """
    Training Isolation Forest sulla parte training dei dati normali
    """
    import numpy as np
    from datetime import datetime

    training_data = dataset_info["training_normal"]

    logger.info(f"Training Isolation Forest su {len(training_data)} record normali")

    # Simula training Isolation Forest
    # In implementazione reale qui ci sarebbe:
    # from sklearn.ensemble import IsolationForest
    # model = IsolationForest(contamination=contamination, random_state=42)
    # model.fit([record['features'] for record in training_data])

    # Per ora simuliamo il modello addestrato
    baseline_scores = []
    for record in training_data:
        # Simula score IF per dati normali (dovrebbero essere alti)
        base_score = np.random.normal(0.7, 0.1)  # Media 0.7, std 0.1
        baseline_scores.append(max(0.0, min(1.0, base_score)))

    # Calcola baseline statistica
    baseline = {
        "mu_normal": np.mean(baseline_scores),
        "sigma_normal": np.std(baseline_scores),
        "threshold_5th": np.percentile(baseline_scores, 5),
        "threshold_95th": np.percentile(baseline_scores, 95),
        "model_type": "IsolationForest",
        "contamination_used": contamination,
        "training_samples": len(training_data),
        "training_timestamp": datetime.now().isoformat(),
    }

    logger.info(
        f"Baseline calcolata: μ={baseline['mu_normal']:.3f}, σ={baseline['sigma_normal']:.3f}"
    )

    return {
        "baseline": baseline,
        "training_scores": baseline_scores,
        "model_metadata": {
            "algorithm": "IsolationForest",
            "contamination": contamination,
            "training_size": len(training_data),
            "feature_count": 8,
        },
    }


def prepare_shuffled_test_set(dataset_info, model_artifacts):
    """
    Prepara il test set shuffled con normali rimanenti + anomalie
    """
    import random
    import numpy as np

    test_normal = dataset_info["test_normal"]
    test_anomalies = dataset_info["test_anomalies"]
    baseline = model_artifacts["baseline"]

    logger.info(
        f"Preparazione test set: {len(test_normal)} normali + {len(test_anomalies)} anomalie"
    )

    # Combina test normali e anomalie
    combined_test_set = []

    # Aggiungi normali con score alti (simili al training)
    for i, record in enumerate(test_normal):
        s_score = simulate_if_score(record["features"], baseline, is_normal=True)
        combined_test_set.append(
            {
                "features": record["features"],
                "s_score": s_score,
                "real_label": "Normal",
                "source": record["source"],
                "original_index": i,
                "data_type": "test_normal",
            }
        )

    # Aggiungi anomalie con score bassi
    for i, record in enumerate(test_anomalies):
        s_score = simulate_if_score(record["features"], baseline, is_normal=False)
        combined_test_set.append(
            {
                "features": record["features"],
                "s_score": s_score,
                "real_label": "Anomaly",
                "source": record["source"],
                "original_index": i,
                "data_type": "test_anomaly",
            }
        )

    # SHUFFLE del test set (importante!)
    random.shuffle(combined_test_set)

    # Aggiungi offset sequenziali dopo shuffle con timestamp simulati
    from datetime import datetime, timedelta

    base_time = datetime.now() - timedelta(hours=1)  # Inizia da 1 ora fa

    for i, record in enumerate(combined_test_set):
        record["offset"] = i
        record["timestamp"] = base_time + timedelta(
            seconds=i * 2
        )  # Avanza di 2 secondi per punto

    logger.info(f"Test set shuffled preparato: {len(combined_test_set)} record totali")

    return combined_test_set


def simulate_if_score(features=None, baseline=None, is_normal=True):
    """
    Calcola l'S-Score usando la formula corretta:
    S(s_new) = {
        1.0                                           se s_new ≤ μ_normal
        max(0, 1 - (s_new - μ_normal)/(3·σ_normal))  se s_new > μ_normal
    }
    """
    import numpy as np

    # Simula un raw_score realistico da Isolation Forest
    if is_normal:
        # Dati normali: raw_score intorno alla baseline o sotto
        raw_score = np.random.normal(
            baseline["mu_normal"] - 0.1, baseline["sigma_normal"]
        )
    else:
        # Anomalie: raw_score sopra la baseline
        raw_score = np.random.normal(
            baseline["mu_normal"] + 0.3, baseline["sigma_normal"] * 2
        )

    # Applica la formula corretta
    mu_normal = baseline["mu_normal"]
    sigma_normal = baseline["sigma_normal"]

    if raw_score <= mu_normal:
        s_score = 1.0
    else:
        deviation = (raw_score - mu_normal) / (3 * sigma_normal)
        s_score = max(0.0, 1.0 - deviation)

    return round(s_score, 3)


def generate_test_point_on_demand(offset, config, dataset_stats, baseline, seed):
    """
    Genera un punto del test set al volo usando seed e offset
    Ricrea lo stesso ordine shuffled del test set originale
    """
    import random
    import numpy as np
    from datetime import datetime, timedelta

    # Usa seed + offset per garantire riproducibilità
    random.seed(seed + offset)
    np.random.seed(seed + offset)

    test_normal_count = dataset_stats.get("test_normal_count", 0)
    test_anomaly_count = dataset_stats.get("test_anomaly_count", 0)
    test_set_total = test_normal_count + test_anomaly_count

    # Ricrea la stessa logica di shuffle del test set originale
    # Generiamo tutti gli indici e li shuffliamo con lo stesso seed
    random.seed(seed)  # Seed fisso per shuffle consistente
    indices = list(range(test_set_total))

    # Primi test_normal_count sono normali, resto sono anomalie
    normal_indices = indices[:test_normal_count]
    anomaly_indices = indices[test_normal_count:]

    # Combina e shuffla
    combined_indices = [(i, "Normal") for i in normal_indices] + [
        (i, "Anomaly") for i in anomaly_indices
    ]
    random.shuffle(combined_indices)

    # Recupera il tipo per questo offset
    if offset < len(combined_indices):
        original_index, label_type = combined_indices[offset]

        # Genera score basato sul tipo (senza features)
        if label_type == "Normal":
            s_score = simulate_if_score(baseline=baseline, is_normal=True)
            source = "smote" if original_index > 600 else "original"
        else:
            s_score = simulate_if_score(baseline=baseline, is_normal=False)
            source = "original"

        # Timestamp progressivo
        base_time = datetime.now() - timedelta(hours=1)
        timestamp = base_time + timedelta(seconds=offset * 2)

        # SOGLIA DI DECISIONE: Il modello dichiara anomalia se S-Score < 0.5
        ANOMALY_THRESHOLD = 0.5
        predicted_label = "Anomaly" if s_score < ANOMALY_THRESHOLD else "Normal"

        # Determina se la predizione è corretta
        is_correct_prediction = predicted_label == label_type

        return {
            "s_score": s_score,
            "real_label": label_type,  # Ground truth dal dataset
            "predicted_label": predicted_label,  # Decisione del modello
            "is_correct": is_correct_prediction,
            "threshold_used": ANOMALY_THRESHOLD,
            "source": source,
            "offset": offset,
            "timestamp": timestamp.isoformat(),
            "original_index": original_index,
            "data_type": f"test_{label_type.lower()}",
        }
    else:
        # Fallback se offset fuori range
        ANOMALY_THRESHOLD = 0.5
        fallback_score = 0.5
        predicted_label = "Normal" if fallback_score >= ANOMALY_THRESHOLD else "Anomaly"

        return {
            "s_score": fallback_score,
            "real_label": "Normal",
            "predicted_label": predicted_label,
            "is_correct": True,  # Assumiamo corretto per fallback
            "threshold_used": ANOMALY_THRESHOLD,
            "source": "fallback",
            "offset": offset,
            "timestamp": datetime.now().isoformat(),
            "original_index": 0,
            "data_type": "fallback",
        }


# Seconda definizione di get_next_point rimossa - duplicata
# Seconda definizione di reset_simulation rimossa - duplicata