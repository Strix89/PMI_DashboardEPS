#!/usr/bin/env python3
"""
Analizzatore Cumulativo delle Metriche di Availability

Questo modulo seleziona un giorno casuale dalle metriche presenti nel database MongoDB
e genera un'analisi cumulativa delle metriche di availability per ogni servizio.

Per ogni servizio calcola un valore percentuale cumulativo usando la formula:
S(P_f, E_b) = 
- 100% se P_f = 0
- 100% - (P_f/E_b × 50%) se 0 < P_f ≤ E_b
- max(0, 50% - ((P_f - E_b)/E_b × 50%)) se P_f > E_b

Dove P_f = fallimenti cumulativi e E_b = soglia fallimenti attesi per servizio.

Usage:
    python metrics_dashboard/utils/cumulative_availability_analyzer.py
"""

import argparse
import json
import logging
import os
import random
import sys
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

# Aggiungi il path del progetto per importare storage_layer
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from storage_layer.storage_manager import StorageManager
from storage_layer.models import AssetDocument
from storage_layer.exceptions import StorageManagerError


# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class StatusType(Enum):
    """Enum per i tipi di status basati sul valore percentuale."""
    CRITICAL = "CRITICAL"
    ATTENZIONE = "ATTENZIONE" 
    GOOD = "GOOD"


