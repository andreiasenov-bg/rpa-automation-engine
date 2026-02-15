"""
Google Sheets Integration — Production-grade integration for Google Sheets API.

Features:
- Service account authentication with google-auth
- Connection pooling and retry logic with exponential backoff
- Tool functions for Claude to invoke via function calling
- Full CRUD operations: read, write, append, find, update
- Comprehensive error handling and logging
- Input validation and security
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import structlog
from google.auth.service_account import Credentials
from google.oauth2.credentials import Credentials as OAuth2Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = structlog.get_logger(__name__)


# ─── Constants ──────────────────────────────────────────────────────

SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
DEFAULT_BATCH_SIZE = 1000
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0


# ─── Exceptions ──────────────────────────────────────────────────────

class GoogleSheetsError(Exception):
    """Base exception for Google Sheets integration."""
    pass


class SpreadsheetNotFoundError(GoogleSheetsError):
    """Raised when spreadsheet cannot be accessed."""
    pass


class PermissionDeniedError(GoogleSheetsError):
    """Raised when user lacks permission to access spreadsheet."""
    pass


class RateLimitError(GoogleSheetsError):
    """Raised when API rate limit is exceeded."""
    pass


class InvalidInputError(GoogleSheetsError):
    """Raised when input validation fails."""
    pass


# ─── Helper Functions ───────────────────────────────────────────────

def _validate_spreadsheet_id(spreadsheet_id: str) -> None:
    """Validate spreadsheet ID format."""
    if not spreadsheet_id or not isinstance(spreadsheet_id, str):
        raise InvalidInputError("spreadsheet_id must be a non-empty string")
    if len(spreadsheet_id) < 20:
        raise InvalidInputError("Invalid spreadsheet ID format (too short)")


def _validate_range(range_str: str) -> None:
    """Validate A1 range format."""
    if not range_str or not isinstance(range_str, str):
        raise InvalidInputError("range must be a non-empty string (e.g., 'A1:B10')")


def _validate_sheet_name(sheet_name: str) -> None:
    """Validate sheet name."""
    if not sheet_name or not isinstance(sheet_name, str):
        raise InvalidInputError("sheet_name must be a non-empty string")


def _parse_a1_reference(cell_ref: str) -> tuple[str, int]:
    """Parse A1-style cell reference into column letter and row number.

    Args:
        cell_ref: Cell reference like "A1", "B5", "Z100"

    Returns:
        Tuple of (column_letter, row_number)
    """
    import re
    match = re.match(r"([A-Z]+)(\d+)", cell_ref.upper())
    if not match:
        raise InvalidInputError(f"Invalid cell reference format: {cell_ref}")
    return match.group(1), int(match.group(2))


def _build_range_with_sheet(range_str: str, sheet_name: str) -> str:
    """Build full A1 range with sheet name prefix."""
    if not range_str:
        return f"'{sheet_name}'!A1"
    if "!" in range_str:
        return range_str  # Already has sheet prefix
    return f"'{sheet_name}'!{range_str}"


async def _retry_with_backoff(
    func: Callable,
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_RETRY_DELAY,
) -> Any:
    """Execute a function with exponential backoff retry logic.

    Args:
        func: Async callable to execute
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds

    Returns:
        Function result

    Raises:
        RateLimitError: If rate limit is exceeded
        GoogleSheetsError: If all retries fail
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            return await func()
        except HttpError as e:
            error_code = e.resp.status
            last_error = e

            if error_code == 429:  # Rate limited
                retry_after = int(e.resp.get("retry-after", 10 * (2 ** attempt)))
                logger.warning(
                    "Google Sheets API rate limited",
                    attempt=attempt,
                    retry_after=retry_after,
                )
                await asyncio.sleep(retry_after)
                continue

            elif error_code == 403:  # Permission denied
                logger.error("Permission denied accessing Google Sheets", error=str(e))
                raise PermissionDeniedError(f"Permission denied: {str(e)}")

            elif error_code == 404:  # Not found
                logger.error("Spreadsheet not found", error=str(e))
                raise SpreadsheetNotFoundError(f"Spreadsheet not found: {str(e)}")

            elif error_code >= 500:  # Server error — retry
                delay = initial_delay * (2 ** attempt)
                logger.warning(
                    "Google API server error, retrying",
                    status=error_code,
                    attempt=attempt,
                    delay=delay,
                )
                await asyncio.sleep(delay)
                continue

            else:
                raise GoogleSheetsError(f"Google Sheets API error: {str(e)}")

        except Exception as e:
            logger.error("Unexpected error in Google Sheets operation", error=str(e))
            last_error = e

            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                await asyncio.sleep(delay)
                continue

    raise GoogleSheetsError(f"Failed after {max_retries} retries: {str(last_error)}")


