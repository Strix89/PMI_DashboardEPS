"""
Device Classification System for Network Discovery Module.

This module provides comprehensive device classification capabilities based on:
- Operating system fingerprinting from NMAP
- Port-based device identification
- SNMP-based manufacturer and model identification
- Classification rules and patterns for different device types
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from .data_models import DeviceInfo, DeviceType


@dataclass
class ClassificationRule:
    """
    A rule for classifying devices based on various criteria.
    
    Attributes:
        name: Human-readable name for the rule
        device_type: The device type this rule classifies to
        priority: Priority of the rule (higher = more important)
        os_patterns: List of regex patterns to match against OS info
        port_patterns: Set of ports that indicate this device type
        snmp_patterns: Dict of SNMP OID patterns to match
        manufacturer_patterns: List of manufacturer names that indicate this type
    """
    name: str
    device_type: DeviceType
    priority: int
    os_patterns: List[str] = None
    port_patterns: Set[int] = None
    snmp_patterns: Dict[str, List[str]] = None
    manufacturer_patterns: List[str] = None


class DeviceClassifier:
    """
    Comprehensive device classification system.
    
    This class provides methods to classify discovered devices into categories
    (IoT, Windows, Linux, NetworkEquipment) based on multiple data sources
    including OS fingerprinting, open ports, and SNMP data.
    """
    
    def __init__(self):
        """Initialize the device classifier with predefined rules."""
        self.classification_rules = self._initialize_classification_rules()
        self.manufacturer_database = self._initialize_manufacturer_database()
        self.port_service_map = self._initialize_port_service_map()
    
    def classify_device(self, device_info: DeviceInfo) -> DeviceType:
        """
        Classify a device based on all available information.
        
        This method uses a multi-stage classification approach:
        1. SNMP-based classification (highest priority)
        2. OS-based classification
        3. Port-based classification
        4. Manufacturer-based classification
        
        Args:
            device_info: DeviceInfo object containing device data
            
        Returns:
            Classified DeviceType
        """
        # Start with unknown type
        classified_type = DeviceType.UNKNOWN
        max_confidence = 0
        
        # Apply classification rules in priority order
        for rule in sorted(self.classification_rules, key=lambda r: r.priority, reverse=True):
            confidence = self._evaluate_rule(device_info, rule)
            
            if confidence > max_confidence:
                max_confidence = confidence
                classified_type = rule.device_type
                
                # If we have very high confidence, stop here
                if confidence >= 0.9:
                    break
        
        # Special case: If SNMP data is available, try SNMP-specific classification
        if device_info.snmp_data and classified_type == DeviceType.UNKNOWN:
            snmp_type = self._classify_from_snmp_data(device_info.snmp_data)
            if snmp_type != DeviceType.UNKNOWN:
                classified_type = snmp_type
        
        return classified_type
    
    def identify_network_equipment(self, snmp_data: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Identify manufacturer and model of network equipment using SNMP data.
        
        Args:
            snmp_data: Dictionary of SNMP OID-value pairs
            
        Returns:
            Tuple of (manufacturer, model) or (None, None) if not identifiable
        """
        if not snmp_data:
            return None, None
        
        # Get system description (most informative OID)
        sys_descr = snmp_data.get('1.3.6.1.2.1.1.1.0', '')
        
        # Try to identify manufacturer and model from system description
        manufacturer, model = self._parse_system_description(sys_descr)
        
        if not manufacturer:
            # Try other SNMP OIDs for manufacturer identification
            manufacturer = self._identify_manufacturer_from_snmp(snmp_data)
        
        if not model:
            # Try to extract model from various SNMP fields
            model = self._identify_model_from_snmp(snmp_data)
        
        return manufacturer, model
    
    def get_device_confidence_score(self, device_info: DeviceInfo, device_type: DeviceType) -> float:
        """
        Calculate confidence score for a specific device type classification.
        
        Args:
            device_info: DeviceInfo object
            device_type: DeviceType to calculate confidence for
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        total_score = 0.0
        max_possible_score = 0.0
        
        # Find rules that match this device type
        matching_rules = [rule for rule in self.classification_rules if rule.device_type == device_type]
        
        for rule in matching_rules:
            rule_score = self._evaluate_rule(device_info, rule)
            rule_weight = rule.priority / 100.0  # Normalize priority to weight
            
            total_score += rule_score * rule_weight
            max_possible_score += rule_weight
        
        if max_possible_score == 0:
            return 0.0
        
        return min(total_score / max_possible_score, 1.0)
    
    def _initialize_classification_rules(self) -> List[ClassificationRule]:
        """
        Initialize the classification rules database.
        
        Returns:
            List of ClassificationRule objects
        """
        rules = []
        
        # Network Equipment Rules (Highest Priority)
        rules.append(ClassificationRule(
            name="SNMP Network Equipment",
            device_type=DeviceType.NETWORK_EQUIPMENT,
            priority=100,
            port_patterns={161, 22, 23, 80, 443},
            snmp_patterns={
                '1.3.6.1.2.1.1.1.0': ['cisco', 'juniper', 'hp', 'dell', 'netgear', 'router', 'switch', 'ios', 'junos']
            }
        ))
        
        rules.append(ClassificationRule(
            name="Network Equipment Ports",
            device_type=DeviceType.NETWORK_EQUIPMENT,
            priority=90,
            port_patterns={161, 22, 23, 80, 443, 8080, 8443, 9999},
            os_patterns=[r'.*cisco.*', r'.*juniper.*', r'.*router.*', r'.*switch.*', r'.*ios.*', r'.*junos.*']
        ))
        
        # Windows Rules
        rules.append(ClassificationRule(
            name="Windows OS Detection",
            device_type=DeviceType.WINDOWS,
            priority=85,
            os_patterns=[r'.*windows.*', r'.*microsoft.*', r'.*win32.*', r'.*winnt.*'],
            port_patterns={135, 139, 445, 3389, 5985, 5986}
        ))
        
        rules.append(ClassificationRule(
            name="Windows Ports",
            device_type=DeviceType.WINDOWS,
            priority=80,
            port_patterns={135, 139, 445, 3389}  # RPC, NetBIOS, SMB, RDP
        ))
        
        # Linux Rules
        rules.append(ClassificationRule(
            name="Linux OS Detection",
            device_type=DeviceType.LINUX,
            priority=85,
            os_patterns=[r'(?!.*embedded).*linux.*', r'.*ubuntu.*', r'.*debian.*', r'.*centos.*', r'.*redhat.*', r'.*fedora.*', r'.*suse.*'],
            port_patterns={22}  # SSH is strong indicator
        ))
        
        rules.append(ClassificationRule(
            name="Linux Server Ports",
            device_type=DeviceType.LINUX,
            priority=75,
            port_patterns={22, 25, 53, 80, 110, 143, 443, 993, 995, 8080}
        ))
        
        # IoT Device Rules (Higher priority than Linux for embedded systems)
        rules.append(ClassificationRule(
            name="IoT SNMP Patterns",
            device_type=DeviceType.IOT,
            priority=88,
            snmp_patterns={
                '1.3.6.1.2.1.1.1.0': ['camera', 'sensor', 'thermostat', 'light', 'smart', 'embedded', 'iot']
            }
        ))
        
        rules.append(ClassificationRule(
            name="IoT OS Detection",
            device_type=DeviceType.IOT,
            priority=87,
            os_patterns=[r'.*embedded.*linux.*', r'.*iot.*', r'.*arduino.*', r'.*raspberry.*', r'.*openwrt.*'],
            manufacturer_patterns=['raspberry', 'arduino', 'espressif', 'broadcom']
        ))
        
        rules.append(ClassificationRule(
            name="IoT Device Ports",
            device_type=DeviceType.IOT,
            priority=70,
            port_patterns={1883, 8883, 5683, 502, 102}  # MQTT, CoAP, Modbus (removed 8080, 9999, 10001 as they're too generic)
        ))
        
        return rules
    
    def _initialize_manufacturer_database(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Initialize manufacturer identification database.
        
        Returns:
            Dictionary mapping manufacturers to their identification patterns
        """
        return {
            'cisco': {
                'patterns': ['cisco', 'ios', 'catalyst', 'nexus', 'asr', 'isr'],
                'oids': ['1.3.6.1.4.1.9'],  # Cisco enterprise OID
                'models': ['catalyst', 'nexus', 'asr', 'isr', 'c9300', 'c9200', 'c3850']
            },
            'juniper': {
                'patterns': ['juniper', 'junos', 'srx', 'mx', 'ex', 'qfx'],
                'oids': ['1.3.6.1.4.1.2636'],  # Juniper enterprise OID
                'models': ['srx', 'mx', 'ex', 'qfx', 'acx', 'ptx']
            },
            'hp': {
                'patterns': ['hp', 'hewlett', 'packard', 'procurve', 'aruba'],
                'oids': ['1.3.6.1.4.1.11'],  # HP enterprise OID
                'models': ['procurve', 'aruba', '2530', '2540', '2930', '3810']
            },
            'dell': {
                'patterns': ['dell', 'force10', 'powerconnect'],
                'oids': ['1.3.6.1.4.1.674'],  # Dell enterprise OID
                'models': ['powerconnect', 'force10', 'n1500', 'n2000', 'n3000', 'n4000']
            },
            'netgear': {
                'patterns': ['netgear', 'prosafe'],
                'oids': ['1.3.6.1.4.1.4526'],  # Netgear enterprise OID
                'models': ['prosafe', 'gs', 'fs', 'xs']
            },
            'ubiquiti': {
                'patterns': ['ubiquiti', 'unifi', 'edgemax', 'airmax'],
                'oids': ['1.3.6.1.4.1.41112'],  # Ubiquiti enterprise OID
                'models': ['unifi', 'edgemax', 'airmax', 'dream', 'cloudkey']
            },
            'mikrotik': {
                'patterns': ['mikrotik', 'routeros', 'routerboard'],
                'oids': ['1.3.6.1.4.1.14988'],  # MikroTik enterprise OID
                'models': ['routerboard', 'ccr', 'crs', 'hap', 'hex']
            },
            'fortinet': {
                'patterns': ['fortinet', 'fortigate', 'fortios'],
                'oids': ['1.3.6.1.4.1.12356'],  # Fortinet enterprise OID
                'models': ['fortigate', 'fortiswitch', 'fortiap', 'fortiwifi']
            }
        }
    
    def _initialize_port_service_map(self) -> Dict[int, str]:
        """
        Initialize port to service mapping for classification.
        
        Returns:
            Dictionary mapping port numbers to service descriptions
        """
        return {
            # Network Equipment Ports
            22: 'SSH',
            23: 'Telnet',
            80: 'HTTP',
            161: 'SNMP',
            443: 'HTTPS',
            8080: 'HTTP-Alt',
            8443: 'HTTPS-Alt',
            9999: 'Management',
            
            # Windows Ports
            135: 'RPC Endpoint Mapper',
            139: 'NetBIOS Session',
            445: 'SMB/CIFS',
            3389: 'RDP',
            5985: 'WinRM HTTP',
            5986: 'WinRM HTTPS',
            
            # Linux/Unix Ports
            25: 'SMTP',
            53: 'DNS',
            110: 'POP3',
            143: 'IMAP',
            993: 'IMAPS',
            995: 'POP3S',
            
            # IoT Ports
            1883: 'MQTT',
            8883: 'MQTT over SSL',
            5683: 'CoAP',
            502: 'Modbus',
            102: 'S7 Communication',
            10001: 'IoT Management'
        }
    
    def _evaluate_rule(self, device_info: DeviceInfo, rule: ClassificationRule) -> float:
        """
        Evaluate how well a device matches a classification rule.
        
        Args:
            device_info: DeviceInfo object to evaluate
            rule: ClassificationRule to apply
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.0
        criteria_count = 0
        
        # Check OS patterns
        if rule.os_patterns and device_info.os_info:
            criteria_count += 1
            for pattern in rule.os_patterns:
                if re.search(pattern, device_info.os_info, re.IGNORECASE):
                    score += 0.4  # OS match is strong indicator
                    break
        
        # Check port patterns
        if rule.port_patterns and device_info.open_ports:
            criteria_count += 1
            matching_ports = set(device_info.open_ports) & rule.port_patterns
            if matching_ports:
                # Score based on percentage of rule ports that match
                port_score = len(matching_ports) / len(rule.port_patterns)
                score += port_score * 0.3  # Port match is moderate indicator
        
        # Check SNMP patterns
        if rule.snmp_patterns and device_info.snmp_data:
            criteria_count += 1
            snmp_score = self._evaluate_snmp_patterns(device_info.snmp_data, rule.snmp_patterns)
            score += snmp_score * 0.4  # SNMP match is strong indicator
        
        # Check manufacturer patterns
        if rule.manufacturer_patterns and device_info.manufacturer:
            criteria_count += 1
            for pattern in rule.manufacturer_patterns:
                if pattern.lower() in device_info.manufacturer.lower():
                    score += 0.3  # Manufacturer match is moderate indicator
                    break
        
        # Normalize score based on number of criteria evaluated
        if criteria_count == 0:
            return 0.0
        
        return min(score, 1.0)
    
    def _evaluate_snmp_patterns(self, snmp_data: Dict[str, str], patterns: Dict[str, List[str]]) -> float:
        """
        Evaluate SNMP data against pattern rules.
        
        Args:
            snmp_data: SNMP OID-value pairs
            patterns: Dictionary of OID patterns to match
            
        Returns:
            Score between 0.0 and 1.0
        """
        total_score = 0.0
        pattern_count = len(patterns)
        
        for oid, pattern_list in patterns.items():
            if oid in snmp_data:
                value = snmp_data[oid].lower()
                for pattern in pattern_list:
                    if pattern.lower() in value:
                        total_score += 1.0 / pattern_count
                        break
        
        return min(total_score, 1.0)
    
    def _classify_from_snmp_data(self, snmp_data: Dict[str, str]) -> DeviceType:
        """
        Classify device based purely on SNMP data.
        
        Args:
            snmp_data: SNMP OID-value pairs
            
        Returns:
            Classified DeviceType
        """
        # Get system description
        sys_descr = snmp_data.get('1.3.6.1.2.1.1.1.0', '').lower()
        
        # Network equipment indicators
        network_indicators = [
            'router', 'switch', 'firewall', 'gateway', 'bridge',
            'cisco', 'juniper', 'hp', 'dell', 'netgear', 'linksys',
            'ios', 'junos', 'routeros', 'fortios', 'pan-os', 'catalyst',
            'nexus', 'procurve', 'aruba'
        ]
        
        # IoT device indicators
        iot_indicators = [
            'camera', 'sensor', 'thermostat', 'light', 'smart',
            'iot', 'embedded', 'arduino', 'raspberry', 'esp32', 'esp8266'
        ]
        
        # Check for network equipment
        for indicator in network_indicators:
            if indicator in sys_descr:
                return DeviceType.NETWORK_EQUIPMENT
        
        # Check for IoT devices
        for indicator in iot_indicators:
            if indicator in sys_descr:
                return DeviceType.IOT
        
        # Check for Windows/Linux indicators
        if 'windows' in sys_descr or 'microsoft' in sys_descr:
            return DeviceType.WINDOWS
        elif any(os in sys_descr for os in ['linux', 'ubuntu', 'debian', 'centos', 'redhat']):
            return DeviceType.LINUX
        
        # If SNMP is responding but no specific indicators, likely network equipment
        return DeviceType.NETWORK_EQUIPMENT
    
    def _parse_system_description(self, sys_descr: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse manufacturer and model from SNMP system description.
        
        Args:
            sys_descr: System description string from SNMP
            
        Returns:
            Tuple of (manufacturer, model)
        """
        if not sys_descr:
            return None, None
        
        sys_descr_lower = sys_descr.lower()
        manufacturer = None
        model = None
        
        # Check each manufacturer in our database
        for mfg_name, mfg_data in self.manufacturer_database.items():
            for pattern in mfg_data['patterns']:
                if pattern in sys_descr_lower:
                    manufacturer = mfg_name.title()
                    
                    # Try to extract model
                    for model_pattern in mfg_data['models']:
                        if model_pattern in sys_descr_lower:
                            # Extract the specific model string
                            model_match = re.search(rf'\b{model_pattern}[a-z0-9\-]*', sys_descr_lower)
                            if model_match:
                                model = model_match.group().upper()
                                break
                    break
            
            if manufacturer:
                break
        
        return manufacturer, model
    
    def _identify_manufacturer_from_snmp(self, snmp_data: Dict[str, str]) -> Optional[str]:
        """
        Identify manufacturer from various SNMP OIDs.
        
        Args:
            snmp_data: SNMP OID-value pairs
            
        Returns:
            Manufacturer name or None
        """
        # Check enterprise OIDs
        for oid, value in snmp_data.items():
            # Look for enterprise OID patterns
            for mfg_name, mfg_data in self.manufacturer_database.items():
                for enterprise_oid in mfg_data.get('oids', []):
                    if oid.startswith(enterprise_oid):
                        return mfg_name.title()
        
        # Check system object ID (1.3.6.1.2.1.1.2.0)
        sys_obj_id = snmp_data.get('1.3.6.1.2.1.1.2.0', '')
        if sys_obj_id:
            for mfg_name, mfg_data in self.manufacturer_database.items():
                for enterprise_oid in mfg_data.get('oids', []):
                    if enterprise_oid in sys_obj_id:
                        return mfg_name.title()
        
        return None
    
    def _identify_model_from_snmp(self, snmp_data: Dict[str, str]) -> Optional[str]:
        """
        Identify device model from SNMP data.
        
        Args:
            snmp_data: SNMP OID-value pairs
            
        Returns:
            Model name or None
        """
        # Common OIDs that might contain model information
        model_oids = [
            '1.3.6.1.2.1.1.1.0',  # sysDescr
            '1.3.6.1.2.1.1.5.0',  # sysName
            '1.3.6.1.2.1.47.1.1.1.1.13.1',  # entPhysicalModelName
        ]
        
        for oid in model_oids:
            if oid in snmp_data:
                value = snmp_data[oid].lower()
                
                # Try to extract model from each manufacturer's model patterns
                for mfg_name, mfg_data in self.manufacturer_database.items():
                    for model_pattern in mfg_data.get('models', []):
                        if model_pattern in value:
                            # Extract the specific model string
                            model_match = re.search(rf'\b{model_pattern}[a-z0-9\-]*', value)
                            if model_match:
                                return model_match.group().upper()
        
        return None