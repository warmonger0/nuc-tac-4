import json
import pandas as pd
import sqlite3
import io
import re
import logging
from typing import Dict, Any, List, Set
from .sql_security import (
    execute_query_safely,
    validate_identifier,
    SQLSecurityError
)
from .constants import NESTED_FIELD_DELIMITER, ARRAY_INDEX_DELIMITER

logger = logging.getLogger(__name__)

def sanitize_table_name(table_name: str) -> str:
    """
    Sanitize table name for SQLite by removing/replacing bad characters
    and validating against SQL injection
    """
    # Remove file extension if present
    if '.' in table_name:
        table_name = table_name.rsplit('.', 1)[0]
    
    # Replace bad characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', table_name)
    
    # Ensure it starts with a letter or underscore
    if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
        sanitized = '_' + sanitized
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = 'table'
    
    # Validate the sanitized name
    try:
        validate_identifier(sanitized, "table")
    except SQLSecurityError:
        # If validation fails, use a safe default
        sanitized = f"table_{hash(table_name) % 100000}"
    
    return sanitized

def convert_csv_to_sqlite(csv_content: bytes, table_name: str) -> Dict[str, Any]:
    """
    Convert CSV file content to SQLite table
    """
    try:
        # Sanitize table name
        table_name = sanitize_table_name(table_name)
        
        # Read CSV into pandas DataFrame
        df = pd.read_csv(io.BytesIO(csv_content))
        
        # Clean column names
        df.columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df.columns]
        
        # Connect to SQLite database
        conn = sqlite3.connect("db/database.db")
        
        # Write DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # Get schema information using safe query execution
        cursor_info = execute_query_safely(
            conn,
            "PRAGMA table_info({table})",
            identifier_params={'table': table_name}
        )
        columns_info = cursor_info.fetchall()
        
        schema = {}
        for col in columns_info:
            schema[col[1]] = col[2]  # column_name: data_type
        
        # Get sample data using safe query execution
        cursor_sample = execute_query_safely(
            conn,
            "SELECT * FROM {table} LIMIT 5",
            identifier_params={'table': table_name}
        )
        sample_rows = cursor_sample.fetchall()
        column_names = [col[1] for col in columns_info]
        sample_data = [dict(zip(column_names, row)) for row in sample_rows]
        
        # Get row count using safe query execution
        cursor_count = execute_query_safely(
            conn,
            "SELECT COUNT(*) FROM {table}",
            identifier_params={'table': table_name}
        )
        row_count = cursor_count.fetchone()[0]
        
        conn.close()
        
        return {
            'table_name': table_name,
            'schema': schema,
            'row_count': row_count,
            'sample_data': sample_data
        }
        
    except Exception as e:
        raise Exception(f"Error converting CSV to SQLite: {str(e)}")

def convert_json_to_sqlite(json_content: bytes, table_name: str) -> Dict[str, Any]:
    """
    Convert JSON file content to SQLite table
    """
    try:
        # Sanitize table name
        table_name = sanitize_table_name(table_name)
        
        # Parse JSON
        data = json.loads(json_content.decode('utf-8'))
        
        # Ensure it's a list of objects
        if not isinstance(data, list):
            raise ValueError("JSON must be an array of objects")
        
        if not data:
            raise ValueError("JSON array is empty")
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(data)
        
        # Clean column names
        df.columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df.columns]
        
        # Connect to SQLite database
        conn = sqlite3.connect("db/database.db")
        
        # Write DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # Get schema information using safe query execution
        cursor_info = execute_query_safely(
            conn,
            "PRAGMA table_info({table})",
            identifier_params={'table': table_name}
        )
        columns_info = cursor_info.fetchall()
        
        schema = {}
        for col in columns_info:
            schema[col[1]] = col[2]  # column_name: data_type
        
        # Get sample data using safe query execution
        cursor_sample = execute_query_safely(
            conn,
            "SELECT * FROM {table} LIMIT 5",
            identifier_params={'table': table_name}
        )
        sample_rows = cursor_sample.fetchall()
        column_names = [col[1] for col in columns_info]
        sample_data = [dict(zip(column_names, row)) for row in sample_rows]
        
        # Get row count using safe query execution
        cursor_count = execute_query_safely(
            conn,
            "SELECT COUNT(*) FROM {table}",
            identifier_params={'table': table_name}
        )
        row_count = cursor_count.fetchone()[0]
        
        conn.close()
        
        return {
            'table_name': table_name,
            'schema': schema,
            'row_count': row_count,
            'sample_data': sample_data
        }
        
    except Exception as e:
        raise Exception(f"Error converting JSON to SQLite: {str(e)}")

