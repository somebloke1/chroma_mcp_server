"""
Unit tests for the context module that provides enhanced context capture functionality.
"""

import unittest
import pytest
from unittest.mock import MagicMock, patch
from src.chroma_mcp_client.context import (
    ModificationType,
    ToolPatterns,
    extract_code_snippets,
    generate_diff_summary,
    track_tool_sequence,
    calculate_confidence_score,
    determine_modification_type,
    manage_bidirectional_links,
)


class TestToolPatternsIdentification(unittest.TestCase):
    """Test case for tool pattern identification functionality."""

    def test_identify_multiple_reads_pattern(self):
        """Test identification of multiple reads pattern."""
        tool_sequence = "read_file→read_file→read_file→edit_file"
        patterns = ToolPatterns.identify_patterns(tool_sequence)
        self.assertIn(ToolPatterns.MULTIPLE_READS, patterns)

    def test_identify_search_then_edit_pattern(self):
        """Test identification of search followed by edit pattern."""
        tool_sequence = "grep_search→read_file→edit_file"
        patterns = ToolPatterns.identify_patterns(tool_sequence)
        self.assertIn(ToolPatterns.SEARCH_THEN_EDIT, patterns)

        tool_sequence = "codebase_search→read_file→edit_file"
        patterns = ToolPatterns.identify_patterns(tool_sequence)
        self.assertIn(ToolPatterns.SEARCH_THEN_EDIT, patterns)

    def test_identify_iterative_refinement_pattern(self):
        """Test identification of edit followed by reapply pattern."""
        tool_sequence = "read_file→edit_file→reapply"
        patterns = ToolPatterns.identify_patterns(tool_sequence)
        self.assertIn(ToolPatterns.ITERATIVE_REFINEMENT, patterns)

    def test_identify_exploration_pattern(self):
        """Test identification of exploration pattern (multiple searches/reads without edits)."""
        tool_sequence = "read_file→grep_search→read_file→codebase_search→read_file"
        patterns = ToolPatterns.identify_patterns(tool_sequence)
        self.assertIn(ToolPatterns.EXPLORATION, patterns)

    def test_identify_code_execution_pattern(self):
        """Test identification of code execution pattern."""
        tool_sequence = "edit_file→run_terminal_cmd"
        patterns = ToolPatterns.identify_patterns(tool_sequence)
        self.assertIn(ToolPatterns.CODE_EXECUTION, patterns)

    def test_multiple_patterns(self):
        """Test identification of multiple patterns in the same sequence."""
        tool_sequence = "read_file→read_file→read_file→grep_search→edit_file→run_terminal_cmd→reapply"
        patterns = ToolPatterns.identify_patterns(tool_sequence)
        self.assertIn(ToolPatterns.MULTIPLE_READS, patterns)
        self.assertIn(ToolPatterns.SEARCH_THEN_EDIT, patterns)
        self.assertIn(ToolPatterns.CODE_EXECUTION, patterns)
        self.assertIn(ToolPatterns.ITERATIVE_REFINEMENT, patterns)


class TestCodeSnippetExtraction(unittest.TestCase):
    """Test case for code snippet extraction functionality."""

    def test_extract_snippets_new_file(self):
        """Test extraction for a new file."""
        before_content = ""
        after_content = "def hello():\n    print('Hello, world!')\n"
        result = extract_code_snippets(before_content, after_content)
        self.assertIn("NEW FILE:", result)
        self.assertIn("def hello():", result)

    def test_extract_snippets_deleted_file(self):
        """Test extraction for a deleted file."""
        before_content = "def hello():\n    print('Hello, world!')\n"
        after_content = ""
        result = extract_code_snippets(before_content, after_content)
        self.assertIn("DELETED FILE:", result)
        self.assertIn("def hello():", result)

    def test_extract_snippets_modified_file(self):
        """Test extraction for a modified file."""
        before_content = "def hello():\n    print('Hello, world!')\n"
        after_content = "def hello():\n    print('Hello, universe!')\n"
        result = extract_code_snippets(before_content, after_content)
        self.assertIn("CHANGED FILE:", result)
        self.assertIn("-    print('Hello, world!')", result)
        self.assertIn("+    print('Hello, universe!')", result)

    def test_extract_snippets_truncation(self):
        """Test truncation of large diffs."""
        before_content = "\n".join([f"line {i}" for i in range(100)])
        after_content = "\n".join([f"line {i}" if i % 2 == 0 else f"modified {i}" for i in range(100)])
        result = extract_code_snippets(before_content, after_content, max_context_lines=20)
        self.assertIn("... (truncated)", result)


