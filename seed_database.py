#!/usr/bin/env python3
"""
SeedDatabase Script for Infrastructure Monitoring Storage Layer

This script generates realistic infrastructure data for testing and development purposes.
It creates 10 machines with their associated services and generates 14 days of minute-by-minute
performance metrics with realistic patterns and variations.

Usage:
    python seed_database.py [options]

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7
"""

import argparse
import logging
import random
import sys
import time
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any, Tuple
import math

from storage_layer.storage_manager import StorageManager
from storage_layer.models import AssetDocument, MetricDocument, create_asset_document, create_metric_document
from storage_layer.exceptions import StorageManagerError


# Infrastructure Asset Definitions (Requirements: 5.2, 5.3)
INFRASTRUCTURE_ASSETS = [
    {
        "asset_id": "pve-node-01",
        "asset_type": "proxmox_node",
        "hostname": "PVE-HOST-01",
        "performance_pattern": "stable_with_io_spikes",
        "data": {
            "status": "running",
            "cpu_cores": 32,
            "memory_gb": 128,
            "storage_gb": 2000,
            "hypervisor_version": "7.4-3",
            "cluster_name": "production"
        },
        "services": [
            {
                "service_id": "svc-pveproxy-01",
                "service_name": "Proxmox Web Interface",
                "service_type": "web_service",
                "port": 8006,
                "downtime_schedule": None
            }
        ]
    },
    {
        "asset_id": "vm-101",
        "asset_type": "vm",
        "hostname": "DB-SERVER-PROD",
        "performance_pattern": "cpu_spikes_business_hours",
        "data": {
            "status": "running",
            "cpu_cores": 8,
            "memory_gb": 32,
            "storage_gb": 500,
            "hypervisor": "pve-node-01",
            "os": "Ubuntu 22.04 LTS"
        },
        "services": [
            {
                "service_id": "svc-mysql-101",
                "service_name": "MySQL Database",
                "service_type": "database",
                "port": 3306,
                "downtime_schedule": None
            },
            {
                "service_id": "svc-reporting-101",
                "service_name": "Reporting Service",
                "service_type": "application",
                "port": 8080,
                "downtime_schedule": {"start_hour": 23, "end_hour": 1}  # 23:00-01:00 daily
            }
        ]
    },
    {
        "asset_id": "vm-102",
        "asset_type": "vm", 
        "hostname": "WEB-SERVER-01",
        "performance_pattern": "high_load_business_hours",
        "data": {
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 16,
            "storage_gb": 200,
            "hypervisor": "pve-node-01",
            "os": "Ubuntu 22.04 LTS"
        },
        "services": [
            {
                "service_id": "svc-nginx-102",
                "service_name": "Nginx Web Server",
                "service_type": "web_server",
                "port": 80,
                "downtime_schedule": None
            },
            {
                "service_id": "svc-php-fpm-102",
                "service_name": "PHP-FPM",
                "service_type": "application",
                "port": 9000,
                "downtime_schedule": None
            }
        ]
    },
    {
        "asset_id": "vm-103",
        "asset_type": "vm",
        "hostname": "APP-SERVER-JAVA",
        "performance_pattern": "memory_leak_pattern",
        "data": {
            "status": "running",
            "cpu_cores": 6,
            "memory_gb": 24,
            "storage_gb": 300,
            "hypervisor": "pve-node-01",
            "os": "Ubuntu 22.04 LTS"
        },
        "services": [
            {
                "service_id": "svc-tomcat-103",
                "service_name": "Apache Tomcat",
                "service_type": "application_server",
                "port": 8080,
                "downtime_schedule": None,
                "degradation_pattern": "memory_pressure"  # Gradual degradation due to memory issues
            },
            {
                "service_id": "svc-elasticsearch-103",
                "service_name": "Elasticsearch",
                "service_type": "search_engine",
                "port": 9200,
                "downtime_schedule": None
            }
        ]
    },
    {
        "asset_id": "ct-201",
        "asset_type": "container",
        "hostname": "CACHE-SERVER-01",
        "performance_pattern": "volatile_load",
        "data": {
            "status": "running",
            "cpu_cores": 2,
            "memory_gb": 8,
            "storage_gb": 50,
            "hypervisor": "pve-node-01",
            "container_type": "LXC",
            "os": "Ubuntu 22.04 LTS"
        },
        "services": [
            {
                "service_id": "svc-redis-201",
                "service_name": "Redis Cache",
                "service_type": "cache",
                "port": 6379,
                "downtime_schedule": None
            }
        ]
    },
    {
        "asset_id": "ct-202",
        "asset_type": "container",
        "hostname": "MONITORING-01",
        "performance_pattern": "stable_low_load",
        "data": {
            "status": "running",
            "cpu_cores": 2,
            "memory_gb": 4,
            "storage_gb": 100,
            "hypervisor": "pve-node-01",
            "container_type": "LXC",
            "os": "Ubuntu 22.04 LTS"
        },
        "services": [
            {
                "service_id": "svc-prometheus-202",
                "service_name": "Prometheus",
                "service_type": "monitoring",
                "port": 9090,
                "downtime_schedule": None
            },
            {
                "service_id": "svc-grafana-202",
                "service_name": "Grafana",
                "service_type": "visualization",
                "port": 3000,
                "downtime_schedule": None
            }
        ]
    },
    {
        "asset_id": "physical-01",
        "asset_type": "physical_host",
        "hostname": "BACKUP-SERVER-01",
        "performance_pattern": "io_wait_nights",
        "data": {
            "status": "running",
            "cpu_cores": 16,
            "memory_gb": 64,
            "storage_gb": 10000,
            "manufacturer": "Dell",
            "model": "PowerEdge R740",
            "location": "Datacenter Rack A1"
        },
        "services": [
            {
                "service_id": "svc-bacula-physical-01",
                "service_name": "Bacula Backup",
                "service_type": "backup",
                "port": 9101,
                "downtime_schedule": None
            }
        ]
    },
    {
        "asset_id": "physical-02",
        "asset_type": "physical_host",
        "hostname": "NAS-SERVER-01",
        "performance_pattern": "stable_with_io_spikes",
        "data": {
            "status": "running",
            "cpu_cores": 8,
            "memory_gb": 32,
            "storage_gb": 50000,
            "manufacturer": "Synology",
            "model": "DS1821+",
            "location": "Datacenter Rack B2"
        },
        "services": [
            {
                "service_id": "svc-nfs-physical-02",
                "service_name": "NFS Server",
                "service_type": "file_server",
                "port": 2049,
                "downtime_schedule": None
            },
            {
                "service_id": "svc-smb-physical-02",
                "service_name": "SMB/CIFS Server",
                "service_type": "file_server",
                "port": 445,
                "downtime_schedule": None
            }
        ]
    },
    {
        "asset_id": "vm-104",
        "asset_type": "vm",
        "hostname": "DEV-SERVER-01",
        "performance_pattern": "development_pattern",
        "data": {
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 16,
            "storage_gb": 250,
            "hypervisor": "pve-node-01",
            "os": "Ubuntu 22.04 LTS"
        },
        "services": [
            {
                "service_id": "svc-jenkins-104",
                "service_name": "Jenkins CI/CD",
                "service_type": "ci_cd",
                "port": 8080,
                "downtime_schedule": None
            },
            {
                "service_id": "svc-gitlab-runner-104",
                "service_name": "GitLab Runner",
                "service_type": "ci_cd",
                "port": 8093,
                "downtime_schedule": None
            }
        ]
    },
    {
        "asset_id": "vm-105",
        "asset_type": "vm",
        "hostname": "MAIL-SERVER-01",
        "performance_pattern": "email_server_pattern",
        "data": {
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 12,
            "storage_gb": 500,
            "hypervisor": "pve-node-01",
            "os": "Ubuntu 22.04 LTS"
        },
        "services": [
            {
                "service_id": "svc-postfix-105",
                "service_name": "Postfix SMTP",
                "service_type": "mail_server",
                "port": 25,
                "downtime_schedule": None
            },
            {
                "service_id": "svc-dovecot-105",
                "service_name": "Dovecot IMAP",
                "service_type": "mail_server",
                "port": 993,
                "downtime_schedule": None
            }
        ]
    }
]

# Acronis backup job definitions
BACKUP_JOBS = [
    {
        "asset_id": "backup-job-001",
        "asset_type": "acronis_backup_job",
        "data": {
            "job_name": "Daily VM Backup",
            "status": "running",
            "schedule": "daily_2am",
            "target_assets": ["vm-101", "vm-102", "vm-103"],
            "backup_type": "incremental",
            "retention_days": 30,
            "last_run": "2024-02-08T02:00:00Z",
            "next_run": "2024-02-09T02:00:00Z"
        }
    },
    {
        "asset_id": "backup-job-002", 
        "asset_type": "acronis_backup_job",
        "data": {
            "job_name": "Weekly Full Backup",
            "status": "running",
            "schedule": "weekly_sunday_1am",
            "target_assets": ["vm-101", "vm-102", "vm-103", "vm-104", "vm-105"],
            "backup_type": "full",
            "retention_days": 90,
            "last_run": "2024-02-04T01:00:00Z",
            "next_run": "2024-02-11T01:00:00Z"
        }
    }
]


