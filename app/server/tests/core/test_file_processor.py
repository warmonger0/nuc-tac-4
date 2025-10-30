import pytest
import json
import pandas as pd
import sqlite3
import os
import io
from pathlib import Path
from unittest.mock import patch
from core.file_processor import (
    convert_csv_to_sqlite,
    convert_json_to_sqlite,
    convert_jsonl_to_sqlite,
    discover_all_fields,
    flatten_record
)


@pytest.fixture
def test_db():
    """Create an in-memory test database"""
    # Create in-memory database
    conn = sqlite3.connect(':memory:')
    
    # Patch the database connection to use our in-memory database
    with patch('core.file_processor.sqlite3.connect') as mock_connect:
        mock_connect.return_value = conn
        yield conn
    
    conn.close()


@pytest.fixture
def test_assets_dir():
    """Get the path to test assets directory"""
    return Path(__file__).parent.parent / "assets"


class TestFileProcessor:
    
    def test_convert_csv_to_sqlite_success(self, test_db, test_assets_dir):
        # Load real CSV file
        csv_file = test_assets_dir / "test_users.csv"
        with open(csv_file, 'rb') as f:
            csv_data = f.read()
        
        table_name = "users"
        result = convert_csv_to_sqlite(csv_data, table_name)
        
        # Verify return structure
        assert result['table_name'] == table_name
        assert 'schema' in result
        assert 'row_count' in result
        assert 'sample_data' in result
        
        # Test the returned data
        assert result['row_count'] == 4  # 4 users in test file
        assert len(result['sample_data']) <= 5  # Should return up to 5 samples
        
        # Verify schema has expected columns (cleaned names)
        assert 'name' in result['schema']
        assert 'age' in result['schema'] 
        assert 'city' in result['schema']
        assert 'email' in result['schema']
        
        # Verify sample data structure and content
        john_data = next((item for item in result['sample_data'] if item['name'] == 'John Doe'), None)
        assert john_data is not None
        assert john_data['age'] == 25
        assert john_data['city'] == 'New York'
        assert john_data['email'] == 'john@example.com'
    
    def test_convert_csv_to_sqlite_column_cleaning(self, test_db, test_assets_dir):
        # Test column name cleaning with real file
        csv_file = test_assets_dir / "column_names.csv"
        with open(csv_file, 'rb') as f:
            csv_data = f.read()
        
        table_name = "test_users"
        result = convert_csv_to_sqlite(csv_data, table_name)
        
        # Verify columns were cleaned in the schema
        assert 'full_name' in result['schema']
        assert 'birth_date' in result['schema']
        assert 'email_address' in result['schema']
        assert 'phone_number' in result['schema']
        
        # Verify sample data has cleaned column names and actual content
        sample = result['sample_data'][0]
        assert 'full_name' in sample
        assert 'birth_date' in sample
        assert 'email_address' in sample
        assert sample['full_name'] == 'John Doe'
        assert sample['birth_date'] == '1990-01-15'
    
    def test_convert_csv_to_sqlite_with_inconsistent_data(self, test_db, test_assets_dir):
        # Test with CSV that has inconsistent row lengths - should raise error
        csv_file = test_assets_dir / "invalid.csv"
        with open(csv_file, 'rb') as f:
            csv_data = f.read()
        
        table_name = "inconsistent_table"
        
        # Pandas will fail on inconsistent CSV data
        with pytest.raises(Exception) as exc_info:
            convert_csv_to_sqlite(csv_data, table_name)
        
        assert "Error converting CSV to SQLite" in str(exc_info.value)
    
    def test_convert_json_to_sqlite_success(self, test_db, test_assets_dir):
        # Load real JSON file
        json_file = test_assets_dir / "test_products.json"
        with open(json_file, 'rb') as f:
            json_data = f.read()
        
        table_name = "products"
        result = convert_json_to_sqlite(json_data, table_name)
        
        # Verify return structure
        assert result['table_name'] == table_name
        assert 'schema' in result
        assert 'row_count' in result
        assert 'sample_data' in result
        
        # Test the returned data
        assert result['row_count'] == 3  # 3 products in test file
        assert len(result['sample_data']) == 3
        
        # Verify schema has expected columns
        assert 'id' in result['schema']
        assert 'name' in result['schema']
        assert 'price' in result['schema']
        assert 'category' in result['schema']
        assert 'in_stock' in result['schema']
        
        # Verify sample data structure and content
        laptop_data = next((item for item in result['sample_data'] if item['name'] == 'Laptop'), None)
        assert laptop_data is not None
        assert laptop_data['price'] == 999.99
        assert laptop_data['category'] == 'Electronics'
        assert laptop_data['in_stock'] == True
    
    def test_convert_json_to_sqlite_invalid_json(self):
        # Test with invalid JSON
        json_data = b'invalid json'
        table_name = "test_table"
        
        with pytest.raises(Exception) as exc_info:
            convert_json_to_sqlite(json_data, table_name)
        
        assert "Error converting JSON to SQLite" in str(exc_info.value)
    
    def test_convert_json_to_sqlite_not_array(self):
        # Test with JSON that's not an array
        json_data = b'{"name": "John", "age": 25}'
        table_name = "test_table"
        
        with pytest.raises(Exception) as exc_info:
            convert_json_to_sqlite(json_data, table_name)
        
        assert "JSON must be an array of objects" in str(exc_info.value)
    
    def test_convert_json_to_sqlite_empty_array(self):
        # Test with empty JSON array
        json_data = b'[]'
        table_name = "test_table"

        with pytest.raises(Exception) as exc_info:
            convert_json_to_sqlite(json_data, table_name)

        assert "JSON array is empty" in str(exc_info.value)


