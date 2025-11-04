"""Performance benchmarks for Timeshard ID Generator."""
import os
import time
import threading
from statistics import mean, median, stdev
from timeshard import TimeshardGenerator


def benchmark_single_threaded(count: int = 100000):
    """Benchmark single-threaded ID generation."""
    generator = TimeshardGenerator(node_id=1)

    print(f"\n{'=' * 70}")
    print(f"Single-Threaded Benchmark")
    print(f"{'=' * 70}")

    # Warmup
    for _ in range(1000):
        generator.next_id()

    # Actual benchmark
    start = time.perf_counter()
    ids = [generator.next_id() for _ in range(count)]
    end = time.perf_counter()

    duration = end - start
    ids_per_sec = count / duration
    avg_time_us = (duration / count) * 1_000_000

    print(f"Generated: {count:,} IDs")
    print(f"Duration: {duration:.4f} seconds")
    print(f"Throughput: {ids_per_sec:,.0f} IDs/second")
    print(f"Avg time per ID: {avg_time_us:.2f} µs")
    print(f"All unique: {len(set(ids)) == count}")


def benchmark_multi_threaded(num_threads: int = 10, ids_per_thread: int = 10000):
    """Benchmark multi-threaded ID generation."""
    generator = TimeshardGenerator(node_id=1)

    print(f"\n{'=' * 70}")
    print(f"Multi-Threaded Benchmark ({num_threads} threads)")
    print(f"{'=' * 70}")

    ids = []
    lock = threading.Lock()

    def generate_ids():
        thread_ids = [generator.next_id() for _ in range(ids_per_thread)]
        with lock:
            ids.extend(thread_ids)

    # Warmup
    for _ in range(1000):
        generator.next_id()

    # Actual benchmark
    start = time.perf_counter()

    threads = [threading.Thread(target=generate_ids) for _ in range(num_threads)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    end = time.perf_counter()

    total_ids = len(ids)
    duration = end - start
    ids_per_sec = total_ids / duration
    avg_time_us = (duration / total_ids) * 1_000_000

    print(f"Generated: {total_ids:,} IDs")
    print(f"Duration: {duration:.4f} seconds")
    print(f"Throughput: {ids_per_sec:,.0f} IDs/second")
    print(f"Avg time per ID: {avg_time_us:.2f} µs")
    print(f"All unique: {len(set(ids)) == total_ids}")


def benchmark_with_different_configs():
    """Benchmark different bit configurations."""
    print(f"\n{'=' * 70}")
    print(f"Configuration Comparison")
    print(f"{'=' * 70}\n")

    configs = [
        ("Standard (10 node bits)", 10, 100000),
        ("High-Scale (12 node bits)", 12, 100000),
        ("High-Throughput (8 node bits)", 8, 100000),
    ]

    print(f"{'Config':<30} {'Throughput':<20} {'Avg Time/ID':<15}")
    print("-" * 70)

    for name, node_bits, count in configs:
        os.environ['TIMESHARD_NODE_ID_BITS'] = str(node_bits)
        generator = TimeshardGenerator(node_id=1)

        # Warmup
        for _ in range(1000):
            generator.next_id()

        # Benchmark
        start = time.perf_counter()
        ids = [generator.next_id() for _ in range(count)]
        duration = time.perf_counter() - start

        throughput = count / duration
        avg_time = (duration / count) * 1_000_000

        print(f"{name:<30} {throughput:>15,.0f} IDs/s   {avg_time:>10.2f} µs")

        del os.environ['TIMESHARD_NODE_ID_BITS']


def benchmark_prefix_operations():
    """Benchmark prefix operations."""
    print(f"\n{'=' * 70}")
    print(f"Prefix Operations Benchmark")
    print(f"{'=' * 70}")

    generator = TimeshardGenerator(node_id=1)
    count = 50000

    # Standard ID generation
    start = time.perf_counter()
    for _ in range(count):
        generator.next_id()
    duration_standard = time.perf_counter() - start

    # With prefix
    start = time.perf_counter()
    for _ in range(count):
        generator.next_id_with_prefix("TXN")
    duration_prefix = time.perf_counter() - start

    # With prefix at position
    start = time.perf_counter()
    for _ in range(count):
        generator.next_id_with_prefix_at("XXX", 4)
    duration_prefix_at = time.perf_counter() - start

    print(f"\nOperations: {count:,} each")
    print(f"\nStandard ID:")
    print(f"  Duration: {duration_standard:.4f}s")
    print(f"  Throughput: {count / duration_standard:,.0f} IDs/s")

    print(f"\nWith Prefix:")
    print(f"  Duration: {duration_prefix:.4f}s")
    print(f"  Throughput: {count / duration_prefix:,.0f} IDs/s")
    print(f"  Overhead: {((duration_prefix / duration_standard - 1) * 100):.1f}%")

    print(f"\nWith Prefix at Position:")
    print(f"  Duration: {duration_prefix_at:.4f}s")
    print(f"  Throughput: {count / duration_prefix_at:,.0f} IDs/s")
    print(f"  Overhead: {((duration_prefix_at / duration_standard - 1) * 100):.1f}%")


def benchmark_latency_distribution():
    """Analyze latency distribution."""
    print(f"\n{'=' * 70}")
    print(f"Latency Distribution Analysis")
    print(f"{'=' * 70}")

    generator = TimeshardGenerator(node_id=1)
    count = 10000

    # Measure individual call latencies
    latencies = []
    for _ in range(count):
        start = time.perf_counter()
        generator.next_id()
        latencies.append((time.perf_counter() - start) * 1_000_000)  # microseconds

    latencies.sort()

    print(f"\nLatency Statistics ({count:,} samples):")
    print(f"  Mean: {mean(latencies):.2f} µs")
    print(f"  Median: {median(latencies):.2f} µs")
    print(f"  Std Dev: {stdev(latencies):.2f} µs")
    print(f"  Min: {min(latencies):.2f} µs")
    print(f"  Max: {max(latencies):.2f} µs")
    print(f"\nPercentiles:")
    print(f"  p50: {latencies[int(count * 0.50)]:.2f} µs")
    print(f"  p90: {latencies[int(count * 0.90)]:.2f} µs")
    print(f"  p95: {latencies[int(count * 0.95)]:.2f} µs")
    print(f"  p99: {latencies[int(count * 0.99)]:.2f} µs")
    print(f"  p99.9: {latencies[int(count * 0.999)]:.2f} µs")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" Timeshard ID Generator - Performance Benchmarks")
    print("=" * 70)

    benchmark_single_threaded(100000)
    benchmark_multi_threaded(10, 10000)
    benchmark_with_different_configs()
    benchmark_prefix_operations()
    benchmark_latency_distribution()

    print(f"\n{'=' * 70}\n")