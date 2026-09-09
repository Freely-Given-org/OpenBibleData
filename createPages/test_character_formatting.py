"""
Comprehensive tests for Rust character formatting conversion.
"""
import unittest
from pathlib import Path

# Import the Rust module
try:
    from openbibledata_rust import convert_usfm_character_formatting
except ImportError:
    print("ERROR: Could not import openbibledata_rust. Make sure to run 'maturin develop' first.")
    raise


class TestCharacterFormattingPsalms(unittest.TestCase):
    """Test OET-RV Psalms verse coloring with \\z markers."""

    def test_psalms_zr_basic_only(self):
        """Test basic_only mode removes \\z markers."""
        usfm = "Some text \\zr verse content"
        result = convert_usfm_character_formatting(
            "OET-RV", "PSA", "book", usfm, True, [], [], False
        )
        assert "\\z" not in result["html"]
        assert "verse content" in result["html"]
        assert result["background_colour"] is None

    def test_psalms_z1_not_basic(self):
        """Test non-basic mode sets background colour for \\z1."""
        usfm = "Some text \\z1 verse content"
        result = convert_usfm_character_formatting(
            "OET-RV", "PSA", "book", usfm, False, [], [], False
        )
        assert result["background_colour"] == "z1"
        assert "<span class=\"z1\">" in result["html"]
        assert "\\z" not in result["html"]

    def test_psalms_z2_not_basic(self):
        """Test \\z2 marker sets background colour."""
        usfm = "Text \\z2 verse"
        result = convert_usfm_character_formatting(
            "OET-RV", "PSA", "book", usfm, False, [], [], False
        )
        assert result["background_colour"] == "z2"

    def test_psalms_z_hilite(self):
        """Test \\z*hilite markers are converted to spans."""
        usfm = "Text \\z1hilite highlighted text\\z1hilite* more"
        result = convert_usfm_character_formatting(
            "OET-RV", "PSA", "book", usfm, False, [], [], False
        )
        assert "<span class=\"z1hilite\">" in result["html"]
        assert "</span>" in result["html"]
        assert "\\z" not in result["html"]

    def test_non_psa_no_z_processing(self):
        """Test that \\z markers are ignored for non-PSA books."""
        usfm = "Text \\zr marker here"
        result = convert_usfm_character_formatting(
            "OET-RV", "MAT", "book", usfm, False, [], [], False
        )
        # Non-PSA books should keep \\z markers as-is or fail assertion
        # The Rust code asserts that \\z is not in html after processing for OET-RV


class TestCharacterFormattingTableCells(unittest.TestCase):
    """Test table cell marker conversion."""

    def test_tc1_marker(self):
        """Test \\tc1 markers are converted to <td> tags."""
        usfm = "\\tc1 cell1 \\tc2 cell2 \\tc3 cell3"
        result = convert_usfm_character_formatting(
            "TCNT", "MAT", "book", usfm, False, [], [], False
        )
        assert "<td>" in result["html"]
        assert "</td><td>" in result["html"]
        assert "\\tc" not in result["html"]

    def test_tc_single_cell(self):
        """Test table cell with no space after marker."""
        usfm = "Start \\tc1content here"
        result = convert_usfm_character_formatting(
            "NET", "MAT", "book", usfm, False, [], [], True
        )
        assert "<td>" in result["html"]


