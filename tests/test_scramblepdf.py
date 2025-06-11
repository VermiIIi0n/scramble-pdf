import pytest
from scramblepdf import parse_cmap, build_cmap, scramble_pdf
from unittest.mock import patch, MagicMock, ANY
from typing import BinaryIO
from pikepdf import Pdf
import sys
from scramblepdf import __main__
from scramblepdf.cli import cli
import tempfile

def test_parse_cmap():
    # Test parse_cmap with a valid beginbfchar / endbfchar block
    cmap_bytes = b"beginbfchar\n<0000> <0020>\n<0001> <0021>\nendbfchar"
    expected = [("0000", "0020"), ("0001", "0021")]
    result = list(parse_cmap(cmap_bytes))
    assert result == expected

# Additional coverage for beginbfrange parsing (both direct and array forms)
def test_parse_cmap_bfrange():
    # Direct range form
    cmap_bytes = (
        b"beginbfrange\n"
        b"<0000> <0002> <0020>\n"  # maps 0000,0001,0002 -> 0020,0021,0022
        b"endbfrange"
    )
    expected_direct = [("0000", "0020"), ("0001", "0021"), ("0002", "0022")]
    assert list(parse_cmap(cmap_bytes)) == expected_direct

    # Array form
    cmap_array_bytes = (
        b"beginbfrange\n"
        b"<0003> <0005> [<0030> <0031> <0032>]\n"  # explicit dst list
        b"endbfrange"
    )
    expected_array = [("0003", "0030"), ("0004", "0031"), ("0005", "0032")]
    assert list(parse_cmap(cmap_array_bytes)) == expected_array

def test_build_cmap():
    # Test build_cmap function
    mapping = {"0000": "0020", "0001": "0021"}
    cmap_string = build_cmap(mapping)
    # Should include correct count and mappings
    assert f"{len(mapping)} beginbfchar" in cmap_string
    assert "<0000> <0020>" in cmap_string
    assert "<0001> <0021>" in cmap_string
    assert "endcmap" in cmap_string

def test_scramble_pdf():
    # Test scramble_pdf function using mock
    pdf_mock = MagicMock(spec=Pdf)
    font_mappings = {}
    selector = lambda x: x == "A"
    scramble_pdf(pdf_mock, 0.5, font_mappings=font_mappings, selector=selector)

# New tests for error cases and selector container
def test_invalid_ratio():
    with pytest.raises(ValueError):
        scramble_pdf(MagicMock(spec=Pdf, pages=[]), -0.1)
    with pytest.raises(ValueError):
        scramble_pdf(MagicMock(spec=Pdf, pages=[]), 1.1)

def test_zero_ratio_no_changes():
    pdf_mock = MagicMock(spec=Pdf)
    pdf_mock.pages = []
    assert scramble_pdf(pdf_mock, 0.0) is None

def test_selector_as_container():
    pdf_mock = MagicMock(spec=Pdf)
    pdf_mock.pages = []
    scramble_pdf(pdf_mock, 1.0, selector={'A', 'B'})

# Revised test_main
def test_main():
    with patch('argparse.ArgumentParser.parse_args', return_value=MagicMock(
            input_pdf='in.pdf', output_pdf='out.pdf', mapping=None,
            ratio=0.5, letters=False, non_letters=False,
            selectregex=None, whitelist=False)), \
         patch('pikepdf.Pdf.open', return_value=MagicMock(spec=Pdf)) as open_mock, \
         patch('scramblepdf.__main__.scramble_pdf') as scramble_mock:
        pdf_instance = open_mock.return_value
        result = __main__.main()
        assert result == 0
        open_mock.assert_called_once_with('in.pdf')
        scramble_mock.assert_called_once_with(
            pdf_instance, 0.5, font_mappings=None,
            selector=ANY, select_as_blacklist=True)
        pdf_instance.save.assert_called_once_with('out.pdf')

# Tests for selector_func behavior via main
def test_selector_func_regex():
    with patch('argparse.ArgumentParser.parse_args', return_value=MagicMock(
            input_pdf='in.pdf', output_pdf='out.pdf', mapping=None,
            ratio=1.0, letters=False, non_letters=False,
            selectregex='[A-Z]', whitelist=False)), \
         patch('pikepdf.Pdf.open', return_value=MagicMock(spec=Pdf)), \
         patch('scramblepdf.__main__.scramble_pdf') as scramble_mock:
        __main__.main()
        scramble_mock.assert_called_once()
        args, kwargs = scramble_mock.call_args
        selector = kwargs['selector']
        assert selector('A') is True
        assert selector('Z') is True
        assert selector('a') is False
        assert selector('0') is False

def test_selector_func_letters_flag():
    with patch('argparse.ArgumentParser.parse_args', return_value=MagicMock(
            input_pdf='in.pdf', output_pdf='out.pdf', mapping=None,
            ratio=1.0, letters=True, non_letters=False,
            selectregex=None, whitelist=False)), \
         patch('pikepdf.Pdf.open', return_value=MagicMock(spec=Pdf)), \
         patch('scramblepdf.__main__.scramble_pdf') as scramble_mock:
        __main__.main()
        scramble_mock.assert_called_once()
        args, kwargs = scramble_mock.call_args
        selector = kwargs['selector']
        # letters flag: non-letters selected, letters skipped
        assert selector('A') is False
        assert selector('1') is True

def test_selector_func_non_letters_flag():
    with patch('argparse.ArgumentParser.parse_args', return_value=MagicMock(
            input_pdf='in.pdf', output_pdf='out.pdf', mapping=None,
            ratio=1.0, letters=False, non_letters=True,
            selectregex=None, whitelist=False)), \
         patch('pikepdf.Pdf.open', return_value=MagicMock(spec=Pdf)), \
         patch('scramblepdf.__main__.scramble_pdf') as scramble_mock:
        __main__.main()
        scramble_mock.assert_called_once()
        args, kwargs = scramble_mock.call_args
        selector = kwargs['selector']
        # non_letters flag: same behavior as letters
        assert selector('A') is False
        assert selector('1') is True

def test_cli():
    # cli should not error and return None
    assert cli() is None

def test_scramble_pdf_with_aigc():
    # Test scramble_pdf with AIGC.pdf using a temporary file
    input_pdf_path = 'tests/testPDF/AIGC.pdf'

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_output:
        try:
            pdf = Pdf.open(input_pdf_path)
            scramble_pdf(pdf, ratio=1.0)
            pdf.save(temp_output.name)
        except Exception as e:
            pytest.fail(f"scramble_pdf raised an exception: {e}")

def test_build_cmap_large_mapping():
    # Build a mapping larger than 100 items to trigger multiple beginbfchar blocks
    mapping = {f"{i:04X}": f"{(i+0x20):04X}" for i in range(150)}
    cmap_text = build_cmap(mapping)
    # There should be at least two beginbfchar blocks (first 100, then 50)
    assert cmap_text.count("beginbfchar") == 2
    assert cmap_text.count("endbfchar") == 2
    # Spot-check a couple of mappings
    assert "<0000> <0020>" in cmap_text
    assert "<0076> <0096>" in cmap_text
