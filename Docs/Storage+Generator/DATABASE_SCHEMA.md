# Database Schema and Performance Guide

## Overview

This document provides comprehensive documentation for the Infrastructure Monitoring Storage database schema, indexing strategies, performance optimizations, and scaling guidelines. The system uses MongoDB 5.0+ with specialized time-series collections for optimal performance.

## Collection Structures

### 1. Metrics Collection (Time-Series)

The `metrics` collection stores high-frequency performance data using MongoDB's native time-series collection format.

#### Schema Structure

```json
{
  "_id": ObjectId("..."),
  "timestamp": ISODate("2024-01-15T10:30:00.000Z"),
  "meta": {
    "asset_id": "vm-101",
    "metric_name": "cpu_usage"
  },
  "value": 75.5
}
```

#### Field Descriptions

- **`_id`**: MongoDB ObjectId (auto-generated)
- **`timestamp`**: UTC timestamp for the metric measurement (timeField)
- **`meta`**: Metadata object containing asset and metric identifiers (metaField)
  - **`asset_id`**: Unique identifier for the monitored asset
  - **`metric_name`**: Type of metric (cpu_usage, memory_usage, io_wait, etc.)
- **`value`**: Numeric value of the metric measurement

#### Time-Series Configuration

```javascript
db.createCollection("metrics", {
  timeseries: {
    timeField: "timestamp",
    metaField: "meta",
    granularity: "minutes"
  }
})
```

**Configuration Details:**
- **timeField**: `timestamp` - MongoDB uses this for time-based partitioning
- **metaField**: `meta` - Groups related measurements together
- **granularity**: `minutes` - Optimizes for minute-level data points

### 2. Assets Collection

The `assets` collection stores infrastructure asset information and metadata.

#### Schema Structure

```json
{
  "_id": "vm-101",
  "asset_type": "vm",
  "hostname": "DB-SERVER-PROD",
  "service_name": null,
  "last_updated": ISODate("2024-01-15T10:30:00.000Z"),
  "data": {
    "status": "running",
    "cpu_cores": 4,
    "memory_gb": 16,
    "hypervisor": "pve-node-01",
    "ip_address": "192.168.1.101",
    "os": "Ubuntu 22.04 LTS"
  }
}
```

#### Field Descriptions

- **`_id`**: Custom string identifier for the asset (primary key)
- **`asset_type`**: Asset category (proxmox_node, vm, container, physical_host, acronis_backup_job, service)
- **`hostname`**: Network hostname (optional, null for services)
- **`service_name`**: Service display name (only for service type assets)
- **`last_updated`**: Timestamp of last modification
- **`data`**: Flexible object containing asset-specific metadata

#### Asset Type Variations

**Physical/Virtual Machines:**
```json
{
  "_id": "vm-101",
  "asset_type": "vm",
  "hostname": "DB-SERVER-PROD",
  "data": {
    "status": "running",
    "cpu_cores": 4,
    "memory_gb": 16,
    "hypervisor": "pve-node-01"
  }
}
```

**Services:**
```json
{
  "_id": "svc-mysql-101",
  "asset_type": "service",
  "service_name": "MySQL Database",
  "data": {
    "parent_asset_id": "vm-101",
    "status": "running",
    "service_type": "MySQL",
    "port": 3306,
    "health_check_url": "tcp://vm-101:3306"
  }
}
```

**Backup Jobs:**
```json
{
  "_id": "backup-job-001",
  "asset_type": "acronis_backup_job",
  "data": {
    "job_name": "Daily VM Backup",
    "target_assets": ["vm-101", "vm-102"],
    "schedule": "0 2 * * *",
    "status": "completed",
    "last_run": ISODate("2024-01-15T02:00:00.000Z")
  }
}
```

## Indexing Strategy

### Metrics Collection Indexes

#### 1. Asset-Time Compound Index
```javascript
db.metrics.createIndex(
  { "meta.asset_id": 1, "timestamp": 1 },
  { 
    name: "asset_time_idx",
    background: true
  }
)
```

**Purpose**: Optimizes queries filtering by specific assets over time ranges
**Query Patterns**: 
- Get all metrics for asset X between time A and B
- Latest metrics for specific asset

#### 2. Metric-Time Compound Index
```javascript
db.metrics.createIndex(
  { "meta.metric_name": 1, "timestamp": 1 },
  { 
    name: "metric_time_idx",
    background: true
  }
)
```

