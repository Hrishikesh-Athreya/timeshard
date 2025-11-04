"""
Distributed  ID Generator.

Inspired by Twitter Snowflake implementation.
This should be used as a singleton - create one instance per process/node.
"""
import os
import socket
import threading
import time
from typing import Dict, Optional


class TimeshardGenerator:
    """
    Thread-safe  ID generator with auto-configuration.

    ID Structure (64 bits):
    - 1 bit: unused (sign bit, always 0)
    - 41 bits: timestamp (milliseconds since custom epoch)
    - configurable bits: node/worker ID (from environment, default 10)
    - remaining bits: sequence number

    Environment Variables:
        TIMESHARD_NODE_ID_BITS: Number of bits for node ID (default: 10, max: 16)
        TIMESHARD_NODE_ID: Override auto-generated node ID
        TIMESHARD_CUSTOM_EPOCH: Custom epoch in milliseconds (default: 2023-12-12)

    Example:
        # Auto-configure from environment
        generator = Generator()

        # Or specify node ID manually
        generator = Generator(node_id=42)

        # Generate IDs
        id1 = generator.next_id()
        id2 = generator.next_id_with_prefix("TXN")
    """

    # Constants
    UNUSED_BITS = 1
    EPOCH_BITS = 41
    DEFAULT_CUSTOM_EPOCH = 1702385533000  # 2023-12-12 00:00:00 UTC

    # Singleton instance
    _instance = None
    _lock = threading.Lock()

    def __init__(self, node_id: Optional[int] = None, custom_epoch: Optional[int] = None):
        """
        Initialize ID generator.

        Args:
            node_id: Node/worker ID. If None, auto-generated from IP or ENV
            custom_epoch: Custom epoch in milliseconds. If None, uses default or ENV

        Raises:
            ValueError: If node_id is out of valid range
            RuntimeError: If NODE_ID_BITS configuration is invalid
        """
        # Get NODE_ID_BITS from environment
        self.node_id_bits = self._get_node_id_bits_from_env()

        # Calculate sequence bits
        self.sequence_bits = 64 - self.EPOCH_BITS - self.node_id_bits - self.UNUSED_BITS

        # Calculate max values
        self.max_node_id = (1 << self.node_id_bits) - 1
        self.max_sequence = (1 << self.sequence_bits) - 1

        # Get custom epoch
        self.custom_epoch = custom_epoch or self._get_custom_epoch_from_env()

        # Get or generate node ID
        if node_id is not None:
            self.node_id = node_id
        else:
            self.node_id = self._get_node_id_from_env() or self._generate_node_id()

        # Validate node ID
        if not 0 <= self.node_id <= self.max_node_id:
            raise ValueError(
                f"Node ID must be between 0 and {self.max_node_id}, got {self.node_id}"
            )

        # State for ID generation
        self._last_timestamp = -1
        self._sequence = 0
        self._gen_lock = threading.Lock()

    @classmethod
    def get_instance(cls, node_id: Optional[int] = None, custom_epoch: Optional[int] = None):
        """
        Get singleton instance (thread-safe).

        Args:
            node_id: Node ID (only used on first call)
            custom_epoch: Custom epoch (only used on first call)

        Returns:
            Singleton TimeshardGenerator instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(node_id=node_id, custom_epoch=custom_epoch)
        return cls._instance

    def next_id(self) -> int:
        """
        Generate next unique ID.

        Returns:
            Unique 64-bit integer ID

        Raises:
            RuntimeError: If system clock moves backwards
        """
        with self._gen_lock:
            current_timestamp = self._timestamp()

            # Check for clock moving backwards
            if current_timestamp < self._last_timestamp:
                raise RuntimeError(
                    f"Clock moved backwards. Refusing to generate ID. "
                    f"Last timestamp: {self._last_timestamp}, Current: {current_timestamp}"
                )

            # Same millisecond - increment sequence
            if current_timestamp == self._last_timestamp:
                self._sequence = (self._sequence + 1) & self.max_sequence

                # Sequence exhausted - wait for next millisecond
                if self._sequence == 0:
                    current_timestamp = self._wait_next_millis(current_timestamp)
            else:
                # New millisecond - reset sequence
                self._sequence = 0

            self._last_timestamp = current_timestamp

            # Construct ID: timestamp | node_id | sequence
            id_value = (
                    (current_timestamp << (self.node_id_bits + self.sequence_bits)) |
                    (self.node_id << self.sequence_bits) |
                    self._sequence
            )

            return id_value

    def next_id_with_prefix(self, prefix: str) -> str:
        """
        Generate ID with string prefix.

        Args:
            prefix: String prefix to prepend

        Returns:
            String like "TXN123456789"

        Example:
            generator.next_id_with_prefix("ORDER")  # "ORDER987654321"
        """
        return f"{prefix}{self.next_id()}"

    def next_id_with_prefix_at(self, prefix: str, position: int) -> str:
        """
        Generate ID with prefix inserted at specific position.

        Args:
            prefix: String to insert
            position: Position in the ID string to insert prefix

        Returns:
            String with prefix inserted at position

        Raises:
            ValueError: If position is invalid

        Example:
            generator.next_id_with_prefix_at("XXX", 4)  # "1234XXX567890"
        """
        id_str = str(self.next_id())

        if position < 0 or position > len(id_str):
            raise ValueError(
                f"Position {position} is out of range for ID length {len(id_str)}"
            )

        return id_str[:position] + prefix + id_str[position:]

    def parse_id(self, id_value: int) -> Dict[str, any]:
        """
        Parse ID back into components.

        Args:
            id_value: ID to parse

        Returns:
            Dictionary with timestamp, node_id, sequence, and datetime
        """
        # Extract sequence
        sequence = id_value & self.max_sequence

        # Extract node_id
        node_mask = (1 << self.node_id_bits) - 1
        node_id = (id_value >> self.sequence_bits) & node_mask

        # Extract timestamp
        timestamp_offset = id_value >> (self.node_id_bits + self.sequence_bits)
        timestamp_ms = timestamp_offset + self.custom_epoch

        return {
            'id': id_value,
            'timestamp': timestamp_ms,
            'timestamp_offset': timestamp_offset,
            'node_id': node_id,
            'sequence': sequence,
            'datetime': time.strftime(
                '%Y-%m-%d %H:%M:%S.%f',
                time.gmtime(timestamp_ms / 1000)
            )[:-3]  # Trim to milliseconds
        }

    def get_config_info(self) -> str:
        """
        Get human-readable configuration information.

        Returns:
            Formatted configuration string
        """
        max_timestamp = (1 << self.EPOCH_BITS) - 1
        years = (max_timestamp / 1000) / (365.25 * 24 * 60 * 60)

        return f"""Timeshard Generator Configuration:
  Bit Allocation: {self.EPOCH_BITS}-{self.node_id_bits}-{self.sequence_bits} (total: {self.EPOCH_BITS + self.node_id_bits + self.sequence_bits})

  Timestamp:
    - Bits: {self.EPOCH_BITS}
    - Range: ~{years:.1f} years from epoch
    - Custom Epoch: {self.custom_epoch} ({self._format_epoch()})

  Node ID:
    - Bits: {self.node_id_bits}
    - Max Nodes: {self.max_node_id + 1:,}
    - Current Node: {self.node_id}

  Sequence:
    - Bits: {self.sequence_bits}
    - IDs per ms: {self.max_sequence + 1:,}
    - Throughput: {(self.max_node_id + 1) * (self.max_sequence + 1):,} IDs/ms globally
