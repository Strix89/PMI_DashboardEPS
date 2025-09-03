# Metrics Operations Implementation

This document describes the implementation of task 3 "Implement metrics operations with time-series optimization" from the infrastructure monitoring storage specification.

## Implemented Features

### 1. save_metrics_batch Method

**Location**: `storage_layer/storage_manager.py`

**Features**:
- Bulk insert operation for high performance
- Comprehensive data validation for each metric in the batch
- Detailed error reporting for malformed data
- Returns count of successfully inserted records
- Retry logic with exponential backoff

**Usage**:
```python
metrics = [
    MetricDocument(
        timestamp=datetime.utcnow(),
        asset_id="vm-101",
        metric_name="cpu_usage",
        value=75.5
    ),
    # ... more metrics
]

inserted_count = storage_manager.save_metrics_batch(metrics)
print(f"Inserted {inserted_count} metrics")
```

### 2. get_metrics Query Method

**Location**: `storage_layer/storage_manager.py`

**Features**:
- Flexible filtering by asset_id, metric_name, and time range
- Multiple filters combined with AND logic
- Returns empty list when no results found (no exceptions)
- Optimized queries using compound indexes
- Results sorted by timestamp (newest first)

**Usage**:
```python
# Get all metrics
all_metrics = storage_manager.get_metrics()

# Filter by asset
vm_metrics = storage_manager.get_metrics(asset_id="vm-101")

# Filter by metric type
cpu_metrics = storage_manager.get_metrics(metric_name="cpu_usage")

# Filter by time range
recent_metrics = storage_manager.get_metrics(
    start_time=datetime.utcnow() - timedelta(hours=1),
    end_time=datetime.utcnow()
)

# Combined filters
specific_metrics = storage_manager.get_metrics(
    asset_id="vm-101",
    metric_name="cpu_usage",
    start_time=start_time,
    end_time=end_time
)
```

### 3. MongoDB Time-Series Collection Setup

**Location**: `storage_layer/storage_manager.py`

**Features**:
- Configures metrics collection as MongoDB time-series collection
- Creates optimized compound indexes:
  - `{meta.asset_id: 1, timestamp: 1}` for asset-based queries
  - `{meta.metric_name: 1, timestamp: 1}` for metric-type queries
- TTL index on timestamp for automatic data retention (90 days)
- Idempotent operation (safe to run multiple times)

**Usage**:
```python
# Setup collection and indexes
result = storage_manager.setup_time_series_collection()
print(f"Setup result: {result}")
```

## Data Format

### MongoDB Time-Series Document Structure

```json
{
  "_id": ObjectId,
  "timestamp": ISODate("2025-02-09T10:30:00.000Z"),
  "meta": {
    "asset_id": "vm-101",
    "metric_name": "cpu_usage"
  },
  "value": 75.5
}
```

## Performance Optimizations

1. **Time-Series Collection**: Uses MongoDB 5.0+ native time-series collections for optimal storage and query performance
2. **Compound Indexes**: Strategic indexing for common query patterns
3. **Bulk Operations**: Batch inserts reduce round-trips and improve throughput
4. **Connection Pooling**: Reuses connections for better performance
5. **Retry Logic**: Handles transient failures gracefully

## Error Handling

- **ValidationError**: Raised for invalid input data
- **OperationError**: Raised for database operation failures
- **ConnectionError**: Raised for connection issues
- **RetryExhaustedError**: Raised when all retry attempts fail

## Testing

Run the test script to verify the implementation:

```bash
python test_metrics_operations.py
```

The test script covers:
- Connection establishment
- Time-series collection setup
- Batch metric insertion
- Various query scenarios
- Error handling validation
- Connection status checking

## Requirements Satisfied

This implementation satisfies the following requirements from the specification:

- **2.1**: Bulk insert operations for metrics
- **2.2**: Metric validation and error handling
- **2.4**: Retry logic with exponential backoff
- **4.1**: Flexible filtering by asset_id
- **4.2**: Filtering by metric_name
- **4.3**: Time range filtering
- **4.4**: Combined filters with AND logic
- **4.5**: Empty list return for no results

## Next Steps

The metrics operations are now fully implemented and ready for use. The next task in the implementation plan is task 4: "Implement asset management operations".