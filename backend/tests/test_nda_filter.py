"""Tests for the NDA filter."""

from app.services.pipeline.nda_filter import NDAFilter


class TestNDAFilterScan:
    """Tests for NDAFilter.scan()."""

    def test_scan_returns_empty_when_no_config(self):
        """scan should return no flags when nda_config is None."""
        nda = NDAFilter()
        result = nda.scan("This contains Acme Corp data", None)
        assert result["flagged"] is False
        assert result["flags"] == []

    def test_scan_finds_blocked_terms(self):
        """scan should flag content containing blocked terms."""
        nda = NDAFilter()
        config = {
            "mode": "flag",
            "blocked_terms": ["Acme Corp", "Project Phoenix"],
            "generalization_rules": [],
        }
        result = nda.scan("We deployed the solution at Acme Corp using Project Phoenix.", config)
        assert result["flagged"] is True
        assert len(result["flags"]) == 2

    def test_scan_case_insensitive(self):
        """scan should find blocked terms regardless of case."""
        nda = NDAFilter()
        config = {"mode": "flag", "blocked_terms": ["secret project"], "generalization_rules": []}
        result = nda.scan("The SECRET PROJECT was launched.", config)
        assert result["flagged"] is True
        assert len(result["flags"]) == 1

    def test_scan_no_match_returns_clean(self):
        """scan should return no flags when content is clean."""
        nda = NDAFilter()
        config = {"mode": "flag", "blocked_terms": ["Acme Corp"], "generalization_rules": []}
        result = nda.scan("A generic company deployed security measures.", config)
        assert result["flagged"] is False
        assert result["flags"] == []

    def test_scan_with_generalization_rules(self):
        """scan should flag content matching generalization rule patterns."""
        nda = NDAFilter()
        config = {
            "mode": "flag",
            "blocked_terms": [],
            "generalization_rules": [
                {"pattern": r"\d{3}-\d{2}-\d{4}", "replacement_template": "[REDACTED SSN]"},
            ],
        }
        result = nda.scan("Employee ID: 123-45-6789 was involved.", config)
        assert result["flagged"] is True
        assert len(result["flags"]) == 1

    def test_scan_returns_mode(self):
        """scan result should include the NDA mode."""
        nda = NDAFilter()
        config = {"mode": "block", "blocked_terms": ["secret"], "generalization_rules": []}
        result = nda.scan("This is a secret.", config)
        assert result["mode"] == "block"

    def test_scan_provides_context(self):
        """scan flags should include context around the matched term."""
        nda = NDAFilter()
        config = {"mode": "flag", "blocked_terms": ["sensitive"], "generalization_rules": []}
        result = nda.scan("This document contains sensitive information about clients.", config)
        assert result["flagged"] is True
        flag = result["flags"][0]
        assert "term" in flag
        assert "context" in flag
        assert "suggestion" in flag


class TestNDAFilterGeneralize:
    """Tests for NDAFilter.apply_generalizations()."""

    def test_apply_generalizations_in_auto_mode(self):
        """apply_generalizations should replace patterns when mode is auto_generalize."""
        nda = NDAFilter()
        config = {
            "mode": "auto_generalize",
            "generalization_rules": [
                {"pattern": r"Acme Corp", "replacement_template": "[a Fortune 500 company]"},
                {"pattern": r"\$\d+M", "replacement_template": "[significant investment]"},
            ],
        }
        content = "Acme Corp invested $50M in security."
        result = nda.apply_generalizations(content, config)
        assert "Acme Corp" not in result
        assert "[a Fortune 500 company]" in result
        assert "$50M" not in result
        assert "[significant investment]" in result

    def test_apply_generalizations_noop_in_flag_mode(self):
        """apply_generalizations should return content unchanged when mode is flag."""
        nda = NDAFilter()
        config = {
            "mode": "flag",
            "generalization_rules": [
                {"pattern": r"Acme Corp", "replacement_template": "[a company]"},
            ],
        }
        content = "Acme Corp deployed the solution."
        result = nda.apply_generalizations(content, config)
        assert result == content

    def test_apply_generalizations_noop_in_block_mode(self):
        """apply_generalizations should return content unchanged when mode is block."""
        nda = NDAFilter()
        config = {
            "mode": "block",
            "generalization_rules": [
                {"pattern": r"Acme Corp", "replacement_template": "[a company]"},
            ],
        }
        content = "Acme Corp deployed the solution."
        result = nda.apply_generalizations(content, config)
        assert result == content

    def test_apply_generalizations_case_insensitive(self):
        """apply_generalizations should replace patterns case-insensitively."""
        nda = NDAFilter()
        config = {
            "mode": "auto_generalize",
            "generalization_rules": [
                {"pattern": r"acme corp", "replacement_template": "[a company]"},
            ],
        }
        content = "ACME CORP is a major client."
        result = nda.apply_generalizations(content, config)
        assert "[a company]" in result

    def test_apply_generalizations_empty_rules(self):
        """apply_generalizations should handle empty rules gracefully."""
        nda = NDAFilter()
        config = {"mode": "auto_generalize", "generalization_rules": []}
        content = "Nothing to generalize."
        result = nda.apply_generalizations(content, config)
        assert result == content