# ─── Google Sheets Client ───────────────────────────────────────────

class GoogleSheetsClient:
    """Client for Google Sheets API with async support and robust error handling.

    Supports:
    - Service account authentication
    - Connection pooling
    - Automatic retry with exponential backoff
    - Comprehensive error handling
    """

    def __init__(self, credentials_path: Optional[str] = None):
        """Initialize Google Sheets client.

        Args:
            credentials_path: Path to service account JSON file.
                             If not provided, reads GOOGLE_SHEETS_CREDENTIALS env var.
        """
        self._credentials_path = credentials_path or os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        self._credentials: Optional[Credentials] = None
        self._service: Optional[Any] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        logger.info("GoogleSheetsClient initialized", credentials_path=bool(self._credentials_path))

    def _load_credentials(self) -> Credentials:
        """Load service account credentials from file."""
        if not self._credentials_path:
            raise GoogleSheetsError(
                "Google Sheets credentials not configured. "
                "Set GOOGLE_SHEETS_CREDENTIALS env var or pass credentials_path."
            )

        path = Path(self._credentials_path)
        if not path.exists():
            raise GoogleSheetsError(f"Credentials file not found: {self._credentials_path}")

        try:
            creds = Credentials.from_service_account_file(
                self._credentials_path,
                scopes=SHEETS_SCOPES,
            )
            logger.info("Service account credentials loaded", email=creds.service_account_email)
            return creds
        except Exception as e:
            logger.error("Failed to load service account credentials", error=str(e))
            raise GoogleSheetsError(f"Failed to load credentials: {str(e)}")

    def _get_service(self) -> Any:
        """Get or create Google Sheets API service."""
        if self._service is not None:
            return self._service

        if self._credentials is None:
            self._credentials = self._load_credentials()

        try:
            self._service = build("sheets", "v4", credentials=self._credentials)
            logger.info("Google Sheets API service created")
            return self._service
        except Exception as e:
            logger.error("Failed to create Google Sheets service", error=str(e))
            raise GoogleSheetsError(f"Failed to create API service: {str(e)}")

    async def read_range(
        self,
        spreadsheet_id: str,
        range_str: str,
        sheet_name: str = "Sheet1",
    ) -> List[List[Any]]:
        """Read a range of cells from a spreadsheet.

        Args:
            spreadsheet_id: ID of the spreadsheet
            range_str: A1 range like "A1:B10"
            sheet_name: Name of the sheet (default: Sheet1)

        Returns:
            List of rows (each row is a list of cell values)
        """
        _validate_spreadsheet_id(spreadsheet_id)
        _validate_range(range_str)
        _validate_sheet_name(sheet_name)

        range_full = _build_range_with_sheet(range_str, sheet_name)

        async def _read():
            service = self._get_service()
            request = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_full,
            )
            response = request.execute()
            return response.get("values", [])

        try:
            result = await _retry_with_backoff(_read)
            logger.info(
                "Range read successfully",
                spreadsheet_id=spreadsheet_id[:10],
                range=range_full,
                rows=len(result),
            )
            return result
        except GoogleSheetsError:
            raise
        except Exception as e:
            logger.error("Failed to read range", error=str(e), range=range_full)
            raise GoogleSheetsError(f"Failed to read range: {str(e)}")

    async def write_range(
        self,
        spreadsheet_id: str,
        range_str: str,
        values: List[List[Any]],
        sheet_name: str = "Sheet1",
    ) -> Dict[str, Any]:
        """Write values to a range of cells.

        Args:
            spreadsheet_id: ID of the spreadsheet
            range_str: A1 range like "A1:B10"
            values: List of rows to write
            sheet_name: Name of the sheet

        Returns:
            Update response metadata
        """
        _validate_spreadsheet_id(spreadsheet_id)
        _validate_range(range_str)
        _validate_sheet_name(sheet_name)

        if not values:
            raise InvalidInputError("values cannot be empty")

        range_full = _build_range_with_sheet(range_str, sheet_name)

        async def _write():
            service = self._get_service()
            body = {"values": values}
            request = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_full,
                valueInputOption="RAW",
                body=body,
            )
            response = request.execute()
            return response

        try:
            result = await _retry_with_backoff(_write)
            logger.info(
                "Range written successfully",
                spreadsheet_id=spreadsheet_id[:10],
                range=range_full,
                rows=len(values),
            )
            return {
                "spreadsheet_id": spreadsheet_id,
                "range": range_full,
                "rows_updated": result.get("updatedRows", 0),
                "columns_updated": result.get("updatedColumns", 0),
                "cells_updated": result.get("updatedCells", 0),
            }
        except GoogleSheetsError:
            raise
        except Exception as e:
            logger.error("Failed to write range", error=str(e), range=range_full)
            raise GoogleSheetsError(f"Failed to write range: {str(e)}")

    async def append_row(
        self,
        spreadsheet_id: str,
        values: List[Any],
        sheet_name: str = "Sheet1",
    ) -> Dict[str, Any]:
        """Append a single row to the end of a sheet.

        Args:
            spreadsheet_id: ID of the spreadsheet
            values: List of cell values to append
            sheet_name: Name of the sheet

        Returns:
            Append response metadata
        """
        _validate_spreadsheet_id(spreadsheet_id)
        _validate_sheet_name(sheet_name)

        if not isinstance(values, list):
            raise InvalidInputError("values must be a list")

        range_full = f"'{sheet_name}'!A:Z"  # Append to full range

        async def _append():
            service = self._get_service()
            body = {"values": [values]}
            request = service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_full,
                valueInputOption="RAW",
                body=body,
            )
            response = request.execute()
            return response

        try:
            result = await _retry_with_backoff(_append)
            logger.info(
                "Row appended successfully",
                spreadsheet_id=spreadsheet_id[:10],
                sheet=sheet_name,
                range=result.get("updates", {}).get("updatedRange", ""),
            )
            return {
                "spreadsheet_id": spreadsheet_id,
                "sheet_name": sheet_name,
                "updated_range": result.get("updates", {}).get("updatedRange", ""),
                "rows_appended": result.get("updates", {}).get("updatedRows", 1),
            }
        except GoogleSheetsError:
            raise
        except Exception as e:
            logger.error("Failed to append row", error=str(e), sheet=sheet_name)
            raise GoogleSheetsError(f"Failed to append row: {str(e)}")

    async def find_row(
        self,
        spreadsheet_id: str,
        search_column: str,
        search_value: str,
        sheet_name: str = "Sheet1",
    ) -> Optional[Dict[str, Any]]:
        """Find first row where a column matches a value.

        Args:
            spreadsheet_id: ID of the spreadsheet
            search_column: Column letter (e.g., "A", "B")
            search_value: Value to search for
            sheet_name: Name of the sheet

        Returns:
            Dict with row_number and values, or None if not found
        """
        _validate_spreadsheet_id(spreadsheet_id)
        _validate_sheet_name(sheet_name)

        if not search_column or not isinstance(search_column, str):
            raise InvalidInputError("search_column must be a valid column letter")

        if search_value is None or search_value == "":
            raise InvalidInputError("search_value cannot be empty")

        search_str = str(search_value).lower()

        try:
            # Read entire column to search
            range_str = f"{search_column}:Z"
            rows = await self.read_range(spreadsheet_id, range_str, sheet_name)

            # Find matching row
            for row_idx, row in enumerate(rows, start=1):
                if row and str(row[0]).lower() == search_str:
                    logger.info(
                        "Row found",
                        spreadsheet_id=spreadsheet_id[:10],
                        row_number=row_idx,
                        search_value=search_value,
                    )
                    return {
                        "row_number": row_idx,
                        "values": row,
                    }

            logger.info(
                "No matching row found",
                spreadsheet_id=spreadsheet_id[:10],
                search_column=search_column,
                search_value=search_value,
            )
            return None

        except GoogleSheetsError:
            raise
        except Exception as e:
            logger.error("Failed to find row", error=str(e))
            raise GoogleSheetsError(f"Failed to find row: {str(e)}")

    async def update_cell(
        self,
        spreadsheet_id: str,
        row: int,
        column: int,
        value: Any,
        sheet_name: str = "Sheet1",
    ) -> Dict[str, Any]:
        """Update a single cell value.

        Args:
            spreadsheet_id: ID of the spreadsheet
            row: Row number (1-indexed)
            column: Column number (1-indexed)
            value: Value to set
            sheet_name: Name of the sheet

        Returns:
            Update response metadata
        """
        _validate_spreadsheet_id(spreadsheet_id)
        _validate_sheet_name(sheet_name)

        if not isinstance(row, int) or row < 1:
            raise InvalidInputError("row must be a positive integer")
        if not isinstance(column, int) or column < 1:
            raise InvalidInputError("column must be a positive integer")

        # Convert column number to letter (1=A, 2=B, etc.)
        col_letter = ""
        col = column
        while col > 0:
            col -= 1
            col_letter = chr(65 + (col % 26)) + col_letter
            col //= 26

        cell_ref = f"{col_letter}{row}"
        range_full = _build_range_with_sheet(cell_ref, sheet_name)

        async def _update():
            service = self._get_service()
            body = {"values": [[value]]}
            request = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_full,
                valueInputOption="RAW",
                body=body,
            )
            response = request.execute()
            return response

        try:
            result = await _retry_with_backoff(_update)
            logger.info(
                "Cell updated successfully",
                spreadsheet_id=spreadsheet_id[:10],
                cell=cell_ref,
                value=str(value)[:50],
            )
            return {
                "spreadsheet_id": spreadsheet_id,
                "cell": cell_ref,
                "value": value,
                "cells_updated": result.get("updatedCells", 1),
            }
        except GoogleSheetsError:
            raise
        except Exception as e:
            logger.error("Failed to update cell", error=str(e), cell=cell_ref)
            raise GoogleSheetsError(f"Failed to update cell: {str(e)}")


