# tests/test_helpers.py

import pytest
from src.helpers import sanitize_err


def test_sanitize_err_simple():
    """Test sanitizing a simple error message."""
    error = Exception("Simple error message")
    result = sanitize_err(error)
    assert result == "Simple error message"


def test_sanitize_err_multiline():
    """Test sanitizing a multiline error message - should take only first line."""
    error = Exception("First line\nSecond line\nThird line")
    result = sanitize_err(error)
    assert result == "First line"


def test_sanitize_err_long_message():
    """Test sanitizing a very long error message - should truncate."""
    long_message = "A" * 1000
    error = Exception(long_message)
    result = sanitize_err(error)
    assert len(result) == 500  # Default max_len
    assert result == "A" * 500


def test_sanitize_err_custom_max_len():
    """Test sanitizing with custom max_len."""
    long_message = "A" * 1000
    error = Exception(long_message)
    result = sanitize_err(error, max_len=100)
    assert len(result) == 100
    assert result == "A" * 100


def test_sanitize_err_multiline_and_long():
    """Test sanitizing multiline error that's also long."""
    long_message = "First line with " + "A" * 1000 + "\nSecond line"
    error = Exception(long_message)
    result = sanitize_err(error)
    assert result == "First line with " + "A" * (500 - len("First line with "))
    assert len(result) == 500