def create_infrastructure_assets() -> List[AssetDocument]:
    """
    Create infrastructure asset definitions with proper data structures.
    
    Returns:
        List of AssetDocument instances for all infrastructure assets
        
    Requirements: 5.2, 5.3
    """
    assets = []
    
    # Create machine assets
    for asset_def in INFRASTRUCTURE_ASSETS:
        asset = create_asset_document(
            asset_id=asset_def["asset_id"],
            asset_type=asset_def["asset_type"],
            hostname=asset_def["hostname"],
            data=asset_def["data"]
        )
        assets.append(asset)
    
    # Create backup job assets
    for backup_def in BACKUP_JOBS:
        asset = create_asset_document(
            asset_id=backup_def["asset_id"],
            asset_type=backup_def["asset_type"],
            data=backup_def["data"]
        )
        assets.append(asset)
    
    return assets


def create_service_assets() -> List[AssetDocument]:
    """
    Create service asset definitions with parent_asset_id relationships.
    
    Returns:
        List of AssetDocument instances for all services
        
    Requirements: 5.2, 5.3
    """
    services = []
    
    for asset_def in INFRASTRUCTURE_ASSETS:
        parent_asset_id = asset_def["asset_id"]
        
        for service_def in asset_def.get("services", []):
            service_data = {
                "parent_asset_id": parent_asset_id,
                "status": "running",
                "service_type": service_def["service_type"],
                "port": service_def["port"]
            }
            
            # Add optional fields
            if "downtime_schedule" in service_def and service_def["downtime_schedule"]:
                service_data["downtime_schedule"] = service_def["downtime_schedule"]
            
            if "degradation_pattern" in service_def:
                service_data["degradation_pattern"] = service_def["degradation_pattern"]
            
            service = create_asset_document(
                asset_id=service_def["service_id"],
                asset_type="service",
                service_name=service_def["service_name"],
                data=service_data
            )
            services.append(service)
    
    return services


def get_asset_performance_pattern(asset_id: str) -> str:
    """
    Get the performance pattern for a specific asset.
    
    Args:
        asset_id: The asset ID to look up
        
    Returns:
        Performance pattern name
    """
    for asset_def in INFRASTRUCTURE_ASSETS:
        if asset_def["asset_id"] == asset_id:
            return asset_def["performance_pattern"]
    
    return "stable_low_load"  # Default pattern


class MetricPatternGenerator:
    """
    Generates realistic performance metrics based on different patterns.
    
    This class implements various performance patterns that simulate real-world
    infrastructure behavior including CPU spikes, memory leaks, I/O wait patterns,
    and realistic noise variations.
    
    Requirements: 5.5
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the pattern generator with optional random seed.
        
        Args:
            seed: Random seed for reproducible results (optional)
        """
        if seed is not None:
            random.seed(seed)
        
        # Pattern-specific state tracking
        self._memory_leak_state = {}  # Track memory growth per asset
        self._volatile_state = {}     # Track volatile pattern state
        
    def generate_cpu_pattern(self, pattern: str, timestamp: datetime, asset_id: str) -> float:
        """
        Generate CPU usage percentage based on the specified pattern.
        
        Args:
            pattern: Performance pattern name
            timestamp: Current timestamp
            asset_id: Asset identifier for state tracking
            
        Returns:
            CPU usage percentage (0-100)
            
        Requirements: 5.5
        """
        hour = timestamp.hour
        minute = timestamp.minute
        day_of_week = timestamp.weekday()  # 0=Monday, 6=Sunday
        
        base_cpu = 0.0
        
        if pattern == "stable_with_io_spikes":
            # Stable CPU with occasional spikes during I/O operations
            base_cpu = 15.0
            if hour == 3 and 0 <= minute <= 30:  # I/O spike at 3 AM
                base_cpu = 45.0
            elif hour in [9, 13, 17] and minute < 15:  # Brief spikes during business hours
                base_cpu = 35.0
                
        elif pattern == "cpu_spikes_business_hours":
            # High CPU during business hours (9-17)
            if 9 <= hour <= 17 and day_of_week < 5:  # Weekdays business hours
                base_cpu = 65.0 + 20.0 * math.sin((hour - 9) * math.pi / 8)  # Sine wave pattern
                if minute % 15 == 0:  # Spike every 15 minutes
                    base_cpu = min(95.0, base_cpu + 25.0)
            else:
                base_cpu = 20.0
                
        elif pattern == "high_load_business_hours":
            # Consistently high load during business hours
            if 9 <= hour <= 17 and day_of_week < 5:
                base_cpu = 75.0 + 15.0 * math.sin((hour - 9) * math.pi / 8)
            elif 18 <= hour <= 22:  # Evening load
                base_cpu = 45.0
            else:
                base_cpu = 25.0
                
        elif pattern == "memory_leak_pattern":
            # CPU increases as memory pressure builds
            days_since_epoch = (timestamp - datetime(2024, 1, 26, tzinfo=UTC)).days
            memory_pressure = min(1.0, (days_since_epoch % 7) / 7.0)  # Weekly cycle
            base_cpu = 30.0 + 40.0 * memory_pressure
            
        elif pattern == "volatile_load":
            # Highly variable load with random spikes
            base_cpu = 25.0
            # Create pseudo-random spikes based on timestamp
            spike_factor = hash(f"{asset_id}_{timestamp.hour}_{timestamp.minute // 5}") % 100
            if spike_factor < 15:  # 15% chance of spike
                base_cpu = 80.0 + (spike_factor % 20)
                
        elif pattern == "stable_low_load":
            # Consistently low CPU usage
            base_cpu = 8.0 + 5.0 * math.sin(hour * math.pi / 12)  # Gentle daily cycle
            
        elif pattern == "io_wait_nights":
            # High CPU during night backup operations
            if 22 <= hour or hour <= 6:
                base_cpu = 55.0 + 20.0 * math.sin((hour % 24) * math.pi / 8)
            else:
                base_cpu = 15.0
                
        elif pattern == "development_pattern":
            # Sporadic usage during development hours
            if 9 <= hour <= 18 and day_of_week < 5:
                # Random activity during dev hours
                activity_factor = hash(f"{asset_id}_{timestamp.hour}_{timestamp.minute // 10}") % 100
                if activity_factor < 30:  # 30% chance of activity
                    base_cpu = 40.0 + (activity_factor % 40)
                else:
                    base_cpu = 10.0
            else:
                base_cpu = 5.0
                
        elif pattern == "email_server_pattern":
            # Higher load during email processing times
            if hour in [8, 9, 13, 17, 18]:  # Peak email times
                base_cpu = 35.0 + 15.0 * math.sin(minute * math.pi / 30)
            else:
                base_cpu = 12.0
        else:
            # Default stable pattern
            base_cpu = 20.0
        
        # Add realistic noise
        return self.add_realistic_noise(base_cpu, 0.15)
    
    def generate_memory_pattern(self, pattern: str, timestamp: datetime, asset_id: str) -> float:
        """
        Generate memory usage percentage based on the specified pattern.
        
        Args:
            pattern: Performance pattern name
            timestamp: Current timestamp
            asset_id: Asset identifier for state tracking
            
        Returns:
            Memory usage percentage (0-100)
            
        Requirements: 5.5
        """
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        
        # Initialize memory leak state if needed
        if asset_id not in self._memory_leak_state:
            self._memory_leak_state[asset_id] = {
                'base_memory': 30.0,
                'leak_start': timestamp,
                'last_reset': timestamp
            }
        
        state = self._memory_leak_state[asset_id]
        base_memory = 0.0
        
        if pattern == "stable_with_io_spikes":
            base_memory = 35.0
            if hour == 3:  # Memory usage during I/O operations
                base_memory = 55.0
                
        elif pattern == "cpu_spikes_business_hours":
            # Memory correlates with CPU load
            if 9 <= hour <= 17 and day_of_week < 5:
                base_memory = 60.0 + 15.0 * math.sin((hour - 9) * math.pi / 8)
            else:
                base_memory = 40.0
                
        elif pattern == "high_load_business_hours":
            if 9 <= hour <= 17 and day_of_week < 5:
                base_memory = 70.0
            else:
                base_memory = 45.0
                
        elif pattern == "memory_leak_pattern":
            # Gradual memory increase with weekly resets
            days_since_reset = (timestamp - state['last_reset']).days
            hours_since_reset = (timestamp - state['last_reset']).total_seconds() / 3600
            
            # Reset memory weekly (every 7 days)
            if days_since_reset >= 7:
                state['base_memory'] = 30.0
                state['last_reset'] = timestamp
                hours_since_reset = 0
            
            # Gradual memory leak: 0.5% per hour
            leak_amount = min(50.0, hours_since_reset * 0.5)
            base_memory = state['base_memory'] + leak_amount
            
        elif pattern == "volatile_load":
            # Variable memory usage
            base_memory = 40.0
            volatility_factor = hash(f"{asset_id}_mem_{timestamp.hour}_{timestamp.minute // 10}") % 100
            if volatility_factor < 20:
                base_memory = 70.0 + (volatility_factor % 25)
                
        elif pattern == "stable_low_load":
            base_memory = 25.0
            
        elif pattern == "io_wait_nights":
            if 22 <= hour or hour <= 6:
                base_memory = 65.0  # High memory during backup operations
            else:
                base_memory = 35.0
                
        elif pattern == "development_pattern":
            if 9 <= hour <= 18 and day_of_week < 5:
                # Variable memory during development
                dev_factor = hash(f"{asset_id}_mem_{timestamp.hour}_{timestamp.minute // 15}") % 100
                if dev_factor < 25:
                    base_memory = 55.0 + (dev_factor % 30)
                else:
                    base_memory = 30.0
            else:
                base_memory = 20.0
                
        elif pattern == "email_server_pattern":
            if hour in [8, 9, 13, 17, 18]:
                base_memory = 50.0
            else:
                base_memory = 35.0
        else:
            base_memory = 40.0
        
        return self.add_realistic_noise(base_memory, 0.10)
    
    def generate_io_pattern(self, pattern: str, timestamp: datetime, asset_id: str) -> float:
        """
        Generate I/O wait percentage based on the specified pattern.
        
        Args:
            pattern: Performance pattern name
            timestamp: Current timestamp
            asset_id: Asset identifier for state tracking
            
        Returns:
            I/O wait percentage (0-100)
            
        Requirements: 5.5
        """
        hour = timestamp.hour
        minute = timestamp.minute
        day_of_week = timestamp.weekday()
        
        base_io = 0.0
        
        if pattern == "stable_with_io_spikes":
            base_io = 5.0
            if hour == 3 and 0 <= minute <= 30:  # Major I/O spike at 3 AM
                base_io = 45.0 + 20.0 * math.sin(minute * math.pi / 30)
            elif hour in [1, 5, 23]:  # Minor I/O operations
                base_io = 15.0
                
        elif pattern == "cpu_spikes_business_hours":
            # Moderate I/O during business hours
            if 9 <= hour <= 17 and day_of_week < 5:
                base_io = 12.0 + 8.0 * math.sin((hour - 9) * math.pi / 8)
            else:
                base_io = 6.0
                
        elif pattern == "high_load_business_hours":
            if 9 <= hour <= 17 and day_of_week < 5:
                base_io = 18.0
            else:
                base_io = 8.0
                
        elif pattern == "memory_leak_pattern":
            # I/O increases with memory pressure (swapping)
            days_since_epoch = (timestamp - datetime(2024, 1, 26, tzinfo=UTC)).days
            memory_pressure = min(1.0, (days_since_epoch % 7) / 7.0)
            base_io = 8.0 + 25.0 * memory_pressure
            
        elif pattern == "volatile_load":
            base_io = 10.0
            io_spike = hash(f"{asset_id}_io_{timestamp.hour}_{timestamp.minute // 3}") % 100
            if io_spike < 10:  # 10% chance of I/O spike
                base_io = 35.0 + (io_spike % 30)
                
        elif pattern == "stable_low_load":
            base_io = 3.0
            
        elif pattern == "io_wait_nights":
            # High I/O during night hours (backup operations)
            if 22 <= hour or hour <= 6:
                base_io = 35.0 + 25.0 * math.sin((hour % 24) * math.pi / 8)
                if hour in [2, 3, 4]:  # Peak backup hours
                    base_io = max(base_io, 50.0)
            else:
                base_io = 5.0
                
        elif pattern == "development_pattern":
            if 9 <= hour <= 18 and day_of_week < 5:
                # Occasional I/O spikes during builds/deployments
                build_factor = hash(f"{asset_id}_io_{timestamp.hour}_{timestamp.minute // 20}") % 100
                if build_factor < 15:  # 15% chance of build I/O
                    base_io = 25.0 + (build_factor % 20)
                else:
                    base_io = 4.0
            else:
                base_io = 2.0
                
        elif pattern == "email_server_pattern":
            if hour in [8, 9, 13, 17, 18]:
                base_io = 15.0  # I/O for email processing
            else:
                base_io = 6.0
        else:
            base_io = 8.0
        
        return self.add_realistic_noise(base_io, 0.20)
    
    def add_realistic_noise(self, base_value: float, noise_factor: float) -> float:
        """
        Add realistic noise and variation to metric values.
        
        Args:
            base_value: Base metric value
            noise_factor: Noise factor (0.0-1.0, typically 0.1-0.3)
            
        Returns:
            Value with added noise, clamped to valid range (0-100)
            
        Requirements: 5.5
        """
        # Generate noise using normal distribution
        noise = random.gauss(0, noise_factor * base_value)
        
        # Add some occasional larger spikes (1% chance)
        if random.random() < 0.01:
            spike_direction = 1 if random.random() < 0.7 else -1  # 70% positive spikes
            spike_magnitude = random.uniform(0.2, 0.5) * base_value
            noise += spike_direction * spike_magnitude
        
        # Apply noise and clamp to valid range
        result = base_value + noise
        return max(0.0, min(100.0, result))
    
    def generate_metric_value(self, metric_name: str, pattern: str, 
                            timestamp: datetime, asset_id: str) -> float:
        """
        Generate a metric value based on metric type and pattern.
        
        Args:
            metric_name: Name of the metric (cpu_usage, memory_usage, io_wait)
            pattern: Performance pattern name
            timestamp: Current timestamp
            asset_id: Asset identifier
            
        Returns:
            Generated metric value
            
        Requirements: 5.5
        """
        if metric_name == "cpu_usage":
            return self.generate_cpu_pattern(pattern, timestamp, asset_id)
        elif metric_name == "memory_usage":
            return self.generate_memory_pattern(pattern, timestamp, asset_id)
        elif metric_name == "io_wait":
            return self.generate_io_pattern(pattern, timestamp, asset_id)
        else:
            # Default pattern for unknown metrics
            return self.add_realistic_noise(50.0, 0.15)