# ─── Tool Registration ───────────────────────────────────────────────

async def sheets_read_range(inputs: Dict[str, Any], client: GoogleSheetsClient) -> Dict[str, Any]:
    """Tool handler: Read a range of cells."""
    try:
        spreadsheet_id = inputs.get("spreadsheet_id", "")
        range_str = inputs.get("range", "A1:Z100")
        sheet_name = inputs.get("sheet_name", "Sheet1")

        rows = await client.read_range(spreadsheet_id, range_str, sheet_name)

        return {
            "success": True,
            "rows": rows,
            "row_count": len(rows),
        }
    except GoogleSheetsError as e:
        logger.error("sheets_read_range failed", error=str(e))
        return {"success": False, "error": str(e)}


async def sheets_write_range(inputs: Dict[str, Any], client: GoogleSheetsClient) -> Dict[str, Any]:
    """Tool handler: Write values to a range."""
    try:
        spreadsheet_id = inputs.get("spreadsheet_id", "")
        range_str = inputs.get("range", "A1")
        values = inputs.get("values", [])
        sheet_name = inputs.get("sheet_name", "Sheet1")

        result = await client.write_range(spreadsheet_id, range_str, values, sheet_name)

        return {
            "success": True,
            **result,
        }
    except GoogleSheetsError as e:
        logger.error("sheets_write_range failed", error=str(e))
        return {"success": False, "error": str(e)}


