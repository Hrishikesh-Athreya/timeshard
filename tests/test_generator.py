"""Tests for Timeshard ID generator."""
import os
import threading
import time
import pytest

from timeshard.generator import TimeshardGenerator


class TestTimeshardGenerator:
    """Tests for TimeshardGenerator."""

    def test_generate_unique_ids(self):
        """Test that IDs are unique."""
        generator = TimeshardGenerator(node_id=1)
        ids = {generator.next_id() for _ in range(10000)}
        assert len(ids) == 10000, "All IDs should be unique"

    def test_ids_are_monotonic(self):
        """Test that IDs increase monotonically."""
        generator = TimeshardGenerator(node_id=1)
        ids = [generator.next_id() for _ in range(1000)]
        assert ids == sorted(ids), "IDs should be monotonically increasing"

    def test_thread_safety(self):
        """Test generator is thread-safe."""
        generator = TimeshardGenerator(node_id=1)
        ids = []
        lock = threading.Lock()

        def generate_ids(count):
            for _ in range(count):
                id_val = generator.next_id()
                with lock:
                    ids.append(id_val)

        threads = [
            threading.Thread(target=generate_ids, args=(1000,))
            for _ in range(10)
        ]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(ids) == 10000
        assert len(set(ids)) == 10000, "All IDs across threads should be unique"

    def test_parse_id(self):
        """Test parsing ID back into components."""
        generator = TimeshardGenerator(node_id=42)
        id_value = generator.next_id()

        parsed = generator.parse_id(id_value)

        assert parsed['node_id'] == 42
        assert parsed['sequence'] >= 0
        assert parsed['timestamp'] > generator.custom_epoch
        assert 'datetime' in parsed

    def test_multiple_ids_same_millisecond(self):
        """Test generating multiple IDs in same millisecond."""
        generator = TimeshardGenerator(node_id=1)

        # Generate rapidly
        ids = [generator.next_id() for _ in range(100)]

        # Parse and check sequences
        parsed_ids = [generator.parse_id(id_val) for id_val in ids]

        # Should have some with same timestamp but different sequences
        timestamps = [p['timestamp_offset'] for p in parsed_ids]
        assert len(set(timestamps)) < len(timestamps), "Should have multiple IDs per millisecond"

    def test_different_nodes_different_ids(self):
        """Test different node IDs produce different IDs."""
        gen1 = TimeshardGenerator(node_id=1)
        gen2 = TimeshardGenerator(node_id=2)

        id1 = gen1.next_id()
        id2 = gen2.next_id()

        assert id1 != id2

        parsed1 = gen1.parse_id(id1)
        parsed2 = gen2.parse_id(id2)

        assert parsed1['node_id'] == 1
        assert parsed2['node_id'] == 2

    def test_invalid_node_id(self):
        """Test that invalid node ID raises error."""
        with pytest.raises(ValueError, match="Node ID must be between"):
            TimeshardGenerator(node_id=-1)

        with pytest.raises(ValueError, match="Node ID must be between"):
            TimeshardGenerator(node_id=1024)  # Max is 1023 for 10 bits

    def test_prefix_support(self):
        """Test ID generation with prefix."""
        generator = TimeshardGenerator(node_id=1)

        id_with_prefix = generator.next_id_with_prefix("TXN")
        assert id_with_prefix.startswith("TXN")

        # Extract numeric part and verify it's valid
        numeric_part = id_with_prefix[3:]
        assert numeric_part.isdigit()

    def test_prefix_at_position(self):
        """Test prefix insertion at specific position."""
        generator = TimeshardGenerator(node_id=1)

        id_with_prefix = generator.next_id_with_prefix_at("XXX", 4)
        assert id_with_prefix[4:7] == "XXX"

    def test_prefix_at_invalid_position(self):
        """Test that invalid position raises error."""
        generator = TimeshardGenerator(node_id=1)

        with pytest.raises(ValueError, match="out of range"):
            generator.next_id_with_prefix_at("XXX", 1000)

    def test_singleton_pattern(self):
        """Test singleton instance."""
        instance1 = TimeshardGenerator.get_instance(node_id=5)
        instance2 = TimeshardGenerator.get_instance(node_id=10)  # Should be ignored

        assert instance1 is instance2
        assert instance1.node_id == 5  # First call's node_id is used

    def test_config_info(self):
        """Test configuration info string."""
        generator = TimeshardGenerator(node_id=1)
        info = generator.get_config_info()

        assert "41-10-12" in info
        assert "Node ID" in info
        assert "Sequence" in info


class TestEnvironmentConfiguration:
    """Tests for environment-based configuration."""

    def test_node_id_from_env(self, monkeypatch):
        """Test reading node ID from environment."""
        monkeypatch.setenv('TIMESHARD_NODE_ID', '123')
        generator = TimeshardGenerator()
        assert generator.node_id == 123

    def test_node_id_bits_from_env(self, monkeypatch):
        """Test configuring node ID bits from environment."""
        monkeypatch.setenv('TIMESHARD_NODE_ID_BITS', '12')
        generator = TimeshardGenerator(node_id=1)

        assert generator.node_id_bits == 12
        assert generator.sequence_bits == 10  # 64 - 41 - 12 - 1
        assert generator.max_node_id == 4095  # 2^12 - 1

    def test_custom_epoch_from_env(self, monkeypatch):
        """Test custom epoch from environment."""
        custom_epoch = 1700000000000
        monkeypatch.setenv('TIMESHARD_CUSTOM_EPOCH', str(custom_epoch))

        generator = TimeshardGenerator(node_id=1)
        assert generator.custom_epoch == custom_epoch

    def test_invalid_node_id_bits(self, monkeypatch):
        """Test that invalid NODE_ID_BITS raises error."""
        monkeypatch.setenv('TIMESHARD_NODE_ID_BITS', '20')  # Too large

        with pytest.raises(RuntimeError, match="must be <= 16"):
            TimeshardGenerator(node_id=1)

    def test_invalid_env_values(self, monkeypatch):
        """Test that non-numeric env values raise errors."""
        monkeypatch.setenv('TIMESHARD_NODE_ID', 'invalid')

        with pytest.raises(RuntimeError, match="must be an integer"):
            TimeshardGenerator()


class TestAutoNodeIdGeneration:
    """Tests for automatic node ID generation from IP."""

    def test_auto_generate_node_id(self):
        """Test that node ID is auto-generated from IP."""
        generator = TimeshardGenerator()

        # Should have generated some node ID
        assert 0 <= generator.node_id <= generator.max_node_id

    def test_auto_node_id_is_consistent(self):
        """Test that auto-generated node ID is consistent."""
        gen1 = TimeshardGenerator()
        gen2 = TimeshardGenerator()

        # Both should generate same node ID on same machine
        assert gen1.node_id == gen2.node_id


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_sequence_exhaustion(self):
        """Test behavior when sequence is exhausted in one millisecond."""
        generator = TimeshardGenerator(node_id=1)

        # Generate more IDs than sequence allows
        # With 12 bits, max is 4095 per ms
        # This should automatically wait for next ms
        ids = [generator.next_id() for _ in range(5000)]

        assert len(set(ids)) == 5000, "All IDs should still be unique"

    def test_high_throughput(self):
        """Test sustained high-throughput generation."""
        generator = TimeshardGenerator(node_id=1)

        start = time.time()
        ids = [generator.next_id() for _ in range(50000)]
        duration = time.time() - start

        assert len(set(ids)) == 50000
        throughput = 50000 / duration

        # Should handle at least 10K IDs/sec
        assert throughput > 10000, f"Throughput too low: {throughput:.0f} IDs/sec"