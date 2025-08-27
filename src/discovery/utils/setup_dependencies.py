"""
PMI Dashboard EPS - Discovery Engine
Setup Dependencies Script

Script per installare le dipendenze Python necessarie per il Discovery Engine.
Disinstalla prima tutte le dipendenze esistenti nell'environment, 
poi installa quelle specifiche del progetto.

Author: PMI Dashboard EPS Team
Date: 27 Agosto 2025

Usage:
    python setup_dependencies.py [--clean] [--force]
"""

import subprocess
import sys
import logging
from pathlib import Path
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def check_virtual_environment():
    """
    Verifica se stiamo eseguendo in un virtual environment.
    
    Returns:
        True se in virtual environment
    """
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

def get_installed_packages():
    """
    Ottiene la lista dei pacchetti installati.
    
    Returns:
        Lista dei nomi dei pacchetti installati
    """
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list', '--format=freeze'],
            capture_output=True,
            text=True,
            check=True
        )
        
        packages = []
        for line in result.stdout.strip().split('\n'):
            if line and '==' in line:
                package_name = line.split('==')[0]
                packages.append(package_name)
        
        return packages
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Errore ottenimento lista pacchetti: {e}")
        return []

def uninstall_all_packages(force: bool = False):
    """
    Disinstalla tutti i pacchetti Python installati nell'environment.
    
    Args:
        force: Se True, non chiede conferma
    """
    if not check_virtual_environment() and not force:
        logger.error("ATTENZIONE: Non sembra essere un virtual environment!")
        logger.error("Questo script potrebbe danneggiare l'installazione Python di sistema.")
        logger.error("Eseguire in un virtual environment o utilizzare --force")
        return False
    
    logger.info("Ottenimento lista pacchetti installati...")
    packages = get_installed_packages()
    
    if not packages:
        logger.info("Nessun pacchetto da disinstallare trovato.")
        return True
    
    # Filtra pacchetti che non devono essere disinstallati
    protected_packages = {
        'pip', 'setuptools', 'wheel', 'distribute', 'pkg-resources'
    }
    
    packages_to_remove = [pkg for pkg in packages if pkg.lower() not in protected_packages]
    
    if not packages_to_remove:
        logger.info("Nessun pacchetto da disinstallare (solo pacchetti protetti presenti).")
        return True
    
    logger.info(f"Trovati {len(packages_to_remove)} pacchetti da disinstallare:")
    for pkg in packages_to_remove[:10]:  # Mostra primi 10
        logger.info(f"  - {pkg}")
    if len(packages_to_remove) > 10:
        logger.info(f"  ... e altri {len(packages_to_remove) - 10} pacchetti")
    
    if not force:
        response = input(f"\nDisinstallare {len(packages_to_remove)} pacchetti? [y/N]: ")
        if response.lower() not in ['y', 'yes', 'si', 's']:
            logger.info("Disinstallazione annullata dall'utente.")
            return False
    
    # Disinstalla i pacchetti
    logger.info("Avvio disinstallazione pacchetti...")
    
    try:
        # Usa pip uninstall con lista di pacchetti
        cmd = [sys.executable, '-m', 'pip', 'uninstall', '-y'] + packages_to_remove
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minuti timeout
        )
        
        if result.returncode == 0:
            logger.info("Disinstallazione completata con successo!")
            return True
        else:
            logger.error(f"Errore durante disinstallazione: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Timeout durante disinstallazione pacchetti")
        return False
    except Exception as e:
        logger.error(f"Errore imprevisto durante disinstallazione: {e}")
        return False

def upgrade_pip():
    """
    Aggiorna pip alla versione più recente.
    
    Returns:
        True se successo
    """
    logger.info("Aggiornamento pip...")
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'],
            capture_output=True,
            text=True,
            check=True,
            timeout=120
        )
        
        logger.info("Pip aggiornato con successo")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Errore aggiornamento pip: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        logger.error("Timeout aggiornamento pip")
        return False

