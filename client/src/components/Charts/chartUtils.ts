/* eslint-disable no-param-reassign */
/* eslint-disable @typescript-eslint/naming-convention */
/* eslint-disable @typescript-eslint/no-use-before-define */
/* eslint-disable vue/max-len */
/* eslint-disable no-underscore-dangle */
/* eslint-disable func-names */
// chartUtils.ts
import * as d3 from 'd3';

// Define types for the data structure
export interface HistogramData {
  bin_edges: number[];
  counts: number[];
}

export interface StringData {
  value: string;
  count: number;
}

// Type for the renderBarChart function arguments
interface BarChartArgs {
  chartElement: HTMLDivElement | null;
  chartData: HistogramData;
  xAxisLabel?: string; // Optional X-axis label
  yAxisLabel?: string; // Optional Y-axis label
}

// Type for the renderPieChart function arguments
interface PieChartArgs {
  chartElement: HTMLDivElement | null;
  chartData: StringData[];
}

// Bar chart rendering function
export const renderBarChart = ({
  chartElement,
  chartData,
  xAxisLabel,
  yAxisLabel,
}: BarChartArgs): void => {
  if (!chartElement || !('bin_edges' in chartData)) return;

  // Clear previous chart
  chartElement.innerHTML = '';

  const { bin_edges, counts } = chartData;

  const svg = d3
    .select(chartElement)
    .append('svg')
    .attr('width', '100%')
    .attr('height', 400);

  const margin = {
    top: 20,
    right: 30,
    bottom: 60, // Increased to accommodate the X-axis label
    left: 50, // Increased to accommodate the Y-axis label
  };
  const width = chartElement.clientWidth - margin.left - margin.right;
  const height = 400 - margin.top - margin.bottom;

  const x = d3
    .scaleLinear()
    .domain([bin_edges[0], bin_edges[bin_edges.length - 1]])
    .range([0, width]);

  const y = d3.scaleLinear().domain([0, d3.max(counts)!]).nice().range([height, 0]);

  const g = svg
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  g.append('g')
    .attr('class', 'axis axis--x')
    .attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(x));

  g.append('g').attr('class', 'axis axis--y').call(d3.axisLeft(y));

  // Append optional X-axis label
  if (xAxisLabel) {
    svg.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', margin.left + width / 2) // Centered relative to the chart
      .attr('y', height + margin.top + 40) // Positioned below the chart
      .attr('text-anchor', 'middle')
      .text(xAxisLabel);
  }

  // Append optional Y-axis label
  if (yAxisLabel) {
    svg.append('text')
      .attr('class', 'y-axis-label')
      .attr('transform', `translate(${margin.left - 30},${margin.top + height / 2}) rotate(-90)`) // Rotated for vertical alignment
      .attr('text-anchor', 'middle')
      .text(yAxisLabel);
  }

  g.selectAll('.bar')
    .data(counts)
    .enter()
    .append('rect')
    .attr('class', 'bar')
    .attr('x', (d, i) => x(bin_edges[i]))
    .attr('y', height) // Start from the bottom of the chart
    .attr('width', (d, i) => x(bin_edges[i + 1]) - x(bin_edges[i]) - 1)
    .attr('height', 0) // Start with height 0 for the transition effect
    .attr('fill', '#4285f4')
    .transition() // Transition for ease effect
    .duration(1000) // Duration of the transition
    .attr('y', (d) => y(d)) // Transition to the final y position
    .attr('height', (d) => height - y(d)); // Transition to the final height
};
// Pie chart rendering function
export const renderPieChart = ({
  chartElement,
  chartData,
  showLabels = true, // Option to enable or disable labels
  showHoverLabel = true, // Option to enable hover labels
}: PieChartArgs & { showLabels?: boolean, showHoverLabel?: boolean }): void => {
  if (!chartElement || !Array.isArray(chartData)) return;

  // eslint-disable-next-line no-param-reassign
  chartElement.innerHTML = ''; // Clear previous chart

  const data = chartData.map((d) => d.count);
  const labels = chartData.map((d) => d.value);
  const total = d3.sum(data); // Calculate total count for percentage

  const svg = d3
    .select(chartElement)
    .append('svg')
    .attr('width', '100%')
    .attr('height', 400)
    .append('g')
    .attr('transform', 'translate(200, 200)');

  const radius = Math.min(400, 400) / 2;

  const color = d3.scaleOrdinal(d3.schemeCategory10);

  const pie = d3.pie<number>().value((d) => d)(data);

  const arc = d3.arc<d3.PieArcDatum<number>>().innerRadius(0).outerRadius(radius);

  svg
    .selectAll('path')
    .data(pie)
    .enter()
    .append('path')
    .attr('d', arc)
    .attr('fill', (d, i) => color(i.toString()))
    .attr('opacity', 0) // Set initial opacity to 0 for fade-in effect
    .transition() // Transition for ease effect
    .duration(1000) // Duration of the transition
    .attr('opacity', 1) // Fade in
    .attrTween('d', function (d) {
      const interpolate = d3.interpolate(this._current || d, d); // Interpolate between previous and current data
      this._current = interpolate(0); // Store the current value
      return (t: number) => arc(interpolate(t)); // Return the interpolated arc
    });

  // Add event handlers after paths are created
  // Create tooltip div
  const tooltip = d3.select('body')
    .append('div')
    .attr('class', 'tooltip')
    .style('position', 'absolute')
    .style('z-index', '9999')
    .style('visibility', 'hidden')
    .style('background', '#333')
    .style('color', '#fff')
    .style('padding', '5px 10px')
    .style('border-radius', '4px')
    .style('font-size', '12px')
    .style('pointer-events', 'none')
    .style('opacity', 0); // Hidden by default

  // Tooltip event handlers
  if (showHoverLabel) {
    svg.selectAll('path')
      .on('mouseover', (event, d) => {
        // Update tooltip content
        tooltip.html(`Label: ${labels[d.index]}<br>Count: ${data[d.index]}<br>Percentage: ${((data[d.index] / total) * 100).toFixed(1)}%`)
          .style('visibility', 'visible')
          .style('top', `${event.clientY - 20}px`) // Adjust with SVG top offset
          .style('left', `${event.clientX + 10}px`) // Adjust with SVG left offset
          .style('opacity', 1); // Show tooltip with transition
      })
      .on('mousemove', (event) => {
        tooltip.style('top', `${event.clientY - 20}px`)
          .style('left', `${event.clientX + 10}px`);
      })
      .on('mouseout', () => {
        tooltip
          .style('visibility', 'hidden'); // Hide tooltip on mouse out
      });
  }
  if (showLabels) {
    svg
      .selectAll('g.label')
      .data(pie)
      .enter()
      .append('g')
      .attr('transform', (d) => `translate(${arc.centroid(d)})`)
      .each(function (d, i) {
        const group = d3.select(this);
        const count = data[i];
        const percentage = ((count / total) * 100).toFixed(1);

        group.append('text')
          .attr('dy', '-0.5em')
          .style('text-anchor', 'middle')
          .text(labels[i])
          .attr('opacity', 0)
          .transition()
          .duration(1000)
          .attr('opacity', 1);

        group.append('text')
          .attr('dy', '0.5em')
          .style('text-anchor', 'middle')
          .text(count)
          .attr('opacity', 0)
          .transition()
          .duration(1000)
          .attr('opacity', 1);

        group.append('text')
          .attr('dy', '1.5em')
          .style('text-anchor', 'middle')
          .text(`${percentage}%`)
          .attr('opacity', 0)
          .transition()
          .duration(1000)
          .attr('opacity', 1);
      });
  }
};

