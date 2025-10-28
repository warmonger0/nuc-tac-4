"""
Tests for visualization analyzer module
"""

import pytest
from core.visualization_analyzer import (
    analyze_columns,
    suggest_chart_types,
    analyze_and_suggest,
    _is_numeric_column,
    _detect_temporal_column,
    _detect_categorical_column
)
from core.data_models import ChartType


class TestColumnAnalysis:
    """Test column analysis functions"""

    def test_is_numeric_column_with_integers(self):
        """Test numeric detection with integer values"""
        values = [1, 2, 3, 4, 5]
        assert _is_numeric_column(values) is True

    def test_is_numeric_column_with_floats(self):
        """Test numeric detection with float values"""
        values = [1.5, 2.7, 3.2, 4.9, 5.1]
        assert _is_numeric_column(values) is True

    def test_is_numeric_column_with_strings(self):
        """Test numeric detection with string values"""
        values = ["apple", "banana", "cherry"]
        assert _is_numeric_column(values) is False

    def test_is_numeric_column_with_numeric_strings(self):
        """Test numeric detection with numeric strings"""
        values = ["1", "2", "3", "4", "5"]
        assert _is_numeric_column(values) is True

    def test_detect_temporal_column_with_iso_dates(self):
        """Test temporal detection with ISO format dates"""
        values = ["2024-01-01", "2024-01-02", "2024-01-03"]
        assert _detect_temporal_column(values) is True

    def test_detect_temporal_column_with_non_dates(self):
        """Test temporal detection with non-date strings"""
        values = ["apple", "banana", "cherry"]
        assert _detect_temporal_column(values) is False

    def test_detect_categorical_column_low_cardinality(self):
        """Test categorical detection with low cardinality"""
        values = ["red", "blue", "red", "green", "blue", "red"]
        assert _detect_categorical_column(values) is True

    def test_detect_categorical_column_high_cardinality(self):
        """Test categorical detection with high cardinality"""
        values = [f"value_{i}" for i in range(100)]
        assert _detect_categorical_column(values) is False

    def test_analyze_columns_basic(self):
        """Test basic column analysis"""
        results = [
            {"name": "Alice", "age": 30, "city": "NYC"},
            {"name": "Bob", "age": 25, "city": "LA"},
            {"name": "Charlie", "age": 35, "city": "NYC"}
        ]
        columns = ["name", "age", "city"]

        analyses = analyze_columns(results, columns)

        assert len(analyses) == 3
        assert analyses[1].name == "age"
        assert analyses[1].is_numeric is True
        assert analyses[2].name == "city"
        assert analyses[2].is_categorical is True

    def test_analyze_columns_empty_results(self):
        """Test column analysis with empty results"""
        results = []
        columns = ["col1", "col2"]

        analyses = analyze_columns(results, columns)

        assert len(analyses) == 0


