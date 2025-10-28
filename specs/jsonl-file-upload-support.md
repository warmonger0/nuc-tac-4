# Feature: JSONL File Upload Support

## Feature Description
Add support for uploading JSONL (JSON Lines) files to the Natural Language SQL Interface. JSONL files will be processed similarly to CSV and JSON files, with each line containing a valid JSON object. The feature will automatically detect all possible fields across all records, flatten nested objects and arrays using configurable delimiters, and create a new SQLite table with a normalized schema. Nested fields will be concatenated with a double underscore (`__`) delimiter, and array items will be indexed using `_0`, `_1`, etc. notation.

## User Story
As a data analyst
I want to upload JSONL files to the application
So that I can query streaming JSON data or large JSON datasets that are typically stored in JSONL format

## Problem Statement
The application currently supports CSV and JSON array formats, but many real-world data sources (logs, streaming APIs, large datasets) export data in JSONL (newline-delimited JSON) format. Users cannot analyze this common data format without manually converting it to JSON arrays first. Additionally, complex nested JSON structures in any format need to be flattened into queryable table columns with a clear, consistent naming convention.

## Solution Statement
Extend the existing file upload infrastructure to detect and process JSONL files. Implement a robust field flattening algorithm that traverses all records to discover every possible field (including nested objects and arrays), then flattens the structure using the `__` delimiter for nested objects and `_N` suffix for array indexing. Store the delimiter configuration in a new constants module for maintainability. Update the UI to indicate JSONL support alongside CSV and JSON, and create test JSONL files to validate the implementation.

## Relevant Files
Use these files to implement the feature:

**Server-side files:**
- `app/server/core/file_processor.py` - Add `convert_jsonl_to_sqlite` function and implement field flattening logic
- `app/server/core/constants.py` - Create new constants module to store delimiter configurations
- `app/server/server.py` - Update upload endpoint to handle `.jsonl` file extension
- `app/server/tests/core/test_file_processor.py` - Add comprehensive tests for JSONL processing and field flattening

**Client-side files:**
- `app/client/index.html` - Update file input accept attribute to include `.jsonl` extension
- `app/client/src/main.ts` - Update upload UI text to indicate JSONL support

**Test data files:**
- `app/server/tests/assets/test_simple.jsonl` - Simple JSONL test file with flat objects
- `app/server/tests/assets/test_nested.jsonl` - JSONL test file with nested objects and arrays
- `app/server/tests/assets/test_complex.jsonl` - JSONL test file with deep nesting and mixed types

### New Files
- `app/server/core/constants.py` - New module containing configuration constants including delimiters

## Implementation Plan
### Phase 1: Foundation
Create the constants module and implement the field discovery and flattening algorithm. This foundational work will enable proper handling of nested structures across all JSON-based formats and provide a centralized configuration for delimiter conventions.

### Phase 2: Core Implementation
Implement the JSONL parsing and conversion function that reads line-by-line JSON, discovers all fields across records, flattens nested structures, and creates SQLite tables. Add comprehensive error handling for malformed JSONL files.

### Phase 3: Integration
Update the server endpoint to route `.jsonl` files to the new conversion function, update the client UI to advertise JSONL support, create test files, and ensure all existing functionality remains intact.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Create Constants Module
- Create `app/server/core/constants.py` with configuration constants
- Define `NESTED_FIELD_DELIMITER = "__"` for separating nested object paths
- Define `ARRAY_INDEX_DELIMITER = "_"` for array item indexing prefix
- Add module docstring explaining the delimiter conventions
- Import constants in relevant modules

### Implement Field Discovery Algorithm
- Add `discover_all_fields` function in `file_processor.py` that takes a list of dictionaries and returns a set of all possible flattened field names
- Implement recursive traversal of nested objects to build field paths using `NESTED_FIELD_DELIMITER`
- Implement array handling that indexes each position (e.g., `items_0`, `items_1`)
- Handle edge cases: empty arrays, null values, mixed types in arrays, deeply nested structures
- Add comprehensive docstrings explaining the algorithm

### Implement Field Flattening Function
- Add `flatten_record` function that takes a nested dictionary and returns a flattened dictionary
- Use `NESTED_FIELD_DELIMITER` to create concatenated field names for nested objects
- Use `ARRAY_INDEX_DELIMITER + str(index)` to create field names for array items
- Handle primitive arrays (strings, numbers) and object arrays consistently
- Ensure the function handles edge cases gracefully (None, empty objects, circular references prevention)