class TestCharacterFormattingBasicMarkups(unittest.TestCase):
    """Test basic character markup conversions."""

    def test_bold_marker(self):
        """Test \\bd markers convert to <b> tags."""
        usfm = "Text with \\bd bold text\\bd* here"
        result = convert_usfm_character_formatting(
            "WEB", "MAT", "book", usfm, False, [], [], False
        )
        assert "<b>bold text</b>" in result["html"]
        assert "\\bd" not in result["html"]

    def test_italic_marker(self):
        """Test \\it markers convert to <i> tags."""
        usfm = "Text with \\it italic text\\it* here"
        result = convert_usfm_character_formatting(
            "WEB", "MAT", "book", usfm, False, [], [], False
        )
        assert "<i>italic text</i>" in result["html"]

    def test_emphasis_marker(self):
        """Test \\em markers convert to <em> tags."""
        usfm = "Text with \\em emphasized text\\em* here"
        result = convert_usfm_character_formatting(
            "WEB", "MAT", "book", usfm, False, [], [], False
        )
        assert "<em>emphasized text</em>" in result["html"]

    def test_superscript_marker(self):
        """Test \\sup markers convert to <sup> tags."""
        usfm = "Footnote\\sup 1\\sup* indicator"
        result = convert_usfm_character_formatting(
            "WEB", "MAT", "book", usfm, False, [], [], False
        )
        assert "<sup>1</sup>" in result["html"]

    def test_bold_italic_marker(self):
        """Test \\bdit markers convert to <b><i> tags."""
        usfm = "Text with \\bdit bold italic\\bdit* here"
        result = convert_usfm_character_formatting(
            "WEB", "MAT", "book", usfm, False, [], [], False
        )
        assert "<b><i>bold italic</i></b>" in result["html"]

    def test_nomina_sacra_lord(self):
        """Test special handling of \\nd LORD\\nd*."""
        usfm = "The \\nd LORD\\nd* is great"
        result = convert_usfm_character_formatting(
            "WEB", "MAT", "book", usfm, False, [], [], False
        )
        # Should convert the special LORD format
        assert "L<span style=\"font-size:.75em;\">ORD</span>" in result["html"]

    def test_nomina_sacra_oet_nt(self):
        """Test OET NT books use nominaSacra class."""
        usfm = "The \\nd Lord\\nd* appeared"
        # Using ROM (Romans, NT book)
        result = convert_usfm_character_formatting(
            "OET-RV", "ROM", "book", usfm, False, ["nd"], ["ROM", "CO1", "CO2"], False
        )
        assert "<span class=\"nominaSacra\">" in result["html"]
        assert "\\nd" not in result["html"]

    def test_nomina_sacra_non_nt(self):
        """Test OET OT books don't use nominaSacra class."""
        usfm = "The \\nd LORD\\nd* God"
        # PSA is OT
        result = convert_usfm_character_formatting(
            "OET-RV", "PSA", "book", usfm, False, ["nd"], ["ROM"], False
        )
        # Should use regular span class "nd" not "nominaSacra"
        assert "<span class=\"nd\">" in result["html"]


class TestCharacterFormattingWordMarkers(unittest.TestCase):
    """Test word marker processing."""

    def test_word_marker_simple(self):
        """Test simple \\w markers are removed."""
        usfm = "\\w word\\w* text"
        result = convert_usfm_character_formatting(
            "WEB", "MAT", "book", usfm, False, [], [], False
        )
        # Should extract just the word content
        assert "word" in result["html"]
        assert "\\w" not in result["html"]

    def test_word_marker_with_attributes(self):
        """Test \\w markers with pipe-separated content."""
        usfm = "\\w Lord|x-occurrence=\"1\" x-occurrences=\"3\"\\w* is here"
        result = convert_usfm_character_formatting(
            "ULT", "MAT", "book", usfm, False, [], [], False
        )
        # Should extract "Lord" without the attributes
        assert "Lord" in result["html"]
        assert "\\w" not in result["html"]
        assert "x-occurrence" not in result["html"]

    def test_word_marker_multiple(self):
        """Test multiple word markers in sequence."""
        usfm = "\\w First\\w* \\w second\\w* \\w third\\w* words"
        result = convert_usfm_character_formatting(
            "ULT", "MAT", "book", usfm, False, [], [], False
        )
        assert "First" in result["html"]
        assert "second" in result["html"]
        assert "third" in result["html"]
        assert "\\w" not in result["html"]

    def test_word_marker_plus_variant(self):
        """Test \\+w marker variant."""
        usfm = "\\+w word\\+w* text"
        result = convert_usfm_character_formatting(
            "WEB", "MAT", "book", usfm, False, [], [], False
        )
        assert "word" in result["html"]
        assert "\\w" not in result["html"]


