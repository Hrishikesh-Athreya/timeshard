# Timeshard

**Variable-length distributed ID generator with human-readable prefixes**

A Snowflake-inspired ID generator that trades deterministic bit allocation for **runtime configurability** and **prefix support**—built for systems where ID semantics matter as much as uniqueness.

```python
from timeshard import TimeshardGenerator

generator = TimeshardGenerator(node_id=1)

# Standard Snowflake behavior
user_id = generator.next_id()  # → 1730678523123456789

# But with prefix support for human-readable IDs
trade_id = generator.next_id_with_prefix("TRD_")  # → "TRD_1730678523123456790"
order_id = generator.next_id_with_prefix("ORD_")  # → "ORD_1730678523123456791"
```

---

## The Core Difference

**Traditional Snowflake**: Fixed bit allocation decided at compile time  
**Timeshard**: Configurable bit allocation at runtime + prefix injection

This isn't just Snowflake with strings tacked on. The design choices prioritize operational flexibility over micro-optimizations:

1. **Runtime Configuration**: Adjust node/sequence bits via environment variables without rebuilding
2. **Prefix Integration**: Built-in support for domain-specific ID namespacing
3. **Python-First**: Optimized for Python's threading model and ecosystem

**The Tradeoff**: ~10-20% overhead for prefix operations in exchange for operational flexibility and human-readable IDs.

---

## Why This Exists

### The Problem with Standard Snowflake

Snowflake IDs are great for uniqueness but terrible for humans:
- `1730678523123456789` tells you nothing about the domain
- Debugging requires looking up "what system generated this?"
- No way to visually distinguish transaction IDs from order IDs

### The Problem with Prefixed UUIDs

```python
order_id = f"ORD_{uuid4()}"  # "ORD_550e8400-e29b-41d4-a716-446655440000"
```