"""

    def _timestamp(self) -> int:
        """Get current timestamp offset from custom epoch."""
        return int(time.time() * 1000) - self.custom_epoch

    def _wait_next_millis(self, last_timestamp: int) -> int:
        """Spin-wait until next millisecond."""
        timestamp = self._timestamp()
        while timestamp <= last_timestamp:
            timestamp = self._timestamp()
        return timestamp

    def _get_node_id_bits_from_env(self) -> int:
        """Get NODE_ID_BITS from environment variable."""
        try:
            node_id_bits = int(os.getenv('TIMESHARD_NODE_ID_BITS', '10'))
        except ValueError:
            raise RuntimeError(
                "TIMESHARD_NODE_ID_BITS environment variable must be an integer"
            )

        if node_id_bits > 16:
            raise RuntimeError(
                f"TIMESHARD_NODE_ID_BITS must be <= 16, got {node_id_bits}"
            )

        if node_id_bits < 1:
            raise RuntimeError(
                f"TIMESHARD_NODE_ID_BITS must be >= 1, got {node_id_bits}"
            )

        return node_id_bits

    def _get_node_id_from_env(self) -> Optional[int]:
        """Get explicit node ID from environment variable."""
        node_id_str = os.getenv('TIMESHARD_NODE_ID')
        if node_id_str is None:
            return None

        try:
            return int(node_id_str)
        except ValueError:
            raise RuntimeError(
                f"TIMESHARD_NODE_ID environment variable must be an integer, got '{node_id_str}'"
            )

    def _get_custom_epoch_from_env(self) -> int:
        """Get custom epoch from environment variable."""
        epoch_str = os.getenv('TIMESHARD_CUSTOM_EPOCH')
        if epoch_str is None:
            return self.DEFAULT_CUSTOM_EPOCH

        try:
            return int(epoch_str)
        except ValueError:
            raise RuntimeError(
                f"TIMESHARD_CUSTOM_EPOCH must be an integer, got '{epoch_str}'"
            )

    def _generate_node_id(self) -> int:
        """
        Auto-generate node ID from machine's IP address.

        Uses last 2 octets of IP address to generate a semi-unique node ID.
        This works well in Kubernetes/Docker environments where each pod gets a unique IP.

        Returns:
            Node ID derived from IP address
        """
        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            octets = [int(x) for x in ip_address.split('.')]

            # Combine last 2 octets: 192.168.1.42 -> (1 << 8) | 42 = 298
            ip_bits = (octets[2] << 8) | octets[3]

            # Mask to fit in node_id_bits
            node_id = ip_bits & self.max_node_id

            return node_id
        except Exception as e:
            # Fallback to 0 if IP detection fails
            import warnings
            warnings.warn(
                f"Failed to auto-generate node ID from IP: {e}. Using node_id=0. "
                f"Consider setting TIMESHARD_NODE_ID environment variable.",
                RuntimeWarning
            )
            return 0

    def _format_epoch(self) -> str:
        """Format custom epoch as human-readable date."""
        return time.strftime(
            '%Y-%m-%d %H:%M:%S UTC',
            time.gmtime(self.custom_epoch / 1000)
        )

    def __repr__(self) -> str:
        return (
            f"TimeshardGenerator(epoch_bits={self.EPOCH_BITS}, "
            f"node_id_bits={self.node_id_bits}, "
            f"sequence_bits={self.sequence_bits}, "
            f"custom_epoch={self.custom_epoch}, "
            f"node_id={self.node_id})"
        )