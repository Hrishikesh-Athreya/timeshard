# Timeshard

**Distributed ID generation that solves real operational problems**

A production-ready Python implementation of the Snowflake algorithm with flexible formatting capabilities. Generate globally unique, time-ordered IDs with custom prefixes for microservices, compliance requirements, logging, and third-party integrations—all without coordination between servers.

```python
from timeshard import TimeshardGenerator

generator = TimeshardGenerator(node_id=1)

# Human-readable IDs for operations
order_id = generator.next_id_with_prefix("ORD_")  # "ORD_1730678523123456789"
user_id = generator.next_id_with_prefix("USR_")   # "USR_1730678523123456790"

# Compliance-ready formatting
tax_id = generator.next_id_with_prefix_at("-TAX-", 4)  # "1730-TAX-678523123456791"

# Correlation IDs for distributed tracing
trace_id = generator.next_id_with_prefix("REQ_")  # "REQ_1730678523123456792"

# All IDs: time-sortable, parseable, globally unique, zero coordination
```

---

## The Problem

Modern distributed systems face multiple ID generation challenges:

| Challenge | Traditional Solutions | Problems |
|-----------|----------------------|----------|
| **Human readability** | UUIDs | `550e8400-e29b-41d4-a716-446655440000` - What is this? |
| **Database performance** | UUIDs | Not time-ordered, poor indexing, slow range queries |
| **Distributed uniqueness** | Database auto-increment | Single point of failure, requires coordination |
| **API compliance** | Random + manual formatting | Collision risk, inconsistent implementation |
| **Namespace isolation** | Separate generators | Maintenance nightmare, no standardization |
| **Auditability** | Opaque IDs | Can't extract metadata (timestamp, server, sequence) |

**Result**: Teams implement different ID generation logic for each use case, leading to inconsistency, maintenance burden, and production issues.

---

## The Solution

Timeshard provides **one ID generator** that handles all these cases:

✅ **Globally unique** across all servers (Snowflake algorithm)  
✅ **Time-ordered** for efficient database indexing  
✅ **Human-readable** with custom prefixes  
✅ **Format-compliant** for third-party APIs and regulations  
✅ **Zero coordination** (no database, no Redis, no network calls)  
✅ **Parseable** to extract timestamp, server ID, and sequence  
✅ **High-performance** (3M+ IDs/second per worker)  

---

## Architecture

### Snowflake Structure (64 bits)
```
┌──────┬─────────────────────┬───────────────┬─────────────┐
│ 1bit │      41 bits       │   X bits      │   Y bits    │
│ sign │   timestamp (ms)   │   node ID     │  sequence   │
└──────┴─────────────────────┴───────────────┴─────────────┘
         ~69 years            runtime config   runtime config
```

### Runtime Configurability

Unlike traditional Snowflake implementations with fixed bit allocation, Timeshard allows configuration at runtime:

```bash
# Adjust based on your deployment scale
export TIMESHARD_NODE_ID_BITS=10  # 1,024 nodes, 4,096 IDs/ms each (default)
export TIMESHARD_NODE_ID_BITS=12  # 4,096 nodes, 1,024 IDs/ms each (large scale)
export TIMESHARD_NODE_ID_BITS=8   # 256 nodes, 16,384 IDs/ms each (high throughput)
```

**Key Innovation**: Change deployment scale without code changes—just adjust environment variables and restart.

---

## Use Cases

### 1. Human-Readable Operations

**Problem**: Customer service, debugging, and logs filled with meaningless UUIDs.

```python
# Before: "Transaction 550e8400-e29b-41d4-a716-446655440000 failed"
# After: "Transaction TXN_1730678523123456789 failed"

transaction_id = generator.next_id_with_prefix("TXN_")
order_id = generator.next_id_with_prefix("ORD_")
payment_id = generator.next_id_with_prefix("PMT_")

# Instantly recognize ID types in logs, dashboards, URLs
```

**Real impact**: Support teams save hours not deciphering cryptic IDs.

### 2. Namespace Isolation in Microservices

**Problem**: Multiple services generating IDs need to avoid collisions and maintain clear boundaries.

