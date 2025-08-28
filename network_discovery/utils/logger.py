"""
Logging system with colored output for network discovery operations.

This module provides a Logger class that supports colored console output
using colorama, different log levels with distinct colors, and progress
indicators for long-running operations.
"""

import sys
import time
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from colorama import Fore, Back, Style, init

# Initialize colorama for cross-platform colored output
init(autoreset=True)


class LogLevel(Enum):
    """Enumeration for different log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Logger:
    """
    Logger class with colored console output and progress indicators.

    Provides structured logging with different levels, colors, and formatting
    utilities for network discovery operations.
    """

    # Color mapping for different log levels
    LEVEL_COLORS = {
        LogLevel.DEBUG: Fore.CYAN,
        LogLevel.INFO: Fore.GREEN,
        LogLevel.WARNING: Fore.YELLOW,
        LogLevel.ERROR: Fore.RED,
    }

    # Symbol mapping for different log levels
    LEVEL_SYMBOLS = {
        LogLevel.DEBUG: "🔍",
        LogLevel.INFO: "ℹ️",
        LogLevel.WARNING: "⚠️",
        LogLevel.ERROR: "❌",
    }

    def __init__(
        self, name: str = "NetworkDiscovery", min_level: LogLevel = LogLevel.INFO
    ):
        """
        Initialize the Logger.

        Args:
            name: Name of the logger (default: "NetworkDiscovery")
            min_level: Minimum log level to display (default: INFO)
        """
        self.name = name
        self.min_level = min_level
        self._progress_active = False
        self._last_progress_length = 0

    def _should_log(self, level: LogLevel) -> bool:
        """
        Check if a message should be logged based on minimum level.

        Args:
            level: Log level to check

        Returns:
            True if message should be logged, False otherwise
        """
        level_order = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3,
        }
        return level_order[level] >= level_order[self.min_level]

    def _format_timestamp(self) -> str:
        """
        Format current timestamp for log messages.

        Returns:
            Formatted timestamp string
        """
        return datetime.now().strftime("%H:%M:%S")

    def _log(self, level: LogLevel, message: str, **kwargs) -> None:
        """
        Internal logging method that handles formatting and output.

        Args:
            level: Log level
            message: Message to log
            **kwargs: Additional formatting arguments
        """
        if not self._should_log(level):
            return

        # Format the log message
        timestamp = self._format_timestamp()
        color = self.LEVEL_COLORS[level]
        symbol = self.LEVEL_SYMBOLS[level]

        # Build the formatted message
        formatted_message = (
            f"{Style.DIM}[{timestamp}]{Style.RESET_ALL} "
            f"{color}{symbol} {level.value:<7}{Style.RESET_ALL} "
            f"{message}"
        )

        # Add any additional formatting
        if kwargs:
            details = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
            formatted_message += f" {Style.DIM}({details}){Style.RESET_ALL}"

        print(
            formatted_message,
            file=sys.stdout if level != LogLevel.ERROR else sys.stderr,
        )

    def debug(self, message: str, **kwargs) -> None:
        """
        Log a debug message.

        Args:
            message: Debug message
            **kwargs: Additional context information
        """
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """
        Log an info message.

        Args:
            message: Info message
            **kwargs: Additional context information
        """
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """
        Log a warning message.

        Args:
            message: Warning message
            **kwargs: Additional context information
        """
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(
        self, message: str, exception: Optional[Exception] = None, **kwargs
    ) -> None:
        """
        Log an error message.

        Args:
            message: Error message
            exception: Optional exception object for additional context
            **kwargs: Additional context information
        """
        if exception:
            kwargs["exception"] = f"{type(exception).__name__}: {str(exception)}"
        self._log(LogLevel.ERROR, message, **kwargs)

    def success(self, message: str, **kwargs) -> None:
        """
        Log a success message (formatted as INFO with special styling).

        Args:
            message: Success message
            **kwargs: Additional context information
        """
        if not self._should_log(LogLevel.INFO):
            return

        if self._progress_active:
            self._clear_progress()

        timestamp = self._format_timestamp()
        formatted_message = (
            f"{Style.DIM}[{timestamp}]{Style.RESET_ALL} "
            f"{Fore.GREEN}✅ SUCCESS {Style.RESET_ALL} "
            f"{Style.BRIGHT}{message}{Style.RESET_ALL}"
        )

        if kwargs:
            details = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
            formatted_message += f" {Style.DIM}({details}){Style.RESET_ALL}"

        print(formatted_message)

    def section(self, title: str) -> None:
        """
        Log a section header for organizing output.

        Args:
            title: Section title
        """
        if not self._should_log(LogLevel.INFO):
            return

        separator = "=" * 60
        print(f"\n{Fore.BLUE}{Style.BRIGHT}{separator}")
        print(f"  {title.upper()}")
        print(f"{separator}{Style.RESET_ALL}\n")

    def progress_start(self, message: str) -> None:
        """
        Start a progress indicator for long-running operations.

        Args:
            message: Progress message to display
        """
        if not self._should_log(LogLevel.INFO):
            return

        timestamp = self._format_timestamp()
        progress_msg = (
            f"{Style.DIM}[{timestamp}]{Style.RESET_ALL} "
            f"{Fore.BLUE}⏳ PROGRESS{Style.RESET_ALL} "
            f"{message}..."
        )

        print(progress_msg, flush=True)  # Removed end="" to allow newline
        self._progress_active = True
        self._last_progress_length = 0  # No need to track length anymore

    def progress_update(self, message: str) -> None:
        """
        Update the current progress indicator.

        Args:
            message: Updated progress message
        """
        if not self._progress_active or not self._should_log(LogLevel.INFO):
            return

        timestamp = self._format_timestamp()
        progress_msg = (
            f"{Style.DIM}[{timestamp}]{Style.RESET_ALL} "
            f"{Fore.BLUE}⏳ PROGRESS{Style.RESET_ALL} "
            f"{message}..."
        )

        print(progress_msg, flush=True)  # Removed clearing and end=""

    def progress_end(self, final_message: Optional[str] = None) -> None:
        """
        End the current progress indicator.

        Args:
            final_message: Optional final message to display
        """
        if not self._progress_active:
            return

        self._progress_active = False

        if final_message and self._should_log(LogLevel.INFO):
            self.success(final_message)

    def _clear_progress(self) -> None:
        """Clear the current progress line (no longer needed with newline approach)."""
        pass  # No longer needed since we use newlines

    def table_header(self, headers: list[str], widths: list[int]) -> None:
        """
        Print a formatted table header.

        Args:
            headers: List of header names
            widths: List of column widths
        """
        if not self._should_log(LogLevel.INFO):
            return

        # Print header row
        header_row = " | ".join(
            [f"{header:<{width}}" for header, width in zip(headers, widths)]
        )
        print(f"{Style.BRIGHT}{header_row}{Style.RESET_ALL}")

        # Print separator
        separator = "-+-".join(["-" * width for width in widths])
        print(f"{Style.DIM}{separator}{Style.RESET_ALL}")

    def table_row(
        self, values: list[str], widths: list[int], highlight: bool = False
    ) -> None:
        """
        Print a formatted table row.

        Args:
            values: List of values to display
            widths: List of column widths
            highlight: Whether to highlight this row
        """
        if not self._should_log(LogLevel.INFO):
            return

        row = " | ".join(
            [f"{str(value):<{width}}" for value, width in zip(values, widths)]
        )

        if highlight:
            print(f"{Style.BRIGHT}{row}{Style.RESET_ALL}")
        else:
            print(row)

    def network_info(self, network: str, host_ip: str, excluded: list[str]) -> None:
        """
        Display network configuration information in a formatted way.

        Args:
            network: Network range being scanned
            host_ip: Host IP address
            excluded: List of excluded IP addresses
        """
        if not self._should_log(LogLevel.INFO):
            return

        print(f"\n{Fore.CYAN}{Style.BRIGHT}🌐 NETWORK CONFIGURATION{Style.RESET_ALL}")
        print(f"  Network Range: {Style.BRIGHT}{network}{Style.RESET_ALL}")
        print(f"  Host IP:       {Style.BRIGHT}{host_ip}{Style.RESET_ALL}")
        print(
            f"  Excluded IPs:  {Style.BRIGHT}{', '.join(excluded)}{Style.RESET_ALL}\n"
        )


# Global logger instance
logger = Logger()


def set_log_level(level: LogLevel) -> None:
    """
    Set the global log level.

    Args:
        level: Minimum log level to display
    """
    global logger
    logger.min_level = level


def get_logger(name: str = "NetworkDiscovery") -> Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return Logger(name)