class CumulativeAvailabilityAnalyzer:
    """
    Classe per l'analisi cumulativa delle metriche di availability.
    """
    
    def __init__(self, storage_manager: StorageManager, config: Optional[Dict[str, Any]] = None):
        """
        Inizializza l'analizzatore.
        
        Args:
            storage_manager: Istanza del storage manager configurato
            config: Configurazione personalizzata (error budgets, pesi)
        """
        self.storage_manager = storage_manager
        self.logger = logger
        
        # Sempre un solo giorno
        self.num_days = 1
        
        # Configurazione personalizzata se fornita
        if config:
            self.service_error_budgets = config.get('service_error_budgets', {})
            self.service_weights = config.get('service_weights', {})
        else:
            self.service_error_budgets = {}
            self.service_weights = {}
        
        # Configurazione E_b per tipo di servizio (fallimenti attesi) - DEFAULT
        self.default_service_eb_config = {
            "web_service": 5,      # Servizi web (nginx, apache)
            "database": 3,         # Database (mysql, redis, elasticsearch)
            "application": 8,      # Applicazioni (tomcat, reporting)
            "backup": 10,          # Servizi di backup
            "monitoring": 4,       # Prometheus, grafana
            "mail": 6,             # Postfix, dovecot
            "ci_cd": 7,            # Jenkins, gitlab-runner
            "file_sharing": 5,     # NFS, SMB
            "default": 5           # Valore di default
        }
        
        # Soglie per determinare il tipo di status
        self.status_thresholds = {
            "critical": 0.5,       # < 50% = CRITICAL
            "attenzione": 0.8      # 50%-80% = ATTENZIONE, > 80% = GOOD
        }
    
    def get_random_day_with_data(self) -> Optional[datetime]:
        """
        Ottiene un giorno casuale con dati di availability nel database.
        
        Returns:
            datetime del giorno casuale con dati, None se non trovato
        """
        try:
            # Ottieni tutte le metriche di availability per trovare il range di date
            metrics = self.storage_manager.get_metrics(metric_name="availability_status")
            
            if not metrics:
                self.logger.warning("Nessuna metrica di availability trovata nel database")
                return None
            
            # Estrai le date uniche
            dates = set()
            for metric in metrics:
                timestamp = metric.get('timestamp')
                if timestamp:
                    # Ottieni solo la data (senza l'ora)
                    date_only = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                    dates.add(date_only)
            
            if not dates:
                self.logger.warning("Nessuna data valida trovata nelle metriche")
                return None
            
            # Seleziona un giorno casuale
            available_dates = list(dates)
            random_date = random.choice(available_dates)
            
            self.logger.info(f"Giorno casuale selezionato: {random_date.strftime('%Y-%m-%d')}")
            
            return random_date
            
        except Exception as e:
            self.logger.error(f"Errore nell'ottenere giorno casuale: {e}")
            return None
        return days[0] if days else None
    
    def get_all_services(self) -> List[Dict[str, Any]]:
        """
        Ottieni tutti i servizi dal database.
        
        Returns:
            Lista di documenti degli asset di tipo service
        """
        try:
            services = self.storage_manager.get_assets_by_type(asset_type="service")
            self.logger.info(f"Trovati {len(services)} servizi nel database")
            return services
        except Exception as e:
            self.logger.error(f"Errore nell'ottenere i servizi: {e}")
            return []
    
    def get_service_eb(self, service_data: Dict[str, Any]) -> int:
        """
        Determina il valore E_b per un servizio specifico.
        Prima controlla configurazione personalizzata, poi fallback sui valori di default.
        
        Args:
            service_data: Dati del servizio dal database
            
        Returns:
            Valore E_b (fallimenti attesi) per il servizio
        """
        service_name = service_data.get('name', service_data.get('service_name', ''))
        service_id = str(service_data.get('_id', ''))
        
        # 1. Prima controlla se c'è un error budget personalizzato per nome o ID
        if self.service_error_budgets:
            if service_name in self.service_error_budgets:
                eb_value = self.service_error_budgets[service_name]
                self.logger.debug(f"Usando error budget personalizzato per '{service_name}': {eb_value}")
                return eb_value
            elif service_id in self.service_error_budgets:
                eb_value = self.service_error_budgets[service_id]
                self.logger.debug(f"Usando error budget personalizzato per ID '{service_id}': {eb_value}")
                return eb_value
        
        # 2. Fallback: usa configurazione di default basata sul tipo
        service_type = service_data.get('data', {}).get('service_type', 'default')
        eb_value = self.default_service_eb_config.get(service_type, self.default_service_eb_config['default'])
        
        self.logger.debug(f"Servizio '{service_name}' tipo '{service_type}' -> E_b default = {eb_value}")
        
        return eb_value
    
    def calculate_cumulative_score(self, cumulative_failures: int, eb_value: int) -> float:
        """
        Calcola il punteggio cumulativo usando la formula specificata.
        
        Args:
            cumulative_failures: Numero di fallimenti cumulativi (P_f)
            eb_value: Soglia di fallimenti attesi (E_b)
            
        Returns:
            Punteggio tra 0.0 e 1.0
        """
        if cumulative_failures == 0:
            return 1.0  # 100%
        
        elif 0 < cumulative_failures <= eb_value:
            # 100% - (P_f/E_b × 50%)
            score = 1.0 - ((cumulative_failures / eb_value) * 0.5)
            return score
        
        else:  # cumulative_failures > eb_value
            # max(0, 50% - ((P_f - E_b)/E_b × 50%))
            score = max(0.0, 0.5 - (((cumulative_failures - eb_value) / eb_value) * 0.5))
            return score
    
    def determine_status_type(self, score: float) -> StatusType:
        """
        Determina il tipo di status basato sul punteggio.
        
        Args:
            score: Punteggio tra 0.0 e 1.0
            
        Returns:
            Tipo di status (CRITICAL, ATTENZIONE, GOOD)
        """
        if score < self.status_thresholds["critical"]:
            return StatusType.CRITICAL
        elif score < self.status_thresholds["attenzione"]:
            return StatusType.ATTENZIONE
        else:
            return StatusType.GOOD
    
    def analyze_service_day(self, service_id: str, target_date: datetime, eb_value: int) -> List[Dict[str, Any]]:
        """
        Analizza le metriche di availability per un servizio in un giorno specifico.
        
        Args:
            service_id: ID del servizio da analizzare
            target_date: Giorno da analizzare
            eb_value: Valore E_b per questo servizio
            
        Returns:
            Lista di tuple con timestamp, score e status_type
        """
        try:
            # Definisci l'intervallo del giorno
            day_start = target_date
            day_end = target_date + timedelta(days=1)
            
            # Ottieni le metriche del giorno per il servizio
            day_metrics = self.storage_manager.get_metrics(
                asset_id=service_id,
                metric_name="availability_status",
                start_time=day_start,
                end_time=day_end
            )
            
            if not day_metrics:
                self.logger.warning(f"Nessuna metrica trovata per il servizio {service_id} nel giorno {target_date.strftime('%Y-%m-%d')}")
                return []
            
            # Ordina le metriche per timestamp (dal più vecchio al più nuovo)
            day_metrics.sort(key=lambda x: x.get('timestamp', datetime.min))
            
            # Calcola i punteggi cumulativi
            results = []
            cumulative_failures = 0
            
            for metric in day_metrics:
                timestamp = metric.get('timestamp')
                value = metric.get('value', 1.0)  # Default a UP se non specificato
                
                # Se il valore è DOWN (0.0), incrementa i fallimenti cumulativi
                if value == 0.0:
                    cumulative_failures += 1
                
                # Calcola il punteggio cumulativo
                score = self.calculate_cumulative_score(cumulative_failures, eb_value)
                
                # Determina il tipo di status
                status_type = self.determine_status_type(score)
                
                # Aggiungi il risultato
                results.append({
                    "timestamp": timestamp.isoformat() if timestamp else None,
                    "score": round(score, 4),
                    "status_type": status_type.value,
                    "cumulative_failures": cumulative_failures,
                    "current_value": value
                })
            
            self.logger.info(f"Analizzate {len(results)} misurazioni per il servizio {service_id}")
            return results
            
        except Exception as e:
            self.logger.error(f"Errore nell'analisi del servizio {service_id}: {e}")
            return []
    
    def generate_analysis(self) -> Dict[str, Any]:
        """
        Genera l'analisi cumulativa completa per tutti i servizi.
        Supporta analisi su più giorni casuali.
        
        Returns:
            Dizionario con i risultati dell'analisi in formato JSON
        """
        self.logger.info("=" * 80)
        self.logger.info("ANALISI CUMULATIVA AVAILABILITY")
        self.logger.info("=" * 80)
        
        # Ottieni un giorno casuale con dati
        random_date = self.get_random_day_with_data()
        if not random_date:
            self.logger.error("Impossibile trovare dati di availability nel database")
            return {}
        
        # Ottieni tutti i servizi
        services = self.get_all_services()
        if not services:
            self.logger.error("Nessun servizio trovato nel database")
            return {}
        
        # Struttura risultato
        result = {
            "analysis_dates": [random_date.isoformat()],
            "analysis_timestamp": datetime.now(UTC).isoformat(),
            "configuration": {
                "num_days": self.num_days,
                "default_service_eb_config": self.default_service_eb_config,
                "custom_error_budgets": self.service_error_budgets,
                "service_weights": self.service_weights,
                "status_thresholds": self.status_thresholds
            },
            "services": {},
            "summary": {}
        }
        
        # Analizza ogni servizio su tutti i giorni selezionati
        total_weighted_score = 0
        total_weight = 0
        service_count = 0
        
        for service in services:
            service_id = service.get('_id') or service.get('asset_id')
            service_name = service.get('name', service.get('service_name', 'N/A'))
            
            if not service_id:
                continue
            
            self.logger.info(f"Analizzando servizio: {service_name} (ID: {service_id})")
            
            # Ottieni E_b per questo servizio
            eb_value = self.get_service_eb(service)
            
            # Ottieni peso del servizio (default: uguale per tutti)
            service_weight = self.service_weights.get(service_name, 1.0 / len(services))
            
            # Analizza il servizio per il giorno selezionato
            service_analysis_data = []
            cumulative_failures_total = 0
            
            day_analysis = self.analyze_service_day(service_id, random_date, eb_value)
            service_analysis_data.extend(day_analysis)
            
            # Somma i fallimenti di questo giorno
            if day_analysis:
                day_failures = max([metric.get('cumulative_failures', 0) for metric in day_analysis])
                cumulative_failures_total += day_failures
            
            # Calcola score finale per il servizio (basato sul giorno analizzato)
            final_score = self.calculate_cumulative_score(cumulative_failures_total, eb_value)
            final_status = self.determine_status_type(final_score)
            
            # Aggiungi ai risultati
            result["services"][service_name] = {
                "service_id": str(service_id),
                "error_budget": eb_value,
                "weight": service_weight,
                "days_analyzed": 1,
                "total_failures": cumulative_failures_total,
                "final_score": round(final_score, 4),
                "final_status": final_status.value,
                "detailed_metrics": service_analysis_data
            }
            
            # Contributo al punteggio aggregato
            total_weighted_score += final_score * service_weight
            total_weight += service_weight
            service_count += 1
            
            self.logger.info(f"  - Score finale: {final_score:.2f}% ({final_status.value})")
        
        # Calcola punteggio aggregato globale
        aggregated_score = total_weighted_score / total_weight if total_weight > 0 else 0
        aggregated_status = self.determine_status_type(aggregated_score)
        
        result["summary"] = {
            "total_services": service_count,
            "aggregated_score": round(aggregated_score, 4),
            "aggregated_status": aggregated_status.value,
            "total_days_analyzed": 1
        }
        
        self.logger.info("=" * 80)
        self.logger.info(f"RISULTATO FINALE: {aggregated_score:.2f}% ({aggregated_status.value})")
        self.logger.info("=" * 80)
        
        return result

    def save_analysis_to_json(self, analysis: Dict[str, Any], output_file: str = None) -> str:
        """
        Salva l'analisi in un file JSON nella cartella output.
        
        Args:
            analysis: Risultati dell'analisi
            output_file: Nome del file di output (opzionale)
            
        Returns:
            Nome del file creato con path completo
        """
        # Determina il percorso della cartella output
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, '..', 'output')
        
        # Assicurati che la cartella output esista
        os.makedirs(output_dir, exist_ok=True)
        
        if output_file is None:
            # Genera nome file con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"cumulative_availability_analysis_{timestamp}.json"
        
        # Costruisci il path completo
        full_path = os.path.join(output_dir, output_file)
        
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Analisi salvata in: {full_path}")
            return full_path
            
        except Exception as e:
            self.logger.error(f"Errore nel salvare l'analisi: {e}")
            raise