- 36+ characters (inefficient storage)
- Random ordering (poor database indexing)
- No timestamp extraction (can't sort by creation time)

### Timeshard's Solution

```python
order_id = generator.next_id_with_prefix("ORD_")  # "ORD_1730678523123456789"
```

- Time-ordered (efficient database scans)
- Compact (20-24 chars with prefix)
- Parseable (extract timestamp, node, sequence)
- Human-readable (know the domain at a glance)

---

## Architecture

### Standard Snowflake (Fixed)
```
┌──────┬─────────────────────┬───────────┬─────────────┐
│ 1bit │      41 bits       │  10 bits  │   12 bits   │
│ sign │   timestamp (ms)   │  node ID  │  sequence   │
└──────┴─────────────────────┴───────────┴─────────────┘
         FIXED AT COMPILE TIME
```

### Timeshard (Configurable)
```
┌──────┬─────────────────────┬───────────────┬─────────────┐
│ 1bit │      41 bits       │   X bits      │   Y bits    │
│ sign │   timestamp (ms)   │   node ID     │  sequence   │
└──────┴─────────────────────┴───────────────┴─────────────┘
         X + Y = 22 bits (configurable at runtime)
```

**Key Innovation**: Bit allocation decided by `TIMESHARD_NODE_ID_BITS` environment variable:
- `X = TIMESHARD_NODE_ID_BITS` (default: 10)
- `Y = 22 - X` (automatically calculated)

### Why This Matters

**Scenario 1**: Small deployment, high burst traffic (trading system)
```bash
export TIMESHARD_NODE_ID_BITS=8  # 256 nodes, 16,384 IDs/ms per node
```

**Scenario 2**: Large deployment, moderate traffic (microservices)
```bash
export TIMESHARD_NODE_ID_BITS=12  # 4,096 nodes, 1,024 IDs/ms per node
```

Change configuration **without code changes**—just restart with different env vars.

---

## Performance

### Benchmarks (M4 MacBook Pro)

```
Single-threaded:     3.1M IDs/sec    (0.32 µs per ID)
Multi-threaded:      3.6M IDs/sec    (0.28 µs per ID, 10 threads)

With Prefix:         2.9M IDs/sec    (21.7% overhead)
With Prefix @Pos:    2.3M IDs/sec    (52.0% overhead)
```

### Latency Distribution
```
p50:   0.29 µs
p90:   0.37 µs
p95:   0.42 µs
p99:   0.42 µs
p99.9: 1.67 µs
```

### Configuration Impact

| Config | Node Bits | Sequence Bits | Throughput | Use Case |
|--------|-----------|---------------|------------|----------|
| High-Throughput | 8 | 14 | 3.5M/s | Few workers, high burst |
| Standard | 10 | 12 | 3.6M/s | Balanced deployment |
| High-Scale | 12 | 10 | 1.0M/s | Many workers, moderate load |

**Key Finding**: 12-bit node config shows 3x slowdown due to increased lock contention. Optimal range: 8-10 bits for most Python workloads.

---

## Installation

```bash
pip install timeshard
```

---

## Usage

### Basic ID Generation

```python
from timeshard import TimeshardGenerator

generator = TimeshardGenerator(node_id=1)

# Generate unique IDs
id1 = generator.next_id()  # 1730678523123456789
id2 = generator.next_id()  # 1730678523123456790

# IDs are time-ordered
assert id2 > id1
```

### Prefix Support (The Killer Feature)

```python
# Different ID namespaces with semantic meaning
trade_id = generator.next_id_with_prefix("TRD_")
# → "TRD_1730678523123456789"

order_id = generator.next_id_with_prefix("ORD_")
# → "ORD_1730678523123456790"

user_id = generator.next_id_with_prefix("USR_")
# → "USR_1730678523123456791"
```

**Why this matters**: Database queries become self-documenting
```sql
-- Immediately clear what you're querying
SELECT * FROM transactions WHERE id LIKE 'TRD_%';
SELECT * FROM orders WHERE id LIKE 'ORD_%';
```

### ID Parsing

```python
parsed = generator.parse_id(1730678523123456789)
# {
#     'id': 1730678523123456789,
#     'timestamp': 1730678523123,
#     'datetime': '2024-11-03 18:42:03.123',
#     'node_id': 1,
#     'sequence': 789
# }

# Use for debugging: "When was this order created?"
order_time = generator.parse_id(order_id)['datetime']
```

### Runtime Configuration

```python
import os

# Configure for your deployment
os.environ['TIMESHARD_NODE_ID_BITS'] = '10'      # 1,024 max workers
os.environ['TIMESHARD_NODE_ID'] = '42'           # This worker's ID
os.environ['TIMESHARD_CUSTOM_EPOCH'] = '1700000000000'  # Epoch in ms

generator = TimeshardGenerator()
```

### Singleton Pattern

```python
# Recommended for production: single generator per process
generator = TimeshardGenerator.get_instance(node_id=1)

# Subsequent calls return same instance
same_gen = TimeshardGenerator.get_instance()
assert generator is same_gen
```

---

## Real-World Use Cases

### 1. Multi-Tenant Trading System

```python
class TradeService:
    def __init__(self):
        self.generator = TimeshardGenerator.get_instance()
    
    def create_trade(self, symbol: str, quantity: int):
        trade_id = self.generator.next_id_with_prefix("TRD_")
        # Store in DB with time-ordered index
        return {
            "id": trade_id,
            "symbol": symbol,
            "quantity": quantity,
            "created_at": self.generator.parse_id(
                int(trade_id.split("_")[1])
            )['datetime']
        }
```

### 2. Event Sourcing with Prefixed Events

```python
# Different event types with clear semantic meaning
user_event = generator.next_id_with_prefix("EVT_USER_")
payment_event = generator.next_id_with_prefix("EVT_PAY_")
audit_event = generator.next_id_with_prefix("EVT_AUD_")

# Query events by type efficiently
db.query("SELECT * FROM events WHERE id LIKE 'EVT_PAY_%' ORDER BY id")
```

### 3. Distributed Order Book

```python
# Each order service worker has unique node_id
# Order IDs are globally unique AND time-ordered
class OrderService:
    def __init__(self, node_id: int):
        self.generator = TimeshardGenerator(node_id=node_id)
    
    def place_order(self, user_id: str, symbol: str, price: float):
        order_id = self.generator.next_id_with_prefix("ORD_")
        # Orders naturally sort by creation time
        return order_id
```

### 4. Audit Trail & Forensics

```python
def investigate_transaction(txn_id: str):
    """Extract metadata from ID without database lookup"""
    numeric_id = int(txn_id.replace("TXN_", ""))
    metadata = generator.parse_id(numeric_id)
    
    print(f"Transaction occurred at: {metadata['datetime']}")
    print(f"Processed by node: {metadata['node_id']}")
    print(f"Sequence in millisecond: {metadata['sequence']}")
```

---

## Configuration Deep Dive

### Environment Variables

```bash
# Node ID bits (1-16, default: 10)
export TIMESHARD_NODE_ID_BITS=10

# Explicit node ID (auto-detected from IP if not set)
export TIMESHARD_NODE_ID=42

# Custom epoch in milliseconds (default: 2023-12-12)
export TIMESHARD_CUSTOM_EPOCH=1702385533000
```

### Auto Node ID Detection

If `TIMESHARD_NODE_ID` is not set, Timeshard derives it from the machine's IP:

```python
# For IP 192.168.1.42:
# Takes last 2 octets: (1 << 8) | 42 = 298
# Masks to fit in configured bits: 298 & 1023 = 298
```

**Perfect for**:
- Kubernetes pods (each gets unique IP)
- Docker containers (auto-assigned IPs)
- Cloud deployments (instance IPs)

### Bit Allocation Decision Tree

```
Need > 1000 workers?
├─ Yes → Use 12 bits (4,096 nodes, 1K IDs/ms each)
└─ No
    └─ Need > 10K IDs/ms per worker?
        ├─ Yes → Use 8 bits (256 nodes, 16K IDs/ms each)
        └─ No → Use 10 bits (1,024 nodes, 4K IDs/ms each) [DEFAULT]
```

---

## API Reference

### `TimeshardGenerator(node_id=None, custom_epoch=None)`

Create a new ID generator.

**Parameters**:
- `node_id` (int, optional): Worker ID. Auto-detected from IP if not provided.
- `custom_epoch` (int, optional): Epoch timestamp in milliseconds. Defaults to 2023-12-12.

**Raises**:
- `ValueError`: If node_id is outside valid range [0, max_node_id]
- `RuntimeError`: If configuration is invalid

### `next_id() -> int`

Generate a unique 64-bit integer ID.

**Returns**: int (guaranteed unique, monotonically increasing)

**Raises**: `RuntimeError` if system clock moves backwards

### `next_id_with_prefix(prefix: str) -> str`

Generate ID with string prefix.

```python
generator.next_id_with_prefix("ORDER")  # "ORDER1730678523123456789"
```

### `next_id_with_prefix_at(prefix: str, position: int) -> str`

Insert prefix at specific position in ID string.

```python
generator.next_id_with_prefix_at("XXX", 4)  # "1730XXX678523123456789"
```

### `parse_id(id_value: int) -> dict`

Decompose ID into components.

**Returns**:
```python
{
    'id': 1730678523123456789,
    'timestamp': 1730678523123,
    'timestamp_offset': 28293990123,
    'node_id': 1,
    'sequence': 789,
    'datetime': '2024-11-03 18:42:03.123'
}
```

### `get_config_info() -> str`

Returns human-readable configuration summary.

### `get_instance(node_id=None, custom_epoch=None) -> TimeshardGenerator`

Get singleton instance (thread-safe).

---

## Design Tradeoffs

### What You Gain

1. **Operational Flexibility**: Change node/sequence bits without recompiling
2. **Human Readability**: IDs have semantic meaning (`TRD_`, `ORD_`, etc.)
3. **Debuggability**: Parse timestamp/node/sequence from any ID
4. **Python Integration**: Designed for Python's threading and deployment patterns

### What You Pay

1. **~20% overhead** for prefix operations vs raw integer generation
2. **Runtime overhead** for bit mask calculations (vs compile-time constants)
3. **String allocation** when using prefixes (vs pure integers)

### When to Use Timeshard

✅ **Use when**:
- IDs need to be human-readable for ops/debugging
- You need runtime configurability (cloud deployments)
- Database queries benefit from prefixed IDs
- Python is your primary language

❌ **Don't use when**:
- Absolute maximum throughput is critical (use pure Snowflake)
- IDs must be pure integers (no string support)
- System is written in Go/Rust (use native implementations)

---

## Thread Safety

Timeshard is fully thread-safe with fine-grained locking:

```python
from concurrent.futures import ThreadPoolExecutor

generator = TimeshardGenerator(node_id=1)

# Generate from multiple threads safely
with ThreadPoolExecutor(max_workers=10) as executor:
    ids = list(executor.map(lambda _: generator.next_id(), range(100000)))

assert len(set(ids)) == 100000  # All unique
```

**Implementation**: Per-generator lock only during ID generation (~0.3µs critical section).

---

## Production Deployment

### Kubernetes

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: order-service
spec:
  replicas: 10
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
      - TIMESHARD_NODE_ID=1
  order-service-2:
    environment:
      - TIMESHARD_NODE_ID=2
  order-service-3:
    environment:
      - TIMESHARD_NODE_ID=3
```

### Important: Clock Synchronization

Timeshard relies on monotonic timestamps. **Use NTP**:

```bash
# Ubuntu/Debian
sudo apt install ntp
sudo systemctl enable ntp

# Monitor clock drift
ntpq -p
```

**Clock Skew Handling**: If clock moves backwards, Timeshard **refuses** to generate IDs to prevent duplicates.

---

## Testing

```bash
# Run test suite
pytest test_generator.py -v

# Run benchmarks
python benchmark.py

# Run examples
python example.py
```

### Key Test Scenarios

- ✅ Uniqueness: 100K IDs, all unique
- ✅ Monotonic ordering: IDs increase over time
- ✅ Thread safety: 10 threads × 10K IDs each
- ✅ Multi-node: No collisions between different node_ids
- ✅ Sequence exhaustion: Waits for next millisecond
- ✅ Clock skew detection: Errors on backwards time

---

## Implementation Notes

### Why Python?

Most Snowflake implementations are in Go/Java. Python version exists because:
- Modern web services use Python (FastAPI, Flask, Django)
- Data pipelines use Python (Airflow, Dagster)
- Trading systems increasingly use Python (QuantLib, backtrader)

### Performance Considerations

1. **GIL Impact**: Limited in practice—lock contention is the bottleneck, not CPU
2. **String overhead**: Only paid when using prefix methods
3. **Integer performance**: Raw `next_id()` is within 2x of C implementations

### Why Not Use UUID?

| Feature | Timeshard | UUID v4 | UUID v7 |
|---------|-----------|---------|---------|
| Size | 64-bit | 128-bit | 128-bit |
| Ordered | ✅ Yes | ❌ No | ✅ Yes |
| Collision-free | ✅ Yes (with unique node_id) | ~Yes (random) | ~Yes (random) |
| Prefix support | ✅ Built-in | ❌ Manual | ❌ Manual |
| Parseable | ✅ Yes | ❌ No | ✅ Partial |
| Database index | ✅ Efficient | ❌ Poor | ✅ Good |

---

## Contributing

This project was built to explore distributed ID generation patterns. Contributions welcome:

1. Fork the repo
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

---

## Acknowledgments

Inspired by:
- [Twitter Snowflake](https://github.com/twitter-archive/snowflake)
- [Instagram's Sharding IDs](https://instagram-engineering.com/sharding-ids-at-instagram-1cf5a71e5a5c)
- [Discord's Snowflake](https://discord.com/developers/docs/reference#snowflakes)

Built as an exploration of operational flexibility vs performance tradeoffs in distributed systems.

---

## License

MIT License - see LICENSE file for details