"""The local fallback subject_digest must equal cns.gate.subject_digest.

A verdict bound without CNS has to verify with CNS, so the fallback in
cns_integration is held to the CNS answer key (contracts/digest-vectors.json
in the CNS repository). Nothing is vendored here. The inline vectors below
always run and carry the digests from that file; when CNS is installed the
fallback is also compared with cns.gate itself, with the vectors file when it
can be found, and with cns_composition.fallback_parity.

The fallback is loaded from source with `cns` made unimportable, so the code
that runs when CNS is absent is the code under test even when CNS is present.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "composition_engine" / "cns_integration.py"


@pytest.fixture(scope="module")
def fallback():
    saved = {k: sys.modules.get(k) for k in ("cns", "cns.gate")}
    sys.modules["cns"] = None  # makes `from cns.gate import ...` raise ImportError
    sys.modules["cns.gate"] = None
    try:
        spec = importlib.util.spec_from_file_location("_fallback_probe", SRC)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    assert mod.HAS_CNS is False
    return mod.subject_digest


# (name, content, digest from CNS contracts/digest-vectors.json)
VECTORS = (
    ("empty", {}, "c348e1722fbda6fbdd0ce8ec7831067eeff989c54b833673b8ebf6890883f012"),
    ("one_int", {"a": 1}, "32a98aef7315bc917ac0b650017f846e82bab90385cfe71b6fb53313ddf0006a"),
    ("bool_is_not_one", {"v": True, "w": 1},
     "525e4bb8f6ca1c3131980e369c25797ee4ba7f596b47e68471cad15e3d5d2aee"),
    ("separator_collision_left", {"ab": "c"},
     "9c91082e6a9ec1dc9b26d6e16a13cf8e3786769e441760af4ddb93be4818670b"),
    ("separator_collision_right", {"a": "bc"},
     "e4be55f20a1f111137a912fb3434b422b392060a6fec2111830f179da02765a1"),
    ("keys_sort_by_code_point", {"b": 1, "B": 2, "a": 3, "A": 4, "_": 5, "é": 6, "z": 7, "É": 8},
     "bbf67385935d6d25443b1b3752c5ac50ac16d0fd121d60f708f5b1a9f8816bbf"),
    ("length_counts_code_points_not_bytes", {"s": "café ✓ \U0001f642"},
     "b1436e6d2c4c8b8ac453885da0ada4fe58a9ede9640f9f79fab7f6bae699719b"),
    ("float_one_is_not_int_one", {"i": 1, "f": 1.0},
     "cd25f1bc921dc98bd2028b2205f7a13a0a3e68110d5027b0890bc4250779febc"),
    ("negative_zero", {"z": -0.0}, "893c683e0df0e4b902f166af65e70080691630f7ebd75b1fcb9c4998548b9b87"),
    ("positive_zero", {"z": 0.0}, "893c683e0df0e4b902f166af65e70080691630f7ebd75b1fcb9c4998548b9b87"),
    ("float_exponents", {"a": 1e-07, "b": 1e22, "c": 1.5e300, "d": 5e-324, "e": 1.7976931348623157e308},
     "9d83d02a537fc0355339432fca0136c4a05329096d31e2012817831598e46e1d"),
    ("ints_past_64_bits",
     {"a": 9223372036854775808, "b": 18446744073709551616, "c": -123456789012345678901234567890},
     "6c630763356972faf026213d9a2f4bdc4b2c8400163a252699d2f7bbde8964c0"),
    ("nested", {"x": [1, 2, {"y": [True, None, "z"]}], "w": {"v": {"u": []}}},
     "61567fcfc252385f02c87806eb3f58eabb56312e798a099794a7acc012c01937"),
)


@pytest.mark.parametrize("name,content,digest", VECTORS, ids=[v[0] for v in VECTORS])
def test_inline_vector(fallback, name, content, digest):
    assert fallback(content) == digest


def test_key_order_does_not_matter(fallback):
    assert fallback({"b": 1, "a": 2}) == fallback({"a": 2, "b": 1}) == (
        "acd0be1d57187dae28a701535f4d6ac035f647d79281337902d0c55d60d5738a"
    )


def test_tuple_digests_as_list(fallback):
    assert fallback({"x": (1, 2)}) == fallback({"x": [1, 2]})


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_refuses_nan_and_infinities(fallback, bad):
    with pytest.raises(TypeError):
        fallback({"x": bad})


def test_refuses_bytes_and_unknown_types(fallback):
    with pytest.raises(TypeError):
        fallback({"x": b"raw"})
    with pytest.raises(TypeError):
        fallback({"x": object()})


def test_refuses_keys_that_collide_once_stringified(fallback):
    with pytest.raises(TypeError):
        fallback({1: "a", "1": "b"})


def _cns():
    try:
        from cns.gate import subject_digest
    except ImportError:
        return None
    return subject_digest


def _vectors_file():
    here = Path(__file__).resolve().parents[2]
    for cand in (os.environ.get("CNS_DIGEST_VECTORS"), here / "CNS" / "contracts" / "digest-vectors.json"):
        if cand and Path(cand).is_file():
            return Path(cand)
    return None


def test_matches_cns_on_inline_vectors_when_cns_is_installed(fallback):
    cns = _cns()
    if cns is None:
        return  # CNS absent: the inline vectors above are the proof
    for name, content, _ in VECTORS:
        assert fallback(content) == cns(content), name


def test_matches_every_published_vector_when_cns_and_the_file_are_present(fallback):
    if _cns() is None or _vectors_file() is None:
        return  # nothing to compare against here; the inline vectors still ran
    vectors = json.loads(_vectors_file().read_text(encoding="utf-8"))["vectors"]
    assert len(vectors) >= 24
    wrong = [v["name"] for v in vectors if fallback(v["content"]) != v["digest"]]
    assert wrong == []


def test_fallback_parity_agrees_when_cns_composition_is_installed(fallback):
    try:
        from cns_composition.fallback_parity import digest_parity
    except ImportError:
        return  # CNS absent: nothing to measure against
    result = digest_parity("composition-engine", fallback)
    assert result.ok, result.differing