def install_requirements():
    """
    Installa le dipendenze dal file requirements.txt.
    
    Returns:
        True se successo
    """
    requirements_file = Path(__file__).parent / 'requirements.txt'
    
    if not requirements_file.exists():
        logger.error(f"File requirements.txt non trovato: {requirements_file}")
        return False
    
    logger.info(f"Installazione dipendenze da {requirements_file}...")
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)],
            capture_output=True,
            text=True,
            timeout=600  # 10 minuti timeout
        )
        
        if result.returncode == 0:
            logger.info("Dipendenze installate con successo!")
            
            # Mostra pacchetti installati
            logger.info("Pacchetti installati:")
            for line in result.stdout.split('\n'):
                if 'Successfully installed' in line:
                    packages = line.replace('Successfully installed', '').strip()
                    logger.info(f"  {packages}")
            
            return True
        else:
            logger.error(f"Errore installazione dipendenze:")
            logger.error(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Timeout durante installazione dipendenze")
        return False
    except Exception as e:
        logger.error(f"Errore imprevisto durante installazione: {e}")
        return False

def verify_installation():
    """
    Verifica che le dipendenze chiave siano installate correttamente.
    
    Returns:
        True se tutte le dipendenze sono installate
    """
    logger.info("Verifica installazione dipendenze...")
    
    critical_packages = [
        'python-nmap',
        'pysnmp', 
        'pyasn1',
        'psutil',
        'netaddr',
        'PyYAML',
        'requests',
        'jsonschema',
        'colorama',
        'click',
        'tabulate',
        'matplotlib',
        'plotly',
        'structlog'
    ]
    
    missing_packages = []
    
    for package in critical_packages:
        try:
            # Tenta import per verificare installazione
            if package == 'python-nmap':
                import nmap
            elif package == 'pysnmp':
                import pysnmp
            elif package == 'pyasn1':
                import pyasn1
            elif package == 'psutil':
                import psutil
            elif package == 'netaddr':
                import netaddr
            elif package == 'PyYAML':
                import yaml
            elif package == 'requests':
                import requests
            elif package == 'jsonschema':
                import jsonschema
            elif package == 'colorama':
                import colorama
            elif package == 'click':
                import click
            elif package == 'tabulate':
                import tabulate
            elif package == 'matplotlib':
                import matplotlib
            elif package == 'plotly':
                import plotly
            elif package == 'structlog':
                import structlog
                
            logger.debug(f"✓ {package} installato correttamente")
            
        except ImportError:
            logger.warning(f"✗ {package} non trovato o non funzionante")
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"Pacchetti mancanti o non funzionanti: {', '.join(missing_packages)}")
        return False
    else:
        logger.info("✓ Tutte le dipendenze critiche sono installate correttamente")
        return True

def parse_arguments():
    """
    Parse degli argomenti CLI.
    
    Returns:
        Argomenti parsati
    """
    parser = argparse.ArgumentParser(
        description='PMI Dashboard EPS - Setup Dependencies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  # Setup completo (disinstalla tutto e reinstalla)
  python setup_dependencies.py --clean
  
  # Installa solo dipendenze senza pulire
  python setup_dependencies.py
  
  # Setup forzato senza conferme
  python setup_dependencies.py --clean --force
        """
    )
    
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Disinstalla tutti i pacchetti esistenti prima di installare'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Non chiede conferme (attenzione!)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Output verboso'
    )
    
    return parser.parse_args()

def main():
    """
    Funzione principale.
    """
    args = parse_arguments()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("="*60)
    print("PMI DASHBOARD EPS - SETUP DEPENDENCIES")
    print("="*60)
    
    # Verifica virtual environment
    if check_virtual_environment():
        logger.info(f"✓ Virtual environment rilevato: {sys.prefix}")
    else:
        logger.warning("⚠ Non sembra essere un virtual environment!")
        if not args.force:
            response = input("Continuare comunque? [y/N]: ")
            if response.lower() not in ['y', 'yes', 'si', 's']:
                logger.info("Setup annullato dall'utente.")
                sys.exit(0)
    
    success = True
    
    try:
        # Fase 1: Pulizia environment (se richiesta)
        if args.clean:
            logger.info("\n--- FASE 1: PULIZIA ENVIRONMENT ---")
            if not uninstall_all_packages(args.force):
                logger.error("Errore durante pulizia environment")
                success = False
        
        # Fase 2: Aggiornamento pip
        if success:
            logger.info("\n--- FASE 2: AGGIORNAMENTO PIP ---")
            if not upgrade_pip():
                logger.warning("Errore aggiornamento pip (continuando...)")
        
        # Fase 3: Installazione dipendenze
        if success:
            logger.info("\n--- FASE 3: INSTALLAZIONE DIPENDENZE ---")
            if not install_requirements():
                logger.error("Errore durante installazione dipendenze")
                success = False
        
        # Fase 4: Verifica installazione
        if success:
            logger.info("\n--- FASE 4: VERIFICA INSTALLAZIONE ---")
            if not verify_installation():
                logger.error("Alcune dipendenze non sono installate correttamente")
                success = False
        
        # Risultato finale
        print("\n" + "="*60)
        if success:
            print("✓ SETUP COMPLETATO CON SUCCESSO!")
            print("Il Discovery Engine è pronto per l'uso.")
            print("\nPer eseguire la discovery:")
            print("  python discovery_main.py --help")
        else:
            print("✗ SETUP FALLITO!")
            print("Controlla i log per dettagli sugli errori.")
            sys.exit(1)
        
        print("="*60)
        
    except KeyboardInterrupt:
        logger.info("\nSetup interrotto dall'utente")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Errore imprevisto durante setup: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