def discover_all_fields(records: List[Dict[str, Any]], prefix: str = "") -> Set[str]:
    """
    Discover all possible flattened field names across all records.

    This function recursively traverses nested objects and arrays to build
    a complete set of all field paths that exist across any record in the dataset.

    Args:
        records: List of dictionaries to analyze
        prefix: Current field path prefix (used in recursion)

    Returns:
        Set of all flattened field names using NESTED_FIELD_DELIMITER and
        ARRAY_INDEX_DELIMITER conventions

    Field naming conventions:
    - Nested objects: parent__child (e.g., "address__city")
    - Array items: field_0, field_1, field_2 (e.g., "tags_0", "tags_1")
    - Combined: deeply__nested__array_0__field

    Edge cases handled:
    - Empty arrays: no fields generated
    - Null values: field name included but no further traversal
    - Mixed types: all variants discovered
    - Different fields across records: union of all fields
    """
    all_fields = set()

    for record in records:
        if not isinstance(record, dict):
            continue

        for key, value in record.items():
            # Build the field name with appropriate prefix
            field_name = f"{prefix}{NESTED_FIELD_DELIMITER}{key}" if prefix else key

            if value is None:
                # Null values are included as fields
                all_fields.add(field_name)
            elif isinstance(value, dict):
                # Recursively discover nested object fields
                nested_fields = discover_all_fields([value], field_name)
                all_fields.update(nested_fields)
            elif isinstance(value, list):
                if not value:
                    # Empty arrays generate no fields
                    continue

                # Process each array item with indexed field names
                for idx, item in enumerate(value):
                    indexed_field = f"{field_name}{ARRAY_INDEX_DELIMITER}{idx}"

                    if isinstance(item, dict):
                        # Array of objects: recursively discover fields
                        nested_fields = discover_all_fields([item], indexed_field)
                        all_fields.update(nested_fields)
                    else:
                        # Array of primitives: add indexed field
                        all_fields.add(indexed_field)
            else:
                # Primitive value (string, number, boolean)
                all_fields.add(field_name)

    return all_fields