class TestFieldDiscovery:
    """Test suite for the discover_all_fields function"""

    def test_discover_flat_fields(self):
        """Test field discovery with simple flat objects"""
        records = [
            {"id": 1, "name": "Alice", "age": 30},
            {"id": 2, "name": "Bob", "age": 25}
        ]
        fields = discover_all_fields(records)

        assert "id" in fields
        assert "name" in fields
        assert "age" in fields
        assert len(fields) == 3

    def test_discover_nested_fields(self):
        """Test field discovery with nested objects"""
        records = [
            {"id": 1, "user": {"name": "Alice", "email": "alice@example.com"}},
            {"id": 2, "user": {"name": "Bob", "email": "bob@example.com"}}
        ]
        fields = discover_all_fields(records)

        assert "id" in fields
        assert "user__name" in fields
        assert "user__email" in fields
        assert len(fields) == 3

    def test_discover_array_of_primitives(self):
        """Test field discovery with arrays of primitives"""
        records = [
            {"id": 1, "tags": ["python", "javascript"]},
            {"id": 2, "tags": ["rust", "go"]}
        ]
        fields = discover_all_fields(records)

        assert "id" in fields
        assert "tags_0" in fields
        assert "tags_1" in fields
        assert len(fields) == 3

    def test_discover_array_of_objects(self):
        """Test field discovery with arrays of objects"""
        records = [
            {"id": 1, "items": [{"name": "item1", "price": 10}, {"name": "item2", "price": 20}]},
            {"id": 2, "items": [{"name": "item3", "price": 30}]}
        ]
        fields = discover_all_fields(records)

        assert "id" in fields
        assert "items_0__name" in fields
        assert "items_0__price" in fields
        assert "items_1__name" in fields
        assert "items_1__price" in fields
        assert len(fields) == 5

    def test_discover_mixed_fields_across_records(self):
        """Test field discovery with different fields in different records"""
        records = [
            {"id": 1, "name": "Alice", "age": 30},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
            {"id": 3, "phone": "123-456-7890"}
        ]
        fields = discover_all_fields(records)

        # Should contain union of all fields
        assert "id" in fields
        assert "name" in fields
        assert "age" in fields
        assert "email" in fields
        assert "phone" in fields
        assert len(fields) == 5

    def test_discover_null_values(self):
        """Test field discovery with null values"""
        records = [
            {"id": 1, "name": "Alice", "age": None},
            {"id": 2, "name": None, "age": 25}
        ]
        fields = discover_all_fields(records)

        assert "id" in fields
        assert "name" in fields
        assert "age" in fields
        assert len(fields) == 3

    def test_discover_empty_arrays(self):
        """Test that empty arrays generate no fields"""
        records = [
            {"id": 1, "tags": []},
            {"id": 2, "tags": ["python"]}
        ]
        fields = discover_all_fields(records)

        assert "id" in fields
        assert "tags_0" in fields
        # Empty array in first record should not generate fields
        assert len(fields) == 2

    def test_discover_deeply_nested(self):
        """Test field discovery with deep nesting"""
        records = [
            {"user": {"profile": {"address": {"city": "NYC"}}}}
        ]
        fields = discover_all_fields(records)

        assert "user__profile__address__city" in fields

    def test_discover_empty_list(self):
        """Test field discovery with empty input"""
        records = []
        fields = discover_all_fields(records)

        assert len(fields) == 0

    def test_discover_non_dict_records(self):
        """Test that non-dict records are skipped"""
        records = [
            {"id": 1, "name": "Alice"},
            "invalid",
            {"id": 2, "name": "Bob"}
        ]
        fields = discover_all_fields(records)

        assert "id" in fields
        assert "name" in fields
        assert len(fields) == 2


