import { useEffect, useRef } from "react";
import * as d3 from "d3";

type Slice = {
    experiment_id: number;
    experiment_name: string;
    total_cost: number;
    percentage?: number;
    run_count?: number;
};

export default function CostPieChart({
    data,
    onSliceClick,
    width = 520,
    height = 360,
}: {
    data: Slice[];
    onSliceClick?: (id: number) => void;
    width?: number;
    height?: number;
}) {
    const svgRef = useRef<SVGSVGElement | null>(null);

    useEffect(() => {
        if (!data?.length) return;

        // Calculate dimensions - leave space for legend
        const radius = Math.min(width, height) / 2 - 40;

        // Create arc generators for normal and hover states
        const arc = d3.arc<d3.PieArcDatum<Slice>>()
            .innerRadius(radius * 0.3)  // Add inner radius for donut style (looks more modern)
            .outerRadius(radius);

        const arcHover = d3.arc<d3.PieArcDatum<Slice>>()
            .innerRadius(radius * 0.3)
            .outerRadius(radius + 10);

        // Create pie layout
        const pie = d3
            .pie<Slice>()
            .value((d) => d.total_cost)
            .sort((a, b) => b.total_cost - a.total_cost)  // Sort by value for better visual hierarchy
            .padAngle(0.02);  // Add small gaps between slices

        // Better color scheme - use a gradient of blues/purples for consistency
        const colorScale = d3.scaleOrdinal<string>()
            .domain(data.map((_, i) => String(i)))
            .range([
                '#3b82f6',  // blue-500
                '#8b5cf6',  // violet-500
                '#06b6d4',  // cyan-500
                '#10b981',  // emerald-500
                '#f59e0b',  // amber-500
                '#ef4444',  // red-500
            ]);

        // Setup SVG
        const svg = d3
            .select(svgRef.current!)
            .attr("width", width)
            .attr("height", height);
        svg.selectAll("*").remove();

        // Add gradient definitions for depth effect
        const defs = svg.append("defs");
        data.forEach((_, i) => {
            const gradient = defs.append("radialGradient")
                .attr("id", `pie-gradient-${i}`)
                .attr("cx", "30%")
                .attr("cy", "30%");

            gradient.append("stop")
                .attr("offset", "0%")
                .style("stop-color", d3.color(colorScale(String(i)))!.brighter(0.5).toString());

            gradient.append("stop")
                .attr("offset", "100%")
                .style("stop-color", colorScale(String(i)));
        });

        // Main group centered
        const g = svg
            .append("g")
            .attr("transform", `translate(${width / 2},${height / 2})`);

        // Create tooltip attached to body for better positioning
        const tooltip = d3
            .select("body")
            .append("div")
            .attr("class", "chart-tooltip")
            .style("position", "absolute")
            .style("pointer-events", "none")
            .style("background", "white")
            .style("border", "1px solid #e5e7eb")
            .style("padding", "10px 12px")
            .style("border-radius", "8px")
            .style("font-size", "13px")
            .style("box-shadow", "0 8px 16px rgba(0,0,0,.12)")
            .style("opacity", 0)
            .style("z-index", 1000);

        // Draw pie slices with animation
        const arcs = g
            .selectAll("path")
            .data(pie(data))
            .enter()
            .append("path")
            .attr("fill", (_, i) => `url(#pie-gradient-${i})`)
            .style("cursor", "pointer")
            .style("filter", "drop-shadow(0 2px 4px rgba(0,0,0,0.1))")
            // Start animation from center
            .transition()
            .duration(800)
            .attrTween("d", function (d) {
                const interpolate = d3.interpolate({ startAngle: 0, endAngle: 0 }, d);
                return function (t) {
                    return arc(interpolate(t))!;
                };
            });

        // Add interactions after animation
        g.selectAll("path")
            .on("mouseenter", function (event, d) {
                // Lift up the slice
                d3.select(this)
                    .transition()
                    .duration(150)
                    .attr("d", arcHover(d))
                    .style("filter", "drop-shadow(0 4px 8px rgba(0,0,0,0.2))");

                // Calculate percentage if not provided
                const totalCost = d3.sum(data, x => x.total_cost);
                const pct = d.data.percentage ?? (d.data.total_cost / totalCost) * 100;

                // Show tooltip with better formatting
                tooltip
                    .style("opacity", 1)
                    .html(
                        `<div style="font-weight:600;margin-bottom:6px;color:#1f2937;font-size:14px">
                            ${d.data.experiment_name}
                        </div>
                        <div style="display:flex;justify-content:space-between;gap:20px">
                            <span style="color:#6b7280">Cost:</span>
                            <span style="font-weight:600;color:#1f2937">$${d.data.total_cost.toFixed(2)}</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;gap:20px">
                            <span style="color:#6b7280">Share:</span>
                            <span style="font-weight:600;color:#1f2937">${pct.toFixed(1)}%</span>
                        </div>
                        ${d.data.run_count != null ?
                            `<div style="display:flex;justify-content:space-between;gap:20px">
                                <span style="color:#6b7280">Runs:</span>
                                <span style="font-weight:600;color:#1f2937">${d.data.run_count}</span>
                            </div>` : ""}`
                    );
            })
            .on("mousemove", function (event) {
                // Position tooltip near cursor
                tooltip
                    .style("left", (event.pageX + 15) + "px")
                    .style("top", (event.pageY - 10) + "px");
            })
            .on("mouseleave", function (_event, d) {
                // Reset slice
                d3.select(this)
                    .transition()
                    .duration(150)
                    .attr("d", arc(d))
                    .style("filter", "drop-shadow(0 2px 4px rgba(0,0,0,0.1))");

                tooltip.style("opacity", 0);
            })
            .on("click", (_event, d) => {
                onSliceClick?.(d.data.experiment_id);
            });

        // Add center text showing total
        // const totalCost = d3.sum(data, d => d.total_cost);
        // const centerText = g.append("g");



        // Add legend on the side
        const legend = svg.append("g")
            .attr("transform", `translate(${width - 120}, 20)`);

        const legendItems = legend.selectAll(".legend-item")
            .data(data.slice(0, 5))  // Show top 5
            .enter()
            .append("g")
            .attr("class", "legend-item")
            .attr("transform", (_, i) => `translate(0, ${i * 25})`)
            .style("cursor", "pointer")
            .on("mouseenter", function (_, d) {
                // Highlight corresponding slice
                g.selectAll("path")
                    .style("opacity", p => p.data.experiment_id === d.experiment_id ? 1 : 0.3);
            })
            .on("mouseleave", function () {
                g.selectAll("path").style("opacity", 1);
            });

        // Legend color box
        legendItems.append("rect")
            .attr("width", 12)
            .attr("height", 12)
            .attr("rx", 2)
            .attr("fill", (_, i) => colorScale(String(i)));

        // Legend text
        legendItems.append("text")
            .attr("x", 18)
            .attr("y", 6)
            .attr("dy", "0.35em")
            .style("font-size", "12px")
            .style("fill", "#4b5563")
            .text(d => {
                const name = d.experiment_name;
                return name.length > 10 ? name.substring(0, 10) + "..." : name;
            });

        // Cleanup
        return () => {
            tooltip.remove();
        };
    }, [data, height, width, onSliceClick]);

    return <svg ref={svgRef} />;
}