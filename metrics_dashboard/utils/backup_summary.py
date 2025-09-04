#!/usr/bin/env python3
"""
Modulo per il riassunto delle metriche di backup

Questo modulo prende un giorno casuale dalle metriche presenti nel database MongoDB
e genera un riassunto delle metriche di backup per ogni asset e backup job.

Per ogni asset e backup job mostra:
- Un esempio di tupla di backup
- Numero totale di tuple di backup
- Numero di backup riusciti (1.0)
- Numero di backup falliti (0.0)
- Numero di giorni con backup
- Numero di backup al giorno
- Percentuale di successo (RPO)
- Informazioni sui backup job Acronis

Usage:
    python metrics_dashboard/utils/backup_summary.py
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


class BackupSummary:
    """
    Classe per generare riassunti delle metriche di backup.
    """
    
    def __init__(self, storage_manager: StorageManager):
        """
        Inizializza il generatore di riassunti.
        
        Args:
            storage_manager: Istanza del storage manager configurato
        """
        self.storage_manager = storage_manager
        self.logger = logger
    
    def get_random_day_with_backup_data(self) -> Optional[datetime]:
        """
        Ottiene un giorno casuale con dati di backup nel database.
        
        Returns:
            Datetime del giorno casuale con dati, None se non ci sono dati
        """
        try:
            # Ottieni tutte le metriche di backup per trovare il range di date
            metrics = self.storage_manager.get_metrics(metric_name="backup_status")
            
            if not metrics:
                self.logger.warning("Nessuna metrica di backup trovata nel database")
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
                self.logger.warning("Nessuna data valida trovata nelle metriche di backup")
                return None
            
            # Seleziona una data casuale
            random_date = random.choice(list(dates))
            self.logger.info(f"Giorno casuale selezionato per i backup: {random_date.strftime('%Y-%m-%d')}")
            
            return random_date
            
        except Exception as e:
            self.logger.error(f"Errore nell'ottenere un giorno casuale per i backup: {e}")
            return None
    
    def get_all_backup_jobs(self) -> List[Dict[str, Any]]:
        """
        Ottieni tutti i backup job Acronis dal database.
        
        Returns:
            Lista di documenti degli asset di tipo acronis_backup_job
        """
        try:
            backup_jobs = self.storage_manager.get_assets_by_type(asset_type="acronis_backup_job")
            self.logger.info(f"Trovati {len(backup_jobs)} backup job Acronis nel database")
            return backup_jobs
        except Exception as e:
            self.logger.error(f"Errore nell'ottenere i backup job: {e}")
            return []
    
    def get_all_assets_with_backups(self) -> List[Dict[str, Any]]:
        """
        Ottieni tutti gli asset che hanno metriche di backup.
        
        Returns:
            Lista di asset ID che hanno dati di backup
        """
        try:
            # Ottieni tutte le metriche di backup
            backup_metrics = self.storage_manager.get_metrics(metric_name="backup_status")
            
            # Estrai gli asset ID unici
            asset_ids = set()
            for metric in backup_metrics:
                asset_id = metric.get('meta', {}).get('asset_id')
                if asset_id:
                    asset_ids.add(asset_id)
            
            # Ottieni le informazioni degli asset
            assets_with_backups = []
            for asset_id in asset_ids:
                try:
                    asset = self.storage_manager.get_asset(asset_id)
                    if asset:
                        assets_with_backups.append(asset)
                except:
                    # Asset potrebbe non esistere più, continua
                    continue
            
            self.logger.info(f"Trovati {len(assets_with_backups)} asset con dati di backup")
            return assets_with_backups
            
        except Exception as e:
            self.logger.error(f"Errore nell'ottenere gli asset con backup: {e}")
            return []
    
    def analyze_asset_backup(self, asset_id: str, random_date: datetime) -> Dict[str, Any]:
        """
        Analizza le metriche di backup per un asset specifico.
        
        Args:
            asset_id: ID dell'asset da analizzare
            random_date: Giorno di riferimento per l'analisi
        
        Returns:
            Dizionario con le statistiche di backup dell'asset
        """
        try:
            # Ottieni tutte le metriche di backup per l'asset
            all_metrics = self.storage_manager.get_metrics(
                asset_id=asset_id,
                metric_name="backup_status"
            )
            
            if not all_metrics:
                return {
                    "asset_id": asset_id,
                    "total_backups": 0,
                    "successful_backups": 0,
                    "failed_backups": 0,
                    "days_with_backups": 0,
                    "backups_per_day": 0,
                    "success_rate": 0.0,
                    "example_tuple": None
                }
            
            # Calcola statistiche totali
            total_backups = len(all_metrics)
            successful_backups = sum(1 for m in all_metrics if m.get('value', 0) == 1.0)
            failed_backups = sum(1 for m in all_metrics if m.get('value', 0) == 0.0)
            success_rate = (successful_backups / total_backups * 100) if total_backups > 0 else 0.0
            
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
                        'value': metric.get('value'),
                        'backup_result': 'SUCCESSO' if metric.get('value', 0) == 1.0 else 'FALLIMENTO'
                    }
                    break
            
            # Se non trova esempio nel giorno casuale, prendi il primo disponibile
            if not example_tuple and all_metrics:
                metric = all_metrics[0]
                example_tuple = {
                    'timestamp': metric.get('timestamp'),
                    'asset_id': metric.get('meta', {}).get('asset_id'),
                    'metric_name': metric.get('meta', {}).get('metric_name'),
                    'value': metric.get('value'),
                    'backup_result': 'SUCCESSO' if metric.get('value', 0) == 1.0 else 'FALLIMENTO'
                }
            
            # Calcola giorni con backup
            dates_with_backups = set()
            backups_per_day = defaultdict(int)
            
            for metric in all_metrics:
                timestamp = metric.get('timestamp')
                if timestamp:
                    date_only = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                    dates_with_backups.add(date_only)
                    backups_per_day[date_only] += 1
            
            days_with_backups = len(dates_with_backups)
            avg_backups_per_day = (
                sum(backups_per_day.values()) / len(backups_per_day)
                if backups_per_day else 0
            )
            
            return {
                "asset_id": asset_id,
                "total_backups": total_backups,
                "successful_backups": successful_backups,
                "failed_backups": failed_backups,
                "days_with_backups": days_with_backups,
                "backups_per_day": round(avg_backups_per_day, 1),
                "success_rate": round(success_rate, 2),
                "example_tuple": example_tuple
            }
            
        except Exception as e:
            self.logger.error(f"Errore nell'analisi dei backup per l'asset {asset_id}: {e}")
            return {
                "asset_id": asset_id,
                "error": str(e)
            }
    
    def analyze_backup_job_schedule(self, backup_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analizza le informazioni di un backup job Acronis.
        
        Args:
            backup_job: Documento del backup job
        
        Returns:
            Dizionario con le informazioni del backup job
        """
        try:
            job_data = backup_job.get('data', {})
            
            # Parsing delle date
            last_run = job_data.get('last_run')
            next_run = job_data.get('next_run')
            
            try:
                if last_run:
                    if isinstance(last_run, str):
                        last_run_dt = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
                    else:
                        last_run_dt = last_run
                else:
                    last_run_dt = None
            except:
                last_run_dt = None
            
            try:
                if next_run:
                    if isinstance(next_run, str):
                        next_run_dt = datetime.fromisoformat(next_run.replace('Z', '+00:00'))
                    else:
                        next_run_dt = next_run
                else:
                    next_run_dt = None
            except:
                next_run_dt = None
            
            # Calcola tempo dall'ultimo backup
            time_since_last_backup = None
            if last_run_dt:
                time_since_last_backup = datetime.now(UTC) - last_run_dt
            
            # Calcola tempo al prossimo backup
            time_to_next_backup = None
            if next_run_dt:
                time_to_next_backup = next_run_dt - datetime.now(UTC)
            
            target_assets = job_data.get('target_assets', [])
            
            return {
                "job_id": backup_job.get('_id') or backup_job.get('asset_id'),
                "job_name": job_data.get('job_name', 'N/A'),
                "status": job_data.get('status', 'unknown'),
                "schedule": job_data.get('schedule', 'N/A'),
                "backup_type": job_data.get('backup_type', 'N/A'),
                "retention_days": job_data.get('retention_days', 'N/A'),
                "target_assets_count": len(target_assets),
                "target_assets": target_assets,
                "last_run": last_run_dt.strftime('%Y-%m-%d %H:%M:%S UTC') if last_run_dt else 'N/A',
                "next_run": next_run_dt.strftime('%Y-%m-%d %H:%M:%S UTC') if next_run_dt else 'N/A',
                "time_since_last_backup": str(time_since_last_backup).split('.')[0] if time_since_last_backup else 'N/A',
                "time_to_next_backup": str(time_to_next_backup).split('.')[0] if time_to_next_backup and time_to_next_backup.total_seconds() > 0 else 'N/A'
            }
            
        except Exception as e:
            self.logger.error(f"Errore nell'analisi del backup job: {e}")
            return {
                "job_id": backup_job.get('_id', 'unknown'),
                "error": str(e)
            }
    
    def generate_summary(self) -> None:
        """
        Genera e mostra il riassunto delle metriche di backup.
        """
        self.logger.info("=" * 80)
        self.logger.info("RIASSUNTO METRICHE DI BACKUP")
        self.logger.info("=" * 80)
        
        # Ottieni un giorno casuale con dati
        random_date = self.get_random_day_with_backup_data()
        if not random_date:
            self.logger.error("Impossibile trovare dati di backup nel database")
            return
        
        # === SEZIONE 1: BACKUP JOBS ACRONIS ===
        self.logger.info("\n" + "=" * 60)
        self.logger.info("BACKUP JOBS ACRONIS")
        self.logger.info("=" * 60)
        
        backup_jobs = self.get_all_backup_jobs()
        if backup_jobs:
            for job in backup_jobs:
                job_info = self.analyze_backup_job_schedule(job)
                
                if 'error' in job_info:
                    self.logger.error(f"Errore nell'analisi del job: {job_info['error']}")
                    continue
                
                self.logger.info(f"\n--- BACKUP JOB: {job_info['job_name']} (ID: {job_info['job_id']}) ---")
                self.logger.info(f"  Status: {job_info['status']}")
                self.logger.info(f"  Pianificazione: {job_info['schedule']}")
                self.logger.info(f"  Tipo backup: {job_info['backup_type']}")
                self.logger.info(f"  Retention: {job_info['retention_days']} giorni")
                self.logger.info(f"  Asset target: {job_info['target_assets_count']} asset")
                self.logger.info(f"  Ultimo backup: {job_info['last_run']}")
                self.logger.info(f"  Prossimo backup: {job_info['next_run']}")
                self.logger.info(f"  Tempo dall'ultimo backup: {job_info['time_since_last_backup']}")
                self.logger.info(f"  Tempo al prossimo backup: {job_info['time_to_next_backup']}")
                
                if job_info['target_assets']:
                    self.logger.info(f"  Asset inclusi: {', '.join(job_info['target_assets'])}")
        else:
            self.logger.info("Nessun backup job Acronis trovato nel database")
        
        # === SEZIONE 2: METRICHE DI BACKUP PER ASSET ===
        self.logger.info("\n" + "=" * 60)
        self.logger.info("METRICHE DI BACKUP PER ASSET")
        self.logger.info("=" * 60)
        
        assets_with_backups = self.get_all_assets_with_backups()
        if not assets_with_backups:
            self.logger.error("Nessun asset con dati di backup trovato nel database")
            return
        
        # Statistiche globali
        total_assets = len(assets_with_backups)
        global_stats = {
            'total_backups': 0,
            'total_successful': 0,
            'total_failed': 0,
            'assets_100_percent': 0,
            'assets_above_95': 0,
            'assets_below_90': 0
        }
        
        # Analizza ogni asset
        for asset in assets_with_backups:
            asset_id = asset.get('_id') or asset.get('asset_id')
            hostname = asset.get('hostname', 'N/A')
            asset_type = asset.get('asset_type', 'N/A')
            
            if not asset_id:
                continue
                
            self.logger.info(f"\n--- ASSET: {hostname} (ID: {asset_id}) ---")
            self.logger.info(f"  Tipo: {asset_type}")
            
            stats = self.analyze_asset_backup(asset_id, random_date)
            
            if 'error' in stats:
                self.logger.error(f"Errore nell'analisi: {stats['error']}")
                continue
            
            # Aggiorna statistiche globali
            global_stats['total_backups'] += stats['total_backups']
            global_stats['total_successful'] += stats['successful_backups']
            global_stats['total_failed'] += stats['failed_backups']
            
            if stats['success_rate'] == 100.0:
                global_stats['assets_100_percent'] += 1
            elif stats['success_rate'] >= 95.0:
                global_stats['assets_above_95'] += 1
            elif stats['success_rate'] < 90.0:
                global_stats['assets_below_90'] += 1
            
            # Mostra esempio di tupla
            if stats['example_tuple']:
                example = stats['example_tuple']
                self.logger.info("  ESEMPIO TUPLA BACKUP:")
                self.logger.info(f"    Timestamp: {example['timestamp']}")
                self.logger.info(f"    Asset ID: {example['asset_id']}")
                self.logger.info(f"    Metric Name: {example['metric_name']}")
                self.logger.info(f"    Value: {example['value']} ({example['backup_result']})")
            else:
                self.logger.info("  ESEMPIO TUPLA BACKUP: Nessun dato disponibile")
            
            # Mostra statistiche
            self.logger.info(f"  STATISTICHE BACKUP:")
            self.logger.info(f"    Totale backup: {stats['total_backups']}")
            self.logger.info(f"    Backup riusciti: {stats['successful_backups']}")
            self.logger.info(f"    Backup falliti: {stats['failed_backups']}")
            self.logger.info(f"    Giorni con backup: {stats['days_with_backups']}")
            self.logger.info(f"    Backup per giorno: {stats['backups_per_day']}")
            self.logger.info(f"    Tasso di successo (RPO): {stats['success_rate']}%")
            
            # Valutazione RPO
            if stats['success_rate'] >= 99.0:
                rpo_status = "ECCELLENTE"
            elif stats['success_rate'] >= 95.0:
                rpo_status = "BUONO"
            elif stats['success_rate'] >= 90.0:
                rpo_status = "ACCETTABILE"
            elif stats['success_rate'] >= 80.0:
                rpo_status = "CRITICO - RICHIEDE ATTENZIONE"
            else:
                rpo_status = "GRAVE - AZIONE IMMEDIATA RICHIESTA"
            
            self.logger.info(f"    Valutazione RPO: {rpo_status}")
        
        # === RIEPILOGO GLOBALE ===
        self.logger.info("\n" + "=" * 60)
        self.logger.info("RIEPILOGO GLOBALE BACKUP")
        self.logger.info("=" * 60)
        
        global_success_rate = (
            (global_stats['total_successful'] / global_stats['total_backups'] * 100)
            if global_stats['total_backups'] > 0 else 0.0
        )
        
        self.logger.info(f"Totale asset analizzati: {total_assets}")
        self.logger.info(f"Totale backup eseguiti: {global_stats['total_backups']}")
        self.logger.info(f"Backup riusciti: {global_stats['total_successful']}")
        self.logger.info(f"Backup falliti: {global_stats['total_failed']}")
        self.logger.info(f"Tasso di successo globale: {global_success_rate:.2f}%")
        self.logger.info(f"")
        self.logger.info(f"DISTRIBUZIONE DELLA QUALITÀ DEI BACKUP:")
        self.logger.info(f"  Asset con 100% successo: {global_stats['assets_100_percent']} ({(global_stats['assets_100_percent']/total_assets*100):.1f}%)")
        self.logger.info(f"  Asset con ≥95% successo: {global_stats['assets_above_95']} ({(global_stats['assets_above_95']/total_assets*100):.1f}%)")
        self.logger.info(f"  Asset con <90% successo: {global_stats['assets_below_90']} ({(global_stats['assets_below_90']/total_assets*100):.1f}%)")
        
        # Raccomandazioni
        self.logger.info(f"\nRACCOMANDAZIONI:")
        if global_success_rate >= 95.0:
            self.logger.info("✅ Il sistema di backup funziona correttamente")
        elif global_success_rate >= 90.0:
            self.logger.info("⚠️  Il sistema di backup richiede attenzione")
        else:
            self.logger.info("🚨 Il sistema di backup ha problemi gravi - azione immediata richiesta")
        
        if global_stats['assets_below_90'] > 0:
            self.logger.info(f"🔍 Investigare gli {global_stats['assets_below_90']} asset con basso tasso di successo")


def main():
    """
    Funzione principale per eseguire il riassunto delle metriche di backup.
    """
    parser = argparse.ArgumentParser(
        description="Genera riassunto delle metriche di backup"
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
        summary_generator = BackupSummary(storage_manager)
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
