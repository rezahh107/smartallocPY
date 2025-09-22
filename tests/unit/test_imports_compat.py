def test_legacy_import_shim():
    # Should import without raising
    from src.core.models.mentor_phase1 import Mentor  # noqa: F401