def generate_time_series_data(storage_manager: StorageManager, 
                            pattern_generator: MetricPatternGenerator,
                            days: int = 14,
                            batch_size: int = 1000,
                            progress_tracker: Optional[Dict[str, Any]] = None) -> int:
    """
    Generate minute-by-minute time-series data for all machines.
    
    Creates CPU, memory, and I/O metrics for each machine based on their
    specific performance patterns. Uses efficient batch insertion for
    large datasets with enhanced progress tracking and resumable execution.
    
    Args:
        storage_manager: StorageManager instance for database operations
        pattern_generator: MetricPatternGenerator for realistic patterns
        days: Number of days of data to generate (default: 14)
        batch_size: Number of metrics to insert per batch (default: 1000)
        progress_tracker: Progress tracking dictionary for resumable execution
        
    Returns:
        Total number of metrics inserted
        
    Requirements: 5.4, 5.5, 5.7
    """
    logger = logging.getLogger(__name__)
    
    # Calculate time range
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=days)
    
    # Get all machine assets (exclude services and backup jobs)
    machine_assets = [asset for asset in INFRASTRUCTURE_ASSETS]
    
    # Metric types to generate
    metric_types = ["cpu_usage", "memory_usage", "io_wait"]
    
    # Calculate total metrics to generate
    minutes_per_day = 24 * 60
    total_minutes = days * minutes_per_day
    total_metrics = len(machine_assets) * len(metric_types) * total_minutes
    
    logger.info(f"Generating {total_metrics:,} metrics for {len(machine_assets)} machines over {days} days")
    logger.info(f"Time range: {start_time.isoformat()} to {end_time.isoformat()}")
    logger.info(f"Batch size: {batch_size:,} metrics per batch")
    
    metrics_batch = []
    total_inserted = 0
    processed_count = 0
    last_progress_log = time.time()
    last_checkpoint_save = time.time()
    
    # Resume from checkpoint if available
    resume_time = start_time
    if progress_tracker and progress_tracker.get("current_date"):
        resume_time = progress_tracker["current_date"]
        logger.info(f"Resuming metrics generation from {resume_time.isoformat()}")
    
    # Generate metrics minute by minute
    current_time = resume_time
    while current_time < end_time:
        for asset_def in machine_assets:
            asset_id = asset_def["asset_id"]
            pattern = asset_def["performance_pattern"]
            
            for metric_name in metric_types:
                # Generate metric value
                value = pattern_generator.generate_metric_value(
                    metric_name, pattern, current_time, asset_id
                )
                
                # Create metric document
                metric = create_metric_document(
                    timestamp=current_time,
                    asset_id=asset_id,
                    metric_name=metric_name,
                    value=value
                )
                
                metrics_batch.append(metric)
                processed_count += 1
                
                # Insert batch when it reaches the specified size
                if len(metrics_batch) >= batch_size:
                    try:
                        batch_start_time = time.time()
                        inserted = storage_manager.save_metrics_batch(metrics_batch)
                        batch_duration = time.time() - batch_start_time
                        total_inserted += inserted
                        
                        # Enhanced progress logging with performance metrics
                        current_log_time = time.time()
                        progress_interval = 30  # Default, could be made configurable
                        if current_log_time - last_progress_log >= progress_interval:
                            progress_pct = (processed_count / total_metrics) * 100
                            metrics_per_second = batch_size / batch_duration if batch_duration > 0 else 0
                            eta_seconds = (total_metrics - processed_count) / metrics_per_second if metrics_per_second > 0 else 0
                            eta_str = str(timedelta(seconds=int(eta_seconds))) if eta_seconds > 0 else "Unknown"
                            
                            logger.info(f"Progress: {progress_pct:.1f}% - Inserted {inserted:,} metrics "
                                      f"(Total: {total_inserted:,}) - Rate: {metrics_per_second:.0f}/sec - ETA: {eta_str}")
                            last_progress_log = current_log_time
                        
                        metrics_batch = []
                        
                        # Update progress tracker
                        if progress_tracker:
                            progress_tracker["completed_operations"] = total_inserted
                            progress_tracker["current_date"] = current_time
                            progress_tracker["last_checkpoint"] = datetime.now(UTC)
                            
                            # Save checkpoint at configurable interval
                            checkpoint_interval = 300  # Default, could be made configurable
                            if current_log_time - last_checkpoint_save >= checkpoint_interval:
                                save_progress_checkpoint(progress_tracker)
                                last_checkpoint_save = current_log_time
                        
                    except Exception as e:
                        logger.error(f"Failed to insert metrics batch at {current_time.isoformat()}: {e}")
                        # Save progress before re-raising
                        if progress_tracker:
                            progress_tracker["current_date"] = current_time
                            save_progress_checkpoint(progress_tracker)
                        raise
        
        # Move to next minute
        current_time += timedelta(minutes=1)
        
        # Log hourly progress with detailed statistics
        if current_time.minute == 0:
            time_progress_pct = ((current_time - start_time).total_seconds() / 
                               (end_time - start_time).total_seconds()) * 100
            hours_remaining = (end_time - current_time).total_seconds() / 3600
            
            logger.info(f"Time progress: {time_progress_pct:.1f}% - Processing {current_time.isoformat()} "
                       f"- Hours remaining: {hours_remaining:.1f}")
            
            # Memory usage check (if psutil is available)
            try:
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                logger.debug(f"Memory usage: {memory_mb:.1f} MB")
            except ImportError:
                pass  # psutil not available, skip memory logging
    
    # Insert any remaining metrics in the batch
    if metrics_batch:
        try:
            batch_start_time = time.time()
            inserted = storage_manager.save_metrics_batch(metrics_batch)
            batch_duration = time.time() - batch_start_time
            total_inserted += inserted
            
            logger.info(f"Final batch: Inserted {inserted:,} metrics in {batch_duration:.2f}s")
        except Exception as e:
            logger.error(f"Failed to insert final metrics batch: {e}")
            raise
    
    # Final statistics
    generation_duration = time.time() - (progress_tracker["start_time"].timestamp() if progress_tracker else time.time())
    avg_rate = total_inserted / generation_duration if generation_duration > 0 else 0
    
    logger.info(f"Time-series data generation complete!")
    logger.info(f"Total metrics inserted: {total_inserted:,}")
    logger.info(f"Generation duration: {timedelta(seconds=int(generation_duration))}")
    logger.info(f"Average insertion rate: {avg_rate:.0f} metrics/second")
    
    return total_inserted


