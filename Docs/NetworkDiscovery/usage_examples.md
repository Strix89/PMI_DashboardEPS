# Network Discovery Module - Usage Examples

This document provides comprehensive examples of using the Network Discovery Module in various scenarios and environments.

## Table of Contents

- [Basic Usage Examples](#basic-usage-examples)
- [Configuration Examples](#configuration-examples)
- [Advanced Usage Scenarios](#advanced-usage-scenarios)
- [Integration Examples](#integration-examples)
- [Troubleshooting Examples](#troubleshooting-examples)

## Basic Usage Examples

### Quick Start - Default Scan

The simplest way to run a network discovery scan:

```bash
# Run with all default settings
python -m network_discovery

# Expected output:
# ℹ️  [2024-01-15 10:30:00] Starting Network Discovery Module
# ℹ️  [2024-01-15 10:30:01] Detected network: 192.168.1.0/24
# ℹ️  [2024-01-15 10:30:01] Scan range: 192.168.1.1-192.168.1.254 (253 addresses)
# ℹ️  [2024-01-15 10:30:01] Starting ARP discovery phase...
# ℹ️  [2024-01-15 10:30:15] ARP scan complete: 12 devices found
# ℹ️  [2024-01-15 10:30:15] Starting NMAP scanning phase...
# ℹ️  [2024-01-15 10:32:30] NMAP scan complete: 12 devices scanned
# ℹ️  [2024-01-15 10:32:30] Starting SNMP querying phase...
# ℹ️  [2024-01-15 10:32:45] SNMP scan complete: 3 devices responded
# ℹ️  [2024-01-15 10:32:45] Generating JSON report...
# ℹ️  [2024-01-15 10:32:46] Scan complete! Report saved to: network_discovery/results/network_discovery_20240115_103246.json
```

### Verbose Output

Enable detailed logging for troubleshooting:

```bash
python -m network_discovery --verbose

# Additional debug output:
# 🔍 [2024-01-15 10:30:00] Loading configuration from: network_discovery/config
# 🔍 [2024-01-15 10:30:00] ARP config: timeout=2, retries=3, method=scapy
# 🔍 [2024-01-15 10:30:01] Excluding addresses: 192.168.1.0, 192.168.1.100, 192.168.1.255
# 🔍 [2024-01-15 10:30:01] ARP scanning 192.168.1.1 with timeout 2s
# 🔍 [2024-01-15 10:30:03] ARP response from 192.168.1.1: aa:bb:cc:dd:ee:ff
```

### Custom Configuration Directory

Use custom configuration files:

```bash
# Create custom config directory
mkdir my_configs
cp -r network_discovery/config/* my_configs/

# Edit configurations as needed
nano my_configs/arp_config.yml

# Run with custom configs
python -m network_discovery --config-dir my_configs
```

### Custom Output Directory

Save results to a specific location:

```bash
# Create output directory
mkdir scan_results_$(date +%Y%m%d)

# Run scan with custom output location
python -m network_discovery --output-dir scan_results_$(date +%Y%m%d)

# Results will be saved to: scan_results_20240115/network_discovery_*.json
```

## Configuration Examples

### Home Network - Fast Discovery

Optimized for home networks with trusted devices:

```yaml
# home_network_config.yml
arp:
  timeout: 1
  retries: 2
  method: "scapy"
  parallel_threads: 15

nmap:
  scan_type: "-sT"
  port_range: "-F"
  timing: "-T4"
  os_detection: "-O"
  service_detection: "-sV"
  max_parallel: 30

snmp:
  versions: [2, 1]
  communities: ["public", "private"]
  timeout: 5
  max_walk_oids: 100
```

Usage:
```bash
python -m network_discovery --config-dir home_network_config.yml
```

### Corporate Network - Production Safe

Conservative settings for production environments:

```yaml
# corporate_config.yml
arp:
  timeout: 3
  retries: 2
  method: "scapy"
  parallel_threads: 5

nmap:
  scan_type: "-sT"
  port_range: "-p 22,80,443,8080,161"
  timing: "-T2"
  os_detection: ""
  service_detection: ""
  max_parallel: 10

snmp:
  versions: [2]
  communities: ["public"]
  timeout: 15
  retries: 1
  max_walk_oids: 25
```

Usage:
```bash
python -m network_discovery --config-dir corporate_config.yml --verbose
```

### Security Assessment - Comprehensive Scan

Detailed scanning for security assessment:

```yaml
# security_assessment_config.yml
arp:
  timeout: 5
  retries: 3
  method: "scapy"
  parallel_threads: 10

nmap:
  scan_type: "-sS"
  port_range: "--top-ports 1000"
  timing: "-T3"
  os_detection: "-O"
  service_detection: "-sV"
  additional_flags:
    - "--script=default"
    - "--script=vuln"
    - "--script=safe"
  max_parallel: 25

snmp:
  versions: [2, 1]
  communities: ["public", "private", "admin", "monitoring"]
  timeout: 20
  retries: 2
  max_walk_oids: 500
  walk_oids:
    - "1.3.6.1.2.1.1"
    - "1.3.6.1.2.1.2"
    - "1.3.6.1.2.1.4"
```

Usage:
```bash
sudo python -m network_discovery --config-dir security_assessment_config.yml
```

## Advanced Usage Scenarios

### Scanning Specific Network Ranges

#### Single Subnet Scan
```bash
# Scan a specific subnet (if your tool supports target specification)
python -m network_discovery --target 192.168.10.0/24
```

#### Multiple Subnet Scans
```bash
# Scan multiple subnets sequentially
for subnet in 192.168.1.0/24 192.168.2.0/24 192.168.3.0/24; do
    echo "Scanning $subnet..."
    python -m network_discovery --target $subnet --output-dir results_$(echo $subnet | tr '/' '_')
done
```

### Scheduled Scanning

#### Daily Scans (Linux/macOS)
```bash
# Add to crontab for daily 2 AM scans
echo "0 2 * * * cd /path/to/network_discovery && python -m network_discovery --output-dir /var/log/network_scans/\$(date +\%Y\%m\%d)" | crontab -
```

#### Weekly Comprehensive Scans
```bash
# Weekly comprehensive scan on Sundays at 3 AM
echo "0 3 * * 0 cd /path/to/network_discovery && python -m network_discovery --config-dir comprehensive_config.yml --output-dir /var/log/weekly_scans/\$(date +\%Y\%m\%d)" | crontab -
```

#### Windows Task Scheduler
```cmd
# Create scheduled task for daily scans
schtasks /create /tn "NetworkDiscovery" /tr "python -m network_discovery" /sc daily /st 02:00 /ru SYSTEM
```

### Parallel Scanning for Large Networks

#### Network Segmentation Approach
```bash
#!/bin/bash
# parallel_scan.sh - Scan large networks in parallel segments

NETWORK_BASE="192.168"
OUTPUT_BASE="parallel_scan_$(date +%Y%m%d)"

# Create output directory
mkdir -p "$OUTPUT_BASE"

# Scan 4 /24 subnets in parallel
for i in {1..4}; do
    (
        echo "Starting scan of $NETWORK_BASE.$i.0/24"
        python -m network_discovery \
            --target "$NETWORK_BASE.$i.0/24" \
            --output-dir "$OUTPUT_BASE/subnet_$i" \
            --config-dir fast_scan_config.yml
        echo "Completed scan of $NETWORK_BASE.$i.0/24"
    ) &
done

# Wait for all scans to complete
wait
echo "All parallel scans completed"

# Merge results (custom script)
python merge_scan_results.py "$OUTPUT_BASE"/*/*.json > "$OUTPUT_BASE/merged_results.json"
```

### Filtering and Processing Results

#### Extract Specific Device Types
```bash
# Extract only network equipment from results
python -c "
import json
import sys

with open(sys.argv[1], 'r') as f:
    data = json.load(f)

network_devices = [d for d in data['devices'] if d['device_type'] == 'NetworkEquipment']
print(f'Found {len(network_devices)} network devices:')
for device in network_devices:
    print(f'  {device[\"ip_address\"]} - {device.get(\"manufacturer\", \"Unknown\")} {device.get(\"model\", \"\")}')
" results/network_discovery_*.json
```

#### Generate CSV Report
```bash
# Convert JSON results to CSV
python -c "
import json
import csv
import sys

with open(sys.argv[1], 'r') as f:
    data = json.load(f)

with open('network_devices.csv', 'w', newline='') as csvfile:
    fieldnames = ['ip_address', 'mac_address', 'hostname', 'device_type', 'os_info', 'manufacturer', 'model']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    
    writer.writeheader()
    for device in data['devices']:
        row = {field: device.get(field, '') for field in fieldnames}
        writer.writerow(row)

print('CSV report generated: network_devices.csv')
" results/network_discovery_*.json
```

## Integration Examples

### Integration with Network Monitoring Systems

#### Nagios Integration
```bash
#!/bin/bash
# nagios_integration.sh - Update Nagios configuration with discovered devices

SCAN_RESULT=$(python -m network_discovery --output-dir /tmp | grep "Report saved to:" | awk '{print $NF}')

# Extract device information
python -c "
import json
import sys

with open('$SCAN_RESULT', 'r') as f:
    data = json.load(f)

# Generate Nagios host definitions
for device in data['devices']:
    if device['device_type'] in ['NetworkEquipment', 'Linux', 'Windows']:
        print(f'''
define host {{
    host_name           {device['hostname'] or device['ip_address'].replace('.', '_')}
    alias               {device.get('manufacturer', '')} {device.get('model', '')}
    address             {device['ip_address']}
    check_command       check-host-alive
    max_check_attempts  3
    check_period        24x7
    contact_groups      network-admins
    notification_interval 30
    notification_period   24x7
}}''')
" > /etc/nagios/conf.d/discovered_hosts.cfg

# Reload Nagios configuration
systemctl reload nagios
```

#### PRTG Integration
```python
#!/usr/bin/env python3
# prtg_integration.py - Add discovered devices to PRTG

import json
import requests
import sys

def add_device_to_prtg(device_info, prtg_server, username, password):
    """Add a discovered device to PRTG monitoring."""
    
    url = f"https://{prtg_server}/api/duplicateobject.htm"
    params = {
        'id': '1',  # Template device ID
        'name': device_info.get('hostname', device_info['ip_address']),
        'host': device_info['ip_address'],
        'username': username,
        'password': password
    }
    
    response = requests.get(url, params=params, verify=False)
    return response.status_code == 200

# Load scan results
with open(sys.argv[1], 'r') as f:
    scan_data = json.load(f)

# Add network devices to PRTG
for device in scan_data['devices']:
    if device['device_type'] == 'NetworkEquipment':
        success = add_device_to_prtg(device, 'prtg.company.com', 'admin', 'password')
        print(f"Added {device['ip_address']} to PRTG: {'Success' if success else 'Failed'}")
```

### Database Integration

#### SQLite Database Storage
```python
#!/usr/bin/env python3
# store_results.py - Store scan results in SQLite database

import json
import sqlite3
import sys
from datetime import datetime

def create_database():
    """Create SQLite database for storing scan results."""
    conn = sqlite3.connect('network_discovery.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            network_scanned TEXT,
            total_devices INTEGER,
            scan_duration REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER,
            ip_address TEXT,
            mac_address TEXT,
            hostname TEXT,
            device_type TEXT,
            os_info TEXT,
            manufacturer TEXT,
            model TEXT,
            open_ports TEXT,
            FOREIGN KEY (scan_id) REFERENCES scans (id)
        )
    ''')
    
    conn.commit()
    return conn

def store_scan_results(json_file):
    """Store scan results in database."""
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    conn = create_database()
    cursor = conn.cursor()
    
    # Insert scan metadata
    cursor.execute('''
        INSERT INTO scans (timestamp, network_scanned, total_devices, scan_duration)
        VALUES (?, ?, ?, ?)
    ''', (
        data['scan_metadata']['timestamp'],
        data['scan_metadata']['network_scanned'],
        len(data['devices']),
        data['scan_metadata']['scan_duration']
    ))
    
    scan_id = cursor.lastrowid
    
    # Insert device information
    for device in data['devices']:
        cursor.execute('''
            INSERT INTO devices (scan_id, ip_address, mac_address, hostname, 
                               device_type, os_info, manufacturer, model, open_ports)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            scan_id,
            device['ip_address'],
            device.get('mac_address'),
            device.get('hostname'),
            device['device_type'],
            device.get('os_info'),
            device.get('manufacturer'),
            device.get('model'),
            ','.join(map(str, device.get('open_ports', [])))
        ))
    
    conn.commit()
    conn.close()
    print(f"Stored scan results in database: {len(data['devices'])} devices")

if __name__ == "__main__":
    store_scan_results(sys.argv[1])
```

Usage:
```bash
# Run scan and store results
RESULT_FILE=$(python -m network_discovery | grep "Report saved to:" | awk '{print $NF}')
python store_results.py "$RESULT_FILE"
```

### API Integration

#### REST API Wrapper
```python
#!/usr/bin/env python3
# api_server.py - REST API wrapper for network discovery

from flask import Flask, jsonify, request
import subprocess
import json
import os
from datetime import datetime

app = Flask(__name__)

@app.route('/api/scan', methods=['POST'])
def start_scan():
    """Start a network discovery scan."""
    config = request.json.get('config', 'default')
    output_dir = f"api_scans/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Run scan
    cmd = ['python', '-m', 'network_discovery', '--output-dir', output_dir]
    if config != 'default':
        cmd.extend(['--config-dir', f'configs/{config}'])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        if result.returncode == 0:
            # Find the generated JSON file
            json_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
            if json_files:
                with open(os.path.join(output_dir, json_files[0]), 'r') as f:
                    scan_data = json.load(f)
                return jsonify({
                    'status': 'success',
                    'scan_id': json_files[0].replace('.json', ''),
                    'devices_found': len(scan_data['devices']),
                    'scan_duration': scan_data['scan_metadata']['scan_duration']
                })
        
        return jsonify({'status': 'error', 'message': result.stderr}), 500
        
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Scan timeout'}), 408

@app.route('/api/results/<scan_id>', methods=['GET'])
def get_results(scan_id):
    """Get scan results by ID."""
    try:
        # Find the scan file
        for root, dirs, files in os.walk('api_scans'):
            for file in files:
                if scan_id in file and file.endswith('.json'):
                    with open(os.path.join(root, file), 'r') as f:
                        return jsonify(json.load(f))
        
        return jsonify({'error': 'Scan not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    os.makedirs('api_scans', exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
```

Usage:
```bash
# Start API server
python api_server.py

# Start scan via API
curl -X POST http://localhost:5000/api/scan \
     -H "Content-Type: application/json" \
     -d '{"config": "fast_scan"}'

# Get results
curl http://localhost:5000/api/results/network_discovery_20240115_103246
```

## Troubleshooting Examples

### Permission Issues

#### Running Without Root Privileges
```bash
# If you get permission errors with NMAP SYN scans
# Edit nmap_config.yml to use TCP connect scans instead:
sed -i 's/scan_type: "-sS"/scan_type: "-sT"/' network_discovery/config/nmap_config.yml

# Run scan
python -m network_discovery
```

#### SNMP Access Issues
```bash
# Test SNMP access manually
snmpwalk -v2c -c public 192.168.1.1 1.3.6.1.2.1.1.1.0

# If access fails, try different community strings in snmp_config.yml:
# communities:
#   - "public"
#   - "private"
#   - "admin"
#   - "monitoring"
```

### Network Connectivity Issues

#### Testing Network Connectivity
```bash
# Test basic connectivity
ping -c 3 192.168.1.1

# Test ARP functionality
arping -c 3 192.168.1.1

# Test NMAP functionality
nmap -sn 192.168.1.1

# If issues persist, try different scanning methods in arp_config.yml:
# method: "ping"  # Fallback method
```

### Performance Issues

#### Slow Scanning
```bash
# Use fast scan configuration
cp network_discovery/config/examples/fast_scan_config.yml network_discovery/config/

# Run with reduced parallelism
python -m network_discovery --verbose

# Monitor network usage during scan
iftop -i eth0  # Linux
netstat -e 1   # Windows
```

#### Memory Issues
```bash
# Monitor memory usage
top -p $(pgrep -f network_discovery)

# If memory usage is high, reduce SNMP data collection:
# Edit snmp_config.yml:
# max_walk_oids: 25
# walk_oids: []  # Disable OID walks
```

### Configuration Validation

#### Validate Configuration Files
```python
#!/usr/bin/env python3
# validate_config.py - Validate configuration files

import yaml
import sys

def validate_config(config_file):
    """Validate a YAML configuration file."""
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        print(f"✅ {config_file}: Valid YAML syntax")
        
        # Basic structure validation
        if 'arp' in config:
            required_arp = ['timeout', 'retries', 'method', 'parallel_threads']
            missing = [key for key in required_arp if key not in config['arp']]
            if missing:
                print(f"⚠️  Missing ARP keys: {missing}")
            else:
                print("✅ ARP configuration: Complete")
        
        if 'nmap' in config:
            required_nmap = ['scan_type', 'port_range', 'timing', 'max_parallel']
            missing = [key for key in required_nmap if key not in config['nmap']]
            if missing:
                print(f"⚠️  Missing NMAP keys: {missing}")
            else:
                print("✅ NMAP configuration: Complete")
        
        if 'snmp' in config:
            required_snmp = ['versions', 'communities', 'timeout']
            missing = [key for key in required_snmp if key not in config['snmp']]
            if missing:
                print(f"⚠️  Missing SNMP keys: {missing}")
            else:
                print("✅ SNMP configuration: Complete")
        
        return True
        
    except yaml.YAMLError as e:
        print(f"❌ {config_file}: Invalid YAML syntax - {e}")
        return False
    except FileNotFoundError:
        print(f"❌ {config_file}: File not found")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_config.py <config_file>")
        sys.exit(1)
    
    validate_config(sys.argv[1])
```

Usage:
```bash
# Validate configuration files
python validate_config.py network_discovery/config/arp_config.yml
python validate_config.py network_discovery/config/nmap_config.yml
python validate_config.py network_discovery/config/snmp_config.yml
```

This comprehensive usage examples document provides practical guidance for using the Network Discovery Module in various real-world scenarios.