def main():
    """
    Funzione principale per eseguire l'analisi cumulativa.
    """
    parser = argparse.ArgumentParser(
        description="Genera analisi cumulativa delle metriche di availability"
    )
    parser.add_argument(
        "--connection-string",
        default="mongodb://localhost:27017",
        help="Stringa di connessione MongoDB (default: mongodb://localhost:27017)"
    )
    parser.add_argument(
        "--database-name",
        default="infrastructure_monitoring",
        help="Nome del database (default: infrastructure_monitoring)"
    )
    parser.add_argument(
        "--output-file",
        help="Nome del file JSON di output (default: auto-generato)"
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Stampa il JSON dei risultati sulla console"
    )
    parser.add_argument(
        "--config-file",
        help="File JSON con configurazione personalizzata (error budgets, pesi)"
    )
    
    args = parser.parse_args()
    
    try:
        # Carica configurazione personalizzata se fornita
        config = None
        if args.config_file:
            try:
                with open(args.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"Configurazione caricata da: {args.config_file}")
            except Exception as e:
                logger.error(f"Errore nel caricamento configurazione: {e}")
                sys.exit(1)
        
        # Inizializza storage manager
        storage_manager = StorageManager(
            connection_string=args.connection_string,
            database_name=args.database_name
        )
        
        # Connetti al database
        storage_manager.connect()
        logger.info(f"Connesso al database: {args.database_name}")
        
        # Genera analisi con configurazione personalizzata
        analyzer = CumulativeAvailabilityAnalyzer(storage_manager, config)
        analysis = analyzer.generate_analysis()
        
        if not analysis:
            logger.error("Nessuna analisi generata")
            sys.exit(1)
        
        # Salva su file
        output_file = analyzer.save_analysis_to_json(analysis, args.output_file)
        
        # Stampa JSON se richiesto
        if args.print_json:
            print("\n" + "="*80)
            print("RISULTATI JSON:")
            print("="*80)
            print(json.dumps(analysis, indent=2, ensure_ascii=False))
        
        logger.info("Analisi completata con successo!")
        logger.info(f"File di output: {output_file}")
        
    except StorageManagerError as e:
        logger.error(f"Errore del storage manager: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Errore imprevisto: {e}")
        sys.exit(1)
    finally:
        # Chiudi connessione
        if 'storage_manager' in locals():
            storage_manager.disconnect()
            logger.info("Connessione al database chiusa")


if __name__ == "__main__":
    main()
