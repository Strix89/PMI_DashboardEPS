# Network Discovery Module - Workflow Documentation

## Complete Scan Workflow

This document describes the detailed workflow of the Network Discovery Module, from initialization to final report generation.

### Overview Workflow Diagram

```mermaid
flowchart TD
    START([Start Application]) --> INIT[Initialize Application]
    INIT --> PREFLIGHT[Pre-flight Checks]
    PREFLIGHT --> PREFLIGHT_OK{Checks Pass?}
    PREFLIGHT_OK -->|No| PREFLIGHT_FAIL[Report Failures]
    PREFLIGHT_FAIL --> EXIT_FAIL([Exit with Error])
    PREFLIGHT_OK -->|Yes| LOAD_CONFIG[Load Configurations]
    
    LOAD_CONFIG --> DETECT_NET[Detect Network]
    DETECT_NET --> CALC_RANGE[Calculate Scan Range]
    CALC_RANGE --> START_SCAN[Start Scan Pipeline]
    
    START_SCAN --> ARP_PHASE[ARP Discovery Phase]
    ARP_PHASE --> ARP_OK{ARP Success?}
    ARP_OK -->|No| ARP_ERROR[Handle ARP Errors]
    ARP_ERROR --> NMAP_PHASE
    ARP_OK -->|Yes| NMAP_PHASE[NMAP Scanning Phase]
    
    NMAP_PHASE --> NMAP_OK{NMAP Success?}
    NMAP_OK -->|No| NMAP_ERROR[Handle NMAP Errors]
    NMAP_ERROR --> SNMP_CHECK
    NMAP_OK -->|Yes| SNMP_CHECK{SNMP Devices Found?}
    
    SNMP_CHECK -->|Yes| SNMP_PHASE[SNMP Querying Phase]
    SNMP_CHECK -->|No| MERGE_RESULTS[Merge Results]
    SNMP_PHASE --> SNMP_OK{SNMP Success?}
    SNMP_OK -->|No| SNMP_ERROR[Handle SNMP Errors]
    SNMP_ERROR --> MERGE_RESULTS
    SNMP_OK -->|Yes| MERGE_RESULTS
    
    MERGE_RESULTS --> CLASSIFY[Classify Devices]
    CLASSIFY --> GENERATE_REPORT[Generate JSON Report]
    GENERATE_REPORT --> SUCCESS([Scan Complete])
```

## Phase 1: Application Initialization

### 1.1 Startup Sequence

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant App as NetworkDiscoveryApp
    participant Logger
    participant ErrorHandler
    
    User->>CLI: python -m network_discovery [args]
    CLI->>CLI: Parse arguments
    CLI->>Logger: Configure log level
    CLI->>App: Create application instance
    App->>Logger: Initialize logger
    App->>ErrorHandler: Initialize error handler
    App->>App: Register signal handlers
    App-->>CLI: Application ready
