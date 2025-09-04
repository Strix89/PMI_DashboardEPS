#!/usr/bin/env python3
"""
Modulo per il riassunto delle metriche di availability

Questo modulo prende un giorno casuale dalle metriche presenti nel database MongoDB
e genera un riassunto delle metriche di availability per ogni servizio.

Per ogni servizio mostra:
- Un esempio di tupla di availability
- Numero totale di tuple di availability
- Numero di tuple DOWN (0.0)  
- Numero di tuple UP (1.0)
- Numero di giorni con misurazioni
- Numero di misurazioni al giorno

Usage:
    python metrics_dashboard/utils/availability_summary.py
"""

import argparse
import logging
import random
import sys
import os
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

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


class AvailabilitySummary:
    """
    Classe per generare riassunti delle metriche di availability.
    """
    
    def __init__(self, storage_manager: StorageManager):
        """
        Inizializza il generatore di riassunti.
        
        Args:
            storage_manager: Istanza del storage manager configurato
        """
        self.storage_manager = storage_manager
        self.logger = logger
    
    def get_random_day_with_data(self) -> Optional[datetime]:
        """
        Ottiene un giorno casuale con dati di availability nel database.
        
        Returns:
            Datetime del giorno casuale con dati, None se non ci sono dati
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
            
            # Seleziona una data casuale
            random_date = random.choice(list(dates))
            self.logger.info(f"Giorno casuale selezionato: {random_date.strftime('%Y-%m-%d')}")
            
            return random_date
            
        except Exception as e:
            self.logger.error(f"Errore nell'ottenere un giorno casuale: {e}")
            return None
    
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
    
    def analyze_service_availability(self, service_id: str, random_date: datetime) -> Dict[str, Any]:
        """
        Analizza le metriche di availability per un servizio specifico.
        
        Args:
            service_id: ID del servizio da analizzare
            random_date: Giorno di riferimento per l'analisi
        
        Returns:
            Dizionario con le statistiche del servizio
        """
        try:
            # Ottieni tutte le metriche di availability per il servizio
            all_metrics = self.storage_manager.get_metrics(
                asset_id=service_id,
                metric_name="availability_status"
            )
            
            if not all_metrics:
                return {
                    "service_id": service_id,
                    "total_metrics": 0,
                    "up_count": 0,
                    "down_count": 0,
                    "days_with_measurements": 0,
                    "measurements_per_day": 0,
                    "example_tuple": None
                }
            
            # Calcola statistiche totali
            total_metrics = len(all_metrics)
            up_count = sum(1 for m in all_metrics if m.get('value', 0) == 1.0)
            down_count = sum(1 for m in all_metrics if m.get('value', 0) == 0.0)
            
            # Trova un esempio di tupla per il giorno casuale
            example_tuple = None
            day_start = random_date
            day_end = random_date + timedelta(days=1)
            
            for metric in all_metrics:
                timestamp = metric.get('timestamp')
                if timestamp and day_start <= timestamp < day_end:
                    example_tuple = {
                        'timestamp': timestamp,
                        'asset_id': metric.get('meta', {}).get('asset_id'),
                        'metric_name': metric.get('meta', {}).get('metric_name'),
                        'value': metric.get('value')
                    }
                    break
            
            # Se non trova esempio nel giorno casuale, prendi il primo disponibile
            if not example_tuple and all_metrics:
                metric = all_metrics[0]
                example_tuple = {
                    'timestamp': metric.get('timestamp'),
                    'asset_id': metric.get('meta', {}).get('asset_id'),
                    'metric_name': metric.get('meta', {}).get('metric_name'),
                    'value': metric.get('value')
                }
            
            # Calcola giorni con misurazioni
            dates_with_data = set()
            metrics_per_day = defaultdict(int)
            
            for metric in all_metrics:
                timestamp = metric.get('timestamp')
                if timestamp:
                    date_only = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                    dates_with_data.add(date_only)
                    metrics_per_day[date_only] += 1
            
            days_with_measurements = len(dates_with_data)
            avg_measurements_per_day = (
                sum(metrics_per_day.values()) / len(metrics_per_day)
                if metrics_per_day else 0
            )
            
            return {
                "service_id": service_id,
                "total_metrics": total_metrics,
                "up_count": up_count,
                "down_count": down_count,
                "days_with_measurements": days_with_measurements,
                "measurements_per_day": round(avg_measurements_per_day, 1),
                "example_tuple": example_tuple
            }
            
        except Exception as e:
            self.logger.error(f"Errore nell'analisi del servizio {service_id}: {e}")
            return {
                "service_id": service_id,
                "error": str(e)
            }
    
    def generate_summary(self) -> None:
        """
        Genera e mostra il riassunto delle metriche di availability.
        """
        self.logger.info("=" * 80)
        self.logger.info("RIASSUNTO METRICHE DI AVAILABILITY")
        self.logger.info("=" * 80)
        
        # Ottieni un giorno casuale con dati
        random_date = self.get_random_day_with_data()
        if not random_date:
            self.logger.error("Impossibile trovare dati di availability nel database")
            return
        
        # Ottieni tutti i servizi
        services = self.get_all_services()
        if not services:
            self.logger.error("Nessun servizio trovato nel database")
            return
        
        # Analizza ogni servizio
        for service in services:
            service_id = service.get('_id') or service.get('asset_id')
            service_name = service.get('service_name', 'N/A')
            
            if not service_id:
                continue
                
            self.logger.info(f"\n--- SERVIZIO: {service_name} (ID: {service_id}) ---")
            
            stats = self.analyze_service_availability(service_id, random_date)
            
            if 'error' in stats:
                self.logger.error(f"Errore nell'analisi: {stats['error']}")
                continue
            
            # Mostra esempio di tupla
            if stats['example_tuple']:
                example = stats['example_tuple']
                self.logger.info("ESEMPIO TUPLA AVAILABILITY:")
                self.logger.info(f"  Timestamp: {example['timestamp']}")
                self.logger.info(f"  Asset ID: {example['asset_id']}")
                self.logger.info(f"  Metric Name: {example['metric_name']}")
                self.logger.info(f"  Value: {example['value']} ({'UP' if example['value'] == 1.0 else 'DOWN'})")
            else:
                self.logger.info("ESEMPIO TUPLA AVAILABILITY: Nessun dato disponibile")
            
            # Mostra statistiche
            self.logger.info(f"\nSTATISTICHE:")
            self.logger.info(f"  Totale tuple availability: {stats['total_metrics']}")
            self.logger.info(f"  Tuple UP (1.0): {stats['up_count']}")
            self.logger.info(f"  Tuple DOWN (0.0): {stats['down_count']}")
            self.logger.info(f"  Giorni con misurazioni: {stats['days_with_measurements']}")
            self.logger.info(f"  Misurazioni per giorno: {stats['measurements_per_day']}")
            
            # Calcola percentuale uptime
            if stats['total_metrics'] > 0:
                uptime_percentage = (stats['up_count'] / stats['total_metrics']) * 100
                self.logger.info(f"  Percentuale uptime: {uptime_percentage:.2f}%")


def main():
    """
    Funzione principale per eseguire il riassunto delle metriche.
    """
    parser = argparse.ArgumentParser(
        description="Genera riassunto delle metriche di availability"
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
    
    args = parser.parse_args()
    
    try:
        # Inizializza storage manager
        storage_manager = StorageManager(
            connection_string=args.connection_string,
            database_name=args.database_name
        )
        
        # Connetti al database
        storage_manager.connect()
        logger.info(f"Connesso al database: {args.database_name}")
        
        # Genera riassunto
        summary_generator = AvailabilitySummary(storage_manager)
        summary_generator.generate_summary()
        
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
