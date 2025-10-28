import './style.css'
import { api } from './api/client'
import { ChartManager, isVisualizationSuitable, trackVisualizationUsage } from './visualization'
import type { ChartCustomization } from './visualization'

// Global state
let currentResults: QueryResponse | null = null;
let chartManager: ChartManager | null = null;
let currentSuggestions: VisualizationSuggestion[] = [];
let currentSuggestion: VisualizationSuggestion | null = null;
let currentCustomization: ChartCustomization = {};

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
  initializeQueryInput();
  initializeFileUpload();
  initializeModal();
  initializeVisualization();
  loadDatabaseSchema();
});

// Query Input Functionality
function initializeQueryInput() {
  const queryInput = document.getElementById('query-input') as HTMLTextAreaElement;
  const queryButton = document.getElementById('query-button') as HTMLButtonElement;
  
  queryButton.addEventListener('click', async () => {
    const query = queryInput.value.trim();
    if (!query) return;
    
    queryButton.disabled = true;
    queryButton.innerHTML = '<span class="loading"></span>';
    
    try {
      const response = await api.processQuery({
        query,
        llm_provider: 'openai'  // Default to OpenAI
      });
      
      displayResults(response, query);
      
      // Clear the input field on success
      queryInput.value = '';
    } catch (error) {
      displayError(error instanceof Error ? error.message : 'Query failed');
    } finally {
      queryButton.disabled = false;
      queryButton.textContent = 'Query';
    }
  });
  
  // Allow Cmd+Enter (Mac) or Ctrl+Enter (Windows/Linux) to submit
  queryInput.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      queryButton.click();
    }
  });
}

// File Upload Functionality
function initializeFileUpload() {
  const dropZone = document.getElementById('drop-zone') as HTMLDivElement;
  const fileInput = document.getElementById('file-input') as HTMLInputElement;
  const browseButton = document.getElementById('browse-button') as HTMLButtonElement;
  
  // Browse button click
  browseButton.addEventListener('click', () => fileInput.click());
  
  // File input change
  fileInput.addEventListener('change', (e) => {
    const files = (e.target as HTMLInputElement).files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  });
  
  // Drag and drop
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });
  
  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });
  
  dropZone.addEventListener('drop', async (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  });
}

// Handle file upload
async function handleFileUpload(file: File) {
  try {
    const response = await api.uploadFile(file);
    
    if (response.error) {
      displayError(response.error);
    } else {
      displayUploadSuccess(response);
      await loadDatabaseSchema();
    }
  } catch (error) {
    displayError(error instanceof Error ? error.message : 'Upload failed');
  }
}

// Load database schema
async function loadDatabaseSchema() {
  try {
    const response = await api.getSchema();
    if (!response.error) {
      displayTables(response.tables);
    }
  } catch (error) {
    console.error('Failed to load schema:', error);
  }
}

// Display query results
function displayResults(response: QueryResponse, query: string) {
  currentResults = response;

  const resultsSection = document.getElementById('results-section') as HTMLElement;
  const sqlDisplay = document.getElementById('sql-display') as HTMLDivElement;
  const resultsContainer = document.getElementById('results-container') as HTMLDivElement;
  const visualizeButton = document.getElementById('visualize-button') as HTMLButtonElement;

  resultsSection.style.display = 'block';

  // Display natural language query and SQL
  sqlDisplay.innerHTML = `
    <div class="query-display">
      <strong>Query:</strong> ${query}
    </div>
    <div class="sql-query">
      <strong>SQL:</strong> <code>${response.sql}</code>
    </div>
  `;

  // Display results table
  if (response.error) {
    resultsContainer.innerHTML = `<div class="error-message">${response.error}</div>`;
    visualizeButton.style.display = 'none';
  } else if (response.results.length === 0) {
    resultsContainer.innerHTML = '<p>No results found.</p>';
    visualizeButton.style.display = 'none';
  } else {
    const table = createResultsTable(response.results, response.columns);
    resultsContainer.innerHTML = '';
    resultsContainer.appendChild(table);

    // Show visualize button if data is suitable
    if (isVisualizationSuitable(response.results, response.columns)) {
      visualizeButton.style.display = 'inline-block';

      // Store suggestions if available
      if (response.visualization_suggestions && response.visualization_suggestions.length > 0) {
        currentSuggestions = response.visualization_suggestions;
      }
    } else {
      visualizeButton.style.display = 'none';
    }
  }

  // Initialize toggle button
  const toggleButton = document.getElementById('toggle-results') as HTMLButtonElement;
  toggleButton.addEventListener('click', () => {
    resultsContainer.style.display = resultsContainer.style.display === 'none' ? 'block' : 'none';
    toggleButton.textContent = resultsContainer.style.display === 'none' ? 'Show' : 'Hide';
  });
}