```python
# Order Service (node_id=1)
order_generator = TimeshardGenerator(node_id=1)
order_id = order_generator.next_id_with_prefix("ORD_")

# Payment Service (node_id=2)
payment_generator = TimeshardGenerator(node_id=2)
payment_id = payment_generator.next_id_with_prefix("PMT_")

# User Service (node_id=3)
user_generator = TimeshardGenerator(node_id=3)
user_id = user_generator.next_id_with_prefix("USR_")

# Database queries by namespace
SELECT * FROM events WHERE event_id LIKE 'ORD_%';  -- Only orders
SELECT * FROM events WHERE event_id LIKE 'PMT_%';  -- Only payments
```

### 3. Distributed Tracing & Correlation IDs

**Problem**: Tracking requests across multiple microservices.

```python
# API Gateway generates correlation ID
correlation_id = generator.next_id_with_prefix("REQ_")

# Pass to all downstream services
logger.info(f"[{correlation_id}] Processing order")
order_service.create(correlation_id=correlation_id)
payment_service.charge(correlation_id=correlation_id)
notification_service.send(correlation_id=correlation_id)

# All logs grouped by correlation_id for full request trace
# Time-ordered for understanding request flow
```

### 4. Third-Party API Compliance

**Problem**: External APIs require specific ID formats.

**Real impact**: One ID generator handles all provider formats instead of maintaining separate logic.

### 5. Regulatory & Compliance Requirements

**Problem**: Government, healthcare, and financial systems require specific ID formats.

```python
# Tax authority: "TAX-XXXX-XXXXXX"
tax_id = generator.next_id_with_prefix("TAX-")

# Healthcare: Patient IDs with "PT" prefix
patient_id = generator.next_id_with_prefix("PT_")

# SWIFT transactions: Format with specific marker
swift_id = generator.next_id_with_prefix_at("-SWIFT-", 8)

# Financial reporting: Audit trail IDs
audit_id = generator.next_id_with_prefix("AUD_")
```

### 6. Database Performance (Time-Ordered Indexing)

**Problem**: UUIDs don't index well, causing slow range queries and poor database performance.

```python
# Timeshard IDs are naturally time-ordered
id1 = generator.next_id()  # 1730678523123456789 (10:00:00.123)
id2 = generator.next_id()  # 1730678523223456790 (10:00:00.223)

# Efficient range queries (uses index)
SELECT * FROM orders 
WHERE order_id > 1730678523000000000 
  AND order_id < 1730678524000000000
ORDER BY order_id;  -- Already sorted!

# Time-based sharding
partition = id % 100  # Distribute by time
```

### 7. Multi-Region Deployment

**Problem**: Need unique IDs across multiple geographic regions without coordination.

```python
# US-EAST workers (node_id 1-1000)
us_generator = TimeshardGenerator(node_id=1)

# EU-WEST workers (node_id 1001-2000)
eu_generator = TimeshardGenerator(node_id=1001)

# ASIA-PACIFIC workers (node_id 2001-3000)
asia_generator = TimeshardGenerator(node_id=2001)

# All generate IDs independently, zero collisions
# No cross-region network calls
```

### 8. Security & Forensics

**Problem**: Need to audit and trace ID origins for security and compliance.

```python
# Suspicious transaction detected
suspicious_id = "TXN_1730678523123456789"

# Parse to extract metadata
numeric_id = int(suspicious_id.split("_")[1])
parsed = generator.parse_id(numeric_id)

print(f"Transaction created: {parsed['datetime']}")     # 2024-11-03 18:42:03.123
print(f"Generated by server: {parsed['node_id']}")     # Server 42
print(f"Sequence in millisecond: {parsed['sequence']}") # 789th ID that ms

# Use for fraud detection, audit trails, forensic analysis
```

### 9. Event Sourcing & CQRS

**Problem**: Events need unique, time-ordered IDs for event streams.

```python
# Different event types with clear prefixes
user_created = generator.next_id_with_prefix("EVT_USER_")
payment_processed = generator.next_id_with_prefix("EVT_PAY_")
order_shipped = generator.next_id_with_prefix("EVT_SHIP_")

# Query events by type efficiently
SELECT * FROM events 
WHERE event_id LIKE 'EVT_PAY_%' 
ORDER BY event_id;  -- Time-ordered replay

# Partition event streams by prefix
```

### 10. URL-Friendly & Shareable IDs

