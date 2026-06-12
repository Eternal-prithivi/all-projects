"""Azure VM manager helpers."""

from app.vm.azure_manager import _is_sku_unavailable, _vm_sizes_to_try


def test_vm_sizes_to_try_includes_fallbacks():
    sizes = _vm_sizes_to_try("Standard_B2s")
    assert sizes[0] == "Standard_B2s"
    assert "Standard_D2s_v3" in sizes


def test_is_sku_unavailable_detects_code():
    class FakeError(Exception):
        error = type("E", (), {"code": "SkuNotAvailable"})()

    assert _is_sku_unavailable(FakeError()) is True
    assert _is_sku_unavailable(RuntimeError("other")) is False