// Create results table
function createResultsTable(results: Record<string, any>[], columns: string[]): HTMLTableElement {
  const table = document.createElement('table');
  table.className = 'results-table';
  
  // Header
  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  columns.forEach(col => {
    const th = document.createElement('th');
    th.textContent = col;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);
  
  // Body
  const tbody = document.createElement('tbody');
  results.forEach(row => {
    const tr = document.createElement('tr');
    columns.forEach(col => {
      const td = document.createElement('td');
      td.textContent = row[col] !== null ? String(row[col]) : '';
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  
  return table;
}

// Display tables
function displayTables(tables: TableSchema[]) {
  const tablesList = document.getElementById('tables-list') as HTMLDivElement;
  
  if (tables.length === 0) {
    tablesList.innerHTML = '<p class="no-tables">No tables loaded. Upload data or use sample data to get started.</p>';
    return;
  }
  
  tablesList.innerHTML = '';
  
  tables.forEach(table => {
    const tableItem = document.createElement('div');
    tableItem.className = 'table-item';
    
    // Header section
    const tableHeader = document.createElement('div');
    tableHeader.className = 'table-header';
    
    const tableLeft = document.createElement('div');
    tableLeft.style.display = 'flex';
    tableLeft.style.alignItems = 'center';
    tableLeft.style.gap = '1rem';
    
    const tableName = document.createElement('div');
    tableName.className = 'table-name';
    tableName.textContent = table.name;
    
    const tableInfo = document.createElement('div');
    tableInfo.className = 'table-info';
    tableInfo.textContent = `${table.row_count} rows, ${table.columns.length} columns`;
    
    tableLeft.appendChild(tableName);
    tableLeft.appendChild(tableInfo);
    
    const removeButton = document.createElement('button');
    removeButton.className = 'remove-table-button';
    removeButton.innerHTML = '&times;';
    removeButton.title = 'Remove table';
    removeButton.onclick = () => removeTable(table.name);
    
    tableHeader.appendChild(tableLeft);
    tableHeader.appendChild(removeButton);
    
    // Columns section
    const tableColumns = document.createElement('div');
    tableColumns.className = 'table-columns';
    
    table.columns.forEach(column => {
      const columnTag = document.createElement('span');
      columnTag.className = 'column-tag';
      
      const columnName = document.createElement('span');
      columnName.className = 'column-name';
      columnName.textContent = column.name;
      
      const columnType = document.createElement('span');
      columnType.className = 'column-type';
      const typeEmoji = getTypeEmoji(column.type);
      columnType.textContent = `${typeEmoji} ${column.type}`;
      
      columnTag.appendChild(columnName);
      columnTag.appendChild(columnType);
      tableColumns.appendChild(columnTag);
    });
    
    tableItem.appendChild(tableHeader);
    tableItem.appendChild(tableColumns);
    tablesList.appendChild(tableItem);
  });
}

// Display upload success
function displayUploadSuccess(response: FileUploadResponse) {
  // Close modal
  const modal = document.getElementById('upload-modal') as HTMLElement;
  modal.style.display = 'none';
  
  // Show success message
  const successDiv = document.createElement('div');
  successDiv.className = 'success-message';
  successDiv.textContent = `Table "${response.table_name}" created successfully with ${response.row_count} rows!`;
  successDiv.style.cssText = `
    background: rgba(40, 167, 69, 0.1);
    border: 1px solid var(--success-color);
    color: var(--success-color);
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
  `;
  
  const tablesSection = document.getElementById('tables-section') as HTMLElement;
  tablesSection.insertBefore(successDiv, tablesSection.firstChild);
  
  // Remove success message after 3 seconds
  setTimeout(() => {
    successDiv.remove();
  }, 3000);
}

// Display error
function displayError(message: string) {
  const errorDiv = document.createElement('div');
  errorDiv.className = 'error-message';
  errorDiv.textContent = message;
  
  const resultsContainer = document.getElementById('results-container') as HTMLDivElement;
  resultsContainer.innerHTML = '';
  resultsContainer.appendChild(errorDiv);
  
  const resultsSection = document.getElementById('results-section') as HTMLElement;
  resultsSection.style.display = 'block';
}

// Initialize modal
function initializeModal() {
  const uploadButton = document.getElementById('upload-data-button') as HTMLButtonElement;
  const modal = document.getElementById('upload-modal') as HTMLElement;
  const closeButton = modal.querySelector('.close-modal') as HTMLButtonElement;
  
  // Open modal
  uploadButton.addEventListener('click', () => {
    modal.style.display = 'flex';
  });
  
  // Close modal
  closeButton.addEventListener('click', () => {
    modal.style.display = 'none';
  });
  
  // Close on background click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.style.display = 'none';
    }
  });
  
  // Initialize sample data buttons
  const sampleButtons = modal.querySelectorAll('.sample-button');
  sampleButtons.forEach(button => {
    button.addEventListener('click', async (e) => {
      const sampleType = (e.currentTarget as HTMLElement).dataset.sample;
      await loadSampleData(sampleType!);
    });
  });
}

// Remove table
async function removeTable(tableName: string) {
  if (!confirm(`Are you sure you want to remove the table "${tableName}"?`)) {
    return;
  }
  
  try {
    const response = await fetch(`/api/table/${tableName}`, {
      method: 'DELETE'
    });
    
    if (!response.ok) {
      throw new Error('Failed to remove table');
    }
    
    // Reload schema
    await loadDatabaseSchema();
    
    // Show success message
    const successDiv = document.createElement('div');
    successDiv.className = 'success-message';
    successDiv.textContent = `Table "${tableName}" removed successfully!`;
    successDiv.style.cssText = `
      background: rgba(40, 167, 69, 0.1);
      border: 1px solid var(--success-color);
      color: var(--success-color);
      padding: 1rem;
      border-radius: 8px;
      margin-bottom: 1rem;
    `;
    
    const tablesSection = document.getElementById('tables-section') as HTMLElement;
    tablesSection.insertBefore(successDiv, tablesSection.firstChild);
    
    setTimeout(() => {
      successDiv.remove();
    }, 3000);
  } catch (error) {
    displayError(error instanceof Error ? error.message : 'Failed to remove table');
  }
}

// Get emoji for data type
function getTypeEmoji(type: string): string {
  const upperType = type.toUpperCase();
  
  // SQLite types
  if (upperType.includes('INT')) return '🔢';
  if (upperType.includes('REAL') || upperType.includes('FLOAT') || upperType.includes('DOUBLE')) return '💯';
  if (upperType.includes('TEXT') || upperType.includes('CHAR') || upperType.includes('STRING')) return '📝';
  if (upperType.includes('DATE') || upperType.includes('TIME')) return '📅';
  if (upperType.includes('BOOL')) return '✓';
  if (upperType.includes('BLOB')) return '📦';
  
  // Default
  return '📊';
}

// Load sample data
async function loadSampleData(sampleType: string) {
  try {
    const filename = sampleType === 'users' ? 'users.json' : 'products.csv';
    const response = await fetch(`/sample-data/${filename}`);

    if (!response.ok) {
      throw new Error('Failed to load sample data');
    }

    const blob = await response.blob();
    const file = new File([blob], filename, { type: blob.type });

    // Upload the file
    await handleFileUpload(file);
  } catch (error) {
    displayError(error instanceof Error ? error.message : 'Failed to load sample data');
  }
}

// Initialize visualization functionality
function initializeVisualization() {
  // Initialize ChartManager
  chartManager = new ChartManager('visualization-canvas');

  // Visualize button click
  const visualizeButton = document.getElementById('visualize-button') as HTMLButtonElement;
  visualizeButton.addEventListener('click', showVisualization);

  // Close visualization button
  const closeVizButton = document.getElementById('close-viz') as HTMLButtonElement;
  closeVizButton.addEventListener('click', hideVisualization);

  // Toggle view button
  const toggleViewButton = document.getElementById('toggle-view') as HTMLButtonElement;
  toggleViewButton.addEventListener('click', toggleView);

  // Chart type selector buttons
  const chartTypeButtons = document.querySelectorAll('.chart-type-btn');
  chartTypeButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      const chartType = (e.currentTarget as HTMLElement).dataset.type as ChartType;
      switchChartType(chartType);
    });
  });

  // Customize button
  const customizeBtn = document.getElementById('customize-btn') as HTMLButtonElement;
  customizeBtn.addEventListener('click', openCustomizationModal);

  // Export button
  const exportBtn = document.getElementById('export-btn') as HTMLButtonElement;
  exportBtn.addEventListener('click', openExportModal);

  // Customization modal
  initializeCustomizationModal();

  // Export modal
  initializeExportModal();
}