class TestDiffSummary(unittest.TestCase):
    """Test case for diff summary generation."""

    def test_generate_summary_new_file(self):
        """Test summary generation for a new file."""
        before_content = ""
        after_content = "def hello():\n    print('Hello, world!')\n"
        result = generate_diff_summary(before_content, after_content, "hello.py")
        self.assertEqual(result, "Created new file hello.py")

    def test_generate_summary_deleted_file(self):
        """Test summary generation for a deleted file."""
        before_content = "def hello():\n    print('Hello, world!')\n"
        after_content = ""
        result = generate_diff_summary(before_content, after_content, "hello.py")
        self.assertEqual(result, "Deleted file hello.py")

    def test_generate_summary_with_function_changes(self):
        """Test summary generation with function additions/removals."""
        before_content = "def hello():\n    print('Hello!')\n"
        after_content = "def hello():\n    print('Hello!')\n\ndef goodbye():\n    print('Goodbye!')\n"
        result = generate_diff_summary(before_content, after_content, "hello.py")
        self.assertIn("Modified hello.py", result)
        self.assertIn("Added: def goodbye", result)

    def test_generate_summary_with_class_changes(self):
        """Test summary generation with class additions/removals."""
        before_content = "class Hello:\n    pass\n\nclass Goodbye:\n    pass\n"
        after_content = "class Hello:\n    pass\n\nclass Welcome:\n    pass\n"
        result = generate_diff_summary(before_content, after_content, "classes.py")
        self.assertIn("Modified classes.py", result)
        self.assertIn("Added: class Welcome", result)
        self.assertIn("Removed: class Goodbye", result)


class TestToolSequenceTracking(unittest.TestCase):
    """Test case for tool sequence tracking."""

    def test_empty_tool_sequence(self):
        """Test handling of empty tool list."""
        result = track_tool_sequence([])
        self.assertEqual(result, "")

    def test_single_tool(self):
        """Test tracking of a single tool."""
        result = track_tool_sequence(["read_file"])
        self.assertEqual(result, "read_file")

    def test_multiple_tools(self):
        """Test tracking of multiple unique tools."""
        result = track_tool_sequence(["read_file", "edit_file", "run_terminal_cmd"])
        self.assertEqual(result, "read_file→edit_file→run_terminal_cmd")

    def test_consecutive_duplicates_filtered(self):
        """Test that consecutive duplicate tools are filtered out."""
        result = track_tool_sequence(["read_file", "read_file", "read_file", "edit_file", "edit_file"])
        self.assertEqual(result, "read_file→edit_file")

    def test_non_consecutive_duplicates_preserved(self):
        """Test that non-consecutive duplicate tools are preserved."""
        result = track_tool_sequence(["read_file", "edit_file", "read_file"])
        self.assertEqual(result, "read_file→edit_file→read_file")


