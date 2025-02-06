/* eslint-disable func-names */
/* eslint-disable import/prefer-default-export */
import * as d3 from 'd3';

export function drawBarChart(
  id: string,
  data: { key: string; value: number; color?: string }[],
  sortOption: 'value' | 'name' | 'static',
  keyStaticLabels: boolean,
  keyHighlightLabels: boolean,
  maxWidth = 300, // Optional max width for the chart, default is 300px
) {
  // Sort the data based on the sort option
  if (sortOption === 'value') {
    data.sort((a, b) => b.value - a.value);
  } else if (sortOption === 'name') {
    data.sort((a, b) => a.key.localeCompare(b.key));
  }

  const svgContainer = d3.select(`#${id}`);
  svgContainer.select('svg').remove();

  let maxLabelWidth = 0;
  if (keyStaticLabels) {
    const tempSvg = svgContainer.append('svg').attr('visibility', 'hidden');
    const tempText = tempSvg
      .selectAll('text')
      .data(data)
      .enter()
      .append('text')
      .style('font-size', '10px')
      .text((d) => d.key);
    tempText.each(function () {
      const textWidth = this.getBBox().width;
      if (textWidth > maxLabelWidth) {
        maxLabelWidth = textWidth;
      }
    });
    tempSvg.remove();
  }

  const margin = {
    top: 20,
    right: 30,
    bottom: 40,
    left: keyStaticLabels ? maxLabelWidth + 10 : 0,
  };
  const width = maxWidth - margin.left - margin.right;
  const minHeight = 25;
  const numBars = data.length;
  const height = Math.max(numBars * minHeight, 300) - margin.top - margin.bottom;

  const maxValue = d3.max(data, (d) => d.value)!;
  const minValue = d3.min(data, (d) => d.value)!;

  const svg = svgContainer
    .append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  svg.append('g').attr('class', 'x-axis').attr('transform', `translate(0,${height})`);
  svg.append('g').attr('class', 'y-axis');

  const x = d3.scaleLinear().domain([minValue, maxValue]).range([0, width]);
  const y = d3
    .scaleBand()
    .domain(data.map((d) => d.key))
    .range([0, height])
    .padding(0.1);

  svg.select('.x-axis').call(d3.axisBottom(x));
  const yAxis = d3.axisLeft(y);

  if (!keyStaticLabels) {
    yAxis.tickFormat(() => '');
  }

  const yAxisSelection = svg.select('.y-axis').call(yAxis);

  const bars = svg.selectAll('rect').data(data);
  bars.exit().remove();

  // Animate the bars from 0 to the current value
  bars
    .enter()
    .append('rect')
    .attr('x', 0)
    .attr('y', (d) => y(d.key)!)
    .attr('width', 0) // Start with a width of 0
    .attr('height', y.bandwidth())
    .attr('fill', (d) => d.color || 'steelblue')
    .merge(bars)
    .transition()
    .duration(1000)
    .attr('width', (d) => x(d.value));

  // Update existing bars
  bars
    .transition()
    .duration(1000)
    .attr('y', (d) => y(d.key)!)
    .attr('width', (d) => x(d.value))
    .attr('height', y.bandwidth())
    .attr('fill', (d) => d.color || 'steelblue');

  // Create tooltip once, don't remove it, just hide/show it dynamically
  let tooltip = svg.select('#tooltip');
  if (tooltip.empty()) {
    tooltip = svg
      .append('text')
      .attr('id', 'tooltip')
      .attr('fill', 'black')
      .style('font-size', '10px')
      .style('font-weight', 'bold')
      .style('visibility', 'hidden'); // Initially hidden
  }

  const highlightBar = (d: { key: string; value: number; color?: string }) => {
    svg
      .selectAll('rect')
      .filter((barData) => barData.key === d.key)
      .attr('fill', 'cyan');

    const barHeight = y.bandwidth();
    const yPosition = y(d.key)! + barHeight / 2 + 3;

    tooltip
      .attr('x', 10) // Position outside the bar to avoid hover flicker
      .attr('y', yPosition)
      .text(`${d.key}: ${d.value.toFixed(2)}`)
      .style('visibility', 'visible');
  };

  let highlightedRect: boolean | { left: number; right: number; top: number; bottom: number } = false;
  const resetBar = (d: { key: string; value: number; color?: string }) => {
    svg
      .selectAll('rect')
      .filter((barData) => barData.key === d.key)
      .attr('fill', d.color || 'steelblue');
    tooltip.style('visibility', 'hidden');
    highlightedRect = false;
  };

  if (keyHighlightLabels) {
    svg
      .selectAll('rect')
      .on('mouseover', (event, d) => {
        highlightedRect = event.target.getBoundingClientRect();
        highlightBar(d);
      })
      .on('mouseout', (event, d) => {
        const bounds = highlightedRect;
        const mouseX = event.clientX;
        const mouseY = event.clientY;

        // Check if the mouse is outside the bounds of the rectangle
        if (bounds) {
          const isInside = mouseX > bounds.left
          && mouseX < bounds.right
          && mouseY > bounds.top
          && mouseY < bounds.bottom;
          if (isInside) {
            return;
          }
        }
        resetBar(d);
      });

    // Add hover events to the Y-axis tick labels
    yAxisSelection
      .selectAll('.tick text')
      .on('mouseover', (event, d) => {
        const hoveredKey = d as string;
        const barData = data.find((bar) => bar.key === hoveredKey);
        if (barData) {
          highlightBar(barData);
        }
      })
      .on('mouseout', (event, d) => {
        const hoveredKey = d as string;
        const barData = data.find((bar) => bar.key === hoveredKey);
        if (barData) {
          resetBar(barData);
        }
      });
  } else {
    svg.selectAll('rect').on('mouseover', null).on('mouseout', null);
    yAxisSelection.selectAll('.tick text').on('mouseover', null).on('mouseout', null);
  }
  const xAxisLabels = svg.select('.x-axis').selectAll('text');

  const labelWidth = Math.max(...xAxisLabels.nodes().map((node) => node.getBBox().width));
  const availableWidth = width / data.length; // Width for each bar

  if (labelWidth > availableWidth) {
    // Remove middle labels, keeping only the first and last
    const ticks = svg.select('.x-axis').selectAll('.tick text');

    ticks.each(function (d, i) {
      if (i !== 0 && i !== ticks.nodes().length - 1) {
        d3.select(this).remove();
      }
    });
  }
}
