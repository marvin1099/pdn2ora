"""Basic tests for pdn2ora converter."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from pdn2ora.converter import convert_pdn_to_ora, read_pdn_info, validate_ora

TESTS_DIR = Path(__file__).parent
SAMPLE_PDN = TESTS_DIR / "w-back-800x600.pdn"
MULTI_LAYER_PDN = TESTS_DIR / "w-b-t-back-l1-l2-800x600.pdn"
ALL_BLEND_PDN = TESTS_DIR / "bw-back-split-800x600.pdn"


@pytest.mark.skipif(not SAMPLE_PDN.exists(), reason="Test fixture missing")
class TestReadInfo:
    def test_single_layer(self):
        info = read_pdn_info(SAMPLE_PDN)
        assert info["width"] == 800
        assert info["height"] == 600
        assert info["layer_count"] == 1
        assert info["layers"][0]["name"] == "Background"

    def test_multi_layer(self):
        info = read_pdn_info(MULTI_LAYER_PDN)
        assert info["layer_count"] == 3
        names = [l["name"] for l in info["layers"]]
        assert "Background" in names
        assert "Layer 2" in names
        assert "Layer 3" in names


@pytest.mark.skipif(not SAMPLE_PDN.exists(), reason="Test fixture missing")
class TestConvert:
    def test_single_layer(self, tmp_path):
        ora_path = tmp_path / "output.ora"
        result = convert_pdn_to_ora(SAMPLE_PDN, ora_path)
        assert result.exists()
        assert result.suffix == ".ora"

    def test_multi_layer(self, tmp_path):
        ora_path = tmp_path / "multi.ora"
        result = convert_pdn_to_ora(MULTI_LAYER_PDN, ora_path)
        assert result.exists()

    def test_no_overwrite(self, tmp_path):
        ora_path = tmp_path / "output.ora"
        convert_pdn_to_ora(SAMPLE_PDN, ora_path)
        with pytest.raises(FileExistsError):
            convert_pdn_to_ora(SAMPLE_PDN, ora_path, overwrite=False)

    def test_overwrite(self, tmp_path):
        ora_path = tmp_path / "output.ora"
        convert_pdn_to_ora(SAMPLE_PDN, ora_path)
        convert_pdn_to_ora(SAMPLE_PDN, ora_path, overwrite=True)
        assert ora_path.exists()

    def test_validate(self, tmp_path):
        ora_path = tmp_path / "validated.ora"
        convert_pdn_to_ora(SAMPLE_PDN, ora_path, validate=True)
        assert ora_path.exists()


@pytest.mark.skipif(not SAMPLE_PDN.exists(), reason="Test fixture missing")
class TestValidate:
    def test_valid_ora(self, tmp_path):
        ora_path = tmp_path / "valid.ora"
        convert_pdn_to_ora(SAMPLE_PDN, ora_path)
        assert validate_ora(ora_path) is True

    def test_invalid_file(self, tmp_path):
        bad = tmp_path / "bad.ora"
        bad.write_text("not an ora file")
        assert validate_ora(bad) is False
