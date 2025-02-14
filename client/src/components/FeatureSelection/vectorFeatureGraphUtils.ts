/* eslint-disable func-names */
import * as d3 from 'd3';
import { FeatureGraphData } from '../../types';

const renderVectorFeatureGraph = (
  data: FeatureGraphData,
  container: SVGSVGElement,
  options?: {
    specificGraphKey?: number; // Option to draw a specific graph
    colors?: Record<number, string>; // Optional custom colors for specific graphs
    xAxisLabel?: string;
    yAxisLabel?: string;
    showXYValuesOnHover?: boolean; // New option to show X/Y instead of indexer
    onLineClick?: (indexer: string | number) => void; // Click handler
    xAxisIsTime?: boolean; // New option to convert x-axis values from UNIX timestamp
    xAxisVerticalLabels?: boolean; // New option to rotate x-axis labels vertically
    zoomable?: boolean; // New option to enable zooming
  },
) => {
  const localContainer = container;
  if (!localContainer || !data) return;

  const svg = d3.select(localContainer);
  svg.selectAll('*').remove(); // Clear previous content

  const margin = {
    top: 20, right: 20, bottom: 70, left: 50,
  };
  const width = (localContainer.clientWidth || 250) - margin.left - margin.right;
  const height = 400 - margin.top - margin.bottom;

  const x = options?.xAxisIsTime
    ? d3.scaleTime().range([0, width]) // Time scale if xAxisIsTime is true
    : d3.scaleLinear().range([0, width]); // Linear scale for numeric data
  const y = d3.scaleLinear().range([height, 0]);

  const line = d3.line()
    .x((d: [number, number]) => x(d[0]))
    .y((d: [number, number]) => y(d[1]));

  const graphsToRender = options?.specificGraphKey !== undefined
    ? { [options.specificGraphKey]: data.graphs[options.specificGraphKey] }
    : data.graphs;

  // Gather all data points for scaling
  const allDataPoints = Object.values(graphsToRender).flatMap((graph) => graph.data);

  if (allDataPoints.length === 0) return; // No data to render

  x.domain(d3.extent(allDataPoints, (d) => d[0]) as [number, number]);
  y.domain(d3.extent(allDataPoints, (d) => d[1]) as [number, number]);

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

  // Generate distinct colors for different graphs
  const colorScale = d3.scaleOrdinal(d3.schemeCategory10);
  const graphKeys = Object.keys(graphsToRender).map(Number);

  // Tooltip container (with background)
  const tooltipGroup = g.append('g')
    .attr('opacity', 0)
    .attr('pointer-events', 'none');

  const tooltipBg = tooltipGroup.append('rect')
    .attr('fill', 'rgba(0, 0, 0, 0.75)')
    .attr('rx', 5)
    .attr('ry', 5)
    .attr('width', 60)
    .attr('height', 30);

  const tooltipText = tooltipGroup.append('text')
    .attr('fill', 'white')
    .attr('font-size', '12px')
    .attr('text-anchor', 'middle');

  const convertXAxis = (d: number) => {
    if (options?.xAxisIsTime) {
      return d3.timeFormat('%Y-%m-%d')(d * 1000);
    }
    return d;
  };

  graphKeys.forEach((key, index) => {
    const graph = graphsToRender[key];
    const color = options?.colors?.[key] || colorScale(index.toString());

    const path = g.append('path')
      .datum(graph.data.sort((a, b) => a[0] - b[0]))
      .attr('fill', 'none')
      .attr('stroke', color)
      .attr('stroke-width', 2)
      .attr('d', line)
      .attr('cursor', 'pointer');

    if (!options?.specificGraphKey) {
      path.on('click', () => options?.onLineClick?.(key))
        .on('mouseover', function () {
          d3.select(this).attr('stroke-width', 4); // Highlight the line
          tooltipGroup.attr('opacity', 1);
        })
        .on('mousemove', (event) => {
          const [mouseX, mouseY] = d3.pointer(event);

          const tooltipTextContent = graph.indexer.toString();
          tooltipText.text(tooltipTextContent)
            .call((text) => {
              // Adjust the background size based on text width
              const bbox = text.node()?.getBBox();
              if (bbox) {
                tooltipBg.attr('x', bbox.x - 5)
                  .attr('y', bbox.y - 5)
                  .attr('width', bbox.width + 10)
                  .attr('height', bbox.height + 10);
              }
            });

          tooltipGroup.attr('transform', `translate(${mouseX + 10}, ${mouseY - 10})`).attr('opacity', 1);
        })
        .on('mouseout', function () {
          d3.select(this).attr('stroke-width', 2); // Reset thickness
          tooltipGroup.attr('opacity', 0);
        });
    } else if (options?.showXYValuesOnHover) {
      g.selectAll(`circle-${key}`)
        .data(graph.data)
        .enter()
        .append('circle')
        .attr('cx', (d) => x(d[0]))
        .attr('cy', (d) => y(d[1]))
        .attr('r', 4)
        .attr('fill', color)
        .attr('opacity', 0.8)
        .on('mouseover', () => {
          tooltipGroup.attr('opacity', 1);
        })
        .on('mousemove', (event, d) => {
          const [mouseX, mouseY] = d3.pointer(event);
          const tooltipTextContent = options?.showXYValuesOnHover
            ? `X: ${convertXAxis(d[0])}\nY: ${d[1]}`
            : graph.indexer.toString();
          tooltipText.text(tooltipTextContent)
            .call((text) => {
              // Adjust the background size based on text width
              const bbox = text.node()?.getBBox();
              if (bbox) {
                tooltipBg.attr('x', bbox.x - 5)
                  .attr('y', bbox.y - 5)
                  .attr('width', bbox.width + 10)
                  .attr('height', bbox.height + 10);
              }
            });

          tooltipGroup.attr('transform', `translate(${mouseX + 10}, ${mouseY - 0})`).attr('opacity', 1);
        })
        .on('mouseout', function () {
          d3.select(this).attr('stroke-width', 2); // Reset thickness
          tooltipGroup.attr('opacity', 0);
        });
    }
    const svgNode = svg.node();
    const tooltipGroupNode = tooltipGroup.node();
    if (svgNode && tooltipGroupNode) {
      svgNode.appendChild(tooltipGroupNode);
    }
  });

  // Zoom functionality
  if (options?.zoomable) {
    const zoom = d3.zoom()
      .scaleExtent([0.5, 10]) // Set zoom scale limits
      .translateExtent([[0, 0], [width, height]]) // Set translation limits
      .on('zoom', (event) => {
        g.attr('transform', event.transform); // Apply the zoom transformation
      });

    svg.call(zoom); // Apply zoom behavior to the entire SVG
  }

  // X-axis
  const xaxis = g.append('g')
    .attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(x).ticks(5));

  // If xAxisIsTime is true, format the axis labels as dates
  if (options?.xAxisIsTime) {
    xaxis.selectAll('text')
      .style('text-anchor', 'middle')
      .attr('dy', '0.35em')
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .text((d: any) => d3.timeFormat('%Y-%m-%d')(d * 1000));
  }

  // If xAxisVerticalLabels is true, rotate the labels vertically and adjust the position
  if (options?.xAxisVerticalLabels) {
    xaxis.selectAll('text')
      .style('text-anchor', 'end')
      .attr('dy', '0.35em')
      .attr('transform', 'rotate(-90)')
      .attr('x', -10) // Shift labels down to position below the axis
      .attr('y', 0); // Adjust the Y position to make sure labels are below
  }

  if (options?.xAxisLabel) {
    xaxis.append('text')
      .attr('x', width / 2)
      .attr('y', 40)
      .attr('fill', 'black')
      .attr('text-anchor', 'middle')
      .text(options?.xAxisLabel);
  }

  // Y-axis
  const yaxis = g.append('g').call(d3.axisLeft(y));

  if (options?.yAxisLabel) {
    // Dynamically adjust label positioning based on tick label width
    const yTickWidth = d3.max(yaxis.selectAll('text').nodes(), (node) => node.getBBox().width) || 0;
    yaxis.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('x', -height / 2 - 10) // Adjust the X position to ensure proper spacing
      .attr('y', -yTickWidth - 10)
      .attr('fill', 'black')
      .attr('text-anchor', 'middle')
      .text(options?.yAxisLabel);
  }
};

// eslint-disable-next-line import/prefer-default-export
export { renderVectorFeatureGraph };
