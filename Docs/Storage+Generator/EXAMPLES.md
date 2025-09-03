# Infrastructure Monitoring Storage - Usage Examples

This document provides comprehensive examples for using the Infrastructure Monitoring Storage Layer in various scenarios.

## Table of Contents

1. [Basic Setup](#basic-setup)
2. [Metric Management](#metric-management)
3. [Asset Management](#asset-management)
4. [Advanced Queries](#advanced-queries)
5. [Error Handling](#error-handling)
6. [Performance Optimization](#performance-optimization)
7. [Maintenance Operations](#maintenance-operations)
8. [Real-World Scenarios](#real-world-scenarios)

## Basic Setup

### Simple Connection

```python
from storage_layer import StorageManager
from storage_layer.models import MetricDocument, AssetDocument
from datetime import datetime, timedelta
import logging

# Enable logging for debugging
logging.basicConfig(level=logging.INFO)

# Create storage manager
storage = StorageManager(
    connection_string="mongodb://localhost:27017",
    database_name="infrastructure_monitoring"
)

# Connect and setup
storage.connect()
storage.setup_time_series_collection()
```

### Production Connection with Authentication

```python
# Production setup with authentication and replica set
storage = StorageManager(
    connection_string="mongodb://monitor_user:secure_password@mongo1:27017,mongo2:27017,mongo3:27017/monitoring?replicaSet=rs0&authSource=admin",
    database_name="infrastructure_monitoring"
)

try:
    storage.connect()
    print("Connected to production MongoDB cluster")
    
    # Verify connection health
    status = storage.get_connection_status()
    print(f"Server version: {status['server_info']['version']}")
    print(f"Connection latency: {status['last_ping']:.3f}s")
    
except Exception as e:
    print(f"Connection failed: {e}")
```

### Context Manager Usage

```python
# Automatic connection management
with StorageManager("mongodb://localhost:27017", "monitoring") as storage:
    storage.setup_time_series_collection()
    
    # Your operations here - connection is automatically managed
    metrics = storage.get_metrics(asset_id="vm-101")
    print(f"Found {len(metrics)} metrics")
    
# Connection automatically closed
```

## Metric Management

### Single Metric Creation

```python
# Create a single metric
cpu_metric = MetricDocument(
    timestamp=datetime.utcnow(),
    asset_id="vm-101",
    metric_name="cpu_usage",
    value=75.5
)

# Save single metric (wrapped in batch)
count = storage.save_metrics_batch([cpu_metric])
print(f"Saved {count} metric")
```

### Batch Metric Creation

```python
import random
from datetime import datetime, timedelta

def generate_realistic_metrics(asset_id: str, hours: int = 24) -> list:
    """Generate realistic metrics for testing."""
    metrics = []
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    for i in range(hours * 60):  # One metric per minute
        timestamp = start_time + timedelta(minutes=i)
        
        # Simulate daily patterns
        hour = timestamp.hour
        base_cpu = 30 + (hour * 2) if 9 <= hour <= 17 else 15  # Higher during business hours
        base_memory = 40 + random.uniform(-5, 15)
        
        metrics.extend([
            MetricDocument(timestamp, asset_id, "cpu_usage", base_cpu + random.uniform(-10, 20)),
            MetricDocument(timestamp, asset_id, "memory_usage", base_memory + random.uniform(-5, 10)),
            MetricDocument(timestamp, asset_id, "disk_io_wait", random.uniform(0, 5)),
        ])
    
    return metrics

# Generate and save 24 hours of metrics
metrics = generate_realistic_metrics("vm-101", hours=24)
inserted_count = storage.save_metrics_batch(metrics)
print(f"Inserted {inserted_count} metrics for 24-hour period")
```

### High-Performance Batch Processing

```python
def process_metrics_in_chunks(metrics: list, chunk_size: int = 1000):
    """Process large metric batches in chunks for optimal performance."""
    total_inserted = 0
    
    for i in range(0, len(metrics), chunk_size):
        chunk = metrics[i:i + chunk_size]
        try:
            inserted = storage.save_metrics_batch(chunk)
            total_inserted += inserted
            print(f"Processed chunk {i//chunk_size + 1}: {inserted} metrics inserted")
        except Exception as e:
            print(f"Failed to process chunk {i//chunk_size + 1}: {e}")
    
    return total_inserted

# Process 10,000 metrics in chunks
large_batch = generate_realistic_metrics("vm-101", hours=168)  # 1 week
total = process_metrics_in_chunks(large_batch)
print(f"Total metrics processed: {total}")
```

## Asset Management

### Creating Different Asset Types

```python
# Proxmox hypervisor node
hypervisor = AssetDocument(
    asset_id="pve-node-01",
    asset_type="proxmox_node",
    hostname="PVE-HOST-01",
    data={
        "status": "running",
        "cpu_cores": 32,
        "memory_gb": 128,
        "storage_pools": ["local", "shared-storage"],
        "cluster_name": "production"
    }
)

# Virtual machine
vm = AssetDocument(
    asset_id="vm-101",
    asset_type="vm",
    hostname="DB-SERVER-PROD",
    data={
        "status": "running",
        "cpu_cores": 4,
        "memory_gb": 16,
        "hypervisor": "pve-node-01",
        "os": "Ubuntu 20.04",
        "ip_address": "192.168.1.101"
    }
)

# Container
container = AssetDocument(
    asset_id="ct-201",
    asset_type="container",
    hostname="WEB-CONTAINER-01",
    data={
        "status": "running",
        "cpu_cores": 2,
        "memory_gb": 4,
        "hypervisor": "pve-node-01",
        "template": "ubuntu-20.04-standard",
        "ip_address": "192.168.1.201"
    }
)

# Service running on VM
mysql_service = AssetDocument(
    asset_id="svc-mysql-101",
    asset_type="service",
    service_name="MySQL Database",
    data={
        "parent_asset_id": "vm-101",
        "status": "running",
        "service_type": "MySQL",
        "version": "8.0.28",
        "port": 3306,
        "config_file": "/etc/mysql/mysql.conf.d/mysqld.cnf",
        "data_directory": "/var/lib/mysql"
    }
)

# Save all assets
assets = [hypervisor, vm, container, mysql_service]
for asset in assets:
    asset_id = storage.upsert_asset(asset)
    print(f"Saved asset: {asset_id}")
```

### Asset Relationships and Hierarchies

```python
def create_infrastructure_hierarchy():
    """Create a complete infrastructure hierarchy."""
    
    # Create hypervisor
    hypervisor = AssetDocument(
        asset_id="pve-node-01",
        asset_type="proxmox_node",
        hostname="PVE-HOST-01",
        data={"status": "running", "cpu_cores": 32, "memory_gb": 128}
    )
    storage.upsert_asset(hypervisor)
    
    # Create VMs on the hypervisor
    vms = []
    for i in range(1, 4):
        vm = AssetDocument(
            asset_id=f"vm-10{i}",
            asset_type="vm",
            hostname=f"SERVER-{i:02d}",
            data={
                "status": "running",
                "hypervisor": "pve-node-01",
                "cpu_cores": 4,
                "memory_gb": 8
            }
        )
        storage.upsert_asset(vm)
        vms.append(vm)
    
    # Create services on each VM
    service_types = ["MySQL", "Apache", "Redis"]
    for i, vm in enumerate(vms):
        service = AssetDocument(
            asset_id=f"svc-{service_types[i].lower()}-{vm.asset_id}",
            asset_type="service",
            service_name=f"{service_types[i]} Service",
            data={
                "parent_asset_id": vm.asset_id,
                "status": "running",
                "service_type": service_types[i],
                "port": [3306, 80, 6379][i]
            }
        )
        storage.upsert_asset(service)
    
    print("Created complete infrastructure hierarchy")

create_infrastructure_hierarchy()

# Query the hierarchy
hierarchy = storage.get_assets_with_services("vm-101")
print(f"VM: {hierarchy['asset']['hostname']}")
print(f"Services: {[svc['service_name'] for svc in hierarchy['services']]}")
```

## Advanced Queries

### Time-Based Metric Queries

```python
from datetime import datetime, timedelta

# Get metrics for the last hour
one_hour_ago = datetime.utcnow() - timedelta(hours=1)
recent_metrics = storage.get_metrics(
    asset_id="vm-101",
    start_time=one_hour_ago
)
print(f"Metrics in last hour: {len(recent_metrics)}")

# Get specific metric type for date range
yesterday = datetime.utcnow() - timedelta(days=1)
today = datetime.utcnow()
cpu_metrics = storage.get_metrics(
    metric_name="cpu_usage",
    start_time=yesterday,
    end_time=today
)
print(f"CPU metrics in last 24h: {len(cpu_metrics)}")

# Get all metrics for specific asset and metric type
vm_cpu_metrics = storage.get_metrics(
    asset_id="vm-101",
    metric_name="cpu_usage"
)
print(f"All CPU metrics for vm-101: {len(vm_cpu_metrics)}")
```

### Asset Discovery and Filtering

```python
# Get all VMs
all_vms = storage.get_assets_by_type("vm")
print(f"Total VMs: {len(all_vms)}")

# Search for database servers
db_servers = storage.get_assets_by_type("vm", hostname_search="DB")
print(f"Database servers: {[vm['hostname'] for vm in db_servers]}")

# Get all services
all_services = storage.get_assets_by_type("service")
print(f"Total services: {len(all_services)}")

# Find services by type
mysql_services = [
    svc for svc in all_services 
    if svc['data'].get('service_type') == 'MySQL'
]
print(f"MySQL services: {len(mysql_services)}")
```

### Complex Asset Relationships

```python
def analyze_infrastructure():
    """Analyze infrastructure relationships and health."""
    
    # Get all hypervisors
    hypervisors = storage.get_assets_by_type("proxmox_node")
    
    for hypervisor in hypervisors:
        print(f"\nHypervisor: {hypervisor['hostname']}")
        
        # Find VMs on this hypervisor
        vms = [
            vm for vm in storage.get_assets_by_type("vm")
            if vm['data'].get('hypervisor') == hypervisor['_id']
        ]
        print(f"  VMs: {len(vms)}")
        
        # Analyze each VM and its services
        for vm in vms:
            vm_hierarchy = storage.get_assets_with_services(vm['_id'])
            services = vm_hierarchy['services']
            inconsistencies = vm_hierarchy['inconsistencies']
            
            print(f"    VM {vm['hostname']}: {len(services)} services")
            
            if inconsistencies:
                print(f"      WARNING: {len(inconsistencies)} relationship issues")
                for issue in inconsistencies:
                    print(f"        - {issue['description']}")
            
            # Check service health
            unhealthy_services = [
                svc for svc in services 
                if svc['data'].get('status') != 'running'
            ]
            if unhealthy_services:
                print(f"      ALERT: {len(unhealthy_services)} unhealthy services")

analyze_infrastructure()
```

## Error Handling

### Comprehensive Error Handling

```python
from storage_layer.exceptions import (
    ConnectionError, ValidationError, OperationError, 
    RetryExhaustedError, ConfigurationError
)

def robust_metric_insertion(metrics: list):
    """Insert metrics with comprehensive error handling."""
    
    try:
        # Attempt to insert metrics
        inserted_count = storage.save_metrics_batch(metrics)
        print(f"Successfully inserted {inserted_count} metrics")
        return inserted_count
        
    except ValidationError as e:
        print(f"Validation failed: {e.message}")
        print(f"Field: {e.context.get('field_name', 'unknown')}")
        print(f"Value: {e.context.get('field_value', 'unknown')}")
        print(f"Rule: {e.context.get('validation_rule', 'unknown')}")
        
        # Handle specific validation errors
        if 'metric_name' in e.context.get('field_name', ''):
            print("Tip: Metric names must start with a letter and contain only alphanumeric characters and underscores")
        
        return 0
        
    except ConnectionError as e:
        print(f"Connection error: {e.message}")
        print(f"Database: {e.context.get('database_name', 'unknown')}")
        
        # Attempt to reconnect
        try:
            print("Attempting to reconnect...")
            storage.disconnect()
            storage.connect()
            print("Reconnection successful, retrying operation...")
            return storage.save_metrics_batch(metrics)
        except Exception as reconnect_error:
            print(f"Reconnection failed: {reconnect_error}")
            return 0
            
    except RetryExhaustedError as e:
        print(f"Operation failed after {e.context['attempts']} attempts")
        print(f"Last error: {e.original_error}")
        
        # Log for investigation
        print("This may indicate a persistent issue that requires investigation")
        return 0
        
    except OperationError as e:
        print(f"Database operation failed: {e.message}")
        print(f"Operation: {e.context.get('operation', 'unknown')}")
        
        # Check if it's a specific MongoDB error
        if e.original_error:
            print(f"MongoDB error: {e.original_error}")
        
        return 0
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 0

# Test error handling
test_metrics = [
    MetricDocument(datetime.utcnow(), "vm-101", "cpu_usage", 75.5),
    # This will cause a validation error:
    # MetricDocument(datetime.utcnow(), "", "cpu_usage", 75.5),  # Empty asset_id
]

result = robust_metric_insertion(test_metrics)
```

### Connection Health Monitoring

```python
def monitor_connection_health():
    """Monitor and report connection health."""
    
    while True:
        try:
            status = storage.get_connection_status()
            
            if status["connected"]:
                print(f"✓ Connected - Ping: {status['last_ping']:.3f}s")
                
                # Check if ping time is concerning
                if status['last_ping'] > 1.0:
                    print("⚠ High latency detected")
                    
            else:
                print(f"✗ Disconnected - Error: {status['error']}")
                
                # Attempt reconnection
                try:
                    storage.disconnect()
                    storage.connect()
                    print("✓ Reconnection successful")
                except Exception as e:
                    print(f"✗ Reconnection failed: {e}")
            
            time.sleep(30)  # Check every 30 seconds
            
        except KeyboardInterrupt:
            print("Monitoring stopped")
            break
        except Exception as e:
            print(f"Health check error: {e}")
            time.sleep(30)

# Run health monitoring (uncomment to use)
# monitor_connection_health()
```

## Performance Optimization

### Efficient Batch Processing

```python
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def benchmark_batch_sizes():
    """Benchmark different batch sizes for optimal performance."""
    
    # Generate test data
    test_metrics = generate_realistic_metrics("benchmark-vm", hours=1)
    batch_sizes = [100, 500, 1000, 2000, 5000]
    
    results = {}
    
    for batch_size in batch_sizes:
        print(f"\nTesting batch size: {batch_size}")
        
        # Clear existing data
        storage.purge_collections()
        
        start_time = time.time()
        total_inserted = 0
        
        for i in range(0, len(test_metrics), batch_size):
            batch = test_metrics[i:i + batch_size]
            inserted = storage.save_metrics_batch(batch)
            total_inserted += inserted
        
        duration = time.time() - start_time
        rate = total_inserted / duration
        
        results[batch_size] = {
            'duration': duration,
            'rate': rate,
            'total': total_inserted
        }
        
        print(f"  Duration: {duration:.2f}s")
        print(f"  Rate: {rate:.0f} metrics/second")
    
    # Find optimal batch size
    optimal_size = max(results.keys(), key=lambda k: results[k]['rate'])
    print(f"\nOptimal batch size: {optimal_size} ({results[optimal_size]['rate']:.0f} metrics/sec)")
    
    return results

# Run benchmark (uncomment to use)
# benchmark_results = benchmark_batch_sizes()
```

### Parallel Processing

```python
def parallel_metric_insertion(asset_ids: list, hours_per_asset: int = 24):
    """Insert metrics for multiple assets in parallel."""
    
    def insert_asset_metrics(asset_id: str) -> dict:
        """Insert metrics for a single asset."""
        try:
            metrics = generate_realistic_metrics(asset_id, hours_per_asset)
            inserted = storage.save_metrics_batch(metrics)
            return {
                'asset_id': asset_id,
                'inserted': inserted,
                'success': True,
                'error': None
            }
        except Exception as e:
            return {
                'asset_id': asset_id,
                'inserted': 0,
                'success': False,
                'error': str(e)
            }
    
    # Process assets in parallel
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all tasks
        future_to_asset = {
            executor.submit(insert_asset_metrics, asset_id): asset_id 
            for asset_id in asset_ids
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_asset):
            result = future.result()
            results.append(result)
            
            if result['success']:
                print(f"✓ {result['asset_id']}: {result['inserted']} metrics")
            else:
                print(f"✗ {result['asset_id']}: {result['error']}")
    
    # Summary
    total_inserted = sum(r['inserted'] for r in results)
    successful = sum(1 for r in results if r['success'])
    
    print(f"\nSummary:")
    print(f"  Assets processed: {len(asset_ids)}")
    print(f"  Successful: {successful}")
    print(f"  Total metrics: {total_inserted}")
    
    return results

# Process multiple assets in parallel
asset_list = [f"vm-{i:03d}" for i in range(1, 11)]  # vm-001 to vm-010
parallel_results = parallel_metric_insertion(asset_list, hours_per_asset=1)
```

## Maintenance Operations

### Automated Cleanup

```python
from datetime import datetime, timedelta

def automated_maintenance():
    """Perform automated maintenance tasks."""
    
    print("Starting automated maintenance...")
    
    # 1. Clean up old metrics (older than 90 days)
    cutoff_date = datetime.utcnow() - timedelta(days=90)
    deleted_metrics = storage.cleanup_old_metrics(cutoff_date)
    print(f"Cleaned up {deleted_metrics} old metrics")
    
    # 2. Optimize indexes
    print("Optimizing indexes...")
    optimization_results = storage.optimize_indexes()
    
    total_duration = optimization_results['performance_metrics']['total_duration']
    indexes_rebuilt = len(optimization_results['indexes_rebuilt'])
    
    print(f"Rebuilt {indexes_rebuilt} indexes in {total_duration:.2f}s")
    
    # 3. Check connection health
    status = storage.get_connection_status()
    if status['connected']:
        print(f"Connection healthy - ping: {status['last_ping']:.3f}s")
    else:
        print(f"Connection issue: {status['error']}")
    
    # 4. Generate maintenance report
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'metrics_cleaned': deleted_metrics,
        'indexes_optimized': indexes_rebuilt,
        'optimization_duration': total_duration,
        'connection_healthy': status['connected']
    }
    
    print("Maintenance completed successfully")
    return report

# Run maintenance
maintenance_report = automated_maintenance()
```

### Data Archival

```python
def archive_old_data(archive_days: int = 365):
    """Archive data older than specified days."""
    
    cutoff_date = datetime.utcnow() - timedelta(days=archive_days)
    
    print(f"Archiving data older than {cutoff_date.isoformat()}")
    
    # Get old metrics for archival
    old_metrics = storage.get_metrics(
        end_time=cutoff_date
    )
    
    if not old_metrics:
        print("No old data to archive")
        return
    
    print(f"Found {len(old_metrics)} metrics to archive")
    
    # In a real scenario, you would export to external storage
    # For this example, we'll just count and delete
    
    # Export to file (example)
    import json
    archive_filename = f"metrics_archive_{cutoff_date.strftime('%Y%m%d')}.json"
    
    with open(archive_filename, 'w') as f:
        # Convert datetime objects to strings for JSON serialization
        serializable_metrics = []
        for metric in old_metrics:
            metric_copy = metric.copy()
            metric_copy['timestamp'] = metric_copy['timestamp'].isoformat()
            serializable_metrics.append(metric_copy)
        
        json.dump(serializable_metrics, f, indent=2)
    
    print(f"Archived {len(old_metrics)} metrics to {archive_filename}")
    
    # Clean up old data
    deleted_count = storage.cleanup_old_metrics(cutoff_date)
    print(f"Deleted {deleted_count} archived metrics from database")
    
    return {
        'archived_count': len(old_metrics),
        'deleted_count': deleted_count,
        'archive_file': archive_filename
    }

# Archive data older than 1 year
# archive_result = archive_old_data(365)
```

## Real-World Scenarios

### Infrastructure Monitoring Dashboard

```python
def get_infrastructure_overview():
    """Get comprehensive infrastructure overview for dashboard."""
    
    overview = {
        'timestamp': datetime.utcnow().isoformat(),
        'assets': {},
        'metrics_summary': {},
        'alerts': []
    }
    
    # Get asset counts by type
    asset_types = ["proxmox_node", "vm", "container", "physical_host", "service"]
    for asset_type in asset_types:
        assets = storage.get_assets_by_type(asset_type)
        overview['assets'][asset_type] = {
            'total': len(assets),
            'running': len([a for a in assets if a['data'].get('status') == 'running']),
            'stopped': len([a for a in assets if a['data'].get('status') == 'stopped']),
            'degraded': len([a for a in assets if a['data'].get('status') == 'degraded'])
        }
    
    # Get recent metrics summary
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_metrics = storage.get_metrics(start_time=one_hour_ago)
    
    # Group metrics by type
    metric_types = {}
    for metric in recent_metrics:
        metric_name = metric['meta']['metric_name']
        if metric_name not in metric_types:
            metric_types[metric_name] = []
        metric_types[metric_name].append(metric['value'])
    
    # Calculate statistics
    for metric_name, values in metric_types.items():
        overview['metrics_summary'][metric_name] = {
            'count': len(values),
            'avg': sum(values) / len(values),
            'min': min(values),
            'max': max(values)
        }
    
    # Check for alerts (high CPU usage)
    if 'cpu_usage' in metric_types:
        high_cpu_metrics = [m for m in recent_metrics 
                           if m['meta']['metric_name'] == 'cpu_usage' and m['value'] > 90]
        
        for metric in high_cpu_metrics:
            overview['alerts'].append({
                'type': 'high_cpu',
                'asset_id': metric['meta']['asset_id'],
                'value': metric['value'],
                'timestamp': metric['timestamp'].isoformat()
            })
    
    return overview

# Get dashboard data
dashboard_data = get_infrastructure_overview()
print(f"Infrastructure Overview:")
print(f"  VMs: {dashboard_data['assets']['vm']['total']} total, {dashboard_data['assets']['vm']['running']} running")
print(f"  Services: {dashboard_data['assets']['service']['total']} total")
print(f"  Alerts: {len(dashboard_data['alerts'])}")
```

### Capacity Planning

```python
def analyze_capacity_trends(days: int = 30):
    """Analyze capacity trends for planning."""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get all VMs
    vms = storage.get_assets_by_type("vm")
    
    capacity_analysis = {
        'analysis_period_days': days,
        'vm_analysis': {},
        'recommendations': []
    }
    
    for vm in vms:
        vm_id = vm['_id']
        vm_hostname = vm.get('hostname', vm_id)
        
        # Get CPU and memory metrics for this VM
        cpu_metrics = storage.get_metrics(
            asset_id=vm_id,
            metric_name="cpu_usage",
            start_time=start_date
        )
        
        memory_metrics = storage.get_metrics(
            asset_id=vm_id,
            metric_name="memory_usage",
            start_time=start_date
        )
        
        if not cpu_metrics and not memory_metrics:
            continue
        
        # Calculate statistics
        cpu_values = [m['value'] for m in cpu_metrics]
        memory_values = [m['value'] for m in memory_metrics]
        
        vm_analysis = {
            'hostname': vm_hostname,
            'cpu_stats': {
                'avg': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                'max': max(cpu_values) if cpu_values else 0,
                'p95': sorted(cpu_values)[int(len(cpu_values) * 0.95)] if cpu_values else 0
            },
            'memory_stats': {
                'avg': sum(memory_values) / len(memory_values) if memory_values else 0,
                'max': max(memory_values) if memory_values else 0,
                'p95': sorted(memory_values)[int(len(memory_values) * 0.95)] if memory_values else 0
            }
        }
        
        capacity_analysis['vm_analysis'][vm_id] = vm_analysis
        
        # Generate recommendations
        if vm_analysis['cpu_stats']['p95'] > 80:
            capacity_analysis['recommendations'].append({
                'vm': vm_hostname,
                'type': 'cpu_upgrade',
                'current_p95': vm_analysis['cpu_stats']['p95'],
                'recommendation': 'Consider increasing CPU allocation'
            })
        
        if vm_analysis['memory_stats']['p95'] > 85:
            capacity_analysis['recommendations'].append({
                'vm': vm_hostname,
                'type': 'memory_upgrade',
                'current_p95': vm_analysis['memory_stats']['p95'],
                'recommendation': 'Consider increasing memory allocation'
            })
    
    return capacity_analysis

# Run capacity analysis
capacity_report = analyze_capacity_trends(30)
print(f"Capacity Analysis ({capacity_report['analysis_period_days']} days):")
print(f"  VMs analyzed: {len(capacity_report['vm_analysis'])}")
print(f"  Recommendations: {len(capacity_report['recommendations'])}")

for rec in capacity_report['recommendations']:
    print(f"    {rec['vm']}: {rec['recommendation']} (current: {rec['current_p95']:.1f}%)")
```

### Automated Alerting

```python
def check_and_alert():
    """Check for alert conditions and generate notifications."""
    
    alerts = []
    current_time = datetime.utcnow()
    
    # Check for high resource usage in last 15 minutes
    check_time = current_time - timedelta(minutes=15)
    recent_metrics = storage.get_metrics(start_time=check_time)
    
    # Group metrics by asset
    asset_metrics = {}
    for metric in recent_metrics:
        asset_id = metric['meta']['asset_id']
        metric_name = metric['meta']['metric_name']
        
        if asset_id not in asset_metrics:
            asset_metrics[asset_id] = {}
        if metric_name not in asset_metrics[asset_id]:
            asset_metrics[asset_id][metric_name] = []
        
        asset_metrics[asset_id][metric_name].append(metric['value'])
    
    # Check alert conditions
    for asset_id, metrics in asset_metrics.items():
        # Get asset info
        asset = storage.get_asset(asset_id)
        if not asset:
            continue
        
        asset_name = asset.get('hostname', asset_id)
        
        # High CPU alert
        if 'cpu_usage' in metrics:
            avg_cpu = sum(metrics['cpu_usage']) / len(metrics['cpu_usage'])
            if avg_cpu > 90:
                alerts.append({
                    'type': 'high_cpu',
                    'severity': 'critical',
                    'asset_id': asset_id,
                    'asset_name': asset_name,
                    'value': avg_cpu,
                    'threshold': 90,
                    'message': f'High CPU usage on {asset_name}: {avg_cpu:.1f}%'
                })
        
        # High memory alert
        if 'memory_usage' in metrics:
            avg_memory = sum(metrics['memory_usage']) / len(metrics['memory_usage'])
            if avg_memory > 95:
                alerts.append({
                    'type': 'high_memory',
                    'severity': 'critical',
                    'asset_id': asset_id,
                    'asset_name': asset_name,
                    'value': avg_memory,
                    'threshold': 95,
                    'message': f'High memory usage on {asset_name}: {avg_memory:.1f}%'
                })
        
        # High I/O wait alert
        if 'disk_io_wait' in metrics:
            avg_io_wait = sum(metrics['disk_io_wait']) / len(metrics['disk_io_wait'])
            if avg_io_wait > 10:
                alerts.append({
                    'type': 'high_io_wait',
                    'severity': 'warning',
                    'asset_id': asset_id,
                    'asset_name': asset_name,
                    'value': avg_io_wait,
                    'threshold': 10,
                    'message': f'High I/O wait on {asset_name}: {avg_io_wait:.1f}%'
                })
    
    # Check for down services
    services = storage.get_assets_by_type("service")
    for service in services:
        if service['data'].get('status') != 'running':
            parent_id = service['data'].get('parent_asset_id')
            parent_asset = storage.get_asset(parent_id) if parent_id else None
            parent_name = parent_asset.get('hostname', parent_id) if parent_asset else 'unknown'
            
            alerts.append({
                'type': 'service_down',
                'severity': 'critical',
                'asset_id': service['_id'],
                'asset_name': service.get('service_name', service['_id']),
                'parent_asset': parent_name,
                'status': service['data'].get('status', 'unknown'),
                'message': f'Service {service.get("service_name")} is {service["data"].get("status")} on {parent_name}'
            })
    
    return alerts

# Check for alerts
current_alerts = check_and_alert()
print(f"Current alerts: {len(current_alerts)}")

for alert in current_alerts:
    severity_icon = "🔴" if alert['severity'] == 'critical' else "🟡"
    print(f"{severity_icon} {alert['message']}")
```

This comprehensive examples file demonstrates real-world usage patterns and advanced scenarios for the Infrastructure Monitoring Storage Layer.