### Implement JSONL Conversion Function
- Add `convert_jsonl_to_sqlite` function in `file_processor.py` following the pattern of existing conversion functions
- Parse JSONL content line-by-line using standard library `json.loads()`
- Collect all valid JSON objects into a list, skipping invalid lines with warnings
- Call `discover_all_fields` to get the complete schema across all records
- Flatten each record using `flatten_record` and fill missing fields with None
- Convert flattened records to pandas DataFrame for SQLite insertion
- Apply the same security validations as existing converters (sanitize table names, validate identifiers)
- Return the same response structure as other converters (table_name, schema, row_count, sample_data)

### Update Server Upload Endpoint
- Modify `upload_file` function in `server.py` to accept `.jsonl` file extension
- Update file type validation to include `.jsonl` in the allowed extensions
- Add routing logic to call `convert_jsonl_to_sqlite` for `.jsonl` files
- Ensure error handling covers JSONL-specific errors (malformed lines, empty files)
- Update endpoint docstring to document JSONL support

### Update Client File Upload UI
- Modify file input in `index.html` to accept `.jsonl` files: `accept=".csv,.json,.jsonl"`
- Update drop zone text in `index.html` to mention `.jsonl` files: "Drag and drop .csv, .json, or .jsonl files here"
- Update `README.md` to document JSONL file support in the features list

### Create Test JSONL Files
- Create `app/server/tests/assets/test_simple.jsonl` with 5 flat JSON objects (e.g., user records with id, name, email)
- Create `app/server/tests/assets/test_nested.jsonl` with 4 records containing nested objects (e.g., user with address object)
- Create `app/server/tests/assets/test_complex.jsonl` with 3 records containing arrays and deep nesting (e.g., orders with items array)
- Create `app/server/tests/assets/test_invalid.jsonl` with some invalid JSON lines to test error handling

### Write Unit Tests for Field Discovery
- Add test class `TestFieldDiscovery` in `test_file_processor.py`
- Test `discover_all_fields` with flat objects (should return all keys)
- Test with nested objects (should return flattened paths with `__`)
- Test with arrays of primitives (should return indexed fields like `tags_0`, `tags_1`)
- Test with arrays of objects (should return all possible combinations)
- Test with mixed field presence across records (union of all fields)
- Test edge cases: empty objects, null values, undefined fields

### Write Unit Tests for Field Flattening
- Add test class `TestFieldFlattening` in `test_file_processor.py`
- Test `flatten_record` with simple nested object
- Test with array of primitives
- Test with array of objects
- Test with deep nesting (3+ levels)
- Test with missing fields (should handle gracefully)
- Verify delimiter usage matches constants

### Write Unit Tests for JSONL Conversion
- Add test class `TestJsonlConversion` in `test_file_processor.py`
- Test `convert_jsonl_to_sqlite` with `test_simple.jsonl` (verify table creation, schema, row count)
- Test with `test_nested.jsonl` (verify nested fields are flattened correctly)
- Test with `test_complex.jsonl` (verify array indexing and deep nesting)
- Test with `test_invalid.jsonl` (verify error handling and partial processing)
- Test with empty JSONL file (should raise appropriate error)
- Test column name cleaning (lowercase, underscore replacement)
- Test schema validation matches flattened structure
- Test sample data contains flattened fields

### Write Integration Tests
- Test full upload flow through server endpoint with JSONL file
- Test that uploaded JSONL data can be queried via natural language
- Test JSONL upload with same filename overwrites existing table
- Test JSONL files with inconsistent schemas across lines
- Test very large JSONL files (performance validation)
- Test JSONL with special characters in field names

### Update Documentation
- Update `README.md` Features section to include JSONL support
- Update `README.md` Usage section to mention JSONL file uploads
- Add examples of supported JSONL format in documentation
- Document the field flattening conventions (double underscore, array indexing)

### Manual Testing Preparation
- Copy test JSONL files to a convenient location for manual testing
- Create a manual test checklist document with expected outcomes
- Test upload via UI drag-and-drop
- Test upload via browse button
- Test query generation against JSONL-created tables
- Verify flattened field names appear correctly in schema display

### Final Validation
- Run all validation commands to ensure zero regressions
- Verify existing CSV and JSON uploads still work correctly
- Verify SQL injection protection still applies to JSONL-generated tables
- Test with real-world JSONL files if available