async def sheets_append_row(inputs: Dict[str, Any], client: GoogleSheetsClient) -> Dict[str, Any]:
    """Tool handler: Append a row to the end of a sheet."""
    try:
        spreadsheet_id = inputs.get("spreadsheet_id", "")
        values = inputs.get("values", [])
        sheet_name = inputs.get("sheet_name", "Sheet1")

        result = await client.append_row(spreadsheet_id, values, sheet_name)

        return {
            "success": True,
            **result,
        }
    except GoogleSheetsError as e:
        logger.error("sheets_append_row failed", error=str(e))
        return {"success": False, "error": str(e)}


async def sheets_find_row(inputs: Dict[str, Any], client: GoogleSheetsClient) -> Dict[str, Any]:
    """Tool handler: Find a row by searching a column."""
    try:
        spreadsheet_id = inputs.get("spreadsheet_id", "")
        search_column = inputs.get("search_column", "A")
        search_value = inputs.get("search_value", "")
        sheet_name = inputs.get("sheet_name", "Sheet1")

        result = await client.find_row(
            spreadsheet_id, search_column, search_value, sheet_name
        )

        if result is None:
            return {
                "success": True,
                "found": False,
                "message": f"No row found with {search_column}={search_value}",
            }

        return {
            "success": True,
            "found": True,
            **result,
        }
    except GoogleSheetsError as e:
        logger.error("sheets_find_row failed", error=str(e))
        return {"success": False, "error": str(e)}


async def sheets_update_cell(inputs: Dict[str, Any], client: GoogleSheetsClient) -> Dict[str, Any]:
    """Tool handler: Update a specific cell."""
    try:
        spreadsheet_id = inputs.get("spreadsheet_id", "")
        row = inputs.get("row", 1)
        column = inputs.get("column", 1)
        value = inputs.get("value", "")
        sheet_name = inputs.get("sheet_name", "Sheet1")

        result = await client.update_cell(
            spreadsheet_id, row, column, value, sheet_name
        )

        return {
            "success": True,
            **result,
        }
    except GoogleSheetsError as e:
        logger.error("sheets_update_cell failed", error=str(e))
        return {"success": False, "error": str(e)}


