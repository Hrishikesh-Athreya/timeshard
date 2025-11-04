"""Example usage of Tmeshard ID Generator."""
import os
import time
from timeshard import TimeshardGenerator


def example_basic_usage():
    """Basic ID generation."""
    print("=" * 70)
    print("EXAMPLE 1: Basic Usage")
    print("=" * 70)

    # Create generator (auto-detects node ID from IP)
    generator = TimeshardGenerator()

    print(generator.get_config_info())

    print("\nGenerating 5 IDs:\n")
    for i in range(5):
        id_value = generator.next_id()
        parsed = generator.parse_id(id_value)
        print(f"  ID: {id_value}")
        print(f"    └─ Generated: {parsed['datetime']}")
        print(f"    └─ Node: {parsed['node_id']}, Sequence: {parsed['sequence']}")
        print()


def example_with_explicit_node_id():
    """Using explicit node ID."""
    print("=" * 70)
    print("EXAMPLE 2: Explicit Node ID")
    print("=" * 70)

    generator = TimeshardGenerator(node_id=42)

    print(f"Generator configured with node_id={generator.node_id}\n")

    id_value = generator.next_id()
    parsed = generator.parse_id(id_value)

    print(f"Generated ID: {id_value}")
    print(f"Node ID: {parsed['node_id']}")
    print()


def example_with_prefixes():
    """Using prefixes for human-readable IDs."""
    print("=" * 70)
    print("EXAMPLE 3: Prefixed IDs (Fintech Use Case)")
    print("=" * 70)

    generator = TimeshardGenerator(node_id=1)

    print("Transaction IDs:")
    for i in range(3):
        txn_id = generator.next_id_with_prefix("TXN_")
        print(f"  {txn_id}")

    print("\nPayment IDs:")
    for i in range(3):
        pmt_id = generator.next_id_with_prefix("PMT_")
        print(f"  {pmt_id}")

    print("\nOrder IDs:")
    for i in range(3):
        order_id = generator.next_id_with_prefix("ORD_")
        print(f"  {order_id}")

    print()


def example_environment_configuration():
    """Using environment variables for configuration."""
    print("=" * 70)
    print("EXAMPLE 4: Environment-Based Configuration")
    print("=" * 70)

    # Simulate environment variables
    os.environ['TIMESHARD_NODE_ID_BITS'] = '12'
    os.environ['TIMESHARD_NODE_ID'] = '500'

    generator = TimeshardGenerator()

    print("Configuration from environment:")
    print(f"  NODE_ID_BITS: {generator.node_id_bits}")
    print(f"  NODE_ID: {generator.node_id}")
    print(f"  SEQUENCE_BITS: {generator.sequence_bits}")
    print(f"  Max IDs per ms: {generator.max_sequence + 1:,}")
    print()

    # Clean up
    del os.environ['TIMESHARD_NODE_ID_BITS']
    del os.environ['TIMESHARD_NODE_ID']


def example_singleton_pattern():
    """Using singleton pattern."""
    print("=" * 70)
    print("EXAMPLE 5: Singleton Pattern (Recommended)")
    print("=" * 70)

    # Get singleton instance
    generator = TimeshardGenerator.get_instance(node_id=10)

    print(f"Singleton instance created with node_id={generator.node_id}")

    # Subsequent calls return same instance
    same_generator = TimeshardGenerator.get_instance()

    print(f"Same instance: {generator is same_generator}")
    print(f"Node ID unchanged: {same_generator.node_id}")
    print()


def example_parsing_ids():
    """Parsing IDs back into components."""
    print("=" * 70)
    print("EXAMPLE 6: Parsing IDs")
    print("=" * 70)

    generator = TimeshardGenerator(node_id=7)

    id_value = generator.next_id()
    parsed = generator.parse_id(id_value)

    print(f"ID: {id_value}\n")
    print("Parsed Components:")
    print(f"  Timestamp: {parsed['timestamp']} ms")
    print(f"  Datetime: {parsed['datetime']}")
    print(f"  Node ID: {parsed['node_id']}")
    print(f"  Sequence: {parsed['sequence']}")
    print()


def example_high_throughput():
    """Demonstrating high-throughput generation."""
    print("=" * 70)
    print("EXAMPLE 7: High-Throughput Generation")
    print("=" * 70)

    generator = TimeshardGenerator(node_id=1)

    print("Generating 100,000 IDs...\n")

    start = time.time()
    ids = [generator.next_id() for _ in range(100000)]
    duration = time.time() - start

    print(f"Generated: {len(ids):,} IDs")
    print(f"Duration: {duration:.3f} seconds")
    print(f"Throughput: {len(ids) / duration:,.0f} IDs/second")
    print(f"All unique: {len(set(ids)) == len(ids)}")

    # Check distribution across milliseconds
    parsed_ids = [generator.parse_id(id_val) for id_val in ids[:1000]]
    unique_timestamps = len(set(p['timestamp_offset'] for p in parsed_ids))

    print(f"\nFirst 1000 IDs spread across {unique_timestamps} milliseconds")
    print(f"Avg IDs per millisecond: {1000 / unique_timestamps:.0f}")
    print()


def example_deployment_scenarios():
    """Show different deployment scenarios."""
    print("=" * 70)
    print("EXAMPLE 8: Deployment Scenarios")
    print("=" * 70)

    scenarios = [
        {
            "name": "Standard Deployment (10 worker bits)",
            "node_bits": 10,
            "node_id": 42
        },
        {
            "name": "High-Scale Deployment (12 worker bits)",
            "node_bits": 12,
            "node_id": 1000
        },
        {
            "name": "High-Throughput (8 worker bits)",
            "node_bits": 8,
            "node_id": 50
        }
    ]

    for scenario in scenarios:
        os.environ['TIMESHARD_NODE_ID_BITS'] = str(scenario['node_bits'])
        generator = TimeshardGenerator(node_id=scenario['node_id'])

        print(f"\n{scenario['name']}:")
        print(f"  Node ID Bits: {generator.node_id_bits}")
        print(f"  Sequence Bits: {generator.sequence_bits}")
        print(f"  Max Workers: {generator.max_node_id + 1:,}")
        print(f"  IDs per ms per worker: {generator.max_sequence + 1:,}")
        print(f"  Global throughput: {(generator.max_node_id + 1) * (generator.max_sequence + 1):,} IDs/ms")

        del os.environ['TIMESHARD_NODE_ID_BITS']

    print()


if __name__ == "__main__":
    example_basic_usage()
    example_with_explicit_node_id()
    example_with_prefixes()
    example_environment_configuration()
    example_singleton_pattern()
    example_parsing_ids()
    example_high_throughput()
    example_deployment_scenarios()