**Problem**: Public-facing IDs need to be short and shareable.

```python
# Clean, shareable URLs
video_id = generator.next_id_with_prefix("VID_")
# → https://yoursite.com/videos/VID_1730678523123456

invite_id = generator.next_id_with_prefix("INV_")
# → https://yoursite.com/invite/INV_1730678523123457

# vs UUID: https://yoursite.com/videos/550e8400-e29b-41d4-a716-446655440000
```

---

## Installation
```bash
pip install git+https://github.com/yourusername/timeshard.git
```

Or clone and install locally:
```bash
git clone https://github.com/yourusername/timeshard.git
cd timeshard
pip install -e .
```

---

## Quick Start

### Basic Usage

```python
from timeshard import TimeshardGenerator

# Create generator (auto-detects node ID from machine IP)
generator = TimeshardGenerator()

# Generate IDs
id1 = generator.next_id()  # 1730678523123456789
id2 = generator.next_id()  # 1730678523123456790

# IDs are time-ordered
assert id2 > id1
```

### With Prefixes

```python
# Generate IDs with semantic meaning
order_id = generator.next_id_with_prefix("ORD_")
# → "ORD_1730678523123456789"

user_id = generator.next_id_with_prefix("USR_")
# → "USR_1730678523123456790"

transaction_id = generator.next_id_with_prefix("TXN_")
# → "TXN_1730678523123456791"
```

### Advanced: Prefix at Position

```python
# Insert prefix at specific position for custom formatting
bank_id = generator.next_id_with_prefix_at("-REF-", 4)
# → "1730-REF-678523123456789"

compliance_id = generator.next_id_with_prefix_at("-TAX-", 6)
# → "173067-TAX-8523123456789"

# Useful for:
# - Legacy system integration
# - Regulatory compliance formats
# - Third-party API requirements
```

### Parsing IDs

```python
# Extract metadata from any ID
parsed = generator.parse_id(1730678523123456789)
# {
#     'id': 1730678523123456789,
#     'timestamp': 1730678523123,
#     'datetime': '2024-11-03 18:42:03.123',
#     'node_id': 1,
#     'sequence': 789
# }

# Use for debugging, auditing, forensics
```

---

## Configuration

### Environment Variables

```bash
# Node ID bits (1-16, default: 10)
# Determines max workers vs IDs per millisecond
export TIMESHARD_NODE_ID_BITS=10

# Explicit node ID (auto-detected from IP if not set)
export TIMESHARD_NODE_ID=42

# Custom epoch in milliseconds (default: 2023-12-12)
export TIMESHARD_CUSTOM_EPOCH=1702385533000
```

### Configuration Guide

Choose node bits based on your deployment:

| Node Bits | Max Workers | IDs/ms per Worker | Use Case |
|-----------|-------------|-------------------|----------|
| 8 | 256 | 16,384 | High throughput, few workers |
| 10 | 1,024 | 4,096 | **Balanced (default)** |
| 12 | 4,096 | 1,024 | Large scale deployment |
| 14 | 16,384 | 256 | Massive scale (e.g., IoT) |

### Auto Node ID Detection

If `TIMESHARD_NODE_ID` is not set, Timeshard derives it from the machine's IP address:

```python
# For IP 192.168.1.42:
# Takes last 2 octets: (1 << 8) | 42 = 298
# Masks to fit configured bits: 298 & 1023 = 298

generator = TimeshardGenerator()  # Auto-detects node_id=298
```

**Perfect for**:
- Kubernetes pods (each gets unique IP)
- Docker containers (auto-assigned IPs)
- Cloud instances (unique IPs)

### Singleton Pattern (Recommended)

```python
# Ensure single generator instance per process
generator = TimeshardGenerator.get_instance(node_id=1)

# Subsequent calls return same instance
same_gen = TimeshardGenerator.get_instance()
assert generator is same_gen
```

---

## Performance

### Benchmarks (M4 MacBook Pro)

```
Single-threaded:     3,148,202 IDs/sec    (0.32 µs per ID)
Multi-threaded:      3,557,020 IDs/sec    (0.28 µs per ID, 10 threads)

With Prefix:         2,863,340 IDs/sec    (21.7% overhead)
With Prefix @Pos:    2,291,598 IDs/sec    (52.0% overhead)
```

