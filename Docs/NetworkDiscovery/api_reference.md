# Network Discovery Module - API Reference

This document provides comprehensive API documentation for the Network Discovery Module's Python classes and methods.

## Table of Contents

- [Core Classes](#core-classes)
  - [NetworkDiscoveryApp](#networkdiscoveryapp)
  - [ScannerOrchestrator](#scannerorchestrator)
  - [Data Models](#data-models)
- [Scanner Classes](#scanner-classes)
  - [ARPScanner](#arpscanner)
  - [NMAPScanner](#nmapscanner)
  - [SNMPScanner](#snmpscanner)
- [Utility Classes](#utility-classes)
  - [Logger](#logger)
  - [ErrorHandler](#errorhandler)
  - [NetworkValidator](#networkvalidator)

---

## Core Classes

### NetworkDiscoveryApp

Main application class that handles CLI interface, pre-flight checks, and application lifecycle.

#### Constructor

```python
NetworkDiscoveryApp()
```

Initializes the application with signal handlers for graceful shutdown.

#### Methods

##### `run(args: argparse.Namespace) -> int`

Run the network discovery application.

**Parameters:**
- `args`: Parsed command line arguments

**Returns:**
- `int`: Exit code (0 for success, non-zero for failure)

**Example:**
```python
from network_discovery.main import NetworkDiscoveryApp, create_argument_parser

parser = create_argument_parser()
args = parser.parse_args()
app = NetworkDiscoveryApp()
exit_code = app.run(args)
```

##### `_perform_preflight_checks() -> bool`

Perform comprehensive pre-flight checks for required external tools and system readiness.

**Returns:**
- `bool`: True if all checks pass, False otherwise

---

### ScannerOrchestrator

Orchestrates the complete network discovery scan pipeline, managing ARP → NMAP → SNMP sequence.

#### Constructor

```python
ScannerOrchestrator(
    config_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    skip_arp: bool = False,
    error_handler: Optional[ErrorHandler] = None
)
```

**Parameters:**
- `config_dir`: Directory containing configuration files (optional)
- `output_dir`: Directory for output files (optional)
- `skip_arp`: Skip ARP scan phase (optional)
- `error_handler`: ErrorHandler instance for centralized error management (optional)

#### Methods

##### `execute_full_scan() -> CompleteScanResult`

Execute the complete scan pipeline: ARP → NMAP → SNMP.

**Returns:**
- `CompleteScanResult`: Complete scan results with all discovered devices

**Raises:**
- `RuntimeError`: If critical scan phases fail

**Example:**
```python
from network_discovery.core.scanner_orchestrator import ScannerOrchestrator

orchestrator = ScannerOrchestrator(
    config_dir="./config",
    output_dir="./results"
)
scan_result = orchestrator.execute_full_scan()
print(f"Found {len(scan_result.devices)} devices")
```

---

## Data Models

### DeviceType

Enumeration of device types that can be detected during network scanning.

**Values:**
- `IOT`: IoT devices
- `WINDOWS`: Windows machines
- `LINUX`: Linux machines
- `NETWORK_EQUIPMENT`: Network equipment (routers, switches, etc.)
- `UNKNOWN`: Unknown device type

### ScanStatus

Enumeration of possible scan statuses.

**Values:**
- `NOT_STARTED`: Scan has not started
- `IN_PROGRESS`: Scan is currently running
- `COMPLETED`: Scan completed successfully
- `FAILED`: Scan failed
- `PARTIAL`: Scan completed with some failures

### NetworkInfo

Information about the host network configuration.

**Attributes:**
- `host_ip: str`: IP address of the scanning host
- `netmask: str`: Network subnet mask
- `network_address: str`: Network address (e.g., 192.168.1.0)
- `broadcast_address: str`: Broadcast address (e.g., 192.168.1.255)
- `interface_name: str`: Name of the network interface used
- `scan_range: List[str]`: List of IP addresses to be scanned

### DeviceInfo

Information about a discovered network device.

**Attributes:**
- `ip_address: str`: IP address of the device
- `mac_address: Optional[str]`: MAC address (if available from ARP)
- `hostname: Optional[str]`: Device hostname (if resolvable)
- `os_info: Optional[str]`: Operating system information from NMAP
- `device_type: DeviceType`: Classified device type
- `manufacturer: Optional[str]`: Device manufacturer (from SNMP if available)
- `model: Optional[str]`: Device model (from SNMP if available)
- `open_ports: List[int]`: List of open TCP/UDP ports
- `services: Dict[int, str]`: Mapping of port numbers to service names
- `snmp_data: Optional[Dict[str, str]]`: SNMP OID-value pairs (if SNMP scan was successful)

**Example:**
```python
from network_discovery.core.data_models import DeviceInfo, DeviceType

device = DeviceInfo(
    ip_address="192.168.1.100",
    mac_address="aa:bb:cc:dd:ee:ff",
    hostname="printer.local",
    device_type=DeviceType.IOT,
    open_ports=[80, 443, 9100]
)
```

---

## Scanner Classes

### ARPScanner

Performs ARP scanning to discover active devices on the local network.

#### Constructor

```python
ARPScanner(logger: Logger, error_handler: ErrorHandler)
```

#### Methods

##### `scan(network_info: NetworkInfo, config: ARPConfig) -> ScanResult`

Execute ARP scan on the specified network range.

**Parameters:**
- `network_info`: Network configuration information
- `config`: ARP scanner configuration

**Returns:**
- `ScanResult`: Results containing discovered devices with IP and MAC addresses

### NMAPScanner

Performs NMAP scanning for port discovery and OS detection.

#### Constructor

```python
NMAPScanner(logger: Logger, error_handler: ErrorHandler)
```

#### Methods

##### `scan(target_ips: List[str], config: NMAPConfig) -> ScanResult`

Execute NMAP scan on specified IP addresses.

**Parameters:**
- `target_ips`: List of IP addresses to scan
- `config`: NMAP scanner configuration

**Returns:**
- `ScanResult`: Results containing port information and OS detection

### SNMPScanner

Performs SNMP scanning to gather device information.

#### Constructor

```python
SNMPScanner(logger: Logger, error_handler: ErrorHandler)
```

#### Methods

##### `scan(target_ips: List[str], config: SNMPConfig) -> ScanResult`

Execute SNMP scan on specified IP addresses.

**Parameters:**
- `target_ips`: List of IP addresses to scan
- `config`: SNMP scanner configuration

**Returns:**
- `ScanResult`: Results containing SNMP data and device information

---

## Utility Classes

### Logger

Provides structured logging with different levels and formatting.

#### Methods

##### `get_logger(name: str) -> Logger`

Get a logger instance for the specified module.

**Parameters:**
- `name`: Module name (typically `__name__`)

**Returns:**
- `Logger`: Configured logger instance

##### `set_log_level(level: LogLevel) -> None`

Set the global logging level.

**Parameters:**
- `level`: LogLevel enum value (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**Example:**
```python
from network_discovery.utils.logger import get_logger, set_log_level, LogLevel

logger = get_logger(__name__)
set_log_level(LogLevel.DEBUG)
logger.info("Starting network scan")
```

### ErrorHandler

Centralized error handling and reporting system.

#### Constructor

```python
ErrorHandler(logger: Logger)
```

#### Methods

##### `handle_error(error: Exception, context: ErrorContext) -> None`

Handle an error with proper logging and context.

**Parameters:**
- `error`: The exception that occurred
- `context`: Error context information

### NetworkValidator

Validates network connectivity and configuration.

#### Constructor

```python
NetworkValidator(error_handler: ErrorHandler, logger: Logger)
```

#### Methods

##### `ping_host(host: str, count: int = 1, timeout: float = 3.0) -> ValidationResult`

Test connectivity to a specific host using ping.

**Parameters:**
- `host`: Target hostname or IP address
- `count`: Number of ping packets to send
- `timeout`: Timeout in seconds for each ping

**Returns:**
- `ValidationResult`: Result indicating success/failure and details

---

## Usage Examples

### Basic Network Scan

```python
from network_discovery.main import NetworkDiscoveryApp, create_argument_parser

# Parse command line arguments
parser = create_argument_parser()
args = parser.parse_args(['--verbose'])

# Run the application
app = NetworkDiscoveryApp()
exit_code = app.run(args)
```

### Programmatic Scan

```python
from network_discovery.core.scanner_orchestrator import ScannerOrchestrator

# Initialize orchestrator
orchestrator = ScannerOrchestrator(
    config_dir="./config",
    output_dir="./results"
)

# Execute scan
result = orchestrator.execute_full_scan()

# Process results
for device in result.devices:
    print(f"Found device: {device.ip_address} ({device.device_type.value})")
```

### Custom Error Handling

```python
from network_discovery.utils.error_handler import ErrorHandler, ErrorContext, ErrorType
from network_discovery.utils.logger import get_logger

logger = get_logger(__name__)
error_handler = ErrorHandler(logger)

try:
    # Your network discovery code here
    pass
except Exception as e:
    context = ErrorContext(
        error_type=ErrorType.NETWORK_ERROR,
        operation="custom_scan",
        component="MyScanner"
    )
    error_handler.handle_error(e, context)
```