def generate_metrics_for_timerange(asset_id: str, pattern: str, 
                                 start_time: datetime, end_time: datetime,
                                 pattern_generator: MetricPatternGenerator) -> List[MetricDocument]:
    """
    Generate metrics for a specific asset and time range.
    
    Args:
        asset_id: Asset identifier
        pattern: Performance pattern name
        start_time: Start of time range
        end_time: End of time range
        pattern_generator: MetricPatternGenerator instance
        
    Returns:
        List of MetricDocument instances
        
    Requirements: 5.4, 5.5
    """
    metrics = []
    metric_types = ["cpu_usage", "memory_usage", "io_wait"]
    
    current_time = start_time
    while current_time < end_time:
        for metric_name in metric_types:
            value = pattern_generator.generate_metric_value(
                metric_name, pattern, current_time, asset_id
            )
            
            metric = create_metric_document(
                timestamp=current_time,
                asset_id=asset_id,
                metric_name=metric_name,
                value=value
            )
            metrics.append(metric)
        
        current_time += timedelta(minutes=1)
    
    return metrics


def generate_polling_history(storage_manager: StorageManager,
                           pattern_generator: MetricPatternGenerator,
                           days: int = 14,
                           batch_size: int = 1000,
                           progress_tracker: Optional[Dict[str, Any]] = None) -> int:
    """
    Generate polling history for availability calculations.
    
    Creates minute-by-minute polling data for all services and machines,
    simulating realistic availability patterns including scheduled downtime,
    random failures, and dependency-based outages.
    
    Args:
        storage_manager: StorageManager instance for database operations
        pattern_generator: MetricPatternGenerator for realistic patterns
        days: Number of days of polling history to generate (default: 14)
        batch_size: Number of polling records to insert per batch (default: 1000)
        progress_tracker: Progress tracking dictionary for resumable execution
        
    Returns:
        Total number of polling records inserted
        
    Requirements: 5.4, 5.5, 5.6
    """
    logger = logging.getLogger(__name__)
    
    # Calculate time range
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=days)
    
    # Get all assets that need polling (machines and services)
    all_assets = []
    
    # Add machine assets
    for asset_def in INFRASTRUCTURE_ASSETS:
        all_assets.append({
            "asset_id": asset_def["asset_id"],
            "asset_type": asset_def["asset_type"],
            "hostname": asset_def["hostname"],
            "performance_pattern": asset_def["performance_pattern"],
            "services": asset_def.get("services", [])
        })
        
        # Add service assets
        for service_def in asset_def.get("services", []):
            all_assets.append({
                "asset_id": service_def["service_id"],
                "asset_type": "service",
                "service_name": service_def["service_name"],
                "parent_asset_id": asset_def["asset_id"],
                "service_def": service_def
            })
    
    # Calculate total polling records to generate
    minutes_per_day = 24 * 60
    total_minutes = days * minutes_per_day
    total_polls = len(all_assets) * total_minutes
    
    logger.info(f"Generating {total_polls:,} polling records for {len(all_assets)} assets over {days} days")
    logger.info(f"Time range: {start_time.isoformat()} to {end_time.isoformat()}")
    logger.info(f"Batch size: {batch_size:,} records per batch")
    
    polling_batch = []
    total_inserted = 0
    processed_count = 0
    last_progress_log = time.time()
    
    # Resume from checkpoint if available
    resume_time = start_time
    if progress_tracker and progress_tracker.get("current_polling_date"):
        resume_time = progress_tracker["current_polling_date"]
        logger.info(f"Resuming polling history generation from {resume_time.isoformat()}")
    
    # Generate polling records minute by minute
    current_time = resume_time
    while current_time < end_time:
        for asset in all_assets:
            asset_id = asset["asset_id"]
            asset_type = asset["asset_type"]
            
            # Determine availability status
            if asset_type == "service":
                availability_status = determine_service_availability(
                    asset, current_time, pattern_generator
                )
            else:
                availability_status = determine_machine_availability(
                    asset, current_time, pattern_generator
                )
            
            # Create polling record as a metric
            polling_metric = create_metric_document(
                timestamp=current_time,
                asset_id=asset_id,
                metric_name="availability_status",
                value=availability_status
            )
            
            # Also create response time metric (simulated)
            response_time = generate_response_time(asset, current_time, availability_status)
            response_metric = create_metric_document(
                timestamp=current_time,
                asset_id=asset_id,
                metric_name="response_time_ms",
                value=response_time
            )
            
            polling_batch.extend([polling_metric, response_metric])
            processed_count += 2
            
            # Insert batch when it reaches the specified size
            if len(polling_batch) >= batch_size:
                try:
                    batch_start_time = time.time()
                    inserted = storage_manager.save_metrics_batch(polling_batch)
                    batch_duration = time.time() - batch_start_time
                    total_inserted += inserted
                    
                    # Progress logging
                    current_log_time = time.time()
                    if current_log_time - last_progress_log >= 30:  # Every 30 seconds
                        progress_pct = (processed_count / (total_polls * 2)) * 100  # *2 for both metrics
                        records_per_second = batch_size / batch_duration if batch_duration > 0 else 0
                        
                        logger.info(f"Polling Progress: {progress_pct:.1f}% - Inserted {inserted:,} records "
                                  f"(Total: {total_inserted:,}) - Rate: {records_per_second:.0f}/sec")
                        last_progress_log = current_log_time
                    
                    polling_batch = []
                    
                    # Update progress tracker
                    if progress_tracker:
                        progress_tracker["completed_polling_operations"] = total_inserted
                        progress_tracker["current_polling_date"] = current_time
                        
                except Exception as e:
                    logger.error(f"Failed to insert polling batch at {current_time.isoformat()}: {e}")
                    if progress_tracker:
                        progress_tracker["current_polling_date"] = current_time
                    raise
        
        # Move to next minute
        current_time += timedelta(minutes=1)
        
        # Log hourly progress
        if current_time.minute == 0:
            time_progress_pct = ((current_time - start_time).total_seconds() / 
                               (end_time - start_time).total_seconds()) * 100
            logger.info(f"Polling Time progress: {time_progress_pct:.1f}% - Processing {current_time.isoformat()}")
    
    # Insert any remaining records in the batch
    if polling_batch:
        try:
            inserted = storage_manager.save_metrics_batch(polling_batch)
            total_inserted += inserted
            logger.info(f"Final polling batch: Inserted {inserted:,} records")
        except Exception as e:
            logger.error(f"Failed to insert final polling batch: {e}")
            raise
    
    logger.info(f"Polling history generation complete!")
    logger.info(f"Total polling records inserted: {total_inserted:,}")
    
    return total_inserted


