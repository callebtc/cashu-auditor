"""Tests for MintLocationResolver"""

import csv
import gzip
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import socket

import pytest

from src.mint_location_resolver import MintLocationResolver


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_db_file = MintLocationResolver.DB_FILE
        original_last_update_file = MintLocationResolver.LAST_UPDATE_FILE

        # Override paths to use temp directory
        MintLocationResolver.DB_FILE = Path(tmpdir) / "dbip-city-ipv4-num.csv.gz"
        MintLocationResolver.LAST_UPDATE_FILE = Path(tmpdir) / "last_update_data" / "dbip-city-ipv4-num.csv.gz.txt"

        yield tmpdir

        # Restore original paths
        MintLocationResolver.DB_FILE = original_db_file
        MintLocationResolver.LAST_UPDATE_FILE = original_last_update_file


@pytest.fixture
def sample_ip_database(temp_data_dir):
    """Create a sample IP database file for testing."""
    db_file = Path(temp_data_dir) / "dbip-city-ipv4-num.csv.gz"
    db_file.parent.mkdir(parents=True, exist_ok=True)

    # Create sample data: start_ip_num, end_ip_num, country, stateprov, city, latitude, longitude
    sample_data = [
        ["16777216", "16777471", "US", "California", "", "Los Angeles", "", "34.0522", "-118.2437", ""],
        ["16777472", "16777727", "US", "New York", "", "New York", "", "40.7128", "-74.0060", ""],
        ["3232235520", "3232235775", "US", "California", "", "San Francisco", "", "37.7749", "-122.4194", ""],
    ]

    with gzip.open(db_file, "wt", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in sample_data:
            writer.writerow(row)

    return db_file


def test_ip_to_int():
    """Test IP address to integer conversion."""
    resolver = MintLocationResolver()
    assert resolver._ip_to_int("1.0.0.0") == 16777216
    assert resolver._ip_to_int("1.0.0.255") == 16777471
    assert resolver._ip_to_int("192.168.0.0") == 3232235520
    assert resolver._ip_to_int("192.168.0.255") == 3232235775


def test_ip_to_int_invalid():
    """Test IP address conversion with invalid input."""
    resolver = MintLocationResolver()
    with pytest.raises(ValueError):
        resolver._ip_to_int("invalid")
    with pytest.raises(ValueError):
        resolver._ip_to_int("1.2.3")


def test_get_last_update_time_nonexistent(temp_data_dir):
    """Test getting last update time when file doesn't exist."""
    resolver = MintLocationResolver()
    assert resolver._get_last_update_time() is None


def test_get_last_update_time_exists(temp_data_dir):
    """Test getting last update time when file exists."""
    resolver = MintLocationResolver()
    timestamp = datetime.utcnow()
    resolver.last_update_file.parent.mkdir(parents=True, exist_ok=True)
    with open(resolver.last_update_file, "w") as f:
        f.write(timestamp.isoformat())

    result = resolver._get_last_update_time()
    assert result is not None
    assert abs((result - timestamp).total_seconds()) < 1


def test_save_last_update_time(temp_data_dir):
    """Test saving last update time."""
    resolver = MintLocationResolver()
    resolver._save_last_update_time()
    assert resolver.last_update_file.exists()
    timestamp = resolver._get_last_update_time()
    assert timestamp is not None
    assert abs((datetime.utcnow() - timestamp).total_seconds()) < 1


def test_should_update_database_no_file(temp_data_dir):
    """Test should update when no file exists."""
    resolver = MintLocationResolver()
    assert resolver._should_update_database() is True


def test_should_update_database_recent(temp_data_dir):
    """Test should not update when file is recent."""
    resolver = MintLocationResolver()
    resolver.last_update_file.parent.mkdir(parents=True, exist_ok=True)
    recent_time = datetime.utcnow() - timedelta(days=1)
    with open(resolver.last_update_file, "w") as f:
        f.write(recent_time.isoformat())
    assert resolver._should_update_database() is False


def test_should_update_database_old(temp_data_dir):
    """Test should update when file is old."""
    resolver = MintLocationResolver()
    resolver.last_update_file.parent.mkdir(parents=True, exist_ok=True)
    old_time = datetime.utcnow() - timedelta(days=8)
    with open(resolver.last_update_file, "w") as f:
        f.write(old_time.isoformat())
    assert resolver._should_update_database() is True


def test_load_database(sample_ip_database):
    """Test loading the IP database."""
    resolver = MintLocationResolver()
    resolver.db_file = sample_ip_database
    resolver._load_database()
    assert len(resolver.ip_ranges) == 3
    # Check that ranges are sorted
    for i in range(len(resolver.ip_ranges) - 1):
        assert resolver.ip_ranges[i][0] <= resolver.ip_ranges[i + 1][0]


def test_load_database_nonexistent(temp_data_dir):
    """Test loading database when file doesn't exist."""
    resolver = MintLocationResolver()
    resolver.db_file = Path(temp_data_dir) / "nonexistent.csv.gz"
    with pytest.raises(FileNotFoundError):
        resolver._load_database()


@pytest.mark.asyncio
async def test_download_database(temp_data_dir):
    """Test downloading the database."""
    resolver = MintLocationResolver()
    resolver.db_file = Path(temp_data_dir) / "dbip-city-ipv4-num.csv.gz"

    # Mock the HTTP response
    mock_response = MagicMock()
    mock_response.content = b"test content"
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        await resolver._download_database()

    assert resolver.db_file.exists()
    assert resolver._get_last_update_time() is not None


def test_url_to_ip():
    """Test extracting IP from URL."""
    resolver = MintLocationResolver()

    # Direct IP address in URL
    ip = resolver._url_to_ip("https://192.168.1.1:3338")
    assert ip == "192.168.1.1"

    # Hostname resolving to IPv4
    addr_info = [
        (socket.AF_INET, None, None, None, ("1.2.3.4", 0)),
        (socket.AF_INET6, None, None, None, ("::1", 0)),
    ]
    with patch("socket.getaddrinfo", return_value=addr_info) as mock_getaddrinfo:
        ip = resolver._url_to_ip("https://example.com:3338")
        assert ip == "1.2.3.4"
        mock_getaddrinfo.assert_called_once()

    # Hostname resolving only to IPv6 (unsupported)
    ipv6_only = [(socket.AF_INET6, None, None, None, ("::1", 0))]
    with patch("socket.getaddrinfo", return_value=ipv6_only):
        ip = resolver._url_to_ip("https://ipv6-only.example.com")
        assert ip is None

    # Invalid URL
    ip = resolver._url_to_ip("not-a-url")
    assert ip is None


def test_ip_to_coordinates(sample_ip_database):
    """Test resolving IP to coordinates."""
    resolver = MintLocationResolver()
    resolver.db_file = sample_ip_database
    resolver._load_database()

    # Test IP in range
    coords = resolver._ip_to_coordinates("1.0.0.100")
    assert coords == (34.0522, -118.2437)

    coords = resolver._ip_to_coordinates("1.0.1.100")
    assert coords == (40.7128, -74.0060)

    # Test IP not in database
    coords = resolver._ip_to_coordinates("10.0.0.1")
    assert coords is None

    # Test invalid IP
    coords = resolver._ip_to_coordinates("invalid")
    assert coords is None


def test_ip_to_coordinates_not_loaded():
    """Test resolving IP when database not loaded."""
    resolver = MintLocationResolver()
    coords = resolver._ip_to_coordinates("1.0.0.1")
    assert coords is None


def test_resolve_mint_location(sample_ip_database):
    """Test resolving mint location."""
    resolver = MintLocationResolver()
    resolver.db_file = sample_ip_database
    resolver._load_database()

    with patch.object(resolver, "_url_to_ip", return_value="1.0.0.100"):
        coords = resolver.resolve_mint_location("https://example.com:3338")
        assert coords == (34.0522, -118.2437)

    with patch.object(resolver, "_url_to_ip", return_value=None):
        coords = resolver.resolve_mint_location("https://example.com:3338")
        assert coords is None


@pytest.mark.asyncio
async def test_ensure_database_updated_new_download(temp_data_dir):
    """Test ensuring database is updated when it needs to be downloaded."""
    resolver = MintLocationResolver()
    resolver.db_file = Path(temp_data_dir) / "dbip-city-ipv4-num.csv.gz"

    # Mock download
    mock_response = MagicMock()
    mock_response.content = b"test content"
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        # Mock the load to avoid needing real CSV data
        with patch.object(resolver, "_load_database"):
            await resolver.ensure_database_updated()

    assert resolver.db_file.exists()


@pytest.mark.asyncio
async def test_ensure_database_updated_existing(sample_ip_database):
    """Test ensuring database is updated when it already exists and is recent."""
    resolver = MintLocationResolver()
    resolver.db_file = sample_ip_database

    # Set recent update time
    resolver.last_update_file.parent.mkdir(parents=True, exist_ok=True)
    recent_time = datetime.utcnow() - timedelta(days=1)
    with open(resolver.last_update_file, "w") as f:
        f.write(recent_time.isoformat())

    # Should not download, just load
    download_called = False
    original_download = resolver._download_database

    async def mock_download():
        nonlocal download_called
        download_called = True
        await original_download()

    resolver._download_database = mock_download
    await resolver.ensure_database_updated()

    assert not download_called
    assert len(resolver.ip_ranges) == 3


@pytest.mark.asyncio
async def test_ensure_database_download_failure_uses_existing(sample_ip_database):
    """Ensure existing DB is used when download fails."""
    resolver = MintLocationResolver()
    resolver.db_file = sample_ip_database

    # Force download attempt by backdating last update
    resolver.last_update_file.parent.mkdir(parents=True, exist_ok=True)
    old_time = datetime.utcnow() - timedelta(days=8)
    with open(resolver.last_update_file, "w") as f:
        f.write(old_time.isoformat())

    with patch.object(resolver, "_download_database", side_effect=Exception("network error")):
        await resolver.ensure_database_updated()

    assert len(resolver.ip_ranges) == 3

