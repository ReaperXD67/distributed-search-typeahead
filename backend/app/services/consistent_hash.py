from __future__ import annotations

import bisect
import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class RingPoint:
    value: int
    node: str


class ConsistentHashRing:
    """A deterministic hash ring with virtual nodes and clockwise failover."""

    def __init__(self, nodes: list[str], virtual_nodes: int = 128) -> None:
        if not nodes:
            raise ValueError("At least one cache node is required")
        if virtual_nodes < 1:
            raise ValueError("virtual_nodes must be positive")
        self.virtual_nodes = virtual_nodes
        self._nodes = list(dict.fromkeys(nodes))
        self._points: list[RingPoint] = []
        self._values: list[int] = []
        self._rebuild()

    @staticmethod
    def _hash(value: str) -> int:
        digest = hashlib.sha256(value.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], byteorder="big", signed=False)

    @property
    def nodes(self) -> tuple[str, ...]:
        return tuple(self._nodes)

    def _rebuild(self) -> None:
        self._points = sorted(
            (
                RingPoint(self._hash(f"{node}:vn:{index}"), node)
                for node in self._nodes
                for index in range(self.virtual_nodes)
            ),
            key=lambda point: point.value,
        )
        self._values = [point.value for point in self._points]

    def add_node(self, node: str) -> None:
        if node not in self._nodes:
            self._nodes.append(node)
            self._rebuild()

    def remove_node(self, node: str) -> None:
        if node not in self._nodes:
            return
        if len(self._nodes) == 1:
            raise ValueError("Cannot remove the final cache node")
        self._nodes.remove(node)
        self._rebuild()

    def get_node(self, key: str) -> str:
        return self.get_nodes(key)[0]

    def get_nodes(self, key: str) -> list[str]:
        """Return each physical node once, clockwise from the key's ring position."""
        position = bisect.bisect_left(self._values, self._hash(key))
        ordered: list[str] = []
        for offset in range(len(self._points)):
            point = self._points[(position + offset) % len(self._points)]
            if point.node not in ordered:
                ordered.append(point.node)
                if len(ordered) == len(self._nodes):
                    break
        return ordered

    def distribution(self, keys: list[str]) -> dict[str, int]:
        result = dict.fromkeys(self._nodes, 0)
        for key in keys:
            result[self.get_node(key)] += 1
        return result
