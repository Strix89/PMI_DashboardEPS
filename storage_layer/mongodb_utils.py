#!/usr/bin/env python3
"""
MongoDB Utilities - Strumenti di Gestione e Test

Questo modulo fornisce utilità per testare, configurare e gestire
la connessione MongoDB per il sistema PMI Dashboard.

Funzionalità:
- Test di connessione e configurazione
- Diagnostica del database
- Gestione degli indici
- Pulizia e manutenzione
- Backup e ripristino
- Monitoraggio delle performance

Utilizzo:
    python storage_layer/mongodb_utils.py --test-connection
    python storage_layer/mongodb_utils.py --create-indexes
    python storage_layer/mongodb_utils.py --database-stats

Autore: PMI Dashboard Team
Data: Febbraio 2025
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Any, Optional
from pathlib import Path

# Aggiungi il percorso del progetto al PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage_layer.mongodb_config import MongoDBConfig, mongodb_config
from storage_layer.storage_manager import StorageManager
from storage_layer.exceptions import StorageManagerError


class MongoDBUtils:
    """
    Classe di utilità per la gestione e il test di MongoDB.
    """
    
    def __init__(self):
        """Inizializza le utilità MongoDB."""
        self.config = MongoDBConfig()
        self.logger = logging.getLogger(__name__)
        
    def test_connection(self) -> bool:
        """
        Testa la connessione a MongoDB con diagnostica dettagliata.
        
        Returns:
            True se la connessione è riuscita, False altrimenti
        """
        print("🔍 Test di connessione MongoDB...")
        
        try:
            # Test connessione base
            if not self.config.test_connection():
                print("❌ Connessione fallita")
                return False
            
            print("✅ Connessione stabilita con successo")
            
            # Informazioni sul server
            server_info = self.config.get_server_info()
            if server_info:
                print(f"📊 Server MongoDB:")
                print(f"   ├── Versione: {server_info.get('version', 'N/A')}")
                print(f"   ├── Platform: {server_info.get('targetMinOS', 'N/A')}")
                print(f"   └── Uptime: {server_info.get('uptimeMillis', 0) // 1000} secondi")
            
            # Statistiche database
            db_stats = self.config.get_database_stats()
            if db_stats:
                print(f"💾 Database '{self.config.config['database']}':")
                print(f"   ├── Collezioni: {db_stats.get('collections', 0)}")
                print(f"   ├── Documenti: {db_stats.get('objects', 0):,}")
                print(f"   ├── Dimensione dati: {self._format_bytes(db_stats.get('dataSize', 0))}")
                print(f"   └── Dimensione storage: {self._format_bytes(db_stats.get('storageSize', 0))}")
            
            return True
            
        except Exception as e:
            print(f"❌ Errore durante il test: {e}")
            return False
    
    def show_configuration(self):
        """Mostra la configurazione MongoDB corrente."""
        print("⚙️  Configurazione MongoDB:")
        
        config = self.config.config
        
        # Configurazione base
        print("📋 Connessione:")
        print(f"   ├── Host: {config['host']}")
        print(f"   ├── Porta: {config['port']}")
        print(f"   ├── Database: {config['database']}")
        print(f"   ├── Ambiente: {config['environment']}")
        print(f"   └── SSL: {'Abilitato' if config['ssl_enabled'] else 'Disabilitato'}")
        
        # Autenticazione
        print("🔐 Autenticazione:")
        auth_status = "Configurata" if config['username'] else "Non configurata"
        print(f"   ├── Status: {auth_status}")
        if config['username']:
            print(f"   ├── Username: {config['username']}")
            print(f"   └── Auth Source: {config['auth_source']}")
        
        # Pool connessioni
        print("🏊 Pool Connessioni:")
        print(f"   ├── Max Pool Size: {config['max_pool_size']}")
        print(f"   ├── Min Pool Size: {config['min_pool_size']}")
        print(f"   └── Max Idle Time: {config['max_idle_time_ms']}ms")
        
        # Timeout
        print("⏱️  Timeout:")
        print(f"   ├── Connect: {config['connect_timeout_ms']}ms")
        print(f"   ├── Server Selection: {config['server_selection_timeout_ms']}ms")
        print(f"   └── Socket: {config['socket_timeout_ms']}ms")
    
    def create_indexes(self) -> bool:
        """
        Crea gli indici ottimali per le collezioni del sistema.
        
        Returns:
            True se gli indici sono stati creati con successo
        """
        print("📇 Creazione indici MongoDB...")
        
        try:
            db = self.config.get_database()
            
            # Indici per la collezione assets
            print("   ├── Indici collezione 'assets'...")
            assets_collection = db.assets
            
            # Indice su asset_id (unico)
            assets_collection.create_index("asset_id", unique=True)
            print("   │   ├── asset_id (unique) ✅")
            
            # Indice su asset_type
            assets_collection.create_index("asset_type")
            print("   │   ├── asset_type ✅")
            
            # Indice su hostname
            assets_collection.create_index("hostname")
            print("   │   ├── hostname ✅")
            
            # Indice composto per servizi
            assets_collection.create_index([("asset_type", 1), ("data.parent_asset_id", 1)])
            print("   │   └── asset_type + parent_asset_id ✅")
            
            # Indici per la collezione metrics
            print("   └── Indici collezione 'metrics'...")
            metrics_collection = db.metrics
            
            # Indice composto principale (asset_id + timestamp)
            metrics_collection.create_index([("asset_id", 1), ("timestamp", -1)])
            print("       ├── asset_id + timestamp ✅")
            
            # Indice su metric_name
            metrics_collection.create_index("metric_name")
            print("       ├── metric_name ✅")
            
            # Indice composto per query temporali
            metrics_collection.create_index([("asset_id", 1), ("metric_name", 1), ("timestamp", -1)])
            print("       ├── asset_id + metric_name + timestamp ✅")
            
            # Indice TTL per pulizia automatica (opzionale, 90 giorni)
            metrics_collection.create_index("timestamp", expireAfterSeconds=90*24*60*60)
            print("       └── TTL index (90 giorni) ✅")
            
            print("✅ Tutti gli indici creati con successo")
            return True
            
        except Exception as e:
            print(f"❌ Errore nella creazione degli indici: {e}")
            return False
    
    def show_indexes(self):
        """Mostra tutti gli indici esistenti."""
        print("📇 Indici MongoDB esistenti:")
        
        try:
            db = self.config.get_database()
            
            # Indici assets
            print("📁 Collezione 'assets':")
            assets_indexes = db.assets.list_indexes()
            for idx in assets_indexes:
                name = idx.get('name', 'N/A')
                keys = idx.get('key', {})
                unique = " (UNIQUE)" if idx.get('unique', False) else ""
                print(f"   ├── {name}: {dict(keys)}{unique}")
            
            # Indici metrics
            print("📈 Collezione 'metrics':")
            metrics_indexes = db.metrics.list_indexes()
            for idx in metrics_indexes:
                name = idx.get('name', 'N/A')
                keys = idx.get('key', {})
                ttl = f" (TTL: {idx['expireAfterSeconds']}s)" if 'expireAfterSeconds' in idx else ""
                print(f"   ├── {name}: {dict(keys)}{ttl}")
                
        except Exception as e:
            print(f"❌ Errore nel recupero degli indici: {e}")
    
    def database_stats(self):
        """Mostra statistiche dettagliate del database."""
        print("📊 Statistiche Database MongoDB:")
        
        try:
            db = self.config.get_database()
            
            # Statistiche generali
            db_stats = db.command('dbStats')
            print("💾 Statistiche Generali:")
            print(f"   ├── Database: {db_stats.get('db', 'N/A')}")
            print(f"   ├── Collezioni: {db_stats.get('collections', 0)}")
            print(f"   ├── Documenti totali: {db_stats.get('objects', 0):,}")
            print(f"   ├── Dimensione dati: {self._format_bytes(db_stats.get('dataSize', 0))}")
            print(f"   ├── Dimensione storage: {self._format_bytes(db_stats.get('storageSize', 0))}")
            print(f"   └── Dimensione indici: {self._format_bytes(db_stats.get('indexSize', 0))}")
            
            # Statistiche per collezione
            collections = db.list_collection_names()
            if collections:
                print("📁 Statistiche per Collezione:")
                for collection_name in collections:
                    coll_stats = db.command('collStats', collection_name)
                    count = coll_stats.get('count', 0)
                    size = coll_stats.get('size', 0)
                    avg_size = coll_stats.get('avgObjSize', 0)
                    
                    print(f"   ├── {collection_name}:")
                    print(f"   │   ├── Documenti: {count:,}")
                    print(f"   │   ├── Dimensione: {self._format_bytes(size)}")
                    print(f"   │   └── Dimensione media doc: {self._format_bytes(avg_size)}")
            
            # Informazioni sui backup (se disponibili)
            self._show_backup_info(db)
            
        except Exception as e:
            print(f"❌ Errore nel recupero delle statistiche: {e}")
    
    def cleanup_old_data(self, days: int = 30) -> bool:
        """
        Pulisce i dati più vecchi di N giorni.
        
        Args:
            days: Numero di giorni da mantenere
            
        Returns:
            True se la pulizia è riuscita
        """
        print(f"🧹 Pulizia dati più vecchi di {days} giorni...")
        
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days)
            
            db = self.config.get_database()
            
            # Pulizia metriche vecchie
            result = db.metrics.delete_many({
                "timestamp": {"$lt": cutoff_date}
            })
            
            deleted_count = result.deleted_count
            print(f"   ├── Metriche eliminate: {deleted_count:,}")
            
            # Compattazione database (opzionale)
            print("   └── Compattazione database...")
            db.command('compact', 'metrics')
            
            print("✅ Pulizia completata con successo")
            return True
            
        except Exception as e:
            print(f"❌ Errore durante la pulizia: {e}")
            return False
    
    def backup_database(self, backup_path: str) -> bool:
        """
        Crea un backup del database.
        
        Args:
            backup_path: Percorso dove salvare il backup
            
        Returns:
            True se il backup è riuscito
        """
        print(f"💾 Creazione backup database...")
        
        try:
            import subprocess
            
            config = self.config.config
            
            # Costruisci comando mongodump
            cmd = [
                'mongodump',
                '--host', f"{config['host']}:{config['port']}",
                '--db', config['database'],
                '--out', backup_path
            ]
            
            # Aggiungi autenticazione se configurata
            if config['username']:
                cmd.extend(['--username', config['username']])
                cmd.extend(['--password', config['password']])
                cmd.extend(['--authenticationDatabase', config['auth_source']])
            
            # Esegui backup
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Backup creato in: {backup_path}")
                return True
            else:
                print(f"❌ Errore backup: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Errore durante il backup: {e}")
            return False
    
    def performance_test(self, duration: int = 60) -> Dict[str, Any]:
        """
        Esegue un test di performance del database.
        
        Args:
            duration: Durata del test in secondi
            
        Returns:
            Dizionario con i risultati del test
        """
        print(f"🚀 Test di performance MongoDB ({duration}s)...")
        
        try:
            storage_manager = StorageManager()
            
            # Metriche del test
            operations = 0
            start_time = time.time()
            errors = 0
            
            print("   ├── Test lettura asset...")
            while time.time() - start_time < duration / 3:
                try:
                    assets = storage_manager.get_all_assets()
                    operations += 1
                except Exception:
                    errors += 1
                
                if operations % 100 == 0:
                    elapsed = time.time() - start_time
                    ops_per_sec = operations / elapsed
                    print(f"   │   └── {operations} ops, {ops_per_sec:.1f} ops/sec")
            
            read_ops = operations
            read_time = time.time() - start_time
            
            print("   ├── Test lettura metriche...")
            operations = 0
            start_time = time.time()
            
            while time.time() - start_time < duration / 3:
                try:
                    # Simula query tipiche
                    end_time = datetime.now(UTC)
                    start_time_query = end_time - timedelta(hours=1)
                    
                    metrics = storage_manager.get_metrics_by_time_range(
                        start_time=start_time_query,
                        end_time=end_time,
                        limit=100
                    )
                    operations += 1
                except Exception:
                    errors += 1
                
                if operations % 50 == 0:
                    elapsed = time.time() - start_time
                    ops_per_sec = operations / elapsed
                    print(f"   │   └── {operations} ops, {ops_per_sec:.1f} ops/sec")
            
            query_ops = operations
            query_time = time.time() - start_time
            
            # Risultati
            results = {
                'read_operations': read_ops,
                'read_ops_per_sec': read_ops / read_time,
                'query_operations': query_ops,
                'query_ops_per_sec': query_ops / query_time,
                'total_errors': errors,
                'test_duration': duration
            }
            
            print("📊 Risultati Test Performance:")
            print(f"   ├── Lettura asset: {results['read_ops_per_sec']:.1f} ops/sec")
            print(f"   ├── Query metriche: {results['query_ops_per_sec']:.1f} ops/sec")
            print(f"   └── Errori totali: {results['total_errors']}")
            
            return results
            
        except Exception as e:
            print(f"❌ Errore durante il test di performance: {e}")
            return {}
    
    def _format_bytes(self, bytes_value: int) -> str:
        """
        Formatta i byte in unità leggibili.
        
        Args:
            bytes_value: Valore in byte
            
        Returns:
            Stringa formattata (es. "1.5 MB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    def _show_backup_info(self, db):
        """Mostra informazioni sui backup se disponibili."""
        try:
            # Cerca job di backup Acronis
            backup_jobs = list(db.assets.find({"asset_type": "acronis_backup_job"}))
            
            if backup_jobs:
                print("💾 Job di Backup Acronis:")
                for job in backup_jobs:
                    job_name = job.get('data', {}).get('job_name', 'N/A')
                    status = job.get('data', {}).get('status', 'N/A')
                    last_run = job.get('data', {}).get('last_run', 'N/A')
                    
                    print(f"   ├── {job_name}:")
                    print(f"   │   ├── Status: {status}")
                    print(f"   │   └── Ultimo run: {last_run}")
                    
        except Exception:
            # Ignora errori nella visualizzazione backup info
            pass


def main():
    """Funzione principale per l'esecuzione da riga di comando."""
    parser = argparse.ArgumentParser(
        description="Utilità per la gestione e il test di MongoDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi di utilizzo:
  python mongodb_utils.py --test-connection
  python mongodb_utils.py --show-config
  python mongodb_utils.py --create-indexes
  python mongodb_utils.py --database-stats
  python mongodb_utils.py --cleanup-old-data --days 30
  python mongodb_utils.py --performance-test --duration 120
        """
    )
    
    # Opzioni principali
    parser.add_argument('--test-connection', action='store_true',
                       help='Testa la connessione a MongoDB')
    parser.add_argument('--show-config', action='store_true',
                       help='Mostra la configurazione MongoDB')
    parser.add_argument('--create-indexes', action='store_true',
                       help='Crea gli indici ottimali')
    parser.add_argument('--show-indexes', action='store_true',
                       help='Mostra gli indici esistenti')
    parser.add_argument('--database-stats', action='store_true',
                       help='Mostra statistiche del database')
    parser.add_argument('--cleanup-old-data', action='store_true',
                       help='Pulisce i dati vecchi')
    parser.add_argument('--backup-database', metavar='PATH',
                       help='Crea backup del database nel percorso specificato')
    parser.add_argument('--performance-test', action='store_true',
                       help='Esegue test di performance')
    
    # Opzioni aggiuntive
    parser.add_argument('--days', type=int, default=30,
                       help='Giorni da mantenere per la pulizia (default: 30)')
    parser.add_argument('--duration', type=int, default=60,
                       help='Durata test performance in secondi (default: 60)')
    parser.add_argument('--verbose', action='store_true',
                       help='Output dettagliato')
    
    args = parser.parse_args()
    
    # Configura logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Crea istanza utilità
    utils = MongoDBUtils()
    
    # Esegui azioni richieste
    if args.test_connection:
        success = utils.test_connection()
        sys.exit(0 if success else 1)
    
    if args.show_config:
        utils.show_configuration()
    
    if args.create_indexes:
        success = utils.create_indexes()
        if not success:
            sys.exit(1)
    
    if args.show_indexes:
        utils.show_indexes()
    
    if args.database_stats:
        utils.database_stats()
    
    if args.cleanup_old_data:
        success = utils.cleanup_old_data(args.days)
        if not success:
            sys.exit(1)
    
    if args.backup_database:
        success = utils.backup_database(args.backup_database)
        if not success:
            sys.exit(1)
    
    if args.performance_test:
        results = utils.performance_test(args.duration)
        if not results:
            sys.exit(1)
    
    # Se nessuna azione specificata, mostra help
    if not any([args.test_connection, args.show_config, args.create_indexes,
                args.show_indexes, args.database_stats, args.cleanup_old_data,
                args.backup_database, args.performance_test]):
        parser.print_help()


if __name__ == '__main__':
    main()