## Testing Strategy
### Unit Tests
- Test field discovery algorithm with various nested structures
- Test field flattening with edge cases (nulls, empty arrays, deep nesting)
- Test JSONL parsing line-by-line with malformed data
- Test delimiter concatenation follows constants configuration
- Test table name sanitization for JSONL files
- Test schema generation for flattened fields
- Test pandas DataFrame conversion with flattened data

### Integration Tests
- Test complete upload flow from JSONL file to SQLite table
- Test natural language queries against JSONL-generated tables
- Test table overwriting with duplicate JSONL uploads
- Test concurrent JSONL uploads
- Test JSONL upload with existing CSV/JSON tables
- Test security validations apply to JSONL data

### Edge Cases
- Empty JSONL files (no records)
- Single-line JSONL files
- JSONL with only invalid lines
- JSONL with inconsistent schemas across records (missing fields, extra fields)
- JSONL with arrays of varying lengths
- JSONL with deeply nested structures (5+ levels)
- JSONL with circular reference-like patterns
- JSONL with very long field names after flattening
- JSONL with special characters requiring sanitization
- JSONL with mixed data types in same field across records
- JSONL with null or undefined values in various positions
- JSONL files larger than 100MB (memory handling)
- JSONL with Unicode characters in field names and values

## Acceptance Criteria
- Users can upload `.jsonl` files via drag-and-drop or file browser
- JSONL files are parsed line-by-line, with each line treated as a separate record
- All possible fields across all records are discovered and included in the schema
- Nested objects are flattened using `__` delimiter (e.g., `address__city`)
- Array items are indexed using `_N` suffix (e.g., `items_0`, `items_1`)
- Malformed JSON lines are skipped with appropriate logging, not failing the entire upload
- Delimiter configurations are stored in `constants.py` and used consistently
- Generated SQLite tables can be queried using natural language just like CSV/JSON tables
- UI clearly indicates support for `.jsonl` files
- Table schema display shows flattened field names correctly
- All existing CSV and JSON upload functionality remains unaffected
- Security validations (SQL injection protection, table name sanitization) apply to JSONL uploads
- At least 3 test JSONL files exist in `tests/assets` for validation

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest tests/core/test_file_processor.py -v` - Run file processor tests including new JSONL tests
- `cd app/server && uv run pytest tests/core/test_file_processor.py::TestJsonlConversion -v` - Run specific JSONL conversion tests
- `cd app/server && uv run pytest tests/core/test_file_processor.py::TestFieldDiscovery -v` - Run field discovery tests
- `cd app/server && uv run pytest tests/core/test_file_processor.py::TestFieldFlattening -v` - Run field flattening tests
- `cd app/server && uv run pytest` - Run all server tests to validate zero regressions
- `cd app/server && uv run pytest tests/test_sql_injection.py -v` - Ensure SQL injection protection works with JSONL tables
- `cd scripts && ./start.sh` - Start the application and manually test:
  - Upload `test_simple.jsonl` and verify table creation
  - Upload `test_nested.jsonl` and verify nested fields are flattened correctly
  - Upload `test_complex.jsonl` and verify array indexing works
  - Query the JSONL-generated tables using natural language
  - Verify schema display shows flattened field names
  - Upload CSV and JSON files to ensure no regression
  - Test drag-and-drop vs browse button for JSONL files
- `cd app/client && npm run build` - Ensure client builds without errors

## Notes
- JSONL format is also known as NDJSON (Newline Delimited JSON) or JSON Lines
- The field discovery algorithm must scan ALL records to build a complete schema, as different records may have different fields
- Array flattening has a practical limit: arrays with 100+ items will create 100+ columns. Consider adding a configuration for max array size in future iterations
- Pandas will automatically infer data types for flattened fields
- Future enhancement: Add option to keep nested structures as JSON strings instead of flattening
- Future enhancement: Add configuration UI to customize delimiter conventions
- Consider performance implications for very large JSONL files (streaming parsing may be needed in future)
- The `__` delimiter is chosen because it's uncommon in typical field names and clearly indicates nesting
- SQLite doesn't support nested data types, so flattening is necessary for queryability
- The implementation should use only Python standard library for JSON parsing (no new dependencies)
- Consider adding a preview feature in the UI to show how fields will be flattened before upload
