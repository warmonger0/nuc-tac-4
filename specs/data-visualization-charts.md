# Feature: Interactive Data Visualization

## Feature Description
An interactive data visualization feature that automatically generates charts and graphs from SQL query results. Users will be able to visualize their data using various chart types (bar, line, pie, scatter) with a single click. The system will intelligently suggest the most appropriate chart type based on the data structure (numerical vs categorical columns, time series detection, etc.). Users can customize visualizations, export them as images, and toggle between table and chart views seamlessly.

## User Story
As a data analyst
I want to visualize my query results as interactive charts
So that I can quickly identify trends, patterns, and insights without manually creating visualizations

## Problem Statement
Currently, users can only view their query results in tabular format, which makes it difficult to identify trends, patterns, and relationships in the data at a glance. Data analysts often need to export results and use separate tools for visualization, breaking their workflow. This creates friction in the data exploration process and slows down insight discovery. Additionally, users without technical visualization skills struggle to create meaningful charts from their data.

## Solution Statement
Implement an integrated data visualization system using Chart.js that automatically analyzes query results and suggests appropriate chart types. The system will provide a "Visualize" button next to query results that opens a visualization panel with intelligent chart recommendations. Users can select from multiple chart types, customize colors and labels, and export visualizations. The solution will detect data patterns (time series, categorical distributions, numerical relationships) and pre-configure charts accordingly, making data visualization accessible to all users regardless of technical expertise.

## Relevant Files
Use these files to implement the feature:

**Server-side files:**
- `app/server/server.py` - Add endpoint for chart configuration suggestions (line 111-148: existing query endpoint will be extended)
- `app/server/core/data_models.py` - Add Pydantic models for visualization requests/responses (after line 82: add VisualizationRequest, VisualizationSuggestion models)
- `app/server/core/llm_processor.py` - Add function to generate chart title and insights using LLM (after line 157: add generate_chart_insights function)

**Client-side files:**
- `app/client/src/main.ts` - Add visualization panel logic and chart rendering (after line 158: add visualization functions)
- `app/client/src/api/client.ts` - Add API methods for visualization suggestions
- `app/client/src/types.d.ts` - Add TypeScript interfaces for visualization types
- `app/client/index.html` - Add HTML structure for visualization panel (after line 36: add visualization panel section)
- `app/client/styles.css` - Add styles for visualization panel and controls

### New Files
- `app/server/core/visualization_analyzer.py` - New module for analyzing data and suggesting visualizations
- `app/client/src/visualization.ts` - New module for chart rendering and management using Chart.js
- `app/server/tests/core/test_visualization_analyzer.py` - Unit tests for visualization analyzer

## Implementation Plan

### Phase 1: Foundation
Set up the visualization infrastructure including Chart.js library integration, data analysis utilities for detecting column types and patterns, and basic data models for visualization configurations. This phase establishes the core capabilities needed to analyze query results and prepare them for visualization.

### Phase 2: Core Implementation
Implement the server-side visualization analyzer that intelligently suggests chart types based on data characteristics, create the API endpoints for visualization suggestions and configuration, and build the client-side chart rendering engine with Chart.js. This phase delivers the core functionality of creating and displaying visualizations.

### Phase 3: Integration
Connect the visualization system to the existing query results display, add UI controls for chart type selection and customization, implement export functionality, and add LLM-powered insights generation to provide context for visualizations. This phase polishes the feature and integrates it seamlessly into the existing user experience.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Install Required Dependencies
- Add Chart.js to frontend: `cd app/client && npm install chart.js`
- Verify Chart.js types are available for TypeScript
- Test Chart.js installation with a simple example

### Create Visualization Data Models
- Add `ChartType` enum to `data_models.py` with values: BAR, LINE, PIE, SCATTER, AREA
- Create `ColumnAnalysis` model with fields: name, data_type, is_numeric, is_temporal, is_categorical, unique_count, sample_values
- Create `VisualizationSuggestion` model with fields: chart_type, x_axis_column, y_axis_columns, title, description, confidence_score
- Create `VisualizationRequest` model with fields: results (list), columns (list)
- Create `VisualizationResponse` model with fields: suggestions (list), primary_suggestion, data_summary
- Add unit tests for all new Pydantic models

### Implement Data Analysis Module
- Create `app/server/core/visualization_analyzer.py` with function `analyze_columns` to detect column types
- Implement `detect_temporal_column` to identify date/time columns using regex and common patterns
- Implement `detect_numeric_columns` to identify numeric data types
- Implement `detect_categorical_columns` to identify low-cardinality text columns (< 20 unique values)
- Implement `suggest_chart_types` that returns ranked list of appropriate visualizations based on column analysis
- Add logic: 1 numeric + 1 categorical = BAR chart; 2+ numeric + 1 temporal = LINE chart; 1 categorical with counts = PIE chart
- Write comprehensive unit tests for all analysis functions