export const renderStyledPieChart = ({ chartElement, chartData }: PieChartArgs): void => {
  if (!chartElement || !Array.isArray(chartData)) return;

  // eslint-disable-next-line no-param-reassign
  chartElement.innerHTML = ''; // Clear any previous chart

  const data = chartData.map((d) => d.count);
  const labels = chartData.map((d) => d.value);
  const total = d3.sum(data); // Calculate total count for percentage

  // Set dimensions and radius for the chart
  const width = 500;
  const height = 400;
  const radius = Math.min(width, height) / 2;

  // Set up color scheme
  const color = d3.scaleOrdinal(d3.schemeCategory10);

  // Create the SVG container
  const svg = d3
    .select(chartElement)
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .append('g')
    .attr('transform', `translate(${width / 2}, ${height / 2})`);

  // Set up the pie layout
  const pie = d3.pie<number>().value((d) => d)(data);

  const arc = d3.arc<d3.PieArcDatum<number>>()
    .innerRadius(0)
    .outerRadius(radius * 0.8); // Slice radius

  const outerArc = d3.arc<d3.PieArcDatum<number>>()
    .innerRadius(radius * 0.9) // Line label outer arc
    .outerRadius(radius * 0.9);

  // Append pie slices
  svg.selectAll('path.slice')
    .data(pie)
    .enter()
    .append('path')
    .attr('class', 'slice')
    .attr('d', arc)
    .style('fill', (d, i) => color(i.toString()))
    .style('stroke', 'white')
    .style('stroke-width', 2)
    .attr('opacity', 0)
    .transition()
    .duration(1000)
    .attr('opacity', 1)
    .attrTween('d', function (d) {
      const interpolate = d3.interpolate(this._current || d, d);
      this._current = interpolate(0);
      return (t: number) => arc(interpolate(t));
    });

  // Append labels
  svg.selectAll('.label')
    .data(pie)
    .enter()
    .append('g')
    .attr('class', 'label')
    .each(function (d, i) {
      const group = d3.select(this);
      const percentage = ((data[i] / total) * 100).toFixed(1);

      group.append('text')
        .attr('dy', '.35em')
        .attr('transform', `translate(${outerArc.centroid(d)})`)
        .style('text-anchor', (subD) => (midAngle(subD) < Math.PI ? 'start' : 'end'))
        .text(`${labels[i]} (${percentage}%)`)
        .attr('opacity', 0)
        .transition()
        .duration(1000)
        .attr('opacity', 1);
    });

  // Append lines
  svg.selectAll('polyline')
    .data(pie)
    .enter()
    .append('polyline')
    .attr('points', (d) => {
      const pos = outerArc.centroid(d);
      pos[0] = radius * (midAngle(d) < Math.PI ? 1 : -1);
      return [arc.centroid(d), outerArc.centroid(d), pos];
    })
    .style('opacity', 0.3)
    .style('stroke', 'black')
    .style('stroke-width', 2)
    .style('fill', 'none');

  // Helper function to calculate the middle angle of a slice
  function midAngle(d: d3.PieArcDatum<number>): number {
    return d.startAngle + (d.endAngle - d.startAngle) / 2;
  }
};
