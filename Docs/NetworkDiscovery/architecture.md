# Network Discovery Module - Architecture Documentation

## System Architecture Overview

The Network Discovery Module follows a modular, pipeline-based architecture that separates concerns and enables easy testing and maintenance.

### High-Level Architecture

```mermaid
graph TB
    subgraph "Application Layer"
        CLI[CLI Interface]
        APP[NetworkDiscoveryApp]
    end
    
    subgraph "Orchestration Layer"
        ORCH[ScannerOrchestrator]
        NET[NetworkDetector]
    end
    
    subgraph "Scanner Layer"
        ARP[ARPScanner]
        NMAP[NMAPScanner]
        SNMP[SNMPScanner]
        BASE[BaseScanner]
    end
    
    subgraph "Processing Layer"
        CLASS[DeviceClassifier]
        REPORT[JSONReporter]
    end
    
    subgraph "Support Layer"
        CONFIG[ConfigLoader]
        LOG[Logger]
        ERROR[ErrorHandler]
        VALID[NetworkValidator]
    end
    
    subgraph "Data Layer"
        MODELS[DataModels]
        RESULTS[Results Directory]
    end
    
    CLI --> APP
    APP --> ORCH
    ORCH --> NET
    ORCH --> ARP
    ORCH --> NMAP
    ORCH --> SNMP
    ARP --> BASE
    NMAP --> BASE
    SNMP --> BASE
    ORCH --> CLASS
    ORCH --> REPORT
    APP --> CONFIG
    APP --> LOG
    APP --> ERROR
    APP --> VALID
    REPORT --> RESULTS
    CLASS --> MODELS
    REPORT --> MODELS
```

### Component Responsibilities

#### Application Layer
- **CLI Interface**: Command-line argument parsing and user interaction
- **NetworkDiscoveryApp**: Main application controller, lifecycle management

#### Orchestration Layer
- **ScannerOrchestrator**: Coordinates the scanning pipeline, manages data flow
- **NetworkDetector**: Auto-detects network configuration and calculates scan ranges

#### Scanner Layer
- **BaseScanner**: Abstract interface defining scanner contract
- **ARPScanner**: Discovers active devices using ARP protocol
- **NMAPScanner**: Performs port scanning and OS detection
- **SNMPScanner**: Queries SNMP-enabled devices for detailed information

#### Processing Layer
- **DeviceClassifier**: Categorizes devices based on collected information
- **JSONReporter**: Generates structured output reports

#### Support Layer
- **ConfigLoader**: Loads and validates YAML configurations
- **Logger**: Provides colored, structured logging
- **ErrorHandler**: Centralized error handling and recovery
- **NetworkValidator**: Validates network connectivity and permissions

#### Data Layer
- **DataModels**: Type-safe data structures for all system entities
- **Results Directory**: File system storage for generated reports

## Detailed Component Design

### Scanner Pipeline Architecture

```mermaid
sequenceDiagram
    participant App as NetworkDiscoveryApp
    participant Orch as ScannerOrchestrator
    participant Net as NetworkDetector
    participant ARP as ARPScanner
    participant NMAP as NMAPScanner
    participant SNMP as SNMPScanner
    participant Class as DeviceClassifier
    participant Report as JSONReporter
    
    App->>Orch: execute_full_scan()
    Orch->>Net: get_host_network_info()
    Net-->>Orch: NetworkInfo
    
    Orch->>ARP: scan(targets, config)
    ARP-->>Orch: ARPScanResult
    
    Orch->>NMAP: scan(arp_targets, config)
    NMAP-->>Orch: NMAPScanResult
    
    Orch->>SNMP: scan(snmp_targets, config)
    SNMP-->>Orch: SNMPScanResult
    
    Orch->>Class: classify_devices(merged_results)
    Class-->>Orch: ClassifiedDevices
    
    Orch->>Report: generate_report(complete_results)
    Report-->>Orch: ReportPath
    
    Orch-->>App: CompleteScanResult
```

### Data Flow Architecture

```mermaid
flowchart LR
    subgraph "Input"
        CONFIG[YAML Configs]
        NETWORK[Network Interface]
    end
    
    subgraph "Detection Phase"
        DETECT[Network Detection]
        RANGE[IP Range Calculation]
    end
    
    subgraph "Scanning Phase"
        ARP_SCAN[ARP Discovery]
        NMAP_SCAN[Port Scanning]
        SNMP_SCAN[SNMP Queries]
    end
    
    subgraph "Processing Phase"
        MERGE[Result Merging]
        CLASSIFY[Device Classification]
    end
    
    subgraph "Output"
        JSON[JSON Report]
        LOGS[Colored Logs]
    end
    
    CONFIG --> DETECT
    NETWORK --> DETECT
    DETECT --> RANGE
    RANGE --> ARP_SCAN
    ARP_SCAN --> NMAP_SCAN
    NMAP_SCAN --> SNMP_SCAN
    ARP_SCAN --> MERGE
    NMAP_SCAN --> MERGE
    SNMP_SCAN --> MERGE
    MERGE --> CLASSIFY
    CLASSIFY --> JSON
    CLASSIFY --> LOGS
```

### Error Handling Architecture