// Show visualization
async function showVisualization() {
  if (!currentResults || !currentResults.results || currentResults.results.length === 0) {
    return;
  }

  const vizPanel = document.getElementById('visualization-panel') as HTMLElement;
  const resultsSection = document.getElementById('results-section') as HTMLElement;

  // Show visualization panel
  vizPanel.style.display = 'block';
  resultsSection.style.display = 'none';

  // Show loading
  const chartLoading = document.getElementById('chart-loading') as HTMLElement;
  chartLoading.style.display = 'block';

  try {
    // Get suggestions if not already available
    if (currentSuggestions.length === 0) {
      const vizResponse = await api.suggestVisualizations({
        results: currentResults.results,
        columns: currentResults.columns
      });

      if (vizResponse.error) {
        throw new Error(vizResponse.error);
      }

      currentSuggestions = vizResponse.suggestions;
    }

    if (currentSuggestions.length === 0) {
      throw new Error('No visualization suggestions available for this data');
    }

    // Use primary suggestion
    currentSuggestion = currentSuggestions[0];

    // Create chart
    if (chartManager) {
      chartManager.createChart(
        currentSuggestion,
        currentResults.results,
        currentResults.columns,
        currentCustomization
      );

      // Track usage
      trackVisualizationUsage(currentSuggestion.chart_type, currentResults.results.length);

      // Show data warning if sampled
      if (currentResults.results.length > 1000) {
        const dataWarning = document.getElementById('data-warning') as HTMLElement;
        dataWarning.style.display = 'block';
        dataWarning.querySelector('p')!.textContent =
          `Showing visualization of ${Math.min(1000, currentResults.results.length)} of ${currentResults.results.length} data points`;
      }

      // Highlight active chart type
      updateActiveChartType(currentSuggestion.chart_type);
    }
  } catch (error) {
    console.error('Visualization error:', error);
    alert(error instanceof Error ? error.message : 'Failed to create visualization');
    hideVisualization();
  } finally {
    chartLoading.style.display = 'none';
  }
}