class TestChartSuggestions:
    """Test chart type suggestion functions"""

    def test_suggest_bar_chart_for_categorical_numeric(self):
        """Test bar chart suggestion for categorical + numeric data"""
        from core.data_models import ColumnAnalysis

        column_analyses = [
            ColumnAnalysis(
                name="category",
                data_type="categorical",
                is_numeric=False,
                is_temporal=False,
                is_categorical=True,
                unique_count=5,
                sample_values=["A", "B", "C", "D", "E"]
            ),
            ColumnAnalysis(
                name="value",
                data_type="numeric",
                is_numeric=True,
                is_temporal=False,
                is_categorical=False,
                unique_count=10,
                sample_values=[10, 20, 30, 40, 50]
            )
        ]

        suggestions = suggest_chart_types(column_analyses)

        assert len(suggestions) > 0
        # Should suggest bar chart for categorical + numeric
        chart_types = [s.chart_type for s in suggestions]
        assert ChartType.BAR in chart_types

    def test_suggest_line_chart_for_temporal_numeric(self):
        """Test line chart suggestion for temporal + numeric data"""
        from core.data_models import ColumnAnalysis

        column_analyses = [
            ColumnAnalysis(
                name="date",
                data_type="temporal",
                is_numeric=False,
                is_temporal=True,
                is_categorical=False,
                unique_count=10,
                sample_values=["2024-01-01", "2024-01-02", "2024-01-03"]
            ),
            ColumnAnalysis(
                name="value",
                data_type="numeric",
                is_numeric=True,
                is_temporal=False,
                is_categorical=False,
                unique_count=10,
                sample_values=[10, 20, 30]
            )
        ]

        suggestions = suggest_chart_types(column_analyses)

        assert len(suggestions) > 0
        # Should suggest line chart for temporal + numeric
        chart_types = [s.chart_type for s in suggestions]
        assert ChartType.LINE in chart_types

    def test_suggest_pie_chart_for_single_categorical(self):
        """Test pie chart suggestion for single categorical column"""
        from core.data_models import ColumnAnalysis

        column_analyses = [
            ColumnAnalysis(
                name="category",
                data_type="categorical",
                is_numeric=False,
                is_temporal=False,
                is_categorical=True,
                unique_count=5,
                sample_values=["A", "B", "C"]
            )
        ]

        suggestions = suggest_chart_types(column_analyses)

        assert len(suggestions) > 0
        # Should suggest pie chart for single categorical
        chart_types = [s.chart_type for s in suggestions]
        assert ChartType.PIE in chart_types

    def test_suggest_scatter_for_two_numeric(self):
        """Test scatter plot suggestion for two numeric columns"""
        from core.data_models import ColumnAnalysis

        column_analyses = [
            ColumnAnalysis(
                name="x_value",
                data_type="numeric",
                is_numeric=True,
                is_temporal=False,
                is_categorical=False,
                unique_count=10,
                sample_values=[1, 2, 3]
            ),
            ColumnAnalysis(
                name="y_value",
                data_type="numeric",
                is_numeric=True,
                is_temporal=False,
                is_categorical=False,
                unique_count=10,
                sample_values=[10, 20, 30]
            )
        ]

        suggestions = suggest_chart_types(column_analyses)

        assert len(suggestions) > 0
        # Should suggest scatter plot for two numeric columns
        chart_types = [s.chart_type for s in suggestions]
        assert ChartType.SCATTER in chart_types

    def test_max_suggestions_limit(self):
        """Test that max suggestions limit is respected"""
        from core.data_models import ColumnAnalysis

        column_analyses = [
            ColumnAnalysis(
                name="date",
                data_type="temporal",
                is_numeric=False,
                is_temporal=True,
                is_categorical=False,
                unique_count=10,
                sample_values=["2024-01-01"]
            ),
            ColumnAnalysis(
                name="category",
                data_type="categorical",
                is_numeric=False,
                is_temporal=False,
                is_categorical=True,
                unique_count=5,
                sample_values=["A"]
            ),
            ColumnAnalysis(
                name="value",
                data_type="numeric",
                is_numeric=True,
                is_temporal=False,
                is_categorical=False,
                unique_count=10,
                sample_values=[10]
            )
        ]

        suggestions = suggest_chart_types(column_analyses, max_suggestions=2)

        assert len(suggestions) <= 2


class TestAnalyzeAndSuggest:
    """Test the main analyze_and_suggest function"""

    def test_analyze_and_suggest_basic(self):
        """Test basic end-to-end analysis and suggestion"""
        results = [
            {"category": "A", "value": 10},
            {"category": "B", "value": 20},
            {"category": "C", "value": 30}
        ]
        columns = ["category", "value"]

        response = analyze_and_suggest(results, columns)

        assert response.error is None
        assert len(response.suggestions) > 0
        assert response.primary_suggestion is not None
        assert response.data_summary["total_rows"] == 3
        assert response.data_summary["total_columns"] == 2

    def test_analyze_and_suggest_empty_data(self):
        """Test with empty data"""
        results = []
        columns = []

        response = analyze_and_suggest(results, columns)

        # Should not error, but should have no suggestions
        assert response.error is None or len(response.suggestions) == 0

    def test_analyze_and_suggest_time_series(self):
        """Test with time series data"""
        results = [
            {"date": "2024-01-01", "sales": 100},
            {"date": "2024-01-02", "sales": 150},
            {"date": "2024-01-03", "sales": 120}
        ]
        columns = ["date", "sales"]

        response = analyze_and_suggest(results, columns)

        assert response.error is None
        assert len(response.suggestions) > 0
        # Should suggest line chart for time series
        chart_types = [s.chart_type for s in response.suggestions]
        assert ChartType.LINE in chart_types