### Latency Distribution
```
Mean:    0.31 µs
Median:  0.29 µs
p50:     0.29 µs
p90:     0.37 µs
p95:     0.42 µs
p99:     0.42 µs
p99.9:   1.67 µs
```

### Configuration Performance Impact

| Config | Node Bits | Throughput | Notes |
|--------|-----------|------------|-------|
| High-Throughput | 8 | 3.5M/s | Best for single-threaded |
| Standard | 10 | 3.6M/s | **Optimal for most workloads** |
| High-Scale | 12 | 1.0M/s | Lock contention increases |

**Key Finding**: 10-bit node configuration provides best balance of throughput and scalability.

Run benchmarks yourself:
```bash
python benchmark.py
```

---

## Distributed System Guarantees

### No Coordination Required

**The Key Advantage**: Generate globally unique IDs across 1000+ servers without any coordination.

```python
# 100 servers processing simultaneously
# Each with unique node_id (1-100)
# Generating millions of IDs per second

for node_id in range(1, 101):
    generator = TimeshardGenerator(node_id=node_id)
    
    # Each server generates independently
    order_id = generator.next_id_with_prefix("ORD_")
    
    # GUARANTEED globally unique
    # NO database lookup
    # NO Redis coordination
    # NO network calls
    # NO race conditions
```

### Contrast with Alternatives

| Approach | Unique? | Distributed? | Time-Ordered? | Readable? | Coordination? | Performance |
|----------|---------|--------------|---------------|-----------|---------------|-------------|
| **Timeshard** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ❌ None | 3M/s |
| UUID v4 | ~Yes | ✅ Yes | ❌ No | ❌ No | ❌ None | 10M/s |
| UUID v7 | ~Yes | ✅ Yes | ✅ Yes | ❌ No | ❌ None | 8M/s |
| Random + prefix | ❌ Risk | ❌ Collisions | ❌ No | ⚠️ Prefix only | ❌ None | 5M/s |
| DB auto-increment | ✅ Yes | ❌ SPOF | ✅ Yes | ⚠️ Numbers only | ✅ Required | ~1K/s |
| Redis counter | ✅ Yes | ⚠️ SPOF | ✅ Yes | ⚠️ Numbers only | ✅ Required | ~10K/s |

**Timeshard uniquely combines**: Distribution + Time-ordering + Readability + Zero coordination

---

## Production Deployment

### Kubernetes StatefulSet

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: order-service
spec:
  replicas: 50  # 50 instances, all generating IDs safely
  template:
    spec:
      containers:
      - name: app
        env:
        - name: TIMESHARD_NODE_ID_BITS
          value: "10"
        - name: TIMESHARD_NODE_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.annotations['statefulset.kubernetes.io/pod-name']
```

### Docker Compose

```yaml
services:
  order-service-1:
    environment:
      - TIMESHARD_NODE_ID_BITS=10
      - TIMESHARD_NODE_ID=1
  
  order-service-2:
    environment:
      - TIMESHARD_NODE_ID_BITS=10
      - TIMESHARD_NODE_ID=2
  
  payment-service:
    environment:
      - TIMESHARD_NODE_ID_BITS=10
      - TIMESHARD_NODE_ID=50
```

### AWS ECS / Fargate

```json
{
  "containerDefinitions": [{
    "environment": [
      {"name": "TIMESHARD_NODE_ID_BITS", "value": "10"},
      {"name": "TIMESHARD_NODE_ID", "value": "${TASK_ID}"}
    ]
  }]
}
```

### Clock Synchronization (Critical)

Timeshard relies on monotonic timestamps. **Always use NTP**:

```bash
# Ubuntu/Debian
sudo apt install ntp
sudo systemctl enable ntp

# Monitor clock drift
ntpq -p