// Hide visualization
function hideVisualization() {
  const vizPanel = document.getElementById('visualization-panel') as HTMLElement;
  const resultsSection = document.getElementById('results-section') as HTMLElement;

  vizPanel.style.display = 'none';
  resultsSection.style.display = 'block';

  // Reset data warning
  const dataWarning = document.getElementById('data-warning') as HTMLElement;
  dataWarning.style.display = 'none';
}

// Toggle between table and chart view
function toggleView() {
  const vizPanel = document.getElementById('visualization-panel') as HTMLElement;
  const resultsSection = document.getElementById('results-section') as HTMLElement;
  const toggleViewButton = document.getElementById('toggle-view') as HTMLButtonElement;

  if (resultsSection.style.display === 'none') {
    // Switch to table
    resultsSection.style.display = 'block';
    vizPanel.style.display = 'none';
    toggleViewButton.textContent = 'Switch to Chart';
  } else {
    // Switch to chart
    resultsSection.style.display = 'none';
    vizPanel.style.display = 'block';
    toggleViewButton.textContent = 'Switch to Table';
  }
}

// Switch chart type
function switchChartType(chartType: ChartType) {
  if (!currentResults || !chartManager) return;

  // Find matching suggestion or create a basic one
  let suggestion = currentSuggestions.find(s => s.chart_type === chartType);

  if (!suggestion) {
    // Create a basic suggestion
    suggestion = {
      chart_type: chartType,
      x_axis_column: currentResults.columns[0],
      y_axis_columns: currentResults.columns.slice(1, 2),
      title: `${chartType.charAt(0).toUpperCase() + chartType.slice(1)} Chart`,
      description: '',
      confidence_score: 0.5
    };
  }

  currentSuggestion = suggestion;

  // Update chart
  chartManager.createChart(
    suggestion,
    currentResults.results,
    currentResults.columns,
    currentCustomization
  );

  // Update active button
  updateActiveChartType(chartType);

  // Track usage
  trackVisualizationUsage(chartType, currentResults.results.length);
}