```

### 1.2 Signal Handler Registration

The application registers handlers for graceful shutdown:
- **SIGINT** (Ctrl+C): Graceful shutdown with cleanup
- **SIGTERM**: Graceful shutdown for process management

### 1.3 Argument Processing

Command-line arguments are processed and validated:
- Configuration directory path validation
- Output directory creation/validation
- Logging level configuration
- Feature flags (skip-checks, skip-arp, etc.)

## Phase 2: Pre-flight Checks

### 2.1 Pre-flight Check Workflow

```mermaid
flowchart TD
    START_PREFLIGHT[Start Pre-flight Checks] --> CHECK_TOOLS[Check External Tools]
    CHECK_TOOLS --> NMAP_CHECK{nmap available?}
    NMAP_CHECK -->|No| NMAP_FAIL[Report nmap missing]
    NMAP_CHECK -->|Yes| ARPING_CHECK{arping available?}
    ARPING_CHECK -->|No| ARPING_WARN[Warn arping missing]
    ARPING_CHECK -->|Yes| TOOLS_OK[Tools validated]
    NMAP_FAIL --> TOOLS_OK
    ARPING_WARN --> TOOLS_OK
    
    TOOLS_OK --> CHECK_PYTHON[Check Python Dependencies]
    CHECK_PYTHON --> DEPS_OK{All deps available?}
    DEPS_OK -->|No| DEPS_FAIL[Report missing dependencies]
    DEPS_OK -->|Yes| CHECK_NETWORK[Test Network Connectivity]
    
    CHECK_NETWORK --> PING_TEST[Ping 8.8.8.8]
    PING_TEST --> PING_OK{Ping successful?}
    PING_OK -->|No| PING_WARN[Warn connectivity issues]
    PING_OK -->|Yes| CHECK_PERMS[Check Network Permissions]
    PING_WARN --> CHECK_PERMS
    
    CHECK_PERMS --> RAW_SOCKET[Try raw socket creation]
    RAW_SOCKET --> SOCKET_OK{Socket created?}
    SOCKET_OK -->|No| SOCKET_WARN[Warn limited permissions]
    SOCKET_OK -->|Yes| PREFLIGHT_COMPLETE[Pre-flight Complete]
    SOCKET_WARN --> PREFLIGHT_COMPLETE
    DEPS_FAIL --> PREFLIGHT_COMPLETE
```

### 2.2 Tool Validation Details

#### External Tool Checks
1. **nmap**: Required for port scanning
   - Check if executable exists in PATH
   - Verify version compatibility
   - Test execution permissions
   
2. **arping**: Optional for ARP scanning
   - Check availability
   - Fallback to scapy if missing
   - Test execution permissions

#### Python Dependency Checks
Required packages validated:
- `colorama`: For colored console output
- `yaml`: For configuration file parsing
- `pysnmp`: For SNMP operations
- `scapy`: For network packet operations

#### Network Permission Checks
- Raw socket creation (requires elevated privileges)
- Regular socket creation (basic network access)
- Interface enumeration capabilities

## Phase 3: Configuration Loading

### 3.1 Configuration Loading Workflow

```mermaid
flowchart TD
    START_CONFIG[Start Configuration Loading] --> FIND_CONFIG[Locate Config Directory]
    FIND_CONFIG --> CONFIG_EXISTS{Config dir exists?}
    CONFIG_EXISTS -->|No| USE_DEFAULT[Use default config directory]
    CONFIG_EXISTS -->|Yes| LOAD_ARP[Load ARP Configuration]
    USE_DEFAULT --> LOAD_ARP
    
    LOAD_ARP --> ARP_EXISTS{arp_config.yml exists?}
    ARP_EXISTS -->|No| ARP_DEFAULT[Use default ARP config]
    ARP_EXISTS -->|Yes| PARSE_ARP[Parse ARP YAML]
    ARP_DEFAULT --> LOAD_NMAP
    PARSE_ARP --> VALIDATE_ARP[Validate ARP config]
    VALIDATE_ARP --> LOAD_NMAP[Load NMAP Configuration]
    
    LOAD_NMAP --> NMAP_EXISTS{nmap_config.yml exists?}
    NMAP_EXISTS -->|No| NMAP_DEFAULT[Use default NMAP config]
    NMAP_EXISTS -->|Yes| PARSE_NMAP[Parse NMAP YAML]
    NMAP_DEFAULT --> LOAD_SNMP
    PARSE_NMAP --> VALIDATE_NMAP[Validate NMAP config]
    VALIDATE_NMAP --> LOAD_SNMP[Load SNMP Configuration]
    
    LOAD_SNMP --> SNMP_EXISTS{snmp_config.yml exists?}
    SNMP_EXISTS -->|No| SNMP_DEFAULT[Use default SNMP config]
    SNMP_EXISTS -->|Yes| PARSE_SNMP[Parse SNMP YAML]
    SNMP_DEFAULT --> CONFIG_COMPLETE[Configuration Complete]
    PARSE_SNMP --> VALIDATE_SNMP[Validate SNMP config]
    VALIDATE_SNMP --> CONFIG_COMPLETE