class TestFieldFlattening:
    """Test suite for the flatten_record function"""

    def test_flatten_simple_nested(self):
        """Test flattening simple nested object"""
        record = {"user": {"name": "Alice", "age": 30}}
        flattened = flatten_record(record)

        assert flattened == {
            "user__name": "Alice",
            "user__age": 30
        }

    def test_flatten_array_of_primitives(self):
        """Test flattening array of primitives"""
        record = {"tags": ["python", "javascript", "rust"]}
        flattened = flatten_record(record)

        assert flattened == {
            "tags_0": "python",
            "tags_1": "javascript",
            "tags_2": "rust"
        }

    def test_flatten_array_of_objects(self):
        """Test flattening array of objects"""
        record = {
            "items": [
                {"name": "item1", "price": 10},
                {"name": "item2", "price": 20}
            ]
        }
        flattened = flatten_record(record)

        assert flattened == {
            "items_0__name": "item1",
            "items_0__price": 10,
            "items_1__name": "item2",
            "items_1__price": 20
        }

    def test_flatten_deep_nesting(self):
        """Test flattening with deep nesting (3+ levels)"""
        record = {
            "user": {
                "profile": {
                    "address": {
                        "city": "NYC",
                        "zip": "10001"
                    }
                }
            }
        }
        flattened = flatten_record(record)

        assert flattened == {
            "user__profile__address__city": "NYC",
            "user__profile__address__zip": "10001"
        }

    def test_flatten_null_values(self):
        """Test that null values are preserved"""
        record = {"id": 1, "name": None, "age": 30}
        flattened = flatten_record(record)

        assert flattened == {
            "id": 1,
            "name": None,
            "age": 30
        }

    def test_flatten_empty_object(self):
        """Test flattening empty object"""
        record = {}
        flattened = flatten_record(record)

        assert flattened == {}

    def test_flatten_empty_array(self):
        """Test that empty arrays generate no fields"""
        record = {"id": 1, "tags": []}
        flattened = flatten_record(record)

        assert flattened == {"id": 1}

    def test_flatten_non_dict_input(self):
        """Test that non-dict input returns empty dict"""
        result = flatten_record("not a dict")
        assert result == {}

        result = flatten_record(None)
        assert result == {}

        result = flatten_record([1, 2, 3])
        assert result == {}

    def test_flatten_mixed_types(self):
        """Test flattening with mixed data types"""
        record = {
            "string": "text",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None
        }
        flattened = flatten_record(record)

        assert flattened == {
            "string": "text",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None
        }

    def test_flatten_complex_structure(self):
        """Test flattening complex nested structure"""
        record = {
            "order_id": 1,
            "customer": {"name": "Alice", "email": "alice@example.com"},
            "items": [
                {"product": "Laptop", "price": 999.99},
                {"product": "Mouse", "price": 29.99}
            ],
            "total": 1029.98
        }
        flattened = flatten_record(record)

        assert flattened == {
            "order_id": 1,
            "customer__name": "Alice",
            "customer__email": "alice@example.com",
            "items_0__product": "Laptop",
            "items_0__price": 999.99,
            "items_1__product": "Mouse",
            "items_1__price": 29.99,
            "total": 1029.98
        }


