"""
MintLocationResolver: Resolves IP addresses of mints to geo coordinates.

This module handles downloading and maintaining a local copy of the IP location
database from dbip-city, and provides functionality to resolve mint URLs to
their geographic coordinates.
"""

import csv
import gzip
import ipaddress
import socket
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import httpx
from loguru import logger


class MintLocationResolver:
    """
    Resolves mint URLs to geographic coordinates using the dbip-city IP database.

    The resolver maintains a local copy of the IP location database and updates
    it at most once per week. It can resolve IP addresses to latitude/longitude
    coordinates for mapping purposes.
    """

    DB_URL = "https://raw.githubusercontent.com/sapics/ip-location-db/refs/heads/main/dbip-city/dbip-city-ipv4-num.csv.gz"
    DB_FILE = Path("data/dbip-city-ipv4-num.csv.gz")
    LAST_UPDATE_FILE = Path("data/last_update_data/dbip-city-ipv4-num.csv.gz.txt")
    UPDATE_INTERVAL_DAYS = 7

    def __init__(self):
        """Initialize the resolver and ensure data directory exists."""
        self.db_file = self.DB_FILE
        self.last_update_file = self.LAST_UPDATE_FILE
        self.ip_ranges: list[Tuple[int, int, float, float]] = []
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        self.last_update_file.parent.mkdir(parents=True, exist_ok=True)

    def _ip_to_int(self, ip: str) -> int:
        """Convert IP address string to integer."""
        parts = ip.split(".")
        if len(parts) != 4:
            raise ValueError(f"Invalid IP address format: {ip}")
        return (
            int(parts[0]) * 256**3
            + int(parts[1]) * 256**2
            + int(parts[2]) * 256
            + int(parts[3])
        )

    def _get_last_update_time(self) -> Optional[datetime]:
        """Get the timestamp of the last database update."""
        if not self.last_update_file.exists():
            return None
        try:
            with open(self.last_update_file, "r") as f:
                timestamp_str = f.read().strip()
                return datetime.fromisoformat(timestamp_str)
        except Exception as e:
            logger.warning(f"Error reading last update time: {e}")
            return None

    def _save_last_update_time(self):
        """Save the current timestamp as the last update time."""
        try:
            with open(self.last_update_file, "w") as f:
                f.write(datetime.utcnow().isoformat())
        except Exception as e:
            logger.error(f"Error saving last update time: {e}")

    def _should_update_database(self) -> bool:
        """Check if the database should be updated."""
        last_update = self._get_last_update_time()
        if last_update is None:
            return True
        days_since_update = (datetime.utcnow() - last_update).days
        return days_since_update >= self.UPDATE_INTERVAL_DAYS

    async def _download_database(self):
        """Download the IP location database from the remote URL."""
        logger.info(f"Downloading IP location database from {self.DB_URL}")
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(self.DB_URL)
                response.raise_for_status()
                with open(self.db_file, "wb") as f:
                    f.write(response.content)
            logger.success(f"Downloaded database to {self.db_file}")
            self._save_last_update_time()
        except Exception as e:
            logger.error(f"Error downloading database: {e}")
            raise

    def _load_database(self):
        """Load the IP location database into memory."""
        if not self.db_file.exists():
            raise FileNotFoundError(
                f"Database file not found: {self.db_file}. Please download it first."
            )

        logger.info(f"Loading IP location database from {self.db_file}")
        self.ip_ranges = []

        try:
            with gzip.open(self.db_file, "rt", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) < 8:
                        continue
                    try:
                        start_ip_num = int(row[0])
                        end_ip_num = int(row[1])
                        # Dataset layout: ..., latitude, longitude, accuracy
                        latitude_str = row[-3].strip()
                        longitude_str = row[-2].strip()
                        if not latitude_str or not longitude_str:
                            continue
                        latitude = float(latitude_str)
                        longitude = float(longitude_str)
                        self.ip_ranges.append((start_ip_num, end_ip_num, latitude, longitude))
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Skipping invalid row: {row}, error: {e}")
                        continue

            # Sort by start IP for binary search efficiency
            self.ip_ranges.sort(key=lambda x: x[0])
            logger.success(f"Loaded {len(self.ip_ranges)} IP ranges from database")
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            raise

    async def ensure_database_updated(self):
        """Ensure the database is up to date, downloading if necessary."""
        needs_download = self._should_update_database() or not self.db_file.exists()
        if needs_download:
            try:
                await self._download_database()
            except Exception as e:
                if not self.db_file.exists():
                    logger.error(
                        "Failed to download IP database and no local copy is available."
                    )
                    raise
                logger.warning(
                    f"Download failed ({e}). Proceeding with existing database at {self.db_file}"
                )
        self._load_database()

    def _url_to_ip(self, url: str) -> Optional[str]:
        """Extract IP address from a URL by resolving the hostname."""
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            if not hostname:
                return None

            # Check if hostname is already an IP address
            try:
                ip_obj = ipaddress.ip_address(hostname)
                if isinstance(ip_obj, ipaddress.IPv4Address):
                    return hostname
                logger.warning(
                    f"Hostname {hostname} resolves to IPv6 which is not supported by dbip dataset."
                )
                return None
            except ValueError:
                pass

            # Resolve hostname to IP (prefer IPv4)
            try:
                addr_info = socket.getaddrinfo(
                    hostname, None, proto=socket.IPPROTO_TCP
                )
            except socket.gaierror as e:
                logger.warning(f"Could not resolve hostname {hostname}: {e}")
                return None

            for info in addr_info:
                sockaddr = info[4]
                if not sockaddr:
                    continue
                ip_candidate = sockaddr[0]
                try:
                    ip_obj = ipaddress.ip_address(ip_candidate)
                    if isinstance(ip_obj, ipaddress.IPv4Address):
                        return ip_candidate
                except ValueError:
                    continue

            logger.warning(
                f"No IPv4 address found for hostname {hostname}. Unable to resolve location."
            )
            return None
        except Exception as e:
            logger.warning(f"Error extracting IP from URL {url}: {e}")
            return None

    def _ip_to_coordinates(self, ip: str) -> Optional[Tuple[float, float]]:
        """Resolve IP address to latitude/longitude coordinates."""
        if not self.ip_ranges:
            logger.warning("IP ranges not loaded. Call ensure_database_updated() first.")
            return None

        try:
            ip_num = self._ip_to_int(ip)
        except ValueError as e:
            logger.warning(f"Invalid IP address {ip}: {e}")
            return None

        # Binary search for the IP range
        left, right = 0, len(self.ip_ranges) - 1
        while left <= right:
            mid = (left + right) // 2
            start_ip, end_ip, lat, lon = self.ip_ranges[mid]

            if start_ip <= ip_num <= end_ip:
                return (lat, lon)
            elif ip_num < start_ip:
                right = mid - 1
            else:
                left = mid + 1

        logger.debug(f"IP {ip} not found in database")
        return None

    def resolve_mint_location(self, mint_url: str) -> Optional[Tuple[float, float]]:
        """
        Resolve a mint URL to its geographic coordinates.

        Args:
            mint_url: The URL of the mint

        Returns:
            Tuple of (latitude, longitude) if found, None otherwise
        """
        ip = self._url_to_ip(mint_url)
        if not ip:
            return None
        return self._ip_to_coordinates(ip)