**Purpose**: Optimizes queries for specific metric types across all assets
**Query Patterns**:
- Get CPU usage for all assets in time range
- Compare specific metric across infrastructure

#### 3. TTL Index for Data Retention
```javascript
db.metrics.createIndex(
  { "timestamp": 1 },
  { 
    name: "ttl_idx",
    expireAfterSeconds: 7776000,  // 90 days
    background: true
  }
)
```

**Purpose**: Automatic cleanup of old metrics data
**Configuration**: Retains 90 days of data (configurable)

### Assets Collection Indexes

#### 1. Asset Type Index
```javascript
db.assets.createIndex(
  { "asset_type": 1 },
  { 
    name: "asset_type_idx",
    background: true
  }
)
```

**Purpose**: Fast filtering by asset type
**Query Patterns**: Get all VMs, all services, etc.

#### 2. Hostname Text Index
```javascript
db.assets.createIndex(
  { "hostname": "text" },
  { 
    name: "hostname_text_idx",
    background: true
  }
)
```

**Purpose**: Case-insensitive hostname search
**Query Patterns**: Find assets by partial hostname match

#### 3. Parent Asset Index (for Services)
```javascript
db.assets.createIndex(
  { "data.parent_asset_id": 1 },
  { 
    name: "parent_asset_idx",
    background: true,
    sparse: true
  }
)
```

**Purpose**: Fast lookup of services by parent asset
**Query Patterns**: Get all services running on specific host

#### 4. Last Updated Index
```javascript
db.assets.createIndex(
  { "last_updated": -1 },
  { 
    name: "last_updated_idx",
    background: true
  }
)
```

**Purpose**: Find recently updated assets
**Query Patterns**: Monitoring for stale data, recent changes

## Time-Series Optimization

### MongoDB Time-Series Benefits

1. **Automatic Bucketing**: MongoDB groups measurements into time-based buckets
2. **Compression**: Specialized compression algorithms for time-series data
3. **Query Optimization**: Automatic query plan optimization for temporal queries
4. **Memory Efficiency**: Reduced memory footprint for time-based operations

### Bucket Configuration

```javascript
// Optimal bucket configuration for minute-level data
{
  timeseries: {
    timeField: "timestamp",
    metaField: "meta",
    granularity: "minutes",
    bucketMaxSpanSeconds: 3600,  // 1 hour buckets
    bucketRoundingSeconds: 60    // Round to minute boundaries
  }
}
```

### Write Optimization Strategies

#### 1. Batch Insertions
```python
# Optimal batch size: 1000-5000 documents
def save_metrics_batch(self, metrics: List[MetricDocument]) -> int:
    batch_size = 1000
    total_inserted = 0
    
    for i in range(0, len(metrics), batch_size):
        batch = metrics[i:i + batch_size]
        mongo_docs = [metric.to_mongo_dict() for metric in batch]
        
        result = self.db.metrics.insert_many(
            mongo_docs,
            ordered=False,  # Allow partial failures
            bypass_document_validation=False
        )
        total_inserted += len(result.inserted_ids)
    
    return total_inserted
```

#### 2. Write Concern Configuration
```python
# Balance between performance and durability
write_concern = WriteConcern(
    w=1,           # Acknowledge from primary only
    j=False,       # Don't wait for journal sync
    wtimeout=5000  # 5 second timeout
)
```

### Read Optimization Strategies

#### 1. Projection Optimization
```python
# Only fetch required fields
def get_metrics(self, asset_id: str, fields: List[str] = None):
    projection = {}
    if fields:
        projection = {field: 1 for field in fields}
        projection['_id'] = 0  # Exclude _id unless needed
    
    return self.db.metrics.find(
        {"meta.asset_id": asset_id},
        projection
    )
```

#### 2. Query Hint Usage
```python
# Force index usage for complex queries
def get_metrics_with_hint(self, asset_id: str, start_time: datetime):
    return self.db.metrics.find(
        {
            "meta.asset_id": asset_id,
            "timestamp": {"$gte": start_time}
        }
    ).hint("asset_time_idx")
```

## Performance Tuning

### Connection Pool Configuration

