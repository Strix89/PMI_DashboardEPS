"""
PMI Dashboard EPS - Discovery Engine
Main Entry Point

Script principale per eseguire la discovery di rete.
Supporta modalità CLI e configurazioni personalizzate.

Author: PMI Dashboard EPS Team
Date: 27 Agosto 2025

Usage:
    python discovery_main.py [--config CONFIG_PATH] [--range TARGET_RANGE] [--output OUTPUT_DIR] [--verbose]
"""

import sys
import argparse
import logging
from pathlib import Path

# Aggiunge il percorso src al PYTHONPATH
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from discovery import DiscoveryEngine

def setup_cli_logging(verbose: bool = False) -> None:
    """
    Configura logging per CLI.
    
    Args:
        verbose: Se True, abilita logging DEBUG
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Riduce verbosità di alcuni logger
    if not verbose:
        logging.getLogger('discovery.scanners').setLevel(logging.WARNING)

def parse_arguments():
    """
    Parsing argomenti CLI.
    
    Returns:
        Argomenti parsati
    """
    parser = argparse.ArgumentParser(
        description='PMI Dashboard EPS - Discovery Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  # Discovery con configurazione predefinita
  python discovery_main.py
  
  # Discovery con range personalizzato
  python discovery_main.py --range 192.168.1.0/24
  
  # Discovery con configurazione personalizzata
  python discovery_main.py --config /path/to/config.yml
  
  # Discovery con output verboso
  python discovery_main.py --verbose
  
  # Discovery con directory output personalizzata
  python discovery_main.py --output /path/to/output
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Percorso file configurazione personalizzato'
    )
    
    parser.add_argument(
        '--range', '-r',
        type=str,
        help='Range di rete target (es. 192.168.1.0/24) - override configurazione'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Directory output personalizzata'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Output verboso (livello DEBUG)'
    )
    
    parser.add_argument(
        '--info', '-i',
        action='store_true',
        help='Mostra solo informazioni configurazione senza eseguire discovery'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='PMI Dashboard EPS Discovery Engine v1.0.0'
    )
    
    return parser.parse_args()

def print_configuration_info(engine: DiscoveryEngine) -> None:
    """
    Stampa informazioni configurazione.
    
    Args:
        engine: Istanza DiscoveryEngine
    """
    print("\n" + "="*60)
    print("PMI DASHBOARD EPS - DISCOVERY ENGINE")
    print("="*60)
    
    config_summary = engine.get_configuration_summary()
    scanner_status = engine.get_scanner_status()
    
    print(f"\nScan ID: {config_summary['scan_id']}")
    print(f"File configurazione: {config_summary['config_file']}")
    print(f"Target range: {config_summary['target_range']}")
    
    # Mostra esclusioni configurate
    if config_summary['configured_exclude_ranges']:
        print(f"Range esclusi (configurati): {', '.join(config_summary['configured_exclude_ranges'])}")
    
    # Mostra esclusioni finali (inclusi IP locali auto-rilevati)
    if config_summary['final_exclude_ranges']:
        print(f"Range esclusi (finali): {', '.join(config_summary['final_exclude_ranges'])}")
    
    # Mostra informazioni di rete locali
    if config_summary['local_network_info']:
        network_info = config_summary['local_network_info']
        print(f"\nInformazioni rete locale:")
        print(f"  - IP locali rilevati: {', '.join(network_info.get('local_ips', []))}")
        if network_info.get('primary_ip'):
            print(f"  - IP primario: {network_info['primary_ip']}")
        if network_info.get('default_gateway'):
            print(f"  - Gateway predefinito: {network_info['default_gateway']}")
    
    print(f"\nScanner abilitati: {', '.join(config_summary['enabled_scanners'])}")
    
    print(f"\nStato scanner:")
    for scanner_name, scanner_info in scanner_status.items():
        status = "ABILITATO" if scanner_info['enabled'] else "DISABILITATO"
        print(f"  - {scanner_info['name']}: {status}")
        
        if scanner_name == 'nmap_scanner' and scanner_info['enabled']:
            print(f"    NMAP Version: {scanner_info.get('nmap_version', 'N/A')}")
        elif scanner_name == 'snmp_scanner' and scanner_info['enabled']:
            versions = scanner_info.get('versions_supported', [])
            communities = scanner_info.get('communities_configured', 0)
            print(f"    Versioni SNMP: {', '.join(versions)}")
            print(f"    Community configurate: {communities}")
    
    print(f"\nFormati output:")
    for output_info in config_summary['output_formats']:
        print(f"  - {output_info['format'].upper()}: {output_info['file']} ({output_info['type']})")
    
    print("="*60 + "\n")

def main():
    """
    Funzione principale.
    """
    # Parse argomenti
    args = parse_arguments()
    
    # Setup logging CLI
    setup_cli_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    
    try:
        print("Inizializzazione Discovery Engine...")
        
        # Inizializza Discovery Engine
        engine = DiscoveryEngine(args.config)
        
        # Mostra informazioni configurazione
        print_configuration_info(engine)
        
        # Se richiesto solo info, esce
        if args.info:
            print("Informazioni configurazione mostrate. Discovery non eseguita.")
            return
        
        # Richiede conferma se non specificato range
        if not args.range:
            config_summary = engine.get_configuration_summary()
            target_range = config_summary['target_range']
            
            if not target_range:
                print("ERRORE: Target range non specificato nella configurazione.")
                print("Utilizzare --range per specificare un range target.")
                sys.exit(1)
            
            print(f"Verrà eseguita la discovery sul range: {target_range}")
            response = input("Continuare? [y/N]: ")
            if response.lower() not in ['y', 'yes', 'si', 's']:
                print("Discovery annullata dall'utente.")
                sys.exit(0)
        
        # Esegue discovery
        print("\nAvvio discovery...\n")
        
        results = engine.run_discovery(args.range)
        
        # Mostra risultati riassuntivi
        print("\n" + "="*60)
        print("RISULTATI DISCOVERY")
        print("="*60)
        
        metadata = results['discovery_metadata']
        stats = results['scan_statistics']
        
        print(f"Dispositivi trovati: {metadata['total_devices']}")
        print(f"Durata scansione: {metadata['scan_duration_seconds']}s")
        print(f"Metodi utilizzati: {', '.join(metadata['scan_methods_used'])}")
        
        # Statistiche per scanner
        if 'arp_scan' in stats and stats['arp_scan']:
            arp_stats = stats['arp_scan']
            print(f"\nARP Scanner:")
            print(f"  - IP scansionati: {arp_stats.get('total_ips_pinged', 0)}")
            print(f"  - Voci ARP: {arp_stats.get('arp_entries_found', 0)}")
            print(f"  - Durata: {arp_stats.get('scan_time_seconds', 0)}s")
        
        if 'nmap_scan' in stats and stats['nmap_scan']:
            nmap_stats = stats['nmap_scan']
            print(f"\nNMAP Scanner:")
            print(f"  - Host responsive: {nmap_stats.get('responsive_hosts', 0)}")
            print(f"  - Porte aperte: {nmap_stats.get('open_ports_found', 0)}")
            print(f"  - Servizi identificati: {nmap_stats.get('services_identified', 0)}")
            print(f"  - OS fingerprint: {nmap_stats.get('os_fingerprints', 0)}")
            print(f"  - Durata: {nmap_stats.get('scan_time_seconds', 0)}s")
        
        if 'snmp_scan' in stats and stats['snmp_scan']:
            snmp_stats = stats['snmp_scan']
            print(f"\nSNMP Scanner:")
            print(f"  - Host accessibili: {snmp_stats.get('snmp_responsive', 0)}")
            print(f"  - OID raccolti: {snmp_stats.get('total_oids_collected', 0)}")
            print(f"  - SNMPv1: {snmp_stats.get('v1_accessible', 0)}")
            print(f"  - SNMPv2c: {snmp_stats.get('v2c_accessible', 0)}")
            print(f"  - Durata: {snmp_stats.get('scan_time_seconds', 0)}s")
        
        # Errori
        if results['errors']:
            print(f"\nErrori rilevati: {len(results['errors'])}")
            for error in results['errors'][:5]:  # Mostra solo primi 5
                print(f"  - {error.get('error_type', 'unknown')}: {error.get('message', '')}")
        
        print("\n" + "="*60)
        print("Discovery completata con successo!")
        print("Controlla la directory output per i file generati.")
        
    except KeyboardInterrupt:
        logger.info("Discovery interrotta dall'utente")
        print("\nDiscovery interrotta dall'utente.")
        sys.exit(130)
        
    except Exception as e:
        logger.error(f"Errore fatale: {e}")
        print(f"\nERRORE: {e}")
        if args.verbose:
            import traceback
            print("\nTraceback completo:")
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
