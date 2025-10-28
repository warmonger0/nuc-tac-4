"""
Visualization Analyzer Module

This module analyzes query results and suggests appropriate chart types
based on the data structure and characteristics.
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import Counter

from .data_models import (
    ChartType,
    ColumnAnalysis,
    VisualizationSuggestion,
    VisualizationResponse
)


def analyze_columns(results: List[Dict[str, Any]], columns: List[str]) -> List[ColumnAnalysis]:
    """
    Analyze columns in query results to determine their characteristics.

    Args:
        results: List of result rows
        columns: List of column names

    Returns:
        List of ColumnAnalysis objects with detected characteristics
    """
    if not results or not columns:
        return []

    analyses = []

    for col in columns:
        values = [row.get(col) for row in results if row.get(col) is not None]

        if not values:
            # Empty column
            analyses.append(ColumnAnalysis(
                name=col,
                data_type="null",
                is_numeric=False,
                is_temporal=False,
                is_categorical=False,
                unique_count=0,
                sample_values=[]
            ))
            continue

        # Determine data type and characteristics
        is_numeric = _is_numeric_column(values)
        is_temporal = _detect_temporal_column(values)
        is_categorical = _detect_categorical_column(values)
        unique_count = len(set(str(v) for v in values))
        sample_values = values[:5]  # First 5 values as samples

        # Infer data type
        if is_temporal:
            data_type = "temporal"
        elif is_numeric:
            data_type = "numeric"
        elif is_categorical:
            data_type = "categorical"
        else:
            data_type = "text"

        analyses.append(ColumnAnalysis(
            name=col,
            data_type=data_type,
            is_numeric=is_numeric,
            is_temporal=is_temporal,
            is_categorical=is_categorical,
            unique_count=unique_count,
            sample_values=sample_values
        ))

    return analyses


def _is_numeric_column(values: List[Any]) -> bool:
    """Check if column contains numeric values."""
    numeric_count = 0
    total = len(values)

    for val in values:
        if isinstance(val, (int, float)):
            numeric_count += 1
        elif isinstance(val, str):
            try:
                float(val)
                numeric_count += 1
            except (ValueError, TypeError):
                pass

    # Consider numeric if >80% of values are numeric
    return numeric_count / total > 0.8 if total > 0 else False


def _detect_temporal_column(values: List[Any]) -> bool:
    """Detect if column contains temporal (date/time) data."""
    temporal_count = 0
    total = len(values)

    # Common date patterns
    date_patterns = [
        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
        r'\d{4}/\d{2}/\d{2}',  # YYYY/MM/DD
        r'\d{2}-\d{2}-\d{4}',  # DD-MM-YYYY
    ]

    for val in values:
        if isinstance(val, (datetime, )):
            temporal_count += 1
        elif isinstance(val, str):
            # Check against date patterns
            for pattern in date_patterns:
                if re.match(pattern, val):
                    temporal_count += 1
                    break

    # Consider temporal if >80% match temporal patterns
    return temporal_count / total > 0.8 if total > 0 else False


def _detect_categorical_column(values: List[Any]) -> bool:
    """Detect if column contains categorical data (low cardinality)."""
    unique_count = len(set(str(v) for v in values))
    total = len(values)

    # Consider categorical if unique count is small (<20) or
    # unique ratio is low (<30% of total)
    if unique_count < 20:
        return True

    unique_ratio = unique_count / total if total > 0 else 0
    return unique_ratio < 0.3


def suggest_chart_types(
    column_analyses: List[ColumnAnalysis],
    max_suggestions: int = 3
) -> List[VisualizationSuggestion]:
    """
    Suggest appropriate chart types based on column analyses.

    Args:
        column_analyses: List of analyzed columns
        max_suggestions: Maximum number of suggestions to return

    Returns:
        List of VisualizationSuggestion objects, ranked by confidence
    """
    if not column_analyses:
        return []

    suggestions = []

    # Categorize columns
    numeric_cols = [c for c in column_analyses if c.is_numeric]
    temporal_cols = [c for c in column_analyses if c.is_temporal]
    categorical_cols = [c for c in column_analyses if c.is_categorical]

    # Rule 1: Temporal + Numeric(s) = Line Chart (time series)
    if temporal_cols and numeric_cols:
        temporal_col = temporal_cols[0]
        y_cols = [c.name for c in numeric_cols[:3]]  # Max 3 series

        suggestions.append(VisualizationSuggestion(
            chart_type=ChartType.LINE,
            x_axis_column=temporal_col.name,
            y_axis_columns=y_cols,
            title=f"{', '.join(y_cols)} over {temporal_col.name}",
            description="Time series visualization showing trends over time",
            confidence_score=0.95
        ))

        # Also suggest area chart for time series
        suggestions.append(VisualizationSuggestion(
            chart_type=ChartType.AREA,
            x_axis_column=temporal_col.name,
            y_axis_columns=y_cols,
            title=f"{', '.join(y_cols)} over {temporal_col.name}",
            description="Area chart showing cumulative trends over time",
            confidence_score=0.85
        ))

    # Rule 2: Categorical + Numeric = Bar Chart
    if categorical_cols and numeric_cols:
        cat_col = categorical_cols[0]
        num_col = numeric_cols[0]

        suggestions.append(VisualizationSuggestion(
            chart_type=ChartType.BAR,
            x_axis_column=cat_col.name,
            y_axis_columns=[num_col.name],
            title=f"{num_col.name} by {cat_col.name}",
            description="Bar chart comparing values across categories",
            confidence_score=0.9
        ))

        # Suggest pie chart if categorical has reasonable cardinality
        if cat_col.unique_count <= 10:
            suggestions.append(VisualizationSuggestion(
                chart_type=ChartType.PIE,
                x_axis_column=cat_col.name,
                y_axis_columns=[num_col.name],
                title=f"{num_col.name} distribution by {cat_col.name}",
                description="Pie chart showing proportional distribution",
                confidence_score=0.8
            ))

    # Rule 3: Two or more numeric columns = Scatter Plot
    if len(numeric_cols) >= 2:
        x_col = numeric_cols[0]
        y_col = numeric_cols[1]

        suggestions.append(VisualizationSuggestion(
            chart_type=ChartType.SCATTER,
            x_axis_column=x_col.name,
            y_axis_columns=[y_col.name],
            title=f"{y_col.name} vs {x_col.name}",
            description="Scatter plot showing relationship between two variables",
            confidence_score=0.75
        ))

    # Rule 4: Single categorical with counts = Pie Chart
    if len(categorical_cols) == 1 and not numeric_cols:
        cat_col = categorical_cols[0]

        suggestions.append(VisualizationSuggestion(
            chart_type=ChartType.PIE,
            x_axis_column=cat_col.name,
            y_axis_columns=["count"],
            title=f"Distribution of {cat_col.name}",
            description="Pie chart showing category distribution",
            confidence_score=0.85
        ))

        suggestions.append(VisualizationSuggestion(
            chart_type=ChartType.BAR,
            x_axis_column=cat_col.name,
            y_axis_columns=["count"],
            title=f"Count by {cat_col.name}",
            description="Bar chart showing category frequencies",
            confidence_score=0.8
        ))

    # Rule 5: Multiple numeric columns without categorical = Bar Chart (compare metrics)
    if len(numeric_cols) >= 2 and not categorical_cols and not temporal_cols:
        y_cols = [c.name for c in numeric_cols[:5]]

        suggestions.append(VisualizationSuggestion(
            chart_type=ChartType.BAR,
            x_axis_column=None,  # Use index or labels
            y_axis_columns=y_cols,
            title=f"Comparison of {', '.join(y_cols)}",
            description="Bar chart comparing multiple metrics",
            confidence_score=0.7
        ))

    # Sort by confidence score and return top suggestions
    suggestions.sort(key=lambda s: s.confidence_score, reverse=True)
    return suggestions[:max_suggestions]


def analyze_and_suggest(
    results: List[Dict[str, Any]],
    columns: List[str]
) -> VisualizationResponse:
    """
    Main function to analyze data and generate visualization suggestions.

    Args:
        results: Query results
        columns: Column names

    Returns:
        VisualizationResponse with suggestions and metadata
    """
    try:
        # Analyze columns
        column_analyses = analyze_columns(results, columns)

        # Generate suggestions
        suggestions = suggest_chart_types(column_analyses)

        # Primary suggestion is the highest confidence one
        primary = suggestions[0] if suggestions else None

        # Data summary
        data_summary = {
            "total_rows": len(results),
            "total_columns": len(columns),
            "numeric_columns": sum(1 for c in column_analyses if c.is_numeric),
            "categorical_columns": sum(1 for c in column_analyses if c.is_categorical),
            "temporal_columns": sum(1 for c in column_analyses if c.is_temporal),
        }

        return VisualizationResponse(
            suggestions=suggestions,
            primary_suggestion=primary,
            data_summary=data_summary,
            error=None
        )

    except Exception as e:
        return VisualizationResponse(
            suggestions=[],
            primary_suggestion=None,
            data_summary={},
            error=str(e)
        )