```python
# Optimal connection pool settings
client = MongoClient(
    connection_string,
    maxPoolSize=50,          # Max connections in pool
    minPoolSize=5,           # Min connections to maintain
    maxIdleTimeMS=30000,     # Close idle connections after 30s
    waitQueueTimeoutMS=5000, # Wait 5s for available connection
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=10000,
    socketTimeoutMS=20000
)
```

### Memory Management

#### 1. Cursor Batching
```python
# Process large result sets efficiently
def process_large_dataset(self, query: dict):
    cursor = self.db.metrics.find(query).batch_size(1000)
    
    for batch in cursor:
        # Process batch
        yield batch
```

#### 2. Aggregation Pipeline Optimization
```python
# Optimize aggregation pipelines
def get_hourly_averages(self, asset_id: str, start_time: datetime):
    pipeline = [
        # Filter early to reduce data volume
        {
            "$match": {
                "meta.asset_id": asset_id,
                "timestamp": {"$gte": start_time}
            }
        },
        # Group by hour
        {
            "$group": {
                "_id": {
                    "hour": {"$dateToString": {
                        "format": "%Y-%m-%d %H:00:00",
                        "date": "$timestamp"
                    }},
                    "metric": "$meta.metric_name"
                },
                "avg_value": {"$avg": "$value"},
                "count": {"$sum": 1}
            }
        },
        # Sort by time
        {"$sort": {"_id.hour": 1}}
    ]
    
    return list(self.db.metrics.aggregate(
        pipeline,
        allowDiskUse=True,  # Allow spilling to disk for large datasets
        cursor={"batchSize": 1000}
    ))
```

### Query Performance Monitoring

#### 1. Profiling Configuration
```javascript
// Enable profiling for slow queries
db.setProfilingLevel(1, { slowms: 100 })

// Query profiling data
db.system.profile.find().limit(5).sort({ ts: -1 }).pretty()
```

#### 2. Index Usage Analysis
```javascript
// Analyze index usage
db.metrics.aggregate([
  { $indexStats: {} }
])

// Find unused indexes
db.runCommand({ collStats: "metrics", indexDetails: true })
```

## Scaling Guidelines

### Horizontal Scaling (Sharding)

#### 1. Shard Key Selection

**For Metrics Collection:**
```javascript
// Compound shard key for even distribution
sh.shardCollection("monitoring.metrics", {
  "meta.asset_id": 1,
  "timestamp": 1
})
```

**Rationale:**
- `asset_id` provides good distribution across assets
- `timestamp` enables efficient range queries
- Compound key prevents hotspots

**For Assets Collection:**
```javascript
// Hash shard key for uniform distribution
sh.shardCollection("monitoring.assets", {
  "_id": "hashed"
})
```

#### 2. Shard Configuration

```javascript
// Configure chunk size for time-series data
use config
db.settings.save({
  _id: "chunksize",
  value: 32  // 32MB chunks (smaller for time-series)
})
```

### Vertical Scaling

#### 1. Hardware Recommendations

**Minimum Production Setup:**
- CPU: 8 cores
- RAM: 32GB
- Storage: SSD with 10,000+ IOPS
- Network: 1Gbps

**High-Volume Setup:**
- CPU: 16+ cores
- RAM: 64GB+
- Storage: NVMe SSD with 50,000+ IOPS
- Network: 10Gbps

#### 2. MongoDB Configuration

```yaml
# mongod.conf optimizations
storage:
  wiredTiger:
    engineConfig:
      cacheSizeGB: 24  # 75% of available RAM
      directoryForIndexes: true
    collectionConfig:
      blockCompressor: snappy
    indexConfig:
      prefixCompression: true

operationProfiling:
  slowOpThresholdMs: 100
  mode: slowOp

net:
  maxIncomingConnections: 1000
```

### Read Scaling with Replicas

#### 1. Replica Set Configuration

```javascript
// Configure replica set with read preferences
rs.initiate({
  _id: "monitoring-rs",
  members: [
    { _id: 0, host: "mongo-primary:27017", priority: 2 },
    { _id: 1, host: "mongo-secondary1:27017", priority: 1 },
    { _id: 2, host: "mongo-secondary2:27017", priority: 1 },
    { _id: 3, host: "mongo-arbiter:27017", arbiterOnly: true }
  ]
})
```

#### 2. Read Preference Strategy

