from ecl_trainer.core.engine import SignalHasher


def test_signal_hasher_is_deterministic():
    hasher = SignalHasher()
    first = hasher.fingerprint(source_uri="s3://bucket/path/file.parquet", schema={"a": "int"})
    second = hasher.fingerprint(source_uri="s3://bucket/other/file.parquet", schema={"a": "int"})
    assert first.dataset_fingerprint == second.dataset_fingerprint
    assert first.source_root_hash_sha256 == second.source_root_hash_sha256