# Check time sync status
timedatectl status
```

**Clock Skew Handling**: If system clock moves backwards, Timeshard **refuses** to generate IDs to prevent duplicates.

---

## API Reference

### `TimeshardGenerator(node_id=None, custom_epoch=None)`

Create a new ID generator.

**Parameters**:
- `node_id` (int, optional): Worker ID (0 to max_node_id). Auto-detected from IP if not provided.
- `custom_epoch` (int, optional): Epoch timestamp in milliseconds. Defaults to 2023-12-12.

**Raises**:
- `ValueError`: If node_id is outside valid range
- `RuntimeError`: If configuration is invalid

**Example**:
```python
generator = TimeshardGenerator(node_id=42)
```

### `next_id() -> int`

Generate a unique 64-bit integer ID.

**Returns**: int (guaranteed unique, monotonically increasing within same millisecond)

**Raises**: `RuntimeError` if system clock moves backwards

**Example**:
```python
id = generator.next_id()  # 1730678523123456789
```

### `next_id_with_prefix(prefix: str) -> str`

Generate ID with string prefix.

**Parameters**:
- `prefix` (str): String to prepend to ID

**Returns**: str (formatted as "{prefix}{id}")

**Example**:
```python
order_id = generator.next_id_with_prefix("ORD_")
# → "ORD_1730678523123456789"
```

### `next_id_with_prefix_at(prefix: str, position: int) -> str`

Insert prefix at specific position in ID string.

**Parameters**:
- `prefix` (str): String to insert
- `position` (int): Position in ID string (0 to length)

**Returns**: str (ID with prefix inserted at position)

**Raises**: `ValueError` if position is invalid

**Example**:
```python
bank_id = generator.next_id_with_prefix_at("-REF-", 4)
# → "1730-REF-678523123456789"
```

### `parse_id(id_value: int) -> dict`

Decompose ID into components.

**Parameters**:
- `id_value` (int): ID to parse

**Returns**: dict with keys:
- `id`: Original ID
- `timestamp`: Absolute timestamp in milliseconds
- `timestamp_offset`: Milliseconds since custom epoch
- `node_id`: Worker/server ID that generated it
- `sequence`: Sequence number within millisecond
- `datetime`: Human-readable timestamp

**Example**:
```python
parsed = generator.parse_id(1730678523123456789)
# {
#     'id': 1730678523123456789,
#     'timestamp': 1730678523123,
#     'datetime': '2024-11-03 18:42:03.123',
#     'node_id': 1,
#     'sequence': 789
# }
```

### `get_config_info() -> str`

Returns human-readable configuration summary showing bit allocation, ranges, and throughput.

**Example**:
```python
print(generator.get_config_info())
```

### `get_instance(node_id=None, custom_epoch=None) -> TimeshardGenerator`

Get singleton instance (thread-safe). Only the first call's parameters are used.

**Example**:
```python
gen1 = TimeshardGenerator.get_instance(node_id=1)
gen2 = TimeshardGenerator.get_instance(node_id=99)  # Returns gen1
assert gen1 is gen2
```

---

## Thread Safety

Timeshard is **fully thread-safe** with fine-grained locking:

```python
from concurrent.futures import ThreadPoolExecutor

generator = TimeshardGenerator(node_id=1)

# Generate from 10 threads simultaneously
with ThreadPoolExecutor(max_workers=10) as executor:
    ids = list(executor.map(
        lambda _: generator.next_id(), 
        range(100000)
    ))

# All IDs are unique
assert len(set(ids)) == 100000

