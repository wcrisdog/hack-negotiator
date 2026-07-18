from app.services.canonicalize import canonical_json, confirm_job_spec, spec_hash


def test_confirm_job_spec_is_deterministic():
    spec = {"b": 2, "a": 1}
    cjson1, hash1 = confirm_job_spec(spec)
    cjson2, hash2 = confirm_job_spec(spec)
    assert cjson1 == cjson2
    assert hash1 == hash2


def test_key_order_does_not_change_hash():
    spec_a = {"a": 1, "b": 2}
    spec_b = {"b": 2, "a": 1}
    assert spec_hash(spec_a) == spec_hash(spec_b)


def test_different_specs_hash_differently():
    assert spec_hash({"a": 1}) != spec_hash({"a": 2})


def test_canonical_json_is_stable_string():
    spec = {"z": 1, "a": {"y": 2, "b": 3}}
    assert canonical_json(spec) == canonical_json(spec)