### Add Visualization Suggestion Endpoint
- Add `POST /api/visualizations/suggest` endpoint in `server.py`
- Endpoint accepts `VisualizationRequest` with query results and columns
- Call `visualization_analyzer` to analyze data and generate suggestions
- Return top 3 chart suggestions with confidence scores
- Add error handling for empty results or invalid data structures
- Log all visualization requests for analytics

### Extend Query Endpoint for Visualization Metadata
- Modify `POST /api/query` endpoint to include visualization metadata in response
- Add `visualization_suggestions` field to `QueryResponse` model (optional)
- Automatically analyze results after query execution and attach suggestions
- Ensure backward compatibility - suggestions are optional and don't break existing clients
- Add flag `include_visualization_hints: bool = True` to `QueryRequest` model

### Create TypeScript Visualization Types
- Add interfaces to `src/types.d.ts`: `ChartType`, `ChartConfig`, `VisualizationSuggestion`
- Create `ChartData` interface with x_values, y_values, labels, colors
- Create `ChartOptions` interface with title, legend, axes configuration
- Ensure types align with Chart.js expected formats

### Build Visualization API Client
- Add `suggestVisualizations` method to `api/client.ts`
- Method accepts query results and returns visualization suggestions
- Add proper error handling and loading states
- Add TypeScript types matching the Pydantic models

### Create Chart Rendering Module
- Create `app/client/src/visualization.ts` with `ChartManager` class
- Implement `createChart` method that accepts chart type, data, and configuration
- Implement `updateChart` method to refresh chart with new data or settings
- Implement `destroyChart` method to properly clean up Chart.js instances
- Add helper functions: `prepareChartData`, `getChartOptions`, `formatDataForChartType`
- Support all chart types: bar, line, pie, scatter, area
- Add responsive chart sizing using Chart.js responsive features

### Build Visualization Panel UI
- Add visualization panel HTML structure to `index.html` after results section
- Include chart canvas element, chart type selector dropdown, and customize/export buttons
- Add toggle button in results header to switch between table and chart view
- Add loading spinner for chart generation
- Ensure proper ARIA labels for accessibility

### Style Visualization Panel
- Add CSS for visualization panel with smooth slide-in animation
- Style chart type selector as icon-based buttons (bar icon, line icon, pie icon, etc.)
- Add hover effects and active states for chart type selection
- Style export button with download icon
- Make charts responsive with max-width constraints
- Add empty state styling for "No visualization available"

### Integrate with Query Results
- Modify `displayResults` function in `main.ts` to show visualization button
- Add event listener for "Visualize" button click
- When clicked, initialize `ChartManager` and render default suggested chart
- Display chart type selector with suggestions highlighted
- Maintain both table and chart views, allow toggling between them

### Implement Chart Type Switching
- Add event handlers for chart type selector buttons
- When user selects different chart type, destroy old chart and create new one
- Validate that selected chart type is compatible with current data
- Show warning message if incompatible (e.g., pie chart needs exactly 1 categorical column)
- Animate transitions between chart types

### Add Chart Customization Controls
- Add color picker for chart colors (single color for bar/line, multiple for pie)
- Add input fields for custom chart title and axis labels
- Add toggle for showing/hiding legend
- Add toggle for showing/hiding grid lines
- Store customizations in state and reapply when switching chart types
- Add "Reset to Default" button to restore original suggestions

### Implement Chart Export Functionality
- Add export button with dropdown: PNG, SVG, CSV (data export)
- Implement PNG export using Chart.js `toBase64Image()` method
- Implement SVG export by converting canvas to SVG (may need library)
- Implement CSV export by converting chart data back to CSV format
- Add filename prompt with suggested name based on query
- Show success message after export

### Add LLM-Powered Chart Insights
- Add `generate_chart_insights` function to `llm_processor.py`
- Function takes chart type, data summary, and column names
- Uses LLM to generate 2-3 sentence insight about the visualization
- Prompt example: "Given a bar chart showing sales by category where Electronics is highest, provide a brief insight"
- Display insights below the chart in a styled insights card
- Add loading state while generating insights
- Implement fallback for LLM failures (generic message)

### Write Visualization Integration Tests
- Test full flow: query execution → visualization suggestion → chart rendering
- Test chart type switching with various data structures
- Test export functionality for each export format
- Test error handling for incompatible visualizations
- Test responsive behavior on different screen sizes
- Mock Chart.js to avoid rendering issues in tests

### Add Visualization Analytics Module
- Create function to track which chart types are most commonly used
- Track successful vs failed visualization attempts
- Store visualization preferences (most used chart types per user session)
- Log visualization generation time for performance monitoring
- Use localStorage for client-side preference storage