```

### 3.2 Configuration Validation

Each configuration file is validated for:
- **Syntax**: Valid YAML format
- **Schema**: Required fields present
- **Values**: Reasonable ranges and types
- **Dependencies**: Compatible settings across configs

## Phase 4: Network Detection

### 4.1 Network Detection Workflow

```mermaid
flowchart TD
    START_DETECT[Start Network Detection] --> GET_INTERFACES[Get Network Interfaces]
    GET_INTERFACES --> FIND_DEFAULT[Find Default Interface]
    FIND_DEFAULT --> GET_IP[Get Interface IP Address]
    GET_IP --> GET_NETMASK[Get Network Mask]
    GET_NETMASK --> CALC_NETWORK[Calculate Network Address]
    CALC_NETWORK --> CALC_BROADCAST[Calculate Broadcast Address]
    CALC_BROADCAST --> CALC_RANGE[Calculate Scan Range]
    CALC_RANGE --> EXCLUDE_ADDRS[Exclude Reserved Addresses]
    EXCLUDE_ADDRS --> LOG_INFO[Log Network Information]
    LOG_INFO --> DETECT_COMPLETE[Network Detection Complete]
```

### 4.2 Address Exclusion Logic

The following addresses are automatically excluded from scanning:
- **Network Address**: First address in subnet (e.g., 192.168.1.0/24)
- **Broadcast Address**: Last address in subnet (e.g., 192.168.1.255/24)
- **Host Address**: The scanning machine's IP address
- **Reserved Ranges**: Any configured exclusion ranges

### 4.3 Network Information Logging

Detected network information is logged:
```
Network Detection Results:
├── Interface: eth0
├── Host IP: 192.168.1.100
├── Network: 192.168.1.0/24
├── Scan Range: 192.168.1.1-192.168.1.254
└── Excluded: 192.168.1.0, 192.168.1.100, 192.168.1.255
```

## Phase 5: ARP Discovery Phase

### 5.1 ARP Scanning Workflow

```mermaid
flowchart TD
    START_ARP[Start ARP Phase] --> LOAD_ARP_CONFIG[Load ARP Configuration]
    LOAD_ARP_CONFIG --> CREATE_TARGETS[Create Target List]
    CREATE_TARGETS --> CHOOSE_METHOD{ARP Method?}
    
    CHOOSE_METHOD -->|arping| ARPING_SCAN[Use arping command]
    CHOOSE_METHOD -->|scapy| SCAPY_SCAN[Use scapy library]
    CHOOSE_METHOD -->|ping| PING_SCAN[Use ICMP ping]
    
    ARPING_SCAN --> PARALLEL_ARP[Execute Parallel ARP Scans]
    SCAPY_SCAN --> PARALLEL_ARP
    PING_SCAN --> PARALLEL_ARP
    
    PARALLEL_ARP --> COLLECT_RESULTS[Collect ARP Results]
    COLLECT_RESULTS --> PARSE_RESPONSES[Parse ARP Responses]
    PARSE_RESPONSES --> EXTRACT_MAC[Extract MAC Addresses]
    EXTRACT_MAC --> LOG_ARP_RESULTS[Log ARP Results]
    LOG_ARP_RESULTS --> ARP_COMPLETE[ARP Phase Complete]