def determine_service_availability(asset: Dict[str, Any], timestamp: datetime, 
                                 pattern_generator: MetricPatternGenerator) -> float:
    """
    Determine service availability status based on various factors.
    
    Args:
        asset: Service asset definition
        timestamp: Current timestamp
        pattern_generator: Pattern generator for realistic variations
        
    Returns:
        Availability status: 100.0 (up), 0.0 (down), 50.0 (degraded)
    """
    service_def = asset.get("service_def", {})
    hour = timestamp.hour
    
    # Check for scheduled downtime
    downtime_schedule = service_def.get("downtime_schedule")
    if downtime_schedule:
        start_hour = downtime_schedule["start_hour"]
        end_hour = downtime_schedule["end_hour"]
        
        # Handle downtime that crosses midnight
        if start_hour > end_hour:  # e.g., 23:00-01:00
            if hour >= start_hour or hour <= end_hour:
                return 0.0  # Service down for maintenance
        else:  # Normal downtime window
            if start_hour <= hour <= end_hour:
                return 0.0  # Service down for maintenance
    
    # Check for degradation patterns
    degradation_pattern = service_def.get("degradation_pattern")
    if degradation_pattern == "memory_pressure":
        # Simulate gradual degradation due to memory issues
        days_since_epoch = (timestamp - datetime(2024, 1, 26, tzinfo=UTC)).days
        memory_pressure_cycle = days_since_epoch % 7  # Weekly cycle
        
        if memory_pressure_cycle >= 5:  # Days 5-6 of the week
            degradation_chance = (memory_pressure_cycle - 4) * 0.4  # 40% on day 5, 80% on day 6
            if random.random() < degradation_chance:
                return 50.0  # Service degraded
    
    # Simulate random service failures (99.5% uptime target)
    service_reliability = 0.995
    random_factor = hash(f"{asset['asset_id']}_{timestamp.hour}_{timestamp.minute}") % 10000 / 10000.0
    
    if random_factor > service_reliability:
        # Determine if it's a complete failure or degradation
        if random_factor > service_reliability + 0.003:  # 0.3% complete failure
            return 0.0  # Service completely down
        else:
            return 50.0  # Service degraded
    
    # Service is running normally
    return 100.0


def determine_machine_availability(asset: Dict[str, Any], timestamp: datetime,
                                 pattern_generator: MetricPatternGenerator) -> float:
    """
    Determine machine availability status based on performance patterns.
    
    Args:
        asset: Machine asset definition
        timestamp: Current timestamp
        pattern_generator: Pattern generator for realistic variations
        
    Returns:
        Availability status: 100.0 (up), 0.0 (down), 50.0 (degraded)
    """
    pattern = asset.get("performance_pattern", "stable_low_load")
    
    # Machines are generally more reliable than services (99.9% uptime)
    machine_reliability = 0.999
    random_factor = hash(f"{asset['asset_id']}_{timestamp.hour}_{timestamp.minute}") % 10000 / 10000.0
    
    if random_factor > machine_reliability:
        # Determine if it's a complete failure or degradation
        if random_factor > machine_reliability + 0.0005:  # 0.05% complete failure
            return 0.0  # Machine completely down
        else:
            return 50.0  # Machine degraded (high load, hardware issues, etc.)
    
    # Check for pattern-specific degradation
    if pattern == "memory_leak_pattern":
        # Higher chance of degradation during memory pressure
        days_since_epoch = (timestamp - datetime(2024, 1, 26, tzinfo=UTC)).days
        memory_pressure = min(1.0, (days_since_epoch % 7) / 7.0)
        
        if memory_pressure > 0.8 and random.random() < 0.02:  # 2% chance during high memory pressure
            return 50.0
    
    elif pattern == "volatile_load":
        # Occasional degradation due to load spikes
        spike_factor = hash(f"{asset['asset_id']}_load_{timestamp.hour}_{timestamp.minute // 5}") % 100
        if spike_factor < 3:  # 3% chance of load-related degradation
            return 50.0
    
    # Machine is running normally
    return 100.0


def generate_response_time(asset: Dict[str, Any], timestamp: datetime, 
                         availability_status: float) -> float:
    """
    Generate realistic response time based on availability status and asset type.
    
    Args:
        asset: Asset definition
        timestamp: Current timestamp
        availability_status: Current availability status
        
    Returns:
        Response time in milliseconds
    """
    asset_type = asset["asset_type"]
    
    # Base response times by asset type
    base_response_times = {
        "service": 50.0,  # Services typically respond faster
        "vm": 100.0,
        "container": 30.0,
        "physical_host": 150.0,
        "proxmox_node": 200.0
    }
    
    base_time = base_response_times.get(asset_type, 100.0)
    
    # Adjust based on availability status
    if availability_status == 0.0:
        # Service/machine is down - timeout
        return 30000.0  # 30 second timeout
    elif availability_status == 50.0:
        # Service/machine is degraded - slower response
        base_time *= random.uniform(3.0, 8.0)
    else:
        # Normal operation - add realistic variation
        base_time *= random.uniform(0.5, 2.0)
    
    # Add time-of-day variation (higher load during business hours)
    hour = timestamp.hour
    if 9 <= hour <= 17:  # Business hours
        base_time *= random.uniform(1.2, 2.5)
    elif 22 <= hour or hour <= 6:  # Night hours (backup operations)
        base_time *= random.uniform(1.1, 1.8)
    
    # Add random spikes (network issues, etc.)
    if random.random() < 0.05:  # 5% chance of spike
        base_time *= random.uniform(2.0, 10.0)
    
    return max(1.0, base_time)  # Minimum 1ms response time