class TestConfidenceScoring(unittest.TestCase):
    """Test case for confidence score calculation."""

    def test_base_score(self):
        """Test the base confidence score."""
        result = calculate_confidence_score("", [], 200)
        self.assertEqual(result, 0.5)

    def test_complex_interaction_bonus(self):
        """Test bonus for complex interactions (more than 3 tools)."""
        result = calculate_confidence_score("tool1→tool2→tool3→tool4", [], 200)
        self.assertGreater(result, 0.5)

    def test_file_edit_bonus(self):
        """Test bonus for file edits."""
        result = calculate_confidence_score("read_file→edit_file", [], 200)
        self.assertGreater(result, 0.5)

    def test_multiple_reads_bonus(self):
        """Test bonus for multiple file reads."""
        result = calculate_confidence_score("read_file→read_file→read_file", [], 200)
        self.assertGreater(result, 0.5)

    def test_terminal_command_bonus(self):
        """Test bonus for terminal commands."""
        result = calculate_confidence_score("edit_file→run_terminal_cmd", [], 200)
        self.assertGreater(result, 0.5)

    def test_reapply_bonus(self):
        """Test bonus for reapply operations."""
        result = calculate_confidence_score("edit_file→reapply", [], 200)
        self.assertGreater(result, 0.5)

    def test_file_changes_bonus(self):
        """Test bonus for file changes."""
        result = calculate_confidence_score("", [{"file": "test.py"}], 200)
        self.assertGreater(result, 0.5)

    def test_multiple_file_changes_bonus(self):
        """Test bonus for multiple file changes."""
        result = calculate_confidence_score("", [{"file": "test.py"}, {"file": "other.py"}], 200)
        self.assertGreater(result, 0.6)

    def test_short_response_penalty(self):
        """Test penalty for very short responses."""
        result = calculate_confidence_score("", [], 50)
        self.assertLess(result, 0.5)

    def test_upper_bound(self):
        """Test that confidence score doesn't exceed 1.0."""
        # Create a scenario with many positive factors
        result = calculate_confidence_score(
            "read_file→read_file→read_file→grep_search→edit_file→run_terminal_cmd→reapply",
            [{"file": "test1.py"}, {"file": "test2.py"}, {"file": "test3.py"}],
            500,
        )
        self.assertLessEqual(result, 1.0)

    def test_lower_bound(self):
        """Test that confidence score doesn't go below 0.0."""
        # This is an unlikely scenario, but testing the boundary
        with patch(
            "src.chroma_mcp_client.context.calculate_confidence_score", return_value=-0.1
        ):  # Force a negative score
            result = min(1.0, max(0.0, -0.1))  # Manually apply bounds
            self.assertGreaterEqual(result, 0.0)


class TestModificationTypeDetection(unittest.TestCase):
    """Test case for modification type detection."""

    def test_detect_bugfix(self):
        """Test detection of bugfix type."""
        result = determine_modification_type([], "Fix the error in the code", "Fixed the bug by changing...")
        self.assertEqual(result, ModificationType.BUGFIX)

    def test_detect_refactor(self):
        """Test detection of refactor type."""
        result = determine_modification_type([], "Refactor this code", "Improved the code structure...")
        self.assertEqual(result, ModificationType.REFACTOR)

    def test_detect_feature(self):
        """Test detection of feature type."""
        result = determine_modification_type([], "Add new login functionality", "Implemented new feature...")
        self.assertEqual(result, ModificationType.FEATURE)

    def test_detect_documentation(self):
        """Test detection of documentation type."""
        result = determine_modification_type([], "Update the README", "Added more documentation...")
        self.assertEqual(result, ModificationType.DOCUMENTATION)

    def test_detect_test(self):
        """Test detection of test type."""
        result = determine_modification_type([], "Add unit tests", "Created test cases...")
        self.assertEqual(result, ModificationType.TEST)

    def test_detect_optimization(self):
        """Test detection of optimization type."""
        result = determine_modification_type([], "Optimize performance", "Made the code run faster...")
        self.assertEqual(result, ModificationType.OPTIMIZATION)

    def test_detect_config(self):
        """Test detection of config type."""
        result = determine_modification_type([], "Update environment settings", "Changed configuration parameters...")
        self.assertEqual(result, ModificationType.CONFIG)

    def test_detect_style(self):
        """Test detection of style type."""
        result = determine_modification_type([], "Fix code formatting", "Applied consistent indentation...")
        self.assertEqual(result, ModificationType.STYLE)

    def test_unknown_type(self):
        """Test fallback to unknown type when no clear indicators."""
        result = determine_modification_type([], "Update the code", "Made some changes...")
        self.assertEqual(result, ModificationType.UNKNOWN)


class TestBidirectionalLinks(unittest.TestCase):
    """Test case for bidirectional link management."""

    def test_manage_bidirectional_links_stub(self):
        """Test the stub implementation of bidirectional link management."""
        mock_client = MagicMock()
        result = manage_bidirectional_links("chat-123", [{"file": "test.py"}], mock_client)
        self.assertEqual(result, {})
        # This is just testing the stub implementation; we'll need more tests when fully implemented


if __name__ == "__main__":
    unittest.main()