# All IDs are time-ordered (within thread)
# Globally ordered by timestamp component
```

**Implementation**: Lock only held during ID generation (~0.3µs critical section). Minimal contention.

---

## Testing

Run the comprehensive test suite:

```bash
pytest test_generator.py -v
```

### Test Coverage

- ✅ **Uniqueness**: 100K IDs, all unique
- ✅ **Monotonic ordering**: IDs increase over time
- ✅ **Thread safety**: 10 threads × 10K IDs each, no collisions
- ✅ **Multi-node**: Different node_ids produce different IDs
- ✅ **Sequence exhaustion**: Automatically waits for next millisecond
- ✅ **Clock skew detection**: Errors on backwards time movement
- ✅ **Parsing**: Round-trip ID → components → verify
- ✅ **Prefix operations**: Validate prefix formatting
- ✅ **Environment config**: Runtime configuration changes
- ✅ **Auto node ID**: IP-based node ID generation

Run benchmarks:
```bash
python benchmark.py
```

Run examples:
```bash
python example.py
```

---

## Design Decisions & Tradeoffs

### Why 41 bits for timestamp?

Provides ~69 years from custom epoch (until ~2093 with default 2023 epoch). Sufficient for any system's operational lifespan.

### Why configurable node bits?

Different systems have different scaling needs:
- **Few workers, high burst** (trading): 8 bits → 256 nodes, 16K IDs/ms each
- **Balanced** (microservices): 10 bits → 1K nodes, 4K IDs/ms each
- **Many workers** (IoT): 12-14 bits → 4K-16K nodes, fewer IDs/ms each

Runtime configuration allows testing and production to use different scales without code changes.

### Why millisecond precision?

Microsecond precision would exhaust 64 bits too quickly, limiting system lifespan. Milliseconds provide sufficient ordering granularity while maximizing the time range.

### What about the prefix overhead?

**Tradeoff Analysis**:
- 21.7% overhead for `next_id_with_prefix()` vs raw integers
- 52.0% overhead for `next_id_with_prefix_at()` vs raw integers

**Worth it because**:
- Human readability saves hours in operations and debugging
- Namespace isolation prevents entire classes of bugs
- Compliance and third-party integration requirements are non-negotiable
- 2.9M IDs/sec with prefix is still faster than any database-coordinated approach

### Clock skew handling

Timeshard **refuses** to generate IDs if the clock moves backwards, preventing potential duplicates. In production:
- Use NTP synchronization (required)
- Monitor clock drift (recommended)
- Alert on clock skew (best practice)

This is a safety-first design: better to fail loudly than silently create duplicates.

---

## Limitations & Considerations

1. **Clock dependency**: Requires synchronized clocks across all nodes (NTP mandatory)
2. **No coordination**: Workers don't communicate—must ensure unique node_ids
3. **Sequence exhaustion**: Max 4,096 IDs/ms/worker (default)—automatically waits for next millisecond
4. **Not cryptographically secure**: IDs are predictable—don't use for security tokens or sessions
5. **64-bit limit**: Maximum ~69 years from custom epoch before wrap-around
6. **Python GIL**: Multi-threaded performance limited by GIL (use multi-process for higher throughput)

---

## Migration Guide

### From UUIDs

```python
# Before
import uuid

user_id = str(uuid.uuid4())  # "550e8400-e29b-41d4-a716-446655440000"

# After
from timeshard import TimeshardGenerator

generator = TimeshardGenerator.get_instance()
user_id = generator.next_id_with_prefix("USR_")  # "USR_1730678523123456789"

# Benefits:
# - 40% smaller (20-25 chars vs 36 chars)
# - Time-ordered (efficient database indexing)
# - Human-readable (instant recognition in logs)
# - Parseable (extract timestamp, server, sequence)
```

### From Database Auto-Increment

```python
# Before
# In database: id SERIAL PRIMARY KEY

# After
from timeshard import TimeshardGenerator

generator = TimeshardGenerator.get_instance(node_id=get_worker_id())
# In database: id BIGINT PRIMARY KEY

# Change application code:
user_id = generator.next_id()  # Instead of letting DB generate

# Benefits:
# - No database round-trip for ID generation
# - Works offline/distributed
# - 3000x faster (3M/s vs 1K/s)
```

---

## Frequently Asked Questions

### Q: What if two servers have the same node_id?

**A**: IDs will collide. You MUST ensure unique node_ids. Use:
- Environment variables (manual assignment)
- Auto-detection from IP (works in most containerized environments)
- StatefulSet ordinals (Kubernetes)
- Instance metadata (cloud providers)

### Q: What happens when sequence exhausts in one millisecond?

**A**: Timeshard automatically waits for the next millisecond. With 4,096 IDs/ms (default), this is rare. If you need more, use 14-bit sequence (8-bit nodes).

### Q: Can I use this for security tokens?

**A**: No. Timeshard IDs are predictable by design. Use cryptographically secure random tokens for:
- Session IDs
- API keys
- Password reset tokens
- OAuth tokens

### Q: How do I handle clock skew?

**A**: 
1. Use NTP (mandatory)
2. Monitor clock drift (recommended)
3. Alert on backwards time movement (best practice)
4. If detected, Timeshard will error rather than risk duplicates

### Q: What's the maximum throughput?

**A**: 
- Single worker: 3M IDs/sec (benchmarked)
- With 1,024 workers (10-bit): 3 billion IDs/sec globally
- Bottleneck is typically GIL, not algorithm