```

### 5.2 ARP Scanning Methods

#### Method 1: arping Command
- Executes external `arping` command
- Fastest and most reliable
- Requires arping tool installation
- May need elevated privileges

#### Method 2: scapy Library
- Pure Python implementation
- Cross-platform compatibility
- No external dependencies
- Slightly slower than arping

#### Method 3: ICMP Ping (Fallback)
- Uses standard ping command
- Most compatible method
- Less accurate (devices may not respond to ping)
- No MAC address information

### 5.3 Parallel Processing

ARP requests are processed in parallel using thread pools:
- Configurable thread count
- Rate limiting to prevent network flooding
- Timeout handling for non-responsive targets
- Retry logic for failed requests

## Phase 6: NMAP Scanning Phase

### 6.1 NMAP Scanning Workflow

```mermaid
flowchart TD
    START_NMAP[Start NMAP Phase] --> FILTER_TARGETS[Filter ARP Results]
    FILTER_TARGETS --> BUILD_COMMAND[Build NMAP Command]
    BUILD_COMMAND --> VALIDATE_COMMAND[Validate Command Parameters]
    VALIDATE_COMMAND --> EXECUTE_NMAP[Execute NMAP Scan]
    
    EXECUTE_NMAP --> MONITOR_PROGRESS[Monitor Scan Progress]
    MONITOR_PROGRESS --> SCAN_COMPLETE{Scan Complete?}
    SCAN_COMPLETE -->|No| CHECK_TIMEOUT{Timeout Reached?}
    CHECK_TIMEOUT -->|Yes| TIMEOUT_ERROR[Handle Timeout]
    CHECK_TIMEOUT -->|No| MONITOR_PROGRESS
    SCAN_COMPLETE -->|Yes| PARSE_XML[Parse NMAP XML Output]
    TIMEOUT_ERROR --> PARSE_XML
    
    PARSE_XML --> EXTRACT_HOSTS[Extract Host Information]
    EXTRACT_HOSTS --> EXTRACT_PORTS[Extract Port Information]
    EXTRACT_PORTS --> EXTRACT_SERVICES[Extract Service Information]
    EXTRACT_SERVICES --> EXTRACT_OS[Extract OS Information]
    EXTRACT_OS --> IDENTIFY_SNMP[Identify SNMP-Enabled Devices]
    IDENTIFY_SNMP --> LOG_NMAP_RESULTS[Log NMAP Results]
    LOG_NMAP_RESULTS --> NMAP_COMPLETE[NMAP Phase Complete]
```

### 6.2 NMAP Command Construction

The NMAP command is built dynamically from configuration:

```bash
nmap -sS -F -T4 -O -sV --script=banner -oX output.xml target1 target2 ...
```

Components:
- **Scan Type** (`-sS`): TCP SYN scan
- **Port Range** (`-F`): Fast scan (top 100 ports)
- **Timing** (`-T4`): Aggressive timing
- **OS Detection** (`-O`): Operating system fingerprinting
- **Service Detection** (`-sV`): Service version detection
- **Scripts** (`--script=banner`): Additional information gathering
- **Output Format** (`-oX`): XML output for parsing

### 6.3 Result Parsing

NMAP XML output is parsed to extract:
- **Host Status**: Up/down status for each target
- **Open Ports**: List of accessible ports per host
- **Services**: Service names and versions
- **Operating System**: OS fingerprinting results
- **SNMP Detection**: Devices with port 161 open

## Phase 7: SNMP Querying Phase

### 7.1 SNMP Scanning Workflow

```mermaid
flowchart TD
    START_SNMP[Start SNMP Phase] --> FILTER_SNMP[Filter SNMP-Enabled Devices]
    FILTER_SNMP --> SNMP_FOUND{SNMP Devices Found?}
    SNMP_FOUND -->|No| SKIP_SNMP[Skip SNMP Phase]
    SNMP_FOUND -->|Yes| LOAD_SNMP_CONFIG[Load SNMP Configuration]
    
    LOAD_SNMP_CONFIG --> ITERATE_DEVICES[Iterate Through Devices]
    ITERATE_DEVICES --> TRY_VERSIONS[Try SNMP Versions]
    TRY_VERSIONS --> TRY_COMMUNITIES[Try Community Strings]
    TRY_COMMUNITIES --> TEST_ACCESS[Test SNMP Access]
    
    TEST_ACCESS --> ACCESS_OK{Access Granted?}
    ACCESS_OK -->|No| NEXT_COMMUNITY[Try Next Community]
    NEXT_COMMUNITY --> MORE_COMMUNITIES{More Communities?}
    MORE_COMMUNITIES -->|Yes| TRY_COMMUNITIES
    MORE_COMMUNITIES -->|No| NEXT_VERSION[Try Next Version]
    NEXT_VERSION --> MORE_VERSIONS{More Versions?}
    MORE_VERSIONS -->|Yes| TRY_VERSIONS
    MORE_VERSIONS -->|No| NEXT_DEVICE[Next Device]
    
    ACCESS_OK -->|Yes| QUERY_SPECIFIC[Query Specific OIDs]
    QUERY_SPECIFIC --> WALK_TREES[Walk OID Trees]
    WALK_TREES --> PARSE_SNMP[Parse SNMP Responses]
    PARSE_SNMP --> NEXT_DEVICE
    
    NEXT_DEVICE --> MORE_DEVICES{More Devices?}
    MORE_DEVICES -->|Yes| ITERATE_DEVICES
    MORE_DEVICES -->|No| LOG_SNMP_RESULTS[Log SNMP Results]
    SKIP_SNMP --> LOG_SNMP_RESULTS
    LOG_SNMP_RESULTS --> SNMP_COMPLETE[SNMP Phase Complete]
