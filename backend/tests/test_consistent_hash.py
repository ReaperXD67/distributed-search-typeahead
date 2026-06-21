from app.services.consistent_hash import ConsistentHashRing


def test_mapping_is_deterministic() -> None:
    first = ConsistentHashRing(["a", "b", "c"], virtual_nodes=64)
    second = ConsistentHashRing(["a", "b", "c"], virtual_nodes=64)
    keys = [f"prefix:{index}" for index in range(1_000)]
    assert [first.get_node(key) for key in keys] == [second.get_node(key) for key in keys]


def test_distribution_is_balanced() -> None:
    ring = ConsistentHashRing(["a", "b", "c"], virtual_nodes=256)
    distribution = ring.distribution([f"prefix:{index}" for index in range(10_000)])
    assert all(2_500 < count < 4_200 for count in distribution.values())


def test_adding_node_moves_only_a_fraction_of_keys() -> None:
    ring = ConsistentHashRing(["a", "b", "c"], virtual_nodes=256)
    keys = [f"prefix:{index}" for index in range(10_000)]
    before = {key: ring.get_node(key) for key in keys}
    ring.add_node("d")
    moved = sum(before[key] != ring.get_node(key) for key in keys) / len(keys)
    assert 0.15 < moved < 0.35


def test_clockwise_failover_lists_every_node_once() -> None:
    ring = ConsistentHashRing(["a", "b", "c"], virtual_nodes=32)
    assert sorted(ring.get_nodes("iphone")) == ["a", "b", "c"]
