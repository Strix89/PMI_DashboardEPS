#!/usr/bin/env python3
"""
Analizzatore Cumulativo delle Metriche di Resilienza dei Backup

Questo modulo genera un'analisi cumulativa delle metriche di resilienza per backup jobs e asset
con backup, simulando ora per ora per una settimana il punteggio di resilienza.

Per ogni backup job/asset calcola:
1. RPO Compliance: max(0, 1 - (actual_RPO / target_RPO))
2. Success Rate: backup_riusciti_cumulativi / backup_totali_cumulativi
3. Resilience Score: (w_RPO × RPO_Compliance) + (w_Success × Success_Rate)

Usage:
    python metrics_dashboard/utils/cumulative_resilience_analyzer.py
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
    level=logging.DEBUG,  # Cambiato da INFO a DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ResilienceLevel(Enum):
    """Enum per i livelli di resilienza basati sul punteggio."""
    EXCELLENT = "EXCELLENT"      # > 90%
    GOOD = "GOOD"               # 75% - 90%
    ACCEPTABLE = "ACCEPTABLE"    # 60% - 75%
    CRITICAL = "CRITICAL"       # 40% - 60%
    SEVERE = "SEVERE"           # < 40%


class CumulativeResilienceAnalyzer:
    """
    Classe per l'analisi cumulativa delle metriche di resilienza dei backup.
    """
    
    def __init__(self, storage_manager: StorageManager, config: Optional[Dict[str, Any]] = None):
        """
        Inizializza l'analizzatore.
        
        Args:
            storage_manager: Istanza del storage manager configurato
            config: Configurazione personalizzata (target_RPO, pesi)
        """
        self.storage_manager = storage_manager
        self.logger = logger
        
        # Sempre una settimana (168 ore)
        self.simulation_hours = 168
        
        # Configurazione personalizzata se fornita
        self.config = config  # Salva la configurazione originale
        if config:
            self.asset_rpo_targets = config.get('asset_rpo_targets', {})
            self.backup_job_rpo_targets = config.get('backup_job_rpo_targets', {})
            self.asset_weights = config.get('asset_weights', {})
            self.backup_job_weights = config.get('backup_job_weights', {})
            
            # Log della configurazione caricata per debug
            logger.info(f"Configurazione caricata - Asset RPO targets: {len(self.asset_rpo_targets)} entries")
            logger.info(f"Configurazione caricata - Backup job RPO targets: {len(self.backup_job_rpo_targets)} entries")
            logger.info(f"Configurazione caricata - Asset weights: {len(self.asset_weights)} entries")
            logger.info(f"Configurazione caricata - Backup job weights: {len(self.backup_job_weights)} entries")
        else:
            self.asset_rpo_targets = {}
            self.backup_job_rpo_targets = {}
            self.asset_weights = {}
            self.backup_job_weights = {}
            logger.info("Nessuna configurazione personalizzata fornita, uso valori default")
        
        # Configurazione default per target RPO (in ore)
        self.default_rpo_config = {
            "vm": 24,                    # Virtual Machines - 24 ore
            "container": 12,             # Container - 12 ore  
            "physical_host": 48,         # Server fisici - 48 ore
            "proxmox_node": 24,         # Nodi Proxmox - 24 ore
            "acronis_backup_job": 24,   # Backup job Acronis - 24 ore
            "default": 24               # Valore di default
        }
        
        # Configurazione default per pesi delle metriche
        self.default_weights = {
            "w_rpo": 0.6,      # Peso per RPO Compliance (60%)
            "w_success": 0.4   # Peso per Success Rate (40%)
        }
        
        # Soglie per determinare il livello di resilienza
        self.resilience_thresholds = {
            "excellent": 0.9,    # > 90% = EXCELLENT
            "good": 0.75,        # 75%-90% = GOOD
            "acceptable": 0.6,   # 60%-75% = ACCEPTABLE
            "critical": 0.4      # 40%-60% = CRITICAL, < 40% = SEVERE
        }
    
    def get_target_rpo_hours(self, entity_id: str, entity_type: str, is_backup_job: bool = False) -> int:
        """
        Ottiene il target RPO in ore per un asset o backup job.
        
        Args:
            entity_id: ID dell'asset o backup job
            entity_type: Tipo dell'asset (vm, container, etc.)
            is_backup_job: True se è un backup job, False se è un asset
            
        Returns:
            Target RPO in ore
        """
        if is_backup_job:
            # Controlla configurazione personalizzata per backup job
            if entity_id in self.backup_job_rpo_targets:
                target_rpo = self.backup_job_rpo_targets[entity_id]
                self.logger.debug(f"Target RPO personalizzato per backup job {entity_id}: {target_rpo}h")
                return target_rpo
            default_rpo = self.default_rpo_config.get("acronis_backup_job", 24)
            self.logger.debug(f"Target RPO default per backup job {entity_id}: {default_rpo}h")
            return default_rpo
        else:
            # Controlla configurazione personalizzata per asset
            if entity_id in self.asset_rpo_targets:
                target_rpo = self.asset_rpo_targets[entity_id]
                self.logger.debug(f"Target RPO personalizzato per asset {entity_id}: {target_rpo}h")
                return target_rpo
            default_rpo = self.default_rpo_config.get(entity_type, self.default_rpo_config["default"])
            self.logger.debug(f"Target RPO default per asset {entity_id} (tipo {entity_type}): {default_rpo}h")
            return default_rpo
    
    def get_weights(self, entity_id: str, is_backup_job: bool = False) -> Dict[str, float]:
        """
        Ottiene i pesi per le metriche di un asset o backup job.
        
        Args:
            entity_id: ID dell'asset o backup job
            is_backup_job: True se è un backup job, False se è un asset
            
        Returns:
            Dizionario con i pesi w_rpo e w_success
        """
        if is_backup_job:
            if entity_id in self.backup_job_weights:
                weights = self.backup_job_weights[entity_id]
                self.logger.debug(f"Pesi personalizzati per backup job {entity_id}: {weights}")
                return weights
        else:
            if entity_id in self.asset_weights:
                weights = self.asset_weights[entity_id]
                self.logger.debug(f"Pesi personalizzati per asset {entity_id}: {weights}")
                return weights
        
        default_weights = self.default_weights.copy()
        self.logger.debug(f"Pesi default per {entity_id}: {default_weights}")
        return default_weights
    
    def calculate_rpo_compliance(self, last_successful_backup: Optional[datetime], 
                               current_time: datetime, target_rpo_hours: int) -> float:
        """
        Calcola la RPO Compliance.
        
        Args:
            last_successful_backup: Timestamp dell'ultimo backup riuscito
            current_time: Timestamp corrente
            target_rpo_hours: Target RPO in ore
            
        Returns:
            Punteggio RPO Compliance (0.0 - 1.0)
        """
        if last_successful_backup is None:
            return 1.0  # Nessun backup ancora riuscito = compliance perfetta (100%)
        
        # Calcola actual RPO in ore
        time_diff = current_time - last_successful_backup
        actual_rpo_hours = time_diff.total_seconds() / 3600
        
        # Se actual_rpo_hours è negativo (backup nel futuro), considera RPO = 0
        if actual_rpo_hours < 0:
            actual_rpo_hours = 0
        
        # Formula: max(0, 1 - (actual_RPO / target_RPO))
        # Assicuriamo che il risultato sia sempre tra 0 e 1
        rpo_compliance = max(0.0, min(1.0, 1.0 - (actual_rpo_hours / target_rpo_hours)))
        return rpo_compliance
    
    def calculate_success_rate(self, total_successful: int, total_attempted: int) -> float:
        """
        Calcola il Success Rate cumulativo.
        
        Args:
            total_successful: Numero totale di backup riusciti
            total_attempted: Numero totale di backup tentati
            
        Returns:
            Success Rate (0.0 - 1.0)
        """
        if total_attempted == 0:
            return 1.0  # Default al 100% se non ci sono ancora tentativi
        
        return total_successful / total_attempted
    
    def calculate_resilience_score(self, rpo_compliance: float, success_rate: float,
                                 weights: Dict[str, float]) -> float:
        """
        Calcola il punteggio finale di resilienza.
        
        Args:
            rpo_compliance: Punteggio RPO Compliance (0.0 - 1.0)
            success_rate: Success Rate (0.0 - 1.0)
            weights: Dizionario con pesi w_rpo e w_success
            
        Returns:
            Punteggio finale di resilienza (0.0 - 1.0)
        """
        w_rpo = weights.get('w_rpo', 0.6)
        w_success = weights.get('w_success', 0.4)
        
        return (w_rpo * rpo_compliance) + (w_success * success_rate)
    
    def determine_resilience_level(self, score: float) -> ResilienceLevel:
        """
        Determina il livello di resilienza basato sul punteggio.
        
        Args:
            score: Punteggio di resilienza (0.0 - 1.0)
            
        Returns:
            Livello di resilienza
        """
        if score >= self.resilience_thresholds["excellent"]:
            return ResilienceLevel.EXCELLENT
        elif score >= self.resilience_thresholds["good"]:
            return ResilienceLevel.GOOD
        elif score >= self.resilience_thresholds["acceptable"]:
            return ResilienceLevel.ACCEPTABLE
        elif score >= self.resilience_thresholds["critical"]:
            return ResilienceLevel.CRITICAL
        else:
            return ResilienceLevel.SEVERE
    
    def get_backup_jobs(self) -> List[Dict[str, Any]]:
        """
        Ottiene tutti i backup job Acronis dal database.
        
        Returns:
            Lista di backup job
        """
        try:
            backup_jobs = self.storage_manager.get_assets_by_type(asset_type="acronis_backup_job")
            self.logger.info(f"Trovati {len(backup_jobs)} backup job Acronis")
            return backup_jobs
        except Exception as e:
            self.logger.error(f"Errore nell'ottenere i backup job: {e}")
            return []
    
    def get_assets_with_backup_data(self) -> List[Dict[str, Any]]:
        """
        Ottiene tutti gli asset che hanno metriche di backup.
        
        Returns:
            Lista di asset con dati di backup
        """
        try:
            # Ottieni tutte le metriche di backup per trovare gli asset
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
                    continue
            
            self.logger.info(f"Trovati {len(assets_with_backups)} asset con dati di backup")
            return assets_with_backups
        except Exception as e:
            self.logger.error(f"Errore nell'ottenere gli asset con backup: {e}")
            return []
    
    def get_backup_metrics_for_entity(self, entity_id: str, 
                                    start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """
        Ottiene le metriche di backup per un'entità in un intervallo di tempo.
        
        Args:
            entity_id: ID dell'entità (asset o target di backup job)
            start_time: Inizio dell'intervallo
            end_time: Fine dell'intervallo
            
        Returns:
            Lista di metriche di backup ordinate per timestamp
        """
        try:
            metrics = self.storage_manager.get_metrics(
                asset_id=entity_id,
                metric_name="backup_status",
                start_time=start_time,
                end_time=end_time
            )
            
            # Ordina per timestamp
            metrics.sort(key=lambda x: x.get('timestamp', datetime.min))
            return metrics
        except Exception as e:
            self.logger.error(f"Errore nel recuperare metriche per {entity_id}: {e}")
            return []
    
    def simulate_entity_resilience(self, entity_id: str, entity_type: str, 
                                 start_time: datetime, is_backup_job: bool = False):
        """
        Simula la resilienza di un'entità ora per ora per una settimana.
        
        Args:
            entity_id: ID dell'entità
            entity_type: Tipo dell'entità
            start_time: Tempo di inizio della simulazione
            is_backup_job: True se è un backup job
            
        Returns:
            Tupla con:
            - Lista di risultati per ogni ora
            - Configurazione utilizzata per questa entità
        """
        results = []
        end_time = start_time + timedelta(hours=self.simulation_hours)
        
        # Ottieni configurazioni per questa entità
        target_rpo_hours = self.get_target_rpo_hours(entity_id, entity_type, is_backup_job)
        weights = self.get_weights(entity_id, is_backup_job)
        
        # Prepara info sulla configurazione utilizzata
        config_used = {
            "target_rpo_hours": target_rpo_hours,
            "weights": weights.copy(),
            "rpo_source": "custom" if (self.config and 
                                     (entity_id in self.config.get("asset_rpo_targets", {}) or
                                      entity_id in self.config.get("backup_job_rpo_targets", {}))) else "default",
            "weights_source": "custom" if (self.config and 
                                         (entity_id in self.config.get("asset_weights", {}) or
                                          entity_id in self.config.get("backup_job_weights", {}))) else "default"
        }
        
        # Ottieni tutte le metriche di backup per l'intera finestra
        all_metrics = self.get_backup_metrics_for_entity(entity_id, start_time, end_time)
        
        # Inizializza contatori cumulativi
        total_backups_attempted = 0
        total_backups_successful = 0
        last_successful_backup = None
        
        # Simula ora per ora
        for hour in range(self.simulation_hours):
            current_time = start_time + timedelta(hours=hour)
            hour_end = current_time + timedelta(hours=1)
            
            # Controlla se ci sono nuovi backup in quest'ora
            for metric in all_metrics:
                metric_time = metric.get('timestamp')
                if metric_time and current_time <= metric_time < hour_end:
                    total_backups_attempted += 1
                    
                    # Gestisce sia metriche semplici (0/1) che complesse (oggetti)
                    metric_value = metric.get('value', 0)
                    if isinstance(metric_value, dict):
                        # Metrica complessa con backup_completed
                        if metric_value.get('backup_completed', 0) == 1.0:
                            total_backups_successful += 1
                            last_successful_backup = metric_time
                    elif metric_value == 1.0:  # Backup riuscito (metrica semplice)
                        total_backups_successful += 1
                        last_successful_backup = metric_time
            
            # Calcola le metriche per quest'ora
            rpo_compliance = self.calculate_rpo_compliance(
                last_successful_backup, current_time, target_rpo_hours
            )
            
            # Per l'ora 0, considera lo stato iniziale come ottimale se non ci sono ancora backup riusciti
            if hour == 0 and total_backups_successful == 0:
                success_rate = 1.0  # Stato iniziale perfetto
            else:
                success_rate = self.calculate_success_rate(
                    total_backups_successful, total_backups_attempted
                )
            
            resilience_score = self.calculate_resilience_score(
                rpo_compliance, success_rate, weights
            )
            resilience_level = self.determine_resilience_level(resilience_score)
            
            # Aggiungi il risultato
            results.append({
                "timestamp": current_time.isoformat(),
                "hour": hour,
                "rpo_compliance": round(rpo_compliance, 4),
                "success_rate": round(success_rate, 4),
                "resilience_score": round(resilience_score, 4),
                "resilience_level": resilience_level.value,
                "total_backups_attempted": total_backups_attempted,
                "total_backups_successful": total_backups_successful,
                "actual_rpo_hours": round(
                    max(0, (current_time - last_successful_backup).total_seconds() / 3600), 2
                ) if last_successful_backup else round((current_time - start_time).total_seconds() / 3600, 2),
                "target_rpo_hours": target_rpo_hours
            })
        
        return results, config_used
    
    def generate_analysis(self) -> Dict[str, Any]:
        """
        Genera l'analisi cumulativa completa per backup job e asset.
        
        Returns:
            Dizionario con i risultati dell'analisi
        """
        self.logger.info("Iniziando l'analisi cumulativa di resilienza")
        
        # Calcola il periodo di simulazione (ultima settimana dei dati)
        try:
            # Trova il timestamp più recente nelle metriche di backup
            all_backup_metrics = self.storage_manager.get_metrics(metric_name="backup_status")
            
            if not all_backup_metrics:
                self.logger.error("Nessuna metrica di backup trovata nel database")
                return {}
            
            # Trova il timestamp più recente
            latest_timestamp = max(
                metric.get('timestamp', datetime.min) for metric in all_backup_metrics
            )
            
            if latest_timestamp == datetime.min:
                latest_timestamp = datetime.now(UTC)
            
            # Usa il timestamp più recente come fine della simulazione
            simulation_end = latest_timestamp.replace(minute=0, second=0, microsecond=0)
            simulation_start = simulation_end - timedelta(hours=self.simulation_hours - 1)
            
        except Exception as e:
            self.logger.error(f"Errore nel determinare il periodo di simulazione: {e}")
            return {}
        
        self.logger.info(f"Periodo di simulazione: {simulation_start} - {simulation_end}")
        
        analysis_result = {
            "simulation_period": {
                "start": simulation_start.isoformat(),
                "end": simulation_end.isoformat(),
                "total_hours": self.simulation_hours
            },
            "configuration": {
                "default_target_rpo_hours": self.default_rpo_config.copy(),
                "default_weights": self.default_weights.copy(),
                "resilience_thresholds": self.resilience_thresholds.copy(),
                # Aggiungi configurazione personalizzata utilizzata
                "custom_asset_rpo_targets": self.config.get("asset_rpo_targets", {}).copy() if self.config else {},
                "custom_backup_job_rpo_targets": self.config.get("backup_job_rpo_targets", {}).copy() if self.config else {},
                "custom_asset_weights": self.config.get("asset_weights", {}).copy() if self.config else {},
                "custom_backup_job_weights": self.config.get("backup_job_weights", {}).copy() if self.config else {},
                "has_custom_config": bool(self.config)
            },
            "individual_assets": {}
        }
        
        # Analizza backup job Acronis come asset individuali
        backup_jobs = self.get_backup_jobs()
        for job in backup_jobs:
            job_id = job.get('_id') or job.get('asset_id')
            job_data = job.get('data', {})
            job_name = job_data.get('job_name', 'Unknown')
            
            if not job_id:
                continue
            
            self.logger.info(f"Analizzando backup job come asset individuale: {job_name} (ID: {job_id})")
            
            try:
                # Simula il backup job come entità standalone
                simulation_data, config_used = self.simulate_entity_resilience(
                    job_id, 'acronis_backup_job', simulation_start, is_backup_job=True
                )
                
                analysis_result["individual_assets"][job_id] = {
                    "hostname": job_name,
                    "asset_type": "acronis_backup_job",
                    "job_name": job_name,
                    "description": job_data.get('description', f'Backup job {job_name}'),
                    "destination": job_data.get('destination', 'Unknown'),
                    "backup_path": job_data.get('backup_path', 'Unknown'),
                    "schedule": job_data.get('schedule', 'Unknown'),
                    "backup_type": job_data.get('backup_type', 'Unknown'),
                    "simulation_data": simulation_data,
                    "config_used": config_used
                }
                
            except Exception as e:
                self.logger.error(f"Errore nell'analisi del backup job {job_id}: {e}")
        
        # Analizza asset individuali con dati backup
        assets_with_backups = self.get_assets_with_backup_data()
        for asset in assets_with_backups:
            asset_id = asset.get('_id') or asset.get('asset_id')
            asset_type = asset.get('asset_type', 'unknown')
            hostname = asset.get('hostname', 'N/A')
            
            if not asset_id or asset_id in analysis_result["individual_assets"]:
                continue  # Skip se già processato come backup job
            
            self.logger.info(f"Analizzando asset individuale: {hostname} (ID: {asset_id})")
            
            try:
                # Ottieni la configurazione utilizzata per questo asset
                simulation_data, config_used = self.simulate_entity_resilience(
                    asset_id, asset_type, simulation_start, is_backup_job=False
                )
                
                analysis_result["individual_assets"][asset_id] = {
                    "hostname": hostname,
                    "asset_type": asset_type,
                    "simulation_data": simulation_data,
                    # Usa la configurazione effettivamente utilizzata durante la simulazione
                    "config_used": config_used
                }
                
            except Exception as e:
                self.logger.error(f"Errore nell'analisi dell'asset {asset_id}: {e}")
        
        self.logger.info("Analisi cumulativa completata")
        
        # Calcola il summary aggregato
        total_entities = 0
        aggregated_score_sum = 0.0
        entity_scores = []
        
        # Raccoglie i punteggi finali da individual assets (inclusi backup jobs)
        for asset_id, asset_data in analysis_result["individual_assets"].items():
            if asset_data["simulation_data"]:
                final_score = asset_data["simulation_data"][-1]["resilience_score"]
                entity_scores.append(final_score)
                aggregated_score_sum += final_score
                total_entities += 1
        
        # Calcola il punteggio aggregato e lo status
        if total_entities > 0:
            aggregated_score = aggregated_score_sum / total_entities
            
            # Determina lo status aggregato basato sui threshold
            if aggregated_score >= self.resilience_thresholds["excellent"]:
                aggregated_status = "EXCELLENT"
            elif aggregated_score >= self.resilience_thresholds["good"]:
                aggregated_status = "GOOD"
            elif aggregated_score >= self.resilience_thresholds["acceptable"]:
                aggregated_status = "ACCEPTABLE"
            elif aggregated_score >= self.resilience_thresholds["critical"]:
                aggregated_status = "CRITICAL"
            else:
                aggregated_status = "SEVERE"
        else:
            aggregated_score = 0.0
            aggregated_status = "SEVERE"
        
        # Aggiunge il summary all'analisi
        analysis_result["summary"] = {
            "total_entities": total_entities,
            "aggregated_score": round(aggregated_score, 2),
            "aggregated_status": aggregated_status,
            "simulation_hours": self.simulation_hours
        }
        
        self.logger.info(f"Summary calcolato: {total_entities} entità, score aggregato: {aggregated_score:.2f}, status: {aggregated_status}")
        
        return analysis_result
    
    def save_analysis_to_json(self, analysis: Dict[str, Any], 
                            output_file: Optional[str] = None) -> str:
        """
        Salva l'analisi su file JSON.
        
        Args:
            analysis: Dizionario con i risultati dell'analisi
            output_file: Nome del file di output (opzionale)
            
        Returns:
            Nome del file salvato
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Salva nella cartella output relativa al modulo metrics_dashboard
            import os
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(script_dir, "output")
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"resilience_analysis_{timestamp}.json")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Analisi salvata su: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"Errore nel salvataggio dell'analisi: {e}")
            raise


def main():
    """
    Funzione principale per eseguire l'analisi cumulativa di resilienza.
    """
    parser = argparse.ArgumentParser(
        description="Genera analisi cumulativa delle metriche di resilienza dei backup"
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
        help="File JSON con configurazione personalizzata (target RPO, pesi)"
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
        analyzer = CumulativeResilienceAnalyzer(storage_manager, config)
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