### Optimize Performance
- Implement debouncing for chart customization changes (300ms delay)
- Lazy load Chart.js library only when visualization is first requested
- Cache visualization suggestions to avoid re-analysis on chart type switching
- Limit maximum data points displayed in charts (e.g., 1000 points) for large datasets
- Add data sampling strategy for large results: show every Nth point or aggregate
- Show warning when data is sampled with "Showing X of Y points"

### Final Polish and Testing
- Add keyboard shortcuts: 'V' to toggle visualization, 'E' to export
- Add tooltips explaining each chart type's best use case
- Implement smooth loading states for all async operations
- Add comprehensive error messages for all failure scenarios
- Test with various query result types: time series, categorical, numerical
- Test edge cases: empty results, single row, single column, all null values
- Run all validation commands to ensure zero regressions

## Testing Strategy

### Unit Tests
- Test column analysis functions with various data types and patterns
- Test chart type suggestion algorithm with different data structures
- Test data preparation functions that convert query results to Chart.js format
- Test export functions with mocked Chart.js instances
- Test visualization analyzer with edge cases: nulls, empty strings, mixed types
- Test LLM insights generation with mocked API responses

### Integration Tests
- Test full visualization flow from query to rendered chart
- Test API endpoint for visualization suggestions with real data
- Test chart type switching maintains data integrity
- Test export functionality creates valid PNG/SVG/CSV files
- Test concurrent visualizations don't interfere with each other
- Test visualization with all sample datasets (users.json, products.csv)

### Edge Cases
- Query results with zero rows (empty results)
- Query results with single row or single column
- All numeric columns (no categorical data for x-axis)
- All categorical columns (no numeric data for y-axis)
- Columns with all null values
- Very large result sets (10,000+ rows)
- Very wide result sets (50+ columns)
- Mixed data types in same column (strings and numbers)
- Date columns in various formats (ISO, Unix timestamp, human-readable)
- Special characters in column names or data values
- Browser without Canvas API support
- Chart.js load failures or errors

## Acceptance Criteria
- "Visualize" button appears next to query results when data is suitable for visualization
- System suggests at least one appropriate chart type for any query with numeric data
- Users can switch between table and chart views without losing data
- All five chart types (bar, line, pie, scatter, area) render correctly with appropriate data
- Users can customize chart colors, titles, and labels through UI controls
- Charts are responsive and resize properly on window resize
- Export functionality generates valid PNG, SVG, and CSV files
- LLM-generated insights appear below charts within 2 seconds
- Performance remains smooth with query results up to 1000 rows
- Keyboard shortcuts work for toggling visualization and exporting
- All existing query and table functionality continues to work without regression
- Charts are accessible with proper ARIA labels for screen readers

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run all server tests to validate zero regressions
- `cd app/server && uv run pytest tests/core/test_visualization_analyzer.py -v` - Run specific visualization tests
- `cd app/server && uv run pytest tests/test_sql_injection.py -v` - Ensure SQL injection protection still works
- `cd app/client && npm run build` - Ensure client builds without TypeScript errors
- `cd app/client && npm run type-check` - Run TypeScript type checking (if available)
- `cd scripts && ./start.sh` - Start the application and manually test:
  - Execute queries with various data types and verify visualization suggestions
  - Test each chart type (bar, line, pie, scatter, area) with appropriate data
  - Toggle between table and chart views multiple times
  - Customize chart colors, titles, and labels
  - Export charts in all three formats (PNG, SVG, CSV)
  - Test with sample datasets (users and products)
  - Test responsive behavior by resizing browser window
  - Test keyboard shortcuts (V for toggle, E for export)
  - Verify LLM insights appear correctly
  - Test with large result sets (create query returning 500+ rows)
  - Test error handling by attempting incompatible visualizations
- `cd app/server && uv run python -c "import chart.js"` - Verify Chart.js is not a Python dependency (should fail, only npm)
- Test in multiple browsers: Chrome, Firefox, Safari (if available)

## Notes
- Chart.js is chosen for its excellent documentation, TypeScript support, and active maintenance
- The visualization analyzer uses heuristics for chart suggestions; future iterations could use ML models
- Consider adding more advanced chart types in future: heatmaps, box plots, histograms
- LLM insights could be enhanced to detect anomalies, outliers, or significant trends
- Future enhancement: Save favorite visualizations or create visualization templates
- Consider implementing data point highlighting that links chart elements back to table rows
- May need to add pagination or virtual scrolling for visualization panel with many suggestions
- The 1000-row limit for charts can be made configurable via environment variables
- Future: Add ability to combine multiple queries into dashboard with multiple charts
- Consider adding chart annotations for marking significant data points
- Export functionality could be extended to include PDF reports with multiple visualizations
- Future: Implement collaborative features where users can share visualizations via URL
- Consider adding animation options for chart rendering (fade in, count up, etc.)
- The data sampling strategy for large datasets should be transparent to users
- Future: Add A/B testing framework to optimize chart type suggestions based on user behavior
