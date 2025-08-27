"""
PMI Dashboard EPS - Discovery Engine
Output Manager

Gestisce la generazione e l'output dei risultati della discovery
in vari formati (JSON, CSV, XML).

Author: PMI Dashboard EPS Team
Date: 27 Agosto 2025
"""

import json
import csv
import xml.etree.ElementTree as ET
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import uuid

logger = logging.getLogger(__name__)

class OutputManager:
    """
    Gestisce l'output dei risultati della discovery in vari formati.
    
    Supporta la generazione di file JSON, CSV e XML secondo la
    configurazione specificata nel file di configurazione.
    """
    
    def __init__(self, config: Dict[str, Any], output_dir: Optional[str] = None):
        """
        Inizializza l'OutputManager.
        
        Args:
            config: Configurazione output dal ConfigManager
            output_dir: Directory di output personalizzata
        """
        self.config = config
        self.output_dir = Path(output_dir) if output_dir else self._get_default_output_dir()
        
        # Crea directory di output se non esiste
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"OutputManager inizializzato con directory: {self.output_dir}")
        
    def _get_default_output_dir(self) -> Path:
        """
        Determina la directory di output predefinita.
        
        Returns:
            Path alla directory output
        """
        # Determina la directory root del progetto
        current_dir = Path(__file__).parent.parent.parent.parent
        return current_dir / "output"
    
    def generate_output(self, discovery_results: Dict[str, Any]) -> List[str]:
        """
        Genera tutti i file di output configurati.
        
        Args:
            discovery_results: Risultati completi della discovery
            
        Returns:
            Lista dei file generati
        """
        logger.info("Avvio generazione output")
        generated_files = []
        
        try:
            # Output principale
            main_file = self._generate_main_output(discovery_results)
            generated_files.append(main_file)
            
            # Output aggiuntivi
            additional_files = self._generate_additional_outputs(discovery_results)
            generated_files.extend(additional_files)
            
            logger.info(f"Generazione output completata: {len(generated_files)} file")
            return generated_files
            
        except Exception as e:
            logger.error(f"Errore nella generazione output: {e}")
            raise
    
    def _generate_main_output(self, discovery_results: Dict[str, Any]) -> str:
        """
        Genera il file di output principale.
        
        Args:
            discovery_results: Risultati della discovery
            
        Returns:
            Percorso del file generato
        """
        output_format = self.config.get('format', 'json').lower()
        output_file = self.config.get('file', 'discovery_results.json')
        
        # Assicura che il file abbia l'estensione corretta
        if output_format == 'json' and not output_file.endswith('.json'):
            output_file += '.json'
        elif output_format == 'xml' and not output_file.endswith('.xml'):
            output_file += '.xml'
        
        file_path = self.output_dir / output_file
        
        logger.debug(f"Generazione output principale: {file_path}")
        
        if output_format == 'json':
            self._write_json(discovery_results, file_path)
        elif output_format == 'xml':
            self._write_xml(discovery_results, file_path)
        else:
            raise ValueError(f"Formato output non supportato: {output_format}")
        
        return str(file_path)
    
    def _generate_additional_outputs(self, discovery_results: Dict[str, Any]) -> List[str]:
        """
        Genera i file di output aggiuntivi configurati.
        
        Args:
            discovery_results: Risultati della discovery
            
        Returns:
            Lista dei file generati
        """
        generated_files = []
        additional_formats = self.config.get('additional_formats', [])
        
        for format_config in additional_formats:
            try:
                file_path = self._generate_format_output(discovery_results, format_config)
                generated_files.append(file_path)
            except Exception as e:
                logger.error(f"Errore generazione formato aggiuntivo {format_config}: {e}")
                # Continua con gli altri formati
        
        return generated_files
    
    def _generate_format_output(self, discovery_results: Dict[str, Any], 
                               format_config: Dict[str, Any]) -> str:
        """
        Genera un output in un formato specifico.
        
        Args:
            discovery_results: Risultati della discovery
            format_config: Configurazione del formato
            
        Returns:
            Percorso del file generato
        """
        output_format = format_config.get('format', '').lower()
        output_file = format_config.get('file', f'discovery.{output_format}')
        
        file_path = self.output_dir / output_file
        
        logger.debug(f"Generazione formato {output_format}: {file_path}")
        
        if output_format == 'json':
            self._write_json(discovery_results, file_path)
        elif output_format == 'csv':
            self._write_csv(discovery_results, file_path, format_config)
        elif output_format == 'xml':
            self._write_xml(discovery_results, file_path)
        else:
            logger.warning(f"Formato non supportato ignorato: {output_format}")
            return ""
        
        return str(file_path)
    
    def _write_json(self, data: Dict[str, Any], file_path: Path) -> None:
        """
        Scrive i dati in formato JSON.
        
        Args:
            data: Dati da scrivere
            file_path: Percorso del file
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if self.config.get('pretty_print', True):
                    indent = self.config.get('indent', 2)
                    json.dump(data, f, indent=indent, ensure_ascii=False)
                else:
                    json.dump(data, f, ensure_ascii=False)
            
            logger.debug(f"File JSON scritto: {file_path}")
            
        except Exception as e:
            logger.error(f"Errore scrittura JSON {file_path}: {e}")
            raise
    
    def _write_csv(self, discovery_results: Dict[str, Any], 
                   file_path: Path, format_config: Dict[str, Any]) -> None:
        """
        Scrive i dispositivi in formato CSV.
        
        Args:
            discovery_results: Risultati della discovery
            file_path: Percorso del file
            format_config: Configurazione CSV
        """
        try:
            devices = discovery_results.get('devices', [])
            fields = format_config.get('fields', ['ip_address', 'hostname', 'device_type', 'vendor'])
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fields)
                writer.writeheader()
                
                for device in devices:
                    row = {}
                    for field in fields:
                        row[field] = self._extract_field_value(device, field)
                    writer.writerow(row)
            
            logger.debug(f"File CSV scritto: {file_path} ({len(devices)} dispositivi)")
            
        except Exception as e:
            logger.error(f"Errore scrittura CSV {file_path}: {e}")
            raise
    
    def _write_xml(self, discovery_results: Dict[str, Any], file_path: Path) -> None:
        """
        Scrive i dati in formato XML.
        
        Args:
            discovery_results: Risultati della discovery
            file_path: Percorso del file
        """
        try:
            root = ET.Element("discovery_results")
            
            # Metadata
            metadata = discovery_results.get('discovery_metadata', {})
            metadata_elem = ET.SubElement(root, "metadata")
            for key, value in metadata.items():
                elem = ET.SubElement(metadata_elem, key)
                elem.text = str(value)
            
            # Devices
            devices = discovery_results.get('devices', [])
            devices_elem = ET.SubElement(root, "devices")
            
            for device in devices:
                device_elem = ET.SubElement(devices_elem, "device")
                self._dict_to_xml(device, device_elem)
            
            # Statistics
            stats = discovery_results.get('scan_statistics', {})
            if stats:
                stats_elem = ET.SubElement(root, "scan_statistics")
                self._dict_to_xml(stats, stats_elem)
            
            # Scrive il file
            tree = ET.ElementTree(root)
            tree.write(file_path, encoding='utf-8', xml_declaration=True)
            
            logger.debug(f"File XML scritto: {file_path}")
            
        except Exception as e:
            logger.error(f"Errore scrittura XML {file_path}: {e}")
            raise
    
    def _dict_to_xml(self, data: Any, parent: ET.Element) -> None:
        """
        Converte ricorsivamente un dizionario in elementi XML.
        
        Args:
            data: Dati da convertire
            parent: Elemento XML padre
        """
        if isinstance(data, dict):
            for key, value in data.items():
                # Sanitizza il nome del tag XML
                tag_name = str(key).replace(' ', '_').replace('-', '_')
                child = ET.SubElement(parent, tag_name)
                self._dict_to_xml(value, child)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                child = ET.SubElement(parent, f"item_{i}")
                self._dict_to_xml(item, child)
        else:
            parent.text = str(data) if data is not None else ""
    
    def _extract_field_value(self, device: Dict[str, Any], field: str) -> str:
        """
        Estrae il valore di un campo da un dispositivo per il CSV.
        
        Args:
            device: Dizionario dispositivo
            field: Nome del campo
            
        Returns:
            Valore del campo come stringa
        """
        # Mappings specifici per campi complessi
        field_mappings = {
            'device_type': lambda d: self._guess_device_type(d),
            'vendor': lambda d: d.get('vendor', '') or self._guess_vendor_from_mac(d.get('mac_address', '')),
            'os_name': lambda d: d.get('operating_system', {}).get('name', ''),
            'open_ports': lambda d: len(d.get('services', [])),
            'snmp_accessible': lambda d: d.get('snmp_data', {}).get('accessible', False)
        }
        
        if field in field_mappings:
            try:
                return str(field_mappings[field](device))
            except:
                return ""
        
        # Campo semplice
        return str(device.get(field, ''))
    
    def _guess_device_type(self, device: Dict[str, Any]) -> str:
        """
        Tenta di identificare il tipo di dispositivo.
        
        Args:
            device: Dizionario dispositivo
            
        Returns:
            Tipo di dispositivo stimato
        """
        # Controlla servizi per identificare il tipo
        services = device.get('services', [])
        open_ports = [s.get('port') for s in services if s.get('state') == 'open']
        
        # Router/Firewall
        if 161 in open_ports and (22 in open_ports or 23 in open_ports):
            return "network_device"
        
        # Web server
        if 80 in open_ports or 443 in open_ports:
            return "web_server"
        
        # Printer
        if 515 in open_ports or 631 in open_ports or 9100 in open_ports:
            return "printer"
        
        # Default
        return "unknown"
    
    def _guess_vendor_from_mac(self, mac_address: str) -> str:
        """
        Tenta di identificare il vendor dal MAC address (OUI).
        
        Args:
            mac_address: Indirizzo MAC
            
        Returns:
            Vendor stimato o stringa vuota
        """
        if not mac_address or len(mac_address) < 8:
            return ""
        
        # OUI mappings comuni (primi 3 ottetti)
        oui_mappings = {
            "00:50:56": "VMware",
            "08:00:27": "VirtualBox", 
            "00:0C:29": "VMware",
            "00:1B:21": "Intel",
            "00:E0:4C": "Cisco",
            "00:90:7F": "Cisco",
            "CC:46:D6": "Cisco",
            "F8:66:F2": "Cisco",
            "3C:CE:73": "Cisco",
            "00:25:84": "Apple",
            "28:CF:E9": "Apple",
            "A4:5E:60": "Apple",
            "00:1F:3C": "Hewlett Packard",
            "00:17:08": "Hewlett Packard"
        }
        
        # Estrae OUI (primi 8 caratteri nel formato XX:XX:XX)
        oui = mac_address[:8].upper()
        return oui_mappings.get(oui, "")
    
    def create_discovery_result_structure(self, scan_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Crea la struttura base per i risultati della discovery.
        
        Args:
            scan_id: ID univoco della scansione
            
        Returns:
            Struttura base dei risultati
        """
        if not scan_id:
            scan_id = str(uuid.uuid4())
            
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        structure = {
            "discovery_metadata": {
                "scan_id": scan_id,
                "timestamp": timestamp,
                "network_range": "",  # Da riempire
                "scan_duration_seconds": 0,  # Da calcolare
                "total_devices": 0,  # Da calcolare
                "scan_methods_used": [],  # Da riempire
                "configuration_used": ""  # Da riempire
            },
            "devices": [],
            "scan_statistics": {
                "arp_scan": {},
                "nmap_scan": {},
                "snmp_scan": {}
            },
            "errors": []
        }
        
        logger.debug(f"Creata struttura risultati con scan_id: {scan_id}")
        return structure
    
    def add_device_to_results(self, results: Dict[str, Any], 
                             device_data: Dict[str, Any]) -> None:
        """
        Aggiunge un dispositivo ai risultati.
        
        Args:
            results: Struttura risultati
            device_data: Dati del dispositivo
        """
        results['devices'].append(device_data)
        results['discovery_metadata']['total_devices'] = len(results['devices'])
        
        logger.debug(f"Aggiunto dispositivo: {device_data.get('ip_address', 'unknown')}")
    
    def add_error_to_results(self, results: Dict[str, Any], 
                           error_data: Dict[str, Any]) -> None:
        """
        Aggiunge un errore ai risultati.
        
        Args:
            results: Struttura risultati  
            error_data: Dati dell'errore
        """
        if 'timestamp' not in error_data:
            error_data['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        results['errors'].append(error_data)
        
        logger.debug(f"Aggiunto errore: {error_data.get('error_type', 'unknown')}")
    
    def finalize_results(self, results: Dict[str, Any], 
                        start_time: datetime) -> None:
        """
        Finalizza i risultati calcolando statistiche finali.
        
        Args:
            results: Struttura risultati
            start_time: Ora di inizio scansione
        """
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        results['discovery_metadata']['scan_duration_seconds'] = round(duration, 2)
        results['discovery_metadata']['total_devices'] = len(results['devices'])
        
        # Aggiorna metodi utilizzati basandosi sui dispositivi trovati
        methods_used = set()
        for device in results['devices']:
            discovery_methods = device.get('discovery_methods', [])
            methods_used.update(discovery_methods)
        
        results['discovery_metadata']['scan_methods_used'] = sorted(list(methods_used))
        
        logger.info(f"Risultati finalizzati: {len(results['devices'])} dispositivi, "
                   f"durata {duration:.2f}s")
    
    def get_output_files_info(self) -> List[Dict[str, str]]:
        """
        Ottiene informazioni sui file di output configurati.
        
        Returns:
            Lista di dizionari con info sui file
        """
        files_info = []
        
        # File principale
        main_format = self.config.get('format', 'json')
        main_file = self.config.get('file', 'discovery_results.json')
        files_info.append({
            'format': main_format,
            'file': main_file,
            'type': 'main'
        })
        
        # File aggiuntivi
        additional_formats = self.config.get('additional_formats', [])
        for format_config in additional_formats:
            files_info.append({
                'format': format_config.get('format', ''),
                'file': format_config.get('file', ''),
                'type': 'additional'
            })
        
        return files_info
    
    def __str__(self) -> str:
        """Rappresentazione string dell'OutputManager."""
        return f"OutputManager(output_dir='{self.output_dir}')"
    
    def __repr__(self) -> str:
        """Rappresentazione debug dell'OutputManager."""
        return f"OutputManager(output_dir='{self.output_dir}', formats={self.get_output_files_info()})"
