/* eslint-disable func-names */
import * as d3 from 'd3';
import { FeatureGraphData } from '../../types';

const renderVectorFeatureGraph = (
  data: FeatureGraphData,
  container: SVGSVGElement,
  options?: {
    specificGraphKey?: number;
    colors?: Record<number, string>;
    xAxisLabel?: string;
    yAxisLabel?: string;
    showXYValuesOnHover?: boolean;
    onLineClick?: (vectorFeatureId: number, indexer: string | number) => void;
    onLineHover?: (vectorFeatureId: number, indexer: string | number) => void;
    onLineExit?: (vectorFeatureId: number, indexer: string | number) => void;
    xAxisIsTime?: boolean;
    xAxisVerticalLabels?: boolean;
    zoomable?: boolean;
    hideBaseData?: boolean;
    showTrendline?: boolean;
    showMovingAverage?: boolean;
    showConfidenceInterval?: boolean;
  },
  baseHeight = 400,
) => {
  const outputColorMapping: Record<number, string> = {};
  const localContainer = container;
  if (!localContainer || !data) return outputColorMapping;

  const svg = d3.select(localContainer);
  svg.selectAll('*').remove();

  const defaultMargin = {
    top: 20, right: 20, bottom: options?.xAxisVerticalLabels ? 70 : 35, left: 50,
  };
  const width = (localContainer.clientWidth || 250) - defaultMargin.left - defaultMargin.right;
  const height = baseHeight - defaultMargin.top - defaultMargin.bottom;

  const x = options?.xAxisIsTime
    ? d3.scaleTime().range([0, width])
    : d3.scaleLinear().range([0, width]);
  const y = d3.scaleLinear().range([height, 0]);

  const line = d3.line()
    .x((d: [number, number]) => x(d[0]))
    .y((d: [number, number]) => y(d[1]));

  const lowerConfidence = d3.line()
    .x((d: [number, number]) => x(d[0]))
    .y((d: [number, number]) => y(d[1]));

  const upperConfidence = d3.line()
    .x((d: [number, number]) => x(d[0]))
    .y((d: [number, number]) => y(d[2]));

  const graphsToRender = options?.specificGraphKey !== undefined
    ? { [options.specificGraphKey]: data.graphs[options.specificGraphKey] }
    : data.graphs;

  const allDataPoints = Object.values(graphsToRender).flatMap((graph) => graph.data);
  if (allDataPoints.length === 0) return outputColorMapping;

  x.domain(d3.extent(allDataPoints, (d) => d[0]) as [number, number]);
  y.domain(d3.extent(allDataPoints, (d) => d[1]) as [number, number]);

  // Estimate max label width based on character count
  const allYValues = Object.values(graphsToRender).flatMap((graph) => graph.data.map((d) => d[1]));

  if (allYValues.length === 0) return outputColorMapping;

  y.domain(d3.extent(allYValues) as [number, number]);

  const maxYValue = Math.max(allYValues);
  const maxYLabel = maxYValue.toFixed(2); // Format to 2 decimal places
  const maxCharacters = maxYLabel.length;

  // Font size and estimated character width
  const fontSize = 12; // Default D3 tick font size
  const estimatedCharacterWidth = fontSize * 0.6; // Approximate width per character

  const estimatedMaxTickWidth = maxCharacters * estimatedCharacterWidth;

  // Adjust left margin based on estimated max tick width
  const adjustedLeftMargin = estimatedMaxTickWidth + (options?.yAxisLabel ? 20 : 10);

  const margin = {
    ...defaultMargin,
    left: Math.max(adjustedLeftMargin, defaultMargin.left),
  };

  // Recalculate width after adjusting margin

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

  const colorScale = d3.scaleOrdinal(d3.schemeCategory10);
  const graphKeys = Object.keys(graphsToRender).map(Number);
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
    outputColorMapping[key] = color;
    let path;
    if (!options?.hideBaseData) {
      path = g.append('path')
        .datum(graph.data.sort((a, b) => a[0] - b[0]))
        .attr('fill', 'none')
        .attr('stroke', color)
        .attr('stroke-width', 2)
        .attr('d', line)
        .attr('cursor', 'pointer')
        .attr('vectorFeatureId', key);
    }

    if (!options?.specificGraphKey && path) {
      path.on('click', () => options?.onLineClick?.(key, graph.indexer))
        .on('mouseover', function () {
          d3.selectAll('path') // Select all paths
            .attr('opacity', 0.3); // Dim all lines
          d3.select(this).attr('stroke-width', 4).attr('opacity', 1.0); // Highlight the line
          tooltipGroup.attr('opacity', 1);
          if (options?.onLineHover) {
            options.onLineHover(key, graph.indexer);
          }
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
          d3.selectAll('path') // Select all paths
            .attr('opacity', 1.0); // Dim all lines
          d3.select(this).attr('stroke-width', 2); // Reset thickness
          tooltipGroup.attr('opacity', 0);
          if (options?.onLineExit) {
            options.onLineExit(key, graph.indexer);
          }
        });
    } else if (options?.showXYValuesOnHover && path) {
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

    if (options?.showTrendline && graph.trendLine) {
      g.append('path')
        .datum(graph.trendLine)
        .attr('fill', 'none')
        .attr('stroke', '#FF00FF')
        .attr('stroke-width', 10)
        .attr('stroke-dasharray', '20,5')
        .attr('d', line)
        .attr('class', `trendline trendline-${key}`);
    }

    if (options?.showMovingAverage && graph.movingAverage) {
      g.append('path')
        .datum(graph.movingAverage)
        .attr('fill', 'none')
        .attr('stroke', '#FFFF00')
        .attr('stroke-width', 5)
        .attr('d', line)
        .attr('class', `moving-average moving-average-${key}`);
    }
    if (options?.showConfidenceInterval && graph.confidenceIntervals) {
      g.append('path')
        .datum(graph.confidenceIntervals)
        .attr('stroke', '#FF0000')
        .attr('stroke-width', 5)
        .attr('stroke-dasharray', '2,2')
        .attr('opacity', 0.75)
        .attr('d', lowerConfidence)
        .attr('class', `confidence-interval confidence-interval-${key}`);
      g.append('path')
        .datum(graph.confidenceIntervals)
        .attr('stroke', '#00FF00')
        .attr('stroke-width', 5)
        .attr('stroke-dasharray', '2,2')
        .attr('opacity', 0.75)
        .attr('d', upperConfidence)
        .attr('class', `confidence-interval confidence-interval-${key}`);
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
      .attr('y', 25)
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
      .attr('y', -yTickWidth - 15)
      .attr('fill', 'black')
      .attr('text-anchor', 'middle')
      .text(options?.yAxisLabel);
  }

  return outputColorMapping;
};

// eslint-disable-next-line import/prefer-default-export
export { renderVectorFeatureGraph };
