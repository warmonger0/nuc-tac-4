/**
 * Visualization Module
 *
 * Handles chart rendering and management using Chart.js
 */

import { Chart, registerables } from 'chart.js';

// Register all Chart.js components
Chart.register(...registerables);

// Color palette for charts
const CHART_COLORS = [
  'rgba(54, 162, 235, 0.8)',   // Blue
  'rgba(255, 99, 132, 0.8)',   // Red
  'rgba(75, 192, 192, 0.8)',   // Green
  'rgba(255, 206, 86, 0.8)',   // Yellow
  'rgba(153, 102, 255, 0.8)',  // Purple
  'rgba(255, 159, 64, 0.8)',   // Orange
];

const CHART_BORDER_COLORS = [
  'rgba(54, 162, 235, 1)',
  'rgba(255, 99, 132, 1)',
  'rgba(75, 192, 192, 1)',
  'rgba(255, 206, 86, 1)',
  'rgba(153, 102, 255, 1)',
  'rgba(255, 159, 64, 1)',
];

export interface ChartCustomization {
  colors?: string[];
  title?: string;
  xAxisLabel?: string;
  yAxisLabel?: string;
  showLegend?: boolean;
  showGrid?: boolean;
}

/**
 * ChartManager class handles chart creation, updates, and destruction
 */
export class ChartManager {
  private chart: Chart | null = null;
  private canvas: HTMLCanvasElement;
  private currentData: Record<string, any>[] = [];
  private currentColumns: string[] = [];

  constructor(canvasId: string) {
    const canvas = document.getElementById(canvasId) as HTMLCanvasElement;
    if (!canvas) {
      throw new Error(`Canvas element with id '${canvasId}' not found`);
    }
    this.canvas = canvas;
  }

  /**
   * Create a new chart with the given configuration
   */
  createChart(
    suggestion: VisualizationSuggestion,
    data: Record<string, any>[],
    columns: string[],
    customization?: ChartCustomization
  ): void {
    // Store data for later use
    this.currentData = data;
    this.currentColumns = columns;

    // Destroy existing chart if any
    this.destroyChart();

    // Prepare chart data based on type
    const chartData = this.prepareChartData(suggestion, data, customization);

    // Get chart options
    const options = this.getChartOptions(suggestion, customization);

    // Create the chart
    this.chart = new Chart(this.canvas, {
      type: this.mapChartType(suggestion.chart_type),
      data: chartData,
      options: options
    });
  }

  /**
   * Update the chart with new data or configuration
   */
  updateChart(
    suggestion: VisualizationSuggestion,
    customization?: ChartCustomization
  ): void {
    if (!this.chart) {
      console.warn('No chart to update, creating new chart');
      return;
    }

    // Update chart data
    const chartData = this.prepareChartData(suggestion, this.currentData, customization);
    this.chart.data = chartData;

    // Update options
    const options = this.getChartOptions(suggestion, customization);
    this.chart.options = options;

    // Redraw
    this.chart.update();
  }

  /**
   * Destroy the current chart instance
   */
  destroyChart(): void {
    if (this.chart) {
      this.chart.destroy();
      this.chart = null;
    }
  }

  /**
   * Export chart as PNG image
   */
  exportPNG(filename: string = 'chart.png'): void {
    if (!this.chart) {
      console.error('No chart to export');
      return;
    }

    const url = this.chart.toBase64Image();
    const link = document.createElement('a');
    link.download = filename;
    link.href = url;
    link.click();
  }

  /**
   * Export chart data as CSV
   */
  exportCSV(filename: string = 'chart-data.csv'): void {
    if (!this.currentData || this.currentData.length === 0) {
      console.error('No data to export');
      return;
    }

    // Convert data to CSV
    const headers = this.currentColumns.join(',');
    const rows = this.currentData.map(row =>
      this.currentColumns.map(col => {
        const value = row[col];
        // Handle values with commas or quotes
        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return value;
      }).join(',')
    );

    const csv = [headers, ...rows].join('\n');

    // Create download link
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = filename;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  }

  /**
   * Get the current chart instance
   */
  getChart(): Chart | null {
    return this.chart;
  }