def generate_backup_history(storage_manager: StorageManager,
                          days: int = 14,
                          batch_size: int = 1000,
                          progress_tracker: Optional[Dict[str, Any]] = None) -> int:
    """
    Generate simple backup history for all machines.
    
    Creates daily backup records with only timestamp and success/failure status.
    No RPO targets or other metadata - just the essential backup data.
    
    Args:
        storage_manager: StorageManager instance for database operations
        days: Number of days of backup history to generate (default: 14)
        batch_size: Number of backup records to insert per batch (default: 1000)
        progress_tracker: Progress tracking dictionary for resumable execution
        
    Returns:
        Total number of backup records inserted
    """
    logger = logging.getLogger(__name__)
    
    # Calculate time range
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=days)
    
    # Get all machine assets that need backup (exclude services)
    machine_assets = []
    for asset_def in INFRASTRUCTURE_ASSETS:
        if asset_def["asset_type"] in ["vm", "container", "physical_host", "proxmox_node"]:
            machine_assets.append(asset_def)
    
    # Define backup success rates by asset type (realistic patterns)
    success_rates = {
        "vm": 0.95,         # VMs: 95% success rate
        "container": 0.92,  # Containers: 92% success rate (slightly lower)
        "physical_host": 0.97, # Physical hosts: 97% success rate (more reliable)
        "proxmox_node": 0.98   # Proxmox nodes: 98% success rate (most reliable)
    }
    
    total_backups = len(machine_assets) * days
    logger.info(f"Generating {total_backups:,} backup records for {len(machine_assets)} machines over {days} days")
    logger.info(f"Time range: {start_time.isoformat()} to {end_time.isoformat()}")
    
    backup_batch = []
    total_inserted = 0
    processed_count = 0
    last_progress_log = time.time()
    
    # Resume from checkpoint if available
    resume_date = start_time.date()
    if progress_tracker and progress_tracker.get("current_backup_date"):
        resume_date = progress_tracker["current_backup_date"].date()
        logger.info(f"Resuming backup history generation from {resume_date}")
    
    # Generate backup records day by day
    current_date = resume_date
    end_date = end_time.date()
    
    while current_date <= end_date:
        for asset_def in machine_assets:
            asset_id = asset_def["asset_id"]
            asset_type = asset_def["asset_type"]
            
            # Determine backup time (typically at night)
            backup_hour = random.choice([1, 2, 3, 4])  # Between 1-4 AM
            backup_minute = random.randint(0, 59)
            backup_time = datetime.combine(current_date, datetime.min.time()).replace(
                hour=backup_hour, minute=backup_minute, tzinfo=UTC
            )
            
            # Skip future backups
            if backup_time > end_time:
                continue
            
            # Determine backup success based on asset type and patterns
            success_rate = success_rates.get(asset_type, 0.95)
            
            # Add some realistic failure patterns
            is_success = determine_backup_success(asset_def, backup_time, success_rate)
            
            # Create backup record as a metric
            backup_status_metric = create_metric_document(
                timestamp=backup_time,
                asset_id=asset_id,
                metric_name="backup_status",
                value=1.0 if is_success else 0.0
            )
            
            backup_batch.append(backup_status_metric)
            processed_count += 1
            
            # Insert batch when it reaches the specified size
            if len(backup_batch) >= batch_size:
                try:
                    batch_start_time = time.time()
                    inserted = storage_manager.save_metrics_batch(backup_batch)
                    batch_duration = time.time() - batch_start_time
                    total_inserted += inserted
                    
                    # Progress logging
                    current_log_time = time.time()
                    if current_log_time - last_progress_log >= 30:  # Every 30 seconds
                        progress_pct = (processed_count / total_backups) * 100
                        records_per_second = batch_size / batch_duration if batch_duration > 0 else 0
                        
                        logger.info(f"Backup Progress: {progress_pct:.1f}% - Inserted {inserted:,} records "
                                  f"(Total: {total_inserted:,}) - Rate: {records_per_second:.0f}/sec")
                        last_progress_log = current_log_time
                    
                    backup_batch = []
                    
                    # Update progress tracker
                    if progress_tracker:
                        progress_tracker["completed_backup_operations"] = total_inserted
                        progress_tracker["current_backup_date"] = datetime.combine(current_date, datetime.min.time()).replace(tzinfo=UTC)
                        
                except Exception as e:
                    logger.error(f"Failed to insert backup batch for {current_date}: {e}")
                    if progress_tracker:
                        progress_tracker["current_backup_date"] = datetime.combine(current_date, datetime.min.time()).replace(tzinfo=UTC)
                    raise
        
        # Move to next day
        current_date += timedelta(days=1)
        
        # Log daily progress
        if current_date.day % 7 == 0:  # Every week
            days_progress = (current_date - start_time.date()).days
            total_days = (end_date - start_time.date()).days
            time_progress_pct = (days_progress / total_days) * 100 if total_days > 0 else 100
            logger.info(f"Backup Time progress: {time_progress_pct:.1f}% - Processing {current_date}")
    
    # Insert any remaining records in the batch
    if backup_batch:
        try:
            inserted = storage_manager.save_metrics_batch(backup_batch)
            total_inserted += inserted
            logger.info(f"Final backup batch: Inserted {inserted:,} records")
        except Exception as e:
            logger.error(f"Failed to insert final backup batch: {e}")
            raise
    
    logger.info(f"Backup history generation complete!")
    logger.info(f"Total backup records inserted: {total_inserted:,}")
    
    return total_inserted


def determine_backup_success(asset_def: Dict[str, Any], backup_time: datetime, base_success_rate: float) -> bool:
    """
    Simple backup success determination based on asset type success rates.
    
    Args:
        asset_def: Asset definition
        backup_time: When the backup is scheduled
        base_success_rate: Base success rate for this asset type
        
    Returns:
        True if backup succeeds, False otherwise
    """
    # Simple random determination based on success rate
    return random.random() < base_success_rate