```

### 7.2 SNMP Access Testing

For each device with port 161 open:

1. **Version Testing**: Try SNMP versions in configured order (v2c, v1)
2. **Community Testing**: Try community strings in configured order
3. **Access Validation**: Perform test query to validate access
4. **Timeout Handling**: Respect configured timeouts and retries

### 7.3 SNMP Data Collection

#### Specific OID Queries
Individual OIDs are queried for essential information:
- System description (1.3.6.1.2.1.1.1.0)
- System name (1.3.6.1.2.1.1.5.0)
- System location (1.3.6.1.2.1.1.6.0)
- Interface count (1.3.6.1.2.1.2.1.0)

#### OID Tree Walking
Complete subtrees are walked for comprehensive data:
- System information tree (1.3.6.1.2.1.1)
- Interface information tree (1.3.6.1.2.1.2)
- IP information tree (1.3.6.1.2.1.4)

## Phase 8: Result Processing

### 8.1 Result Merging Workflow

```mermaid
flowchart TD
    START_MERGE[Start Result Merging] --> COLLECT_ARP[Collect ARP Results]
    COLLECT_ARP --> COLLECT_NMAP[Collect NMAP Results]
    COLLECT_NMAP --> COLLECT_SNMP[Collect SNMP Results]
    COLLECT_SNMP --> CREATE_DEVICE_MAP[Create Device Map by IP]
    
    CREATE_DEVICE_MAP --> MERGE_ARP_DATA[Merge ARP Data]
    MERGE_ARP_DATA --> MERGE_NMAP_DATA[Merge NMAP Data]
    MERGE_NMAP_DATA --> MERGE_SNMP_DATA[Merge SNMP Data]
    MERGE_SNMP_DATA --> RESOLVE_CONFLICTS[Resolve Data Conflicts]
    RESOLVE_CONFLICTS --> MERGE_COMPLETE[Merge Complete]
```

### 8.2 Device Classification Workflow

```mermaid
flowchart TD
    START_CLASS[Start Device Classification] --> ANALYZE_OS[Analyze OS Information]
    ANALYZE_OS --> OS_WINDOWS{Windows Detected?}
    OS_WINDOWS -->|Yes| CLASS_WINDOWS[Classify as Windows]
    OS_WINDOWS -->|No| OS_LINUX{Linux Detected?}
    OS_LINUX -->|Yes| CLASS_LINUX[Classify as Linux]
    OS_LINUX -->|No| ANALYZE_PORTS[Analyze Open Ports]
    
    ANALYZE_PORTS --> IOT_PORTS{IoT Ports Detected?}
    IOT_PORTS -->|Yes| CLASS_IOT[Classify as IoT]
    IOT_PORTS -->|No| NETWORK_PORTS{Network Ports Detected?}
    NETWORK_PORTS -->|Yes| ANALYZE_SNMP[Analyze SNMP Data]
    NETWORK_PORTS -->|No| CLASS_UNKNOWN[Classify as Unknown]
    
    ANALYZE_SNMP --> SNMP_VENDOR{Vendor Info Available?}
    SNMP_VENDOR -->|Yes| CLASS_NETWORK[Classify as Network Equipment]
    SNMP_VENDOR -->|No| CLASS_NETWORK
    
    CLASS_WINDOWS --> LOG_CLASSIFICATION[Log Classification Results]
    CLASS_LINUX --> LOG_CLASSIFICATION
    CLASS_IOT --> LOG_CLASSIFICATION
    CLASS_NETWORK --> LOG_CLASSIFICATION
    CLASS_UNKNOWN --> LOG_CLASSIFICATION
    LOG_CLASSIFICATION --> CLASS_COMPLETE[Classification Complete]