```mermaid
graph TD
    subgraph "Error Sources"
        NET_ERR[Network Errors]
        PERM_ERR[Permission Errors]
        CONFIG_ERR[Configuration Errors]
        TOOL_ERR[External Tool Errors]
    end
    
    subgraph "Error Handler"
        DETECT[Error Detection]
        CLASSIFY_ERR[Error Classification]
        RECOVERY[Recovery Strategy]
        LOGGING[Error Logging]
    end
    
    subgraph "Recovery Actions"
        RETRY[Retry with Backoff]
        FALLBACK[Fallback Method]
        SKIP[Skip Operation]
        ABORT[Abort Scan]
    end
    
    NET_ERR --> DETECT
    PERM_ERR --> DETECT
    CONFIG_ERR --> DETECT
    TOOL_ERR --> DETECT
    
    DETECT --> CLASSIFY_ERR
    CLASSIFY_ERR --> RECOVERY
    RECOVERY --> LOGGING
    
    RECOVERY --> RETRY
    RECOVERY --> FALLBACK
    RECOVERY --> SKIP
    RECOVERY --> ABORT
```

## Design Patterns Used

### 1. Strategy Pattern
- **Scanner Interface**: Different scanning strategies (ARP, NMAP, SNMP) implement common interface
- **Configuration Loading**: Different config formats can be supported through common interface

### 2. Pipeline Pattern
- **Scanning Pipeline**: Sequential execution of ARP → NMAP → SNMP with data passing
- **Data Processing**: Raw results → Parsed results → Classified results → Report

### 3. Observer Pattern
- **Logging System**: Components notify logger of events and progress
- **Error Handling**: Components notify error handler of exceptions

### 4. Factory Pattern
- **Scanner Creation**: Scanners are created based on configuration
- **Report Generation**: Different report formats can be created through factory

### 5. Command Pattern
- **CLI Interface**: Command-line arguments encapsulated as commands
- **Scanner Operations**: Each scan operation encapsulated as executable command

## Configuration Architecture

### Configuration Hierarchy

```mermaid
graph TD
    subgraph "Configuration Sources"
        DEFAULT[Default Configs]
        USER[User Configs]
        CLI[CLI Arguments]
    end
    
    subgraph "Configuration Loading"
        LOADER[ConfigLoader]
        VALIDATOR[Config Validator]
        MERGER[Config Merger]
    end
    
    subgraph "Configuration Usage"
        ARP_CONFIG[ARP Configuration]
        NMAP_CONFIG[NMAP Configuration]
        SNMP_CONFIG[SNMP Configuration]
    end
    
    DEFAULT --> LOADER
    USER --> LOADER
    CLI --> LOADER
    
    LOADER --> VALIDATOR
    VALIDATOR --> MERGER
    
    MERGER --> ARP_CONFIG
    MERGER --> NMAP_CONFIG
    MERGER --> SNMP_CONFIG
```

### Configuration Precedence
1. **CLI Arguments** (highest priority)
2. **User Configuration Files**
3. **Default Configuration Files** (lowest priority)

## Security Considerations

### Privilege Requirements
- **NMAP SYN Scans**: Require root/administrator privileges
- **Raw Socket Operations**: Require elevated permissions
- **Network Interface Access**: May require special permissions

### Security Best Practices
- **Input Validation**: All user inputs and configuration values are validated
- **Error Information**: Sensitive information is not exposed in error messages
- **Network Isolation**: Scans are limited to local network segments
- **Rate Limiting**: Built-in delays prevent network flooding

## Performance Characteristics

### Scalability Factors
- **Network Size**: Linear scaling with number of IP addresses
- **Parallel Operations**: Configurable parallelism for different phases
- **Memory Usage**: Bounded by device count and SNMP data volume
- **CPU Usage**: Moderate during active scanning phases

### Optimization Strategies
- **Parallel Scanning**: Multiple threads for ARP and NMAP operations
- **Efficient Data Structures**: Minimal memory footprint for device data
- **Lazy Loading**: SNMP data loaded only when needed
- **Caching**: Network configuration cached for scan duration

## Extension Points

### Adding New Scanners
1. Implement `BaseScanner` interface
2. Add configuration schema
3. Register with `ScannerOrchestrator`
4. Add device classification rules

### Adding New Output Formats
1. Implement reporter interface
2. Add format-specific configuration
3. Register with report factory
4. Update CLI options

### Adding New Device Types
1. Extend `DeviceType` enum
2. Add classification rules to `DeviceClassifier`
3. Update output schema
4. Add documentation

## Testing Architecture

### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: Component interaction testing
- **System Tests**: End-to-end workflow testing
- **Performance Tests**: Scalability and timing validation

### Test Doubles
- **Mock Scanners**: For testing without network access
- **Stub Configurations**: For testing different scenarios
- **Fake Networks**: For controlled testing environments

## Deployment Considerations

### System Requirements
- **Python 3.8+**: Core runtime requirement
- **External Tools**: nmap, arping (optional)
- **Network Access**: Local network scanning permissions
- **File System**: Write access for configuration and results

### Installation Methods
- **Package Installation**: pip install from requirements.txt
- **Standalone Deployment**: Self-contained directory structure
- **Container Deployment**: Docker image with all dependencies

### Configuration Management
- **Default Configurations**: Shipped with reasonable defaults
- **Environment-Specific**: Override defaults for different environments
- **Version Control**: Configuration files can be version controlled