def simulate_service_states(storage_manager: StorageManager, 
                          start_time: datetime, end_time: datetime) -> int:
    """
    Simulate realistic service state changes and downtime scenarios.
    
    Implements scheduled downtime, service degradation scenarios, and
    dependency handling where services inherit host machine state.
    
    Args:
        storage_manager: StorageManager instance for database operations
        start_time: Start time for simulation
        end_time: End time for simulation
        
    Returns:
        Number of service state updates performed
        
    Requirements: 5.6
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting service state simulation")
    
    updates_count = 0
    
    # Process each day in the time range
    current_date = start_time.date()
    end_date = end_time.date()
    
    while current_date <= end_date:
        current_datetime = datetime.combine(current_date, datetime.min.time()).replace(tzinfo=UTC)
        
        # Process each asset and its services
        for asset_def in INFRASTRUCTURE_ASSETS:
            asset_id = asset_def["asset_id"]
            
            # Get current host status (assume running unless simulating failure)
            host_status = "running"
            
            # Simulate occasional host issues (1% chance per day)
            if random.random() < 0.01:
                host_status = "degraded"
                logger.info(f"Simulating host degradation for {asset_id} on {current_date}")
            
            # Process services for this asset
            for service_def in asset_def.get("services", []):
                service_id = service_def["service_id"]
                service_name = service_def["service_name"]
                
                # Determine service status based on various factors
                service_status = determine_service_status(
                    service_def, current_datetime, host_status, asset_id
                )
                
                # Update service asset with new status
                try:
                    service_data = {
                        "parent_asset_id": asset_id,
                        "status": service_status,
                        "service_type": service_def["service_type"],
                        "port": service_def["port"],
                        "last_status_change": current_datetime.isoformat()
                    }
                    
                    # Add degradation info if applicable
                    if service_status == "degraded" and "degradation_pattern" in service_def:
                        service_data["degradation_reason"] = service_def["degradation_pattern"]
                    
                    # Add downtime schedule if applicable
                    if "downtime_schedule" in service_def and service_def["downtime_schedule"]:
                        service_data["downtime_schedule"] = service_def["downtime_schedule"]
                    
                    service_asset = create_asset_document(
                        asset_id=service_id,
                        asset_type="service",
                        service_name=service_name,
                        data=service_data
                    )
                    
                    storage_manager.upsert_asset(service_asset)
                    updates_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to update service {service_id}: {e}")
        
        current_date += timedelta(days=1)
    
    logger.info(f"Service state simulation complete. Total updates: {updates_count}")
    return updates_count


def determine_service_status(service_def: Dict[str, Any], current_time: datetime, 
                           host_status: str, asset_id: str) -> str:
    """
    Determine service status based on schedules, patterns, and host status.
    
    Args:
        service_def: Service definition dictionary
        current_time: Current timestamp
        host_status: Status of the host machine
        asset_id: Asset ID for logging
        
    Returns:
        Service status: "running", "stopped", "degraded", or "unknown"
        
    Requirements: 5.6
    """
    logger = logging.getLogger(__name__)
    
    # If host is not running, services inherit the host status
    if host_status != "running":
        logger.debug(f"Service {service_def['service_id']} inheriting host status: {host_status}")
        return host_status
    
    # Check for scheduled downtime
    downtime_schedule = service_def.get("downtime_schedule")
    if downtime_schedule:
        current_hour = current_time.hour
        start_hour = downtime_schedule["start_hour"]
        end_hour = downtime_schedule["end_hour"]
        
        # Handle downtime that crosses midnight
        if start_hour > end_hour:  # e.g., 23:00-01:00
            if current_hour >= start_hour or current_hour <= end_hour:
                logger.debug(f"Service {service_def['service_id']} in scheduled downtime")
                return "stopped"
        else:  # Normal downtime window
            if start_hour <= current_hour <= end_hour:
                logger.debug(f"Service {service_def['service_id']} in scheduled downtime")
                return "stopped"
    
    # Check for degradation patterns
    degradation_pattern = service_def.get("degradation_pattern")
    if degradation_pattern == "memory_pressure":
        # Simulate gradual degradation due to memory issues
        days_since_epoch = (current_time - datetime(2024, 1, 26, tzinfo=UTC)).days
        memory_pressure_cycle = days_since_epoch % 7  # Weekly cycle
        
        if memory_pressure_cycle >= 5:  # Days 5-6 of the week
            # Simulate degradation during high memory pressure
            degradation_chance = (memory_pressure_cycle - 4) * 0.3  # 30% on day 5, 60% on day 6
            if random.random() < degradation_chance:
                logger.debug(f"Service {service_def['service_id']} degraded due to memory pressure")
                return "degraded"
    
    # Simulate random service issues (very low probability)
    service_reliability = 0.999  # 99.9% uptime
    if random.random() > service_reliability:
        issue_type = random.choice(["stopped", "degraded"])
        logger.debug(f"Service {service_def['service_id']} experiencing random issue: {issue_type}")
        return issue_type
    
    # Default to running
    return "running"


def create_service_state_history(storage_manager: StorageManager,
                                start_time: datetime, end_time: datetime) -> int:
    """
    Create historical service state data with realistic state changes.
    
    This function generates service state history that includes:
    - Scheduled maintenance windows
    - Random service failures and recoveries
    - Dependency-based state changes
    
    Args:
        storage_manager: StorageManager instance
        start_time: Start time for history generation
        end_time: End time for history generation
        
    Returns:
        Number of state change records created
        
    Requirements: 5.6
    """
    logger = logging.getLogger(__name__)
    logger.info("Creating service state history")
    
    state_changes = 0
    
    # Generate state changes at various intervals
    current_time = start_time
    
    while current_time < end_time:
        # Check every 4 hours for potential state changes
        for asset_def in INFRASTRUCTURE_ASSETS:
            for service_def in asset_def.get("services", []):
                service_id = service_def["service_id"]
                
                # Determine if a state change should occur
                if should_generate_state_change(service_def, current_time):
                    new_status = determine_service_status(
                        service_def, current_time, "running", asset_def["asset_id"]
                    )
                    
                    # Create state change record (could be stored as metrics or events)
                    state_metric = create_metric_document(
                        timestamp=current_time,
                        asset_id=service_id,
                        metric_name="service_status",
                        value=status_to_numeric(new_status)
                    )
                    
                    try:
                        storage_manager.save_metrics_batch([state_metric])
                        state_changes += 1
                    except Exception as e:
                        logger.error(f"Failed to save service state change for {service_id}: {e}")
        
        current_time += timedelta(hours=4)
    
    logger.info(f"Service state history creation complete. State changes: {state_changes}")
    return state_changes


def should_generate_state_change(service_def: Dict[str, Any], timestamp: datetime) -> bool:
    """
    Determine if a service state change should be generated at this time.
    
    Args:
        service_def: Service definition
        timestamp: Current timestamp
        
    Returns:
        True if a state change should be generated
    """
    # Always generate state changes during scheduled downtime transitions
    downtime_schedule = service_def.get("downtime_schedule")
    if downtime_schedule:
        hour = timestamp.hour
        start_hour = downtime_schedule["start_hour"]
        end_hour = downtime_schedule["end_hour"]
        
        # Generate state change at downtime start/end
        if hour == start_hour or hour == end_hour:
            return True
    
    # Generate occasional random state changes (low probability)
    return random.random() < 0.05  # 5% chance every 4 hours


def status_to_numeric(status: str) -> float:
    """
    Convert service status to numeric value for metric storage.
    
    Args:
        status: Service status string
        
    Returns:
        Numeric representation (0-100)
    """
    status_map = {
        "running": 100.0,
        "degraded": 50.0,
        "stopped": 0.0,
        "unknown": 25.0
    }
    return status_map.get(status, 25.0)


def setup_logging(log_level: str = "INFO", log_file: str = "storage_layer/logs/seed_database.log", 
                 quiet: bool = False) -> logging.Logger:
    """
    Set up enhanced logging configuration for the seed script.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file
        quiet: If True, suppress console output
        
    Returns:
        Configured logger instance
        
    Requirements: 5.7
    """
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # File handler with detailed formatting
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Always log everything to file
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Console handler (unless quiet mode)
    if not quiet:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)
    
    # Log startup information
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("SeedDatabase Script Starting")
    logger.info(f"Log level: {log_level}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Quiet mode: {quiet}")
    logger.info("=" * 80)
    
    return logger


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments for the seed database script.
    
    Returns:
        Parsed arguments namespace
        
    Requirements: 5.7
    """
    parser = argparse.ArgumentParser(
        description="Seed database with realistic infrastructure monitoring data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python seed_database.py --connection mongodb://localhost:27017 --database test_monitoring
  python seed_database.py --days 7 --batch-size 500 --log-level DEBUG
  python seed_database.py --skip-cleanup --resume
        """
    )
    
    # Database connection options
    parser.add_argument(
        "--connection", "-c",
        default="mongodb://localhost:27017",
        help="MongoDB connection string (default: mongodb://localhost:27017)"
    )
    
    parser.add_argument(
        "--database", "-d",
        default="infrastructure_monitoring",
        help="Database name (default: infrastructure_monitoring)"
    )
    
    # Data generation options
    parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="Number of days of data to generate (default: 14)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for metric insertion (default: 1000)"
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible results (optional)"
    )
    
    # Execution control options
    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Skip database cleanup at start (default: False)"
    )
    
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous execution (default: False)"
    )
    
    parser.add_argument(
        "--assets-only",
        action="store_true",
        help="Only create assets, skip metrics generation (default: False)"
    )
    
    parser.add_argument(
        "--metrics-only",
        action="store_true",
        help="Only generate metrics, skip asset creation (default: False)"
    )
    
    parser.add_argument(
        "--polling-only",
        action="store_true",
        help="Only generate polling history, skip other operations (default: False)"
    )
    
    parser.add_argument(
        "--backup-only",
        action="store_true",
        help="Only generate backup history, skip other operations (default: False)"
    )
    
    # Logging options
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress console output (log to file only)"
    )
    
    parser.add_argument(
        "--log-file",
        default="storage_layer/logs/seed_database.log",
        help="Log file path (default: storage_layer/logs/seed_database.log)"
    )
    
    parser.add_argument(
        "--checkpoint-file",
        default="seed_progress.json",
        help="Checkpoint file path for resumable execution (default: seed_progress.json)"
    )
    
    parser.add_argument(
        "--progress-interval",
        type=int,
        default=30,
        help="Progress logging interval in seconds (default: 30)"
    )
    
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=300,
        help="Checkpoint save interval in seconds (default: 300)"
    )
    
    return parser.parse_args()


def create_progress_tracker(total_operations: int) -> Dict[str, Any]:
    """
    Create a progress tracking state for resumable execution.
    
    Args:
        total_operations: Total number of operations to track
        
    Returns:
        Progress tracking dictionary
        
    Requirements: 5.7
    """
    return {
        "total_operations": total_operations,
        "completed_operations": 0,
        "start_time": datetime.now(UTC),
        "last_checkpoint": datetime.now(UTC),
        "phase": "initialization",
        "current_asset": None,
        "current_date": None,
        "system_info": get_system_info()
    }


def get_system_info() -> Dict[str, Any]:
    """
    Collect system information for logging and debugging.
    
    Returns:
        Dictionary with system information
        
    Requirements: 5.7
    """
    import platform
    import sys
    
    info = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "hostname": platform.node()
    }
    
    # Add memory info if psutil is available
    try:
        import psutil
        memory = psutil.virtual_memory()
        info["total_memory_gb"] = round(memory.total / (1024**3), 2)
        info["available_memory_gb"] = round(memory.available / (1024**3), 2)
        info["cpu_count"] = psutil.cpu_count()
    except ImportError:
        info["memory_info"] = "psutil not available"
    
    return info


def log_execution_summary(logger: logging.Logger, progress: Dict[str, Any], 
                         total_inserted: int, args: argparse.Namespace) -> None:
    """
    Log comprehensive execution summary with statistics.
    
    Args:
        logger: Logger instance
        progress: Progress tracking dictionary
        total_inserted: Total number of records inserted
        args: Command line arguments
        
    Requirements: 5.7
    """
    execution_time = datetime.now(UTC) - progress['start_time']
    
    logger.info("=" * 80)
    logger.info("EXECUTION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total execution time: {execution_time}")
    logger.info(f"Total records inserted: {total_inserted:,}")
    logger.info(f"Average insertion rate: {total_inserted / execution_time.total_seconds():.0f} records/second")
    logger.info(f"Database: {args.database}")
    logger.info(f"Connection: {args.connection}")
    logger.info(f"Days of data: {args.days}")
    logger.info(f"Batch size: {args.batch_size}")
    
    if "system_info" in progress:
        logger.info("System Information:")
        for key, value in progress["system_info"].items():
            logger.info(f"  {key}: {value}")
    
    logger.info("=" * 80)


def save_progress_checkpoint(progress: Dict[str, Any], checkpoint_file: str = "seed_progress.json") -> None:
    """
    Save progress checkpoint to file for resumable execution with enhanced error handling.
    
    Args:
        progress: Progress tracking dictionary
        checkpoint_file: Path to checkpoint file
        
    Requirements: 5.7
    """
    import json
    import os
    import tempfile
    
    logger = logging.getLogger(__name__)
    
    # Convert datetime objects to ISO strings for JSON serialization
    checkpoint_data = progress.copy()
    for key, value in checkpoint_data.items():
        if isinstance(value, datetime):
            checkpoint_data[key] = value.isoformat()
    
    # Add metadata
    checkpoint_data["checkpoint_version"] = "1.0"
    checkpoint_data["saved_at"] = datetime.now(UTC).isoformat()
    
    try:
        # Write to temporary file first, then rename (atomic operation)
        temp_file = checkpoint_file + ".tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
        
        # Atomic rename
        if os.name == 'nt':  # Windows
            if os.path.exists(checkpoint_file):
                os.remove(checkpoint_file)
        os.rename(temp_file, checkpoint_file)
        
        logger.debug(f"Checkpoint saved to {checkpoint_file}")
        
    except Exception as e:
        logger.warning(f"Failed to save checkpoint to {checkpoint_file}: {e}")
        # Clean up temp file if it exists
        temp_file = checkpoint_file + ".tmp"
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass


def load_progress_checkpoint(checkpoint_file: str = "seed_progress.json") -> Optional[Dict[str, Any]]:
    """
    Load progress checkpoint from file for resumable execution with validation.
    
    Args:
        checkpoint_file: Path to checkpoint file
        
    Returns:
        Progress tracking dictionary or None if not found/invalid
        
    Requirements: 5.7
    """
    import json
    import os
    
    logger = logging.getLogger(__name__)
    
    if not os.path.exists(checkpoint_file):
        logger.debug(f"No checkpoint file found at {checkpoint_file}")
        return None
    
    try:
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)
        
        # Validate checkpoint structure
        required_fields = ["total_operations", "completed_operations", "start_time", "phase"]
        for field in required_fields:
            if field not in checkpoint_data:
                logger.warning(f"Invalid checkpoint: missing field '{field}'")
                return None
        
        # Convert ISO strings back to datetime objects
        datetime_fields = ["start_time", "last_checkpoint", "current_date", "saved_at"]
        for key in datetime_fields:
            if key in checkpoint_data and isinstance(checkpoint_data[key], str):
                try:
                    checkpoint_data[key] = datetime.fromisoformat(checkpoint_data[key].replace('Z', '+00:00'))
                except ValueError:
                    try:
                        checkpoint_data[key] = datetime.fromisoformat(checkpoint_data[key])
                    except ValueError:
                        logger.warning(f"Invalid datetime format in checkpoint for field '{key}'")
                        checkpoint_data[key] = datetime.now(UTC)
        
        logger.info(f"Loaded checkpoint from {checkpoint_file}")
        logger.info(f"Checkpoint phase: {checkpoint_data['phase']}")
        logger.info(f"Progress: {checkpoint_data['completed_operations']}/{checkpoint_data['total_operations']}")
        
        return checkpoint_data
    
    except Exception as e:
        logger.warning(f"Failed to load checkpoint from {checkpoint_file}: {e}")
        return None


def main():
    """
    Main execution function with comprehensive error handling and progress tracking.
    
    Requirements: 5.1, 5.7
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    # Set up enhanced logging
    logger = setup_logging(args.log_level, args.log_file, args.quiet)
    
    # Log execution parameters
    logger.info("Starting SeedDatabase script execution")
    logger.info(f"Parameters: days={args.days}, batch_size={args.batch_size}, "
               f"database={args.database}")
    logger.info(f"Connection: {args.connection}")
    logger.info(f"Checkpoint file: {args.checkpoint_file}")
    logger.info(f"Progress interval: {args.progress_interval}s")
    logger.info(f"Checkpoint interval: {args.checkpoint_interval}s")
    
    if args.seed:
        logger.info(f"Using random seed: {args.seed}")
        random.seed(args.seed)
    
    # Initialize progress tracking
    progress = None
    if args.resume:
        progress = load_progress_checkpoint(args.checkpoint_file)
        if progress:
            logger.info(f"Resuming from checkpoint: {progress['phase']} "
                       f"({progress['completed_operations']}/{progress['total_operations']})")
        else:
            logger.warning("No checkpoint found, starting from beginning")
    
    if not progress:
        total_ops = 0
        
        # Calculate total operations based on what will be generated
        if not args.metrics_only and not args.polling_only:
            # Asset creation operations
            total_ops += len(INFRASTRUCTURE_ASSETS) + len(BACKUP_JOBS) + sum(
                len(asset.get("services", [])) for asset in INFRASTRUCTURE_ASSETS
            )
        
        if not args.assets_only and not args.polling_only:
            # Metrics generation operations (3 metrics per asset per minute)
            total_ops += args.days * 24 * 60 * len(INFRASTRUCTURE_ASSETS) * 3
        
        if not args.assets_only and not args.metrics_only and not args.backup_only:
            # Polling history operations (2 polling records per asset per minute: availability + response_time)
            # Include both machines and services
            total_assets = len(INFRASTRUCTURE_ASSETS) + sum(
                len(asset.get("services", [])) for asset in INFRASTRUCTURE_ASSETS
            )
            total_ops += args.days * 24 * 60 * total_assets * 2
        
        if not args.assets_only and not args.metrics_only and not args.polling_only:
            # Backup history operations (1 backup record per machine per day: status only)
            machine_count = len([a for a in INFRASTRUCTURE_ASSETS if a["asset_type"] in ["vm", "container", "physical_host", "proxmox_node"]])
            total_ops += args.days * machine_count
        
        progress = create_progress_tracker(total_ops)
    
    try:
        # Initialize storage manager
        logger.info("Connecting to MongoDB")
        storage_manager = StorageManager(args.connection, args.database)
        storage_manager.connect()
        
        # Database cleanup (Requirements: 5.1)
        if not args.skip_cleanup and (not args.resume or progress["phase"] == "initialization"):
            logger.info("Cleaning up existing data")
            cleanup_result = storage_manager.purge_collections()
            logger.info(f"Cleanup complete: {cleanup_result}")
            progress["phase"] = "cleanup_complete"
            save_progress_checkpoint(progress, args.checkpoint_file)
        
        # Create assets (Requirements: 5.2, 5.3)
        if not args.metrics_only and not args.polling_only and not args.backup_only and (not args.resume or progress["phase"] in ["initialization", "cleanup_complete"]):
            logger.info("Creating infrastructure assets")
            
            # Create machine and backup job assets
            assets = create_infrastructure_assets()
            for asset in assets:
                storage_manager.upsert_asset(asset)
                progress["completed_operations"] += 1
            
            logger.info(f"Created {len(assets)} infrastructure assets")
            
            # Create service assets
            services = create_service_assets()
            for service in services:
                storage_manager.upsert_asset(service)
                progress["completed_operations"] += 1
            
            logger.info(f"Created {len(services)} service assets")
            progress["phase"] = "assets_complete"
            save_progress_checkpoint(progress, args.checkpoint_file)
        
        # Generate metrics (Requirements: 5.4, 5.5)
        if not args.assets_only and not args.polling_only and not args.backup_only and (not args.resume or progress["phase"] in ["initialization", "cleanup_complete", "assets_complete"]):
            logger.info("Generating time-series metrics")
            
            pattern_generator = MetricPatternGenerator(args.seed)
            metrics_inserted = generate_time_series_data(
                storage_manager, pattern_generator, args.days, args.batch_size, progress
            )
            
            logger.info(f"Generated {metrics_inserted:,} metrics")
            progress["phase"] = "metrics_complete"
            progress["completed_operations"] = metrics_inserted
            save_progress_checkpoint(progress, args.checkpoint_file)
        
        # Generate polling history for availability calculations (Requirements: 5.4, 5.5, 5.6)
        if not args.assets_only and not args.metrics_only and not args.backup_only and (not args.resume or progress["phase"] in ["initialization", "cleanup_complete", "assets_complete", "metrics_complete"]):
            logger.info("Generating polling history for availability calculations")
            
            if 'pattern_generator' not in locals():
                pattern_generator = MetricPatternGenerator(args.seed)
            
            polling_inserted = generate_polling_history(
                storage_manager, pattern_generator, args.days, args.batch_size, progress
            )
            
            logger.info(f"Generated {polling_inserted:,} polling records")
            progress["phase"] = "polling_complete"
            progress["completed_operations"] += polling_inserted
            save_progress_checkpoint(progress, args.checkpoint_file)
        
        # Generate backup history for RPO calculations
        if not args.assets_only and not args.metrics_only and not args.polling_only and (not args.resume or progress["phase"] in ["initialization", "cleanup_complete", "assets_complete", "metrics_complete", "polling_complete"]):
            logger.info("Generating backup history for RPO calculations")
            
            backup_inserted = generate_backup_history(
                storage_manager, args.days, args.batch_size, progress
            )
            
            logger.info(f"Generated {backup_inserted:,} backup records")
            progress["phase"] = "backup_complete"
            progress["completed_operations"] += backup_inserted
            save_progress_checkpoint(progress, args.checkpoint_file)
        
        # Simulate service states (Requirements: 5.6)
        if not args.assets_only and not args.polling_only and not args.backup_only and (not args.resume or progress["phase"] in ["initialization", "cleanup_complete", "assets_complete", "metrics_complete", "polling_complete", "backup_complete"]):
            logger.info("Simulating service states and downtime")
            
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(days=args.days)
            
            state_updates = simulate_service_states(storage_manager, start_time, end_time)
            logger.info(f"Simulated {state_updates} service state changes")
            
            progress["phase"] = "complete"
            save_progress_checkpoint(progress, args.checkpoint_file)
        
        # Final summary
        total_records = progress.get("completed_operations", 0)
        log_execution_summary(logger, progress, total_records, args)
        logger.info("SeedDatabase script execution completed successfully")
        
        # Clean up checkpoint file on successful completion
        import os
        if os.path.exists(args.checkpoint_file):
            os.remove(args.checkpoint_file)
            logger.info(f"Removed checkpoint file: {args.checkpoint_file}")
    
    except KeyboardInterrupt:
        logger.warning("Execution interrupted by user")
        if progress:
            save_progress_checkpoint(progress, args.checkpoint_file)
            logger.info(f"Progress saved to {args.checkpoint_file}. Use --resume to continue from checkpoint.")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Script execution failed: {e}", exc_info=True)
        if progress:
            save_progress_checkpoint(progress, args.checkpoint_file)
            logger.info(f"Progress saved to {args.checkpoint_file}. Use --resume to continue from checkpoint.")
        sys.exit(1)
    
    finally:
        # Clean up resources
        try:
            if 'storage_manager' in locals():
                storage_manager.disconnect()
                logger.info("Disconnected from MongoDB")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")


if __name__ == "__main__":
    main()