// Update active chart type button
function updateActiveChartType(chartType: ChartType) {
  const chartTypeButtons = document.querySelectorAll('.chart-type-btn');
  chartTypeButtons.forEach(btn => {
    if ((btn as HTMLElement).dataset.type === chartType) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
}

// Initialize customization modal
function initializeCustomizationModal() {
  const modal = document.getElementById('customization-modal') as HTMLElement;
  const closeButton = modal.querySelector('.close-modal') as HTMLButtonElement;
  const applyButton = document.getElementById('apply-customization') as HTMLButtonElement;
  const resetButton = document.getElementById('reset-customization') as HTMLButtonElement;

  // Close modal
  closeButton.addEventListener('click', () => {
    modal.style.display = 'none';
  });

  // Apply customization
  applyButton.addEventListener('click', () => {
    const title = (document.getElementById('chart-title') as HTMLInputElement).value;
    const xAxisLabel = (document.getElementById('x-axis-label') as HTMLInputElement).value;
    const yAxisLabel = (document.getElementById('y-axis-label') as HTMLInputElement).value;
    const showLegend = (document.getElementById('show-legend') as HTMLInputElement).checked;
    const showGrid = (document.getElementById('show-grid') as HTMLInputElement).checked;

    currentCustomization = {
      title: title || undefined,
      xAxisLabel: xAxisLabel || undefined,
      yAxisLabel: yAxisLabel || undefined,
      showLegend,
      showGrid
    };

    // Update chart
    if (chartManager && currentSuggestion && currentResults) {
      chartManager.updateChart(currentSuggestion, currentCustomization);
    }

    modal.style.display = 'none';
  });

  // Reset customization
  resetButton.addEventListener('click', () => {
    currentCustomization = {};

    // Clear form
    (document.getElementById('chart-title') as HTMLInputElement).value = '';
    (document.getElementById('x-axis-label') as HTMLInputElement).value = '';
    (document.getElementById('y-axis-label') as HTMLInputElement).value = '';
    (document.getElementById('show-legend') as HTMLInputElement).checked = true;
    (document.getElementById('show-grid') as HTMLInputElement).checked = true;

    // Update chart
    if (chartManager && currentSuggestion && currentResults) {
      chartManager.createChart(
        currentSuggestion,
        currentResults.results,
        currentResults.columns,
        currentCustomization
      );
    }

    modal.style.display = 'none';
  });

  // Close on background click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.style.display = 'none';
    }
  });
}

// Open customization modal
function openCustomizationModal() {
  const modal = document.getElementById('customization-modal') as HTMLElement;

  // Pre-fill with current values
  if (currentSuggestion) {
    (document.getElementById('chart-title') as HTMLInputElement).value =
      currentCustomization.title || currentSuggestion.title;
  }

  (document.getElementById('x-axis-label') as HTMLInputElement).value =
    currentCustomization.xAxisLabel || '';
  (document.getElementById('y-axis-label') as HTMLInputElement).value =
    currentCustomization.yAxisLabel || '';
  (document.getElementById('show-legend') as HTMLInputElement).checked =
    currentCustomization.showLegend !== undefined ? currentCustomization.showLegend : true;
  (document.getElementById('show-grid') as HTMLInputElement).checked =
    currentCustomization.showGrid !== undefined ? currentCustomization.showGrid : true;

  modal.style.display = 'flex';
}

// Initialize export modal
function initializeExportModal() {
  const modal = document.getElementById('export-modal') as HTMLElement;
  const closeButton = modal.querySelector('.close-modal') as HTMLButtonElement;
  const exportOptions = modal.querySelectorAll('.export-option');

  // Close modal
  closeButton.addEventListener('click', () => {
    modal.style.display = 'none';
  });

  // Export options
  exportOptions.forEach(option => {
    option.addEventListener('click', () => {
      const format = (option as HTMLElement).dataset.format as 'png' | 'csv';
      handleExport(format);
      modal.style.display = 'none';
    });
  });

  // Close on background click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.style.display = 'none';
    }
  });
}

// Open export modal
function openExportModal() {
  const modal = document.getElementById('export-modal') as HTMLElement;
  modal.style.display = 'flex';
}

// Handle export
function handleExport(format: 'png' | 'csv') {
  if (!chartManager) return;

  const timestamp = new Date().toISOString().slice(0, 10);
  const filename = `chart-${timestamp}`;

  if (format === 'png') {
    chartManager.exportPNG(`${filename}.png`);
  } else if (format === 'csv') {
    chartManager.exportCSV(`${filename}.csv`);
  }

  // Show success message
  const successDiv = document.createElement('div');
  successDiv.className = 'success-message';
  successDiv.textContent = `Chart exported as ${format.toUpperCase()} successfully!`;
  successDiv.style.cssText = `
    position: fixed;
    top: 2rem;
    right: 2rem;
    background: rgba(40, 167, 69, 0.9);
    color: white;
    padding: 1rem 1.5rem;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    z-index: 10000;
  `;

  document.body.appendChild(successDiv);

  setTimeout(() => {
    successDiv.remove();
  }, 3000);
}