class TestCharacterFormattingSpanMarkers(unittest.TestCase):
    """Test span-based character markers."""

    def test_add_marker_becomes_span(self):
        """Test \\add markers convert to spans."""
        usfm = "Text with \\add added text\\add* here"
        result = convert_usfm_character_formatting(
            "NET", "MAT", "book", usfm, False, ["add"], [], False
        )
        assert '<span class="add">' in result["html"]
        assert "</span>" in result["html"]

    def test_bk_marker_becomes_span(self):
        """Test \\bk markers convert to spans."""
        usfm = "See \\bk The Gospel\\bk* for details"
        result = convert_usfm_character_formatting(
            "NET", "MAT", "book", usfm, False, ["bk"], [], False
        )
        assert '<span class="bk">' in result["html"]

    def test_multiple_span_markers(self):
        """Test multiple different span markers."""
        usfm = "\\add added\\add* and \\bk book\\bk* text"
        result = convert_usfm_character_formatting(
            "NET", "MAT", "book", usfm, False, ["add", "bk"], [], False
        )
        assert '<span class="add">' in result["html"]
        assert '<span class="bk">' in result["html"]
        assert "</span>" in result["html"]


class TestCharacterFormattingEmbeddedPlus(unittest.TestCase):
    """Test handling of embedded USFM markers with + (\\+ prefix)."""

    def test_plus_marker_replaced(self):
        """Test \\+ embedded marker style is handled."""
        usfm = "Text with \\+em embedded emphasis\\+em* marker"
        result = convert_usfm_character_formatting(
            "WEB", "MAT", "book", usfm, False, [], [], False
        )
        # The \\+ should be replaced with \\
        assert "<em>" in result["html"]
        assert "\\+" not in result["html"]


class TestCharacterFormattingValidation(unittest.TestCase):
    """Test validation and edge cases."""

    def test_empty_input(self):
        """Test empty USFM input."""
        result = convert_usfm_character_formatting(
            "WEB", "MAT", "book", "", False, [], [], False
        )
        assert result["html"] == ""
        assert result["background_colour"] is None
        assert result["files_to_copy"] == []

    def test_plain_text_unchanged(self):
        """Test plain text without markers."""
        usfm = "This is just plain text with no USFM markers."
        result = convert_usfm_character_formatting(
            "WEB", "MAT", "book", usfm, False, [], [], False
        )
        assert result["html"] == usfm

    def test_return_structure(self):
        """Test the returned structure has all expected keys."""
        result = convert_usfm_character_formatting(
            "WEB", "MAT", "book", "test", False, [], [], False
        )
        assert "html" in result
        assert "background_colour" in result
        assert "files_to_copy" in result
        assert isinstance(result["html"], str)
        assert isinstance(result["files_to_copy"], list)


class TestCharacterFormattingNETVersion(unittest.TestCase):
    """Test NET-specific character marker handling."""

    def test_net_version_special_markers(self):
        """Test NET version adds extra markers."""
        usfm = "Hebrew: \\heb דָּבָר\\heb* and Greek: \\grk λόγος\\grk*"
        result = convert_usfm_character_formatting(
            "NET", "MAT", "book", usfm, False, ["heb", "grk"], [], True
        )
        # These markers should be converted to spans for NET version
        assert '<span class="heb">' in result["html"]
        assert '<span class="grk">' in result["html"]

    def test_net_version_flag(self):
        """Test is_net_version flag affects marker handling."""
        usfm = "\\fx note\\fx*"
        result = convert_usfm_character_formatting(
            "NET", "MAT", "book", usfm, False, ["fx"], [], True
        )
        assert '<span class="fx">' in result["html"]


class TestCharacterFormattingOETSpecific(unittest.TestCase):
    """Test OET-specific features."""

    def test_oet_untranslated_handling(self):
        """Test OET untranslated word annotation."""
        # This is a simplified test - real OET data has complex HTML
        html_with_untr = '<span class="untr"><a title="Exact word"'
        usfm = html_with_untr
        result = convert_usfm_character_formatting(
            "OET-LV", "MAT", "book", usfm, False, ["untr"], [], False
        )
        # Result should process untranslated markers
        # The function will try to append "(untranslated)" to titles


if __name__ == "__main__":
    unittest.main()