class TestJsonlConversion:
    """Test suite for JSONL conversion"""

    def test_convert_jsonl_simple(self, test_db, test_assets_dir):
        """Test converting simple JSONL file"""
        jsonl_file = test_assets_dir / "test_simple.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "simple_users"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        assert result['table_name'] == table_name
        assert result['row_count'] == 5
        assert 'id' in result['schema']
        assert 'name' in result['schema']
        assert 'email' in result['schema']
        assert 'age' in result['schema']
        assert len(result['sample_data']) == 5

    def test_convert_jsonl_nested(self, test_db, test_assets_dir):
        """Test converting JSONL with nested objects"""
        jsonl_file = test_assets_dir / "test_nested.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "nested_users"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        assert result['table_name'] == table_name
        assert result['row_count'] == 4
        # Check flattened nested fields
        assert 'address__city' in result['schema']
        assert 'address__state' in result['schema']
        assert 'address__zip' in result['schema']

    def test_convert_jsonl_complex(self, test_db, test_assets_dir):
        """Test converting JSONL with complex nested structures and arrays"""
        jsonl_file = test_assets_dir / "test_complex.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "orders"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        assert result['table_name'] == table_name
        assert result['row_count'] == 3
        # Check nested customer fields
        assert 'customer__name' in result['schema']
        assert 'customer__email' in result['schema']
        # Check array fields with indexing
        assert 'items_0__product' in result['schema']
        assert 'items_0__price' in result['schema']
        assert 'items_0__qty' in result['schema']
        assert 'items_1__product' in result['schema']

    def test_convert_jsonl_invalid_lines(self, test_db, test_assets_dir):
        """Test JSONL with some invalid lines (should skip and continue)"""
        jsonl_file = test_assets_dir / "test_invalid.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "partial_valid"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Should successfully process valid records
        assert result['table_name'] == table_name
        assert result['row_count'] == 3  # Only 3 valid records
        assert 'id' in result['schema']
        assert 'name' in result['schema']

    def test_convert_jsonl_empty_file(self, test_db):
        """Test JSONL with empty file"""
        jsonl_data = b''
        table_name = "empty_table"

        with pytest.raises(Exception) as exc_info:
            convert_jsonl_to_sqlite(jsonl_data, table_name)

        assert "JSONL file is empty" in str(exc_info.value)

    def test_convert_jsonl_all_invalid(self, test_db):
        """Test JSONL with all invalid lines"""
        jsonl_data = b'{invalid json}\n{more invalid}\n'
        table_name = "all_invalid"

        with pytest.raises(Exception) as exc_info:
            convert_jsonl_to_sqlite(jsonl_data, table_name)

        assert "No valid JSON objects found" in str(exc_info.value)

    def test_convert_jsonl_column_name_cleaning(self, test_db):
        """Test that column names are cleaned (lowercase, underscore replacement)"""
        jsonl_data = b'{"User-Name": "Alice", "AGE": 30}\n{"User-Name": "Bob", "AGE": 25}\n'
        table_name = "cleaned_columns"

        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Column names should be cleaned
        assert 'user_name' in result['schema']
        assert 'age' in result['schema']

    def test_convert_jsonl_inconsistent_schema(self, test_db):
        """Test JSONL with inconsistent schemas across lines"""
        jsonl_data = b'{"id": 1, "name": "Alice", "age": 30}\n{"id": 2, "name": "Bob", "email": "bob@example.com"}\n{"id": 3, "phone": "123-456-7890"}\n'
        table_name = "inconsistent"

        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Should include all fields from all records
        assert result['row_count'] == 3
        assert 'id' in result['schema']
        assert 'name' in result['schema']
        assert 'age' in result['schema']
        assert 'email' in result['schema']
        assert 'phone' in result['schema']

    def test_convert_jsonl_single_line(self, test_db):
        """Test JSONL with single line"""
        jsonl_data = b'{"id": 1, "name": "Alice"}\n'
        table_name = "single_line"

        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        assert result['row_count'] == 1
        assert 'id' in result['schema']
        assert 'name' in result['schema']