  /**
   * Prepare chart data based on suggestion and raw data
   */
  private prepareChartData(
    suggestion: VisualizationSuggestion,
    data: Record<string, any>[],
    customization?: ChartCustomization
  ): ChartData {
    const { chart_type, x_axis_column, y_axis_columns } = suggestion;

    // Sample data if too large (max 1000 points)
    const maxPoints = 1000;
    const sampledData = data.length > maxPoints
      ? this.sampleData(data, maxPoints)
      : data;

    let labels: string[] = [];
    let datasets: any[] = [];

    if (chart_type === 'pie') {
      // Pie chart: categories and single value
      labels = sampledData.map(row => String(row[x_axis_column || ''] || 'Unknown'));

      const values = sampledData.map(row => {
        const val = row[y_axis_columns[0]];
        return typeof val === 'number' ? val : 0;
      });

      datasets = [{
        label: y_axis_columns[0],
        data: values,
        backgroundColor: CHART_COLORS,
        borderColor: CHART_BORDER_COLORS,
        borderWidth: 1
      }];
    } else if (chart_type === 'scatter') {
      // Scatter plot: x and y coordinates
      const xCol = x_axis_column || y_axis_columns[0];
      const yCol = y_axis_columns[0] || y_axis_columns[1];

      datasets = [{
        label: `${yCol} vs ${xCol}`,
        data: sampledData.map(row => ({
          x: row[xCol],
          y: row[yCol]
        })),
        backgroundColor: customization?.colors?.[0] || CHART_COLORS[0],
        borderColor: customization?.colors?.[0] || CHART_BORDER_COLORS[0],
      }];
    } else {
      // Bar, line, area charts
      if (x_axis_column) {
        labels = sampledData.map(row => String(row[x_axis_column] || ''));
      } else {
        labels = sampledData.map((_, i) => String(i + 1));
      }

      datasets = y_axis_columns.map((col, index) => {
        const values = sampledData.map(row => {
          const val = row[col];
          return typeof val === 'number' ? val : 0;
        });

        return {
          label: col,
          data: values,
          backgroundColor: customization?.colors?.[index] || CHART_COLORS[index % CHART_COLORS.length],
          borderColor: customization?.colors?.[index] || CHART_BORDER_COLORS[index % CHART_BORDER_COLORS.length],
          borderWidth: 2,
          fill: chart_type === 'area'
        };
      });
    }

    return { labels, datasets };
  }

  /**
   * Get chart options based on type and customization
   */
  private getChartOptions(
    suggestion: VisualizationSuggestion,
    customization?: ChartCustomization
  ): any {
    const title = customization?.title || suggestion.title;
    const showLegend = customization?.showLegend !== undefined ? customization.showLegend : true;
    const showGrid = customization?.showGrid !== undefined ? customization.showGrid : true;

    const baseOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: title,
          font: {
            size: 16,
            weight: 'bold'
          }
        },
        legend: {
          display: showLegend,
          position: 'top' as const
        },
        tooltip: {
          enabled: true
        }
      }
    };

    // Add axis configuration for non-pie charts
    if (suggestion.chart_type !== 'pie') {
      return {
        ...baseOptions,
        scales: {
          x: {
            title: {
              display: !!customization?.xAxisLabel,
              text: customization?.xAxisLabel || ''
            },
            grid: {
              display: showGrid
            }
          },
          y: {
            title: {
              display: !!customization?.yAxisLabel,
              text: customization?.yAxisLabel || ''
            },
            grid: {
              display: showGrid
            },
            beginAtZero: true
          }
        }
      };
    }

    return baseOptions;
  }

  /**
   * Map internal chart type to Chart.js type
   */
  private mapChartType(type: ChartType): 'bar' | 'line' | 'pie' | 'scatter' | 'line' {
    if (type === 'area') {
      return 'line'; // Area is line with fill
    }
    return type;
  }

  /**
   * Sample data to reduce number of points
   */
  private sampleData(data: Record<string, any>[], maxPoints: number): Record<string, any>[] {
    if (data.length <= maxPoints) {
      return data;
    }

    const step = Math.ceil(data.length / maxPoints);
    const sampled: Record<string, any>[] = [];

    for (let i = 0; i < data.length; i += step) {
      sampled.push(data[i]);
    }

    return sampled;
  }
}

/**
 * Helper function to check if visualization is suitable for the data
 */
export function isVisualizationSuitable(
  results: Record<string, any>[],
  columns: string[]
): boolean {
  // Need at least some data and columns
  if (!results || results.length === 0 || !columns || columns.length === 0) {
    return false;
  }

  // Need at least one numeric or categorical column
  const hasNumericOrCategorical = columns.some(col => {
    const firstValue = results[0][col];
    return typeof firstValue === 'number' || typeof firstValue === 'string';
  });

  return hasNumericOrCategorical;
}

/**
 * Track visualization usage for analytics
 */
export function trackVisualizationUsage(
  chartType: ChartType,
  _dataSize: number
): void {
  try {
    const stats = JSON.parse(localStorage.getItem('viz_stats') || '{}');

    // Track chart type usage
    stats[chartType] = (stats[chartType] || 0) + 1;

    // Track total visualizations
    stats.total = (stats.total || 0) + 1;

    // Track last used
    stats.lastUsed = new Date().toISOString();

    localStorage.setItem('viz_stats', JSON.stringify(stats));
  } catch (error) {
    console.warn('Failed to track visualization usage:', error);
  }
}