def flatten_record(record: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    """
    Flatten a nested dictionary into a single-level dictionary.

    Converts nested structures into flat key-value pairs using consistent
    delimiter conventions. Handles nested objects, arrays of primitives,
    and arrays of objects.

    Args:
        record: Dictionary to flatten (may contain nested structures)
        prefix: Current field path prefix (used in recursion)

    Returns:
        Flattened dictionary with concatenated field names

    Examples:
        {"user": {"name": "John"}} -> {"user__name": "John"}
        {"tags": ["a", "b"]} -> {"tags_0": "a", "tags_1": "b"}
        {"items": [{"id": 1}, {"id": 2}]} -> {"items_0__id": 1, "items_1__id": 2}

    Edge cases handled:
    - None values: preserved as None
    - Empty objects: no fields generated
    - Empty arrays: no fields generated
    - Non-dict input: returns empty dict
    """
    flattened = {}

    if not isinstance(record, dict):
        return flattened

    for key, value in record.items():
        # Build the field name with appropriate prefix
        field_name = f"{prefix}{NESTED_FIELD_DELIMITER}{key}" if prefix else key

        if value is None:
            # Preserve None values
            flattened[field_name] = None
        elif isinstance(value, dict):
            # Recursively flatten nested objects
            nested_flat = flatten_record(value, field_name)
            flattened.update(nested_flat)
        elif isinstance(value, list):
            if not value:
                # Empty arrays generate no fields
                continue

            # Process each array item with indexed field names
            for idx, item in enumerate(value):
                indexed_field = f"{field_name}{ARRAY_INDEX_DELIMITER}{idx}"

                if isinstance(item, dict):
                    # Array of objects: recursively flatten
                    nested_flat = flatten_record(item, indexed_field)
                    flattened.update(nested_flat)
                else:
                    # Array of primitives: add indexed field directly
                    flattened[indexed_field] = item
        else:
            # Primitive value (string, number, boolean)
            flattened[field_name] = value

    return flattened

def convert_jsonl_to_sqlite(jsonl_content: bytes, table_name: str) -> Dict[str, Any]:
    """
    Convert JSONL (JSON Lines) file content to SQLite table.

    JSONL format consists of newline-delimited JSON objects, with each line
    containing a valid JSON object. This function:
    1. Parses each line as separate JSON object
    2. Discovers all possible fields across all records
    3. Flattens nested structures using delimiter conventions
    4. Creates a normalized SQLite table with all fields

    Args:
        jsonl_content: Raw bytes of JSONL file
        table_name: Desired table name (will be sanitized)

    Returns:
        Dictionary containing:
        - table_name: Sanitized table name used
        - schema: Column names and data types
        - row_count: Number of records inserted
        - sample_data: First 5 rows as list of dicts

    Raises:
        Exception: If file is empty, all lines invalid, or database error occurs

    Flattening conventions:
    - Nested objects: parent__child
    - Array items: field_0, field_1
    - Missing fields: filled with None

    Invalid JSON lines are skipped with warning logs rather than failing
    the entire upload.
    """
    try:
        # Sanitize table name
        table_name = sanitize_table_name(table_name)

        # Parse JSONL content line by line
        jsonl_text = jsonl_content.decode('utf-8')
        lines = jsonl_text.strip().split('\n')

        # Parse each line as JSON, collecting valid records
        records = []
        invalid_lines = []

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                # Skip empty lines
                continue

            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    logger.warning(f"Line {line_num}: Expected JSON object, got {type(record).__name__}")
                    invalid_lines.append(line_num)
                    continue
                records.append(record)
            except json.JSONDecodeError as e:
                logger.warning(f"Line {line_num}: Invalid JSON - {str(e)}")
                invalid_lines.append(line_num)
                continue

        # Validate we have at least one valid record
        if not records:
            if invalid_lines:
                raise ValueError(f"No valid JSON objects found. Invalid lines: {invalid_lines}")
            else:
                raise ValueError("JSONL file is empty")

        # Log if some lines were skipped
        if invalid_lines:
            logger.info(f"Skipped {len(invalid_lines)} invalid lines: {invalid_lines[:10]}{'...' if len(invalid_lines) > 10 else ''}")

        # Discover all possible fields across all records
        all_fields = discover_all_fields(records)

        if not all_fields:
            raise ValueError("No fields discovered in JSONL records")

        # Flatten each record and fill missing fields with None
        flattened_records = []
        for record in records:
            flattened = flatten_record(record)
            # Ensure all discovered fields are present in each record
            complete_record = {field: flattened.get(field, None) for field in all_fields}
            flattened_records.append(complete_record)

        # Convert to pandas DataFrame
        df = pd.DataFrame(flattened_records)

        # Clean column names (lowercase, replace special chars with underscore)
        df.columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df.columns]

        # Connect to SQLite database
        conn = sqlite3.connect("db/database.db")

        # Write DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)

        # Get schema information using safe query execution
        cursor_info = execute_query_safely(
            conn,
            "PRAGMA table_info({table})",
            identifier_params={'table': table_name}
        )
        columns_info = cursor_info.fetchall()

        schema = {}
        for col in columns_info:
            schema[col[1]] = col[2]  # column_name: data_type

        # Get sample data using safe query execution
        cursor_sample = execute_query_safely(
            conn,
            "SELECT * FROM {table} LIMIT 5",
            identifier_params={'table': table_name}
        )
        sample_rows = cursor_sample.fetchall()
        column_names = [col[1] for col in columns_info]
        sample_data = [dict(zip(column_names, row)) for row in sample_rows]

        # Get row count using safe query execution
        cursor_count = execute_query_safely(
            conn,
            "SELECT COUNT(*) FROM {table}",
            identifier_params={'table': table_name}
        )
        row_count = cursor_count.fetchone()[0]

        conn.close()

        return {
            'table_name': table_name,
            'schema': schema,
            'row_count': row_count,
            'sample_data': sample_data
        }

    except Exception as e:
        raise Exception(f"Error converting JSONL to SQLite: {str(e)}")