```

### 8.3 Classification Rules

#### Windows Detection
- OS fingerprint contains "Windows"
- Common Windows ports: 135, 139, 445, 3389
- Windows-specific services detected

#### Linux Detection
- OS fingerprint contains "Linux"
- Common Linux ports: 22 (SSH), 80/443 (web services)
- Unix-like service signatures

#### IoT Device Detection
- Common IoT ports: 1883 (MQTT), 5683 (CoAP), 8080 (web interface)
- Embedded system signatures
- Limited service profiles

#### Network Equipment Detection
- SNMP data contains network vendor information
- Network management ports: 161 (SNMP), 23 (Telnet), 80/443 (web management)
- Router/switch specific OIDs in SNMP data

## Phase 9: Report Generation

### 9.1 Report Generation Workflow

```mermaid
flowchart TD
    START_REPORT[Start Report Generation] --> COLLECT_METADATA[Collect Scan Metadata]
    COLLECT_METADATA --> CALC_STATISTICS[Calculate Statistics]
    CALC_STATISTICS --> FORMAT_DEVICES[Format Device Information]
    FORMAT_DEVICES --> CREATE_JSON[Create JSON Structure]
    CREATE_JSON --> VALIDATE_JSON[Validate JSON Schema]
    VALIDATE_JSON --> GENERATE_FILENAME[Generate Timestamp Filename]
    GENERATE_FILENAME --> WRITE_FILE[Write JSON File]
    WRITE_FILE --> LOG_REPORT_PATH[Log Report Path]
    LOG_REPORT_PATH --> REPORT_COMPLETE[Report Generation Complete]
```

### 9.2 Report Structure

The final JSON report contains:

#### Scan Metadata
- Timestamp and duration
- Network configuration
- Scan parameters used
- Success/failure status

#### Scan Statistics
- Total addresses scanned
- Devices found per phase
- Timing information
- Error counts

#### Device Information
- Complete device profiles
- Classification results
- All collected data (ARP, NMAP, SNMP)
- Confidence scores

### 9.3 File Naming Convention

Reports are saved with timestamp-based names:
```
network_discovery_YYYYMMDD_HHMMSS.json
```

If a file with the same timestamp exists, a counter is appended:
```
network_discovery_YYYYMMDD_HHMMSS_001.json
```

## Error Handling Throughout Workflow

### Error Categories

1. **Network Errors**: Connection timeouts, unreachable hosts
2. **Permission Errors**: Insufficient privileges for operations
3. **Configuration Errors**: Invalid or missing configuration
4. **Tool Errors**: External tool failures or missing tools

### Recovery Strategies

1. **Retry with Backoff**: For transient network errors
2. **Fallback Methods**: Alternative scanning methods when primary fails
3. **Graceful Degradation**: Continue with partial results when possible
4. **User Guidance**: Provide actionable error messages and solutions

### Logging Throughout Workflow

Each phase logs:
- **Progress Information**: Current operation and completion percentage
- **Success Messages**: Successful operations and results
- **Warning Messages**: Non-critical issues and fallback actions
- **Error Messages**: Failures with detailed context and suggestions

The logging system uses color coding for easy visual parsing:
- 🟢 **Green**: Success and progress
- 🟡 **Yellow**: Warnings and non-critical issues
- 🔴 **Red**: Errors and failures
- 🔵 **Blue**: Informational messages
- 🟣 **Cyan**: Debug information (verbose mode)