def register_sheets_tools(tool_registry: Any, sheets_client: GoogleSheetsClient) -> None:
    """Register all Google Sheets tools with the ToolRegistry.

    Args:
        tool_registry: ToolRegistry instance from ClaudeClient
        sheets_client: GoogleSheetsClient instance
    """

    # Helper to create handler with client binding
    def make_handler(handler_func: Callable) -> Callable:
        async def wrapper(inputs: Dict[str, Any]) -> Dict[str, Any]:
            return await handler_func(inputs, sheets_client)
        return wrapper

    # Tool 1: Read Range
    tool_registry.register(
        name="sheets_read_range",
        description=(
            "Read a range of cells from a Google Sheet. Returns all values in the specified range. "
            "Use this to retrieve data from a spreadsheet."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "The Google Sheets spreadsheet ID (from the URL)",
                },
                "range": {
                    "type": "string",
                    "description": (
                        "The A1 range to read (e.g., 'A1:D10', 'A:B', 'A1'). "
                        "Defaults to A1:Z100 if not specified."
                    ),
                    "default": "A1:Z100",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Name of the sheet to read from (defaults to 'Sheet1')",
                    "default": "Sheet1",
                },
            },
            "required": ["spreadsheet_id"],
        },
        handler=make_handler(sheets_read_range),
    )

    # Tool 2: Write Range
    tool_registry.register(
        name="sheets_write_range",
        description=(
            "Write values to a range of cells in a Google Sheet. "
            "This will overwrite any existing values in the target range."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "The Google Sheets spreadsheet ID",
                },
                "range": {
                    "type": "string",
                    "description": (
                        "The A1 range to write to (e.g., 'A1', 'A1:C3'). "
                        "The range should match the dimensions of the values."
                    ),
                },
                "values": {
                    "type": "array",
                    "description": (
                        "List of rows to write, where each row is a list of cell values. "
                        "Example: [[1, 2, 3], [4, 5, 6]]"
                    ),
                    "items": {
                        "type": "array",
                        "items": {},  # Accepts any JSON-serializable value
                    },
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Name of the sheet to write to (defaults to 'Sheet1')",
                    "default": "Sheet1",
                },
            },
            "required": ["spreadsheet_id", "range", "values"],
        },
        handler=make_handler(sheets_write_range),
    )

    # Tool 3: Append Row
    tool_registry.register(
        name="sheets_append_row",
        description=(
            "Append a single row of values to the end of a Google Sheet. "
            "This is useful for adding new records or log entries."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "The Google Sheets spreadsheet ID",
                },
                "values": {
                    "type": "array",
                    "description": (
                        "List of cell values to append as a single row. "
                        "Example: ['John', 'Doe', 'john@example.com']"
                    ),
                    "items": {},  # Accepts any JSON-serializable value
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Name of the sheet to append to (defaults to 'Sheet1')",
                    "default": "Sheet1",
                },
            },
            "required": ["spreadsheet_id", "values"],
        },
        handler=make_handler(sheets_append_row),
    )

    # Tool 4: Find Row
    tool_registry.register(
        name="sheets_find_row",
        description=(
            "Find the first row where a specified column matches a given value. "
            "Returns the row number and values if found, or null if not found."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "The Google Sheets spreadsheet ID",
                },
                "search_column": {
                    "type": "string",
                    "description": (
                        "Column letter to search in (e.g., 'A', 'B', 'C'). "
                        "Search is case-insensitive."
                    ),
                    "default": "A",
                },
                "search_value": {
                    "type": "string",
                    "description": "Value to search for in the column",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Name of the sheet to search (defaults to 'Sheet1')",
                    "default": "Sheet1",
                },
            },
            "required": ["spreadsheet_id", "search_value"],
        },
        handler=make_handler(sheets_find_row),
    )

    # Tool 5: Update Cell
    tool_registry.register(
        name="sheets_update_cell",
        description=(
            "Update the value of a single cell in a Google Sheet. "
            "Specify the cell using row and column numbers (1-indexed)."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "The Google Sheets spreadsheet ID",
                },
                "row": {
                    "type": "integer",
                    "description": "Row number (1-indexed, where 1 is the first row)",
                },
                "column": {
                    "type": "integer",
                    "description": "Column number (1-indexed, where 1 is column A)",
                },
                "value": {
                    "description": "The value to set in the cell (string, number, boolean, etc.)",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Name of the sheet (defaults to 'Sheet1')",
                    "default": "Sheet1",
                },
            },
            "required": ["spreadsheet_id", "row", "column", "value"],
        },
        handler=make_handler(sheets_update_cell),
    )

    logger.info(
        "Google Sheets tools registered",
        tool_count=5,
        tools=["sheets_read_range", "sheets_write_range", "sheets_append_row",
               "sheets_find_row", "sheets_update_cell"],
    )