```python
# Distribute read load across replicas
from pymongo import ReadPreference

# For real-time dashboards (slight lag acceptable)
read_preference = ReadPreference.SECONDARY_PREFERRED

# For critical operations (must be current)
read_preference = ReadPreference.PRIMARY

client = MongoClient(
    connection_string,
    read_preference=read_preference
)
```

## Maintenance Guidelines

### Regular Maintenance Tasks

#### 1. Index Maintenance

```python
def optimize_indexes():
    """Rebuild and optimize indexes for better performance"""
    
    # Rebuild indexes to defragment
    collections = ['metrics', 'assets']
    
    for collection_name in collections:
        collection = self.db[collection_name]
        
        # Get index information
        indexes = collection.list_indexes()
        
        for index in indexes:
            if index['name'] != '_id_':  # Skip default index
                # Rebuild index in background
                collection.reindex(index['name'])
                logger.info(f"Rebuilt index {index['name']} on {collection_name}")
```

#### 2. Data Cleanup

```python
def cleanup_old_data(retention_days: int = 90):
    """Remove metrics older than retention period"""
    
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    
    result = self.db.metrics.delete_many({
        "timestamp": {"$lt": cutoff_date}
    })
    
    logger.info(f"Deleted {result.deleted_count} old metric documents")
    
    # Compact collection after large deletions
    self.db.command("compact", "metrics")
```

#### 3. Performance Monitoring

```python
def monitor_performance():
    """Monitor database performance metrics"""
    
    # Check slow queries
    slow_queries = self.db.system.profile.find({
        "millis": {"$gt": 100}
    }).sort("ts", -1).limit(10)
    
    # Check index usage
    index_stats = self.db.metrics.aggregate([{"$indexStats": {}}])
    
    # Check collection stats
    metrics_stats = self.db.command("collStats", "metrics")
    assets_stats = self.db.command("collStats", "assets")
    
    return {
        "slow_queries": list(slow_queries),
        "index_stats": list(index_stats),
        "collection_stats": {
            "metrics": metrics_stats,
            "assets": assets_stats
        }
    }
```

### Backup and Recovery

#### 1. Backup Strategy

```bash
#!/bin/bash
# Daily backup script

BACKUP_DIR="/backups/mongodb/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Full backup
mongodump --host mongodb-primary:27017 \
          --db monitoring \
          --out $BACKUP_DIR \
          --gzip

# Compress backup
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

# Retain 30 days of backups
find /backups/mongodb -name "*.tar.gz" -mtime +30 -delete
```

#### 2. Point-in-Time Recovery

```bash
# Enable oplog for point-in-time recovery
mongod --replSet monitoring-rs --oplogSize 10240  # 10GB oplog

# Restore to specific point in time
mongorestore --host mongodb-primary:27017 \
             --db monitoring \
             --oplogReplay \
             --oplogLimit 1640995200:1 \
             /backup/path
```

### Monitoring and Alerting

#### 1. Key Metrics to Monitor

- **Connection Pool Usage**: Alert if > 80% utilized
- **Slow Query Count**: Alert if > 10 queries/minute over 100ms
- **Replication Lag**: Alert if > 10 seconds
- **Disk Usage**: Alert if > 85% full
- **Memory Usage**: Alert if cache hit ratio < 95%
- **Index Usage**: Alert for unused indexes

#### 2. Health Check Queries

```python
def health_check():
    """Comprehensive database health check"""
    
    health_status = {
        "connection": False,
        "replica_status": None,
        "slow_queries": 0,
        "disk_usage": None,
        "index_efficiency": None
    }
    
    try:
        # Test connection
        self.db.command("ping")
        health_status["connection"] = True
        
        # Check replica set status
        rs_status = self.db.command("replSetGetStatus")
        health_status["replica_status"] = rs_status["ok"]
        
        # Count slow queries in last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        slow_count = self.db.system.profile.count_documents({
            "ts": {"$gte": one_hour_ago},
            "millis": {"$gt": 100}
        })
        health_status["slow_queries"] = slow_count
        
        # Check disk usage
        stats = self.db.command("dbStats")
        health_status["disk_usage"] = {
            "data_size": stats["dataSize"],
            "storage_size": stats["storageSize"],
            "index_size": stats["indexSize"]
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        health_status["error"] = str(e)
    
    return health_status
```

This comprehensive documentation covers all aspects of the database schema, performance optimization, and scaling considerations for the Infrastructure Monitoring Storage system.