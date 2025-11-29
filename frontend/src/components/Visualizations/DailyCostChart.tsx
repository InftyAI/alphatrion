import { useEffect, useMemo, useRef } from "react";
import * as d3 from "d3";

type Point = {
    date: string;
    total_cost: number;
    run_count?: number;
    experiment_count?: number
};

// Helper function to calculate moving average for trend line
function movingAverage(arr: number[], window = 7) {
    const out: number[] = [];
    for (let i = 0; i < arr.length; i++) {
        const start = Math.max(0, i - window + 1);
        const slice = arr.slice(start, i + 1);
        out.push(d3.mean(slice) ?? 0);
    }
    return out;
}

export default function DailyCostChart({
    data,
    onBarClick,
    width = 520,
    height = 360,
}: {
    data: Point[];
    onBarClick?: (isoDate: string) => void;
    width?: number;
    height?: number;
}) {
    const svgRef = useRef<SVGSVGElement | null>(null);

    // Parse date strings into Date objects once
    const parsed = useMemo(
        () =>
            data.map((d) => ({
                ...d,
                dateObj: new Date(d.date),
            })),
        [data]
    );

    useEffect(() => {
        if (!parsed.length) return;

        // Chart margins - gives space for axes labels
        const m = { top: 24, right: 16, bottom: 36, left: 56 };
        const w = width - m.left - m.right;
        const h = height - m.top - m.bottom;

        // X scale - band scale for bars with dates
        const x = d3
            .scaleBand<Date>()
            .domain(parsed.map((d) => d.dateObj))
            .range([0, w])
            .padding(0.2);

        // Y scale - linear scale for costs
        const y = d3
            .scaleLinear()
            .domain([0, d3.max(parsed, (d) => d.total_cost)! * 1.1])
            .nice()
            .range([h, 0]);

        // Calculate moving average for trend line
        const costSeries = parsed.map((d) => d.total_cost);
        const ma7 = movingAverage(costSeries, 7);

        // Clear and setup SVG
        const svg = d3.select(svgRef.current!).attr("width", width).attr("height", height);
        svg.selectAll("*").remove();

        // Create gradient for bars - gives them a nice depth effect
        const defs = svg.append("defs");
        const gradient = defs.append("linearGradient")
            .attr("id", "bar-gradient")
            .attr("x1", "0%")
            .attr("y1", "0%")
            .attr("x2", "0%")
            .attr("y2", "100%");

        gradient.append("stop")
            .attr("offset", "0%")
            .style("stop-color", "#60a5fa");  // Light blue at top

        gradient.append("stop")
            .attr("offset", "100%")
            .style("stop-color", "#3b82f6");  // Darker blue at bottom

        // Main chart group - offset by margins
        const g = svg.append("g").attr("transform", `translate(${m.left},${m.top})`);

        // X axis - format dates nicely and don't show too many
        g.append("g")
            .attr("transform", `translate(0,${h})`)
            .call(
                d3.axisBottom(x)
                    .tickFormat((d) => d3.timeFormat("%b %d")(d as Date))  // "Oct 12" format
                    .tickValues(
                        x.domain().filter((_, i) =>
                            i % Math.max(1, Math.floor(parsed.length / 7)) === 0
                        )  // Show max 7 tick marks
                    )
            );

        // Y axis - format as currency
        g.append("g")
            .call(
                d3.axisLeft(y)
                    .ticks(5)
                    .tickFormat((v) => `$${Number(v).toFixed(0)}` as any)
            );

        // Create tooltip div - styled nicely with shadow
        const tooltip = d3
            .select("body")  // Attach to body for better positioning
            .append("div")
            .attr("class", "chart-tooltip")
            .style("position", "absolute")
            .style("pointer-events", "none")
            .style("background", "white")
            .style("border", "1px solid #e5e7eb")
            .style("padding", "8px 10px")
            .style("border-radius", "6px")
            .style("font-size", "12px")
            .style("box-shadow", "0 6px 14px rgba(0,0,0,.08)")
            .style("opacity", 0)
            .style("z-index", 1000);  // Make sure it's on top

        // Draw bars with nice gradient fill
        g.selectAll("rect.bar")
            .data(parsed)
            .enter()
            .append("rect")
            .attr("class", "bar")
            .attr("x", (d) => x(d.dateObj)!)
            .attr("y", h)  // Start from bottom for animation
            .attr("width", x.bandwidth())
            .attr("height", 0)  // Start with 0 height
            .attr("fill", "url(#bar-gradient)")
            .style("cursor", "pointer")
            // Animate bars growing upward
            .transition()
            .duration(600)
            .delay((_, i) => i * 30)  // Stagger animation
            .attr("y", (d) => y(d.total_cost))
            .attr("height", (d) => h - y(d.total_cost));

        // Add hover interactions after animation
        g.selectAll("rect.bar")
            .on("mouseenter", function (event, d) {
                // Darken bar on hover
                d3.select(this)
                    .transition()
                    .duration(100)
                    .attr("fill", "#2563eb");

                // Format date nicely for tooltip
                const formattedDate = d3.timeFormat("%B %d, %Y")(d.dateObj);

                // Show tooltip with formatted content
                tooltip
                    .style("opacity", 1)
                    .html(
                        `<div style="font-weight:600;margin-bottom:4px;color:#1f2937">${formattedDate}</div>
                        <div style="color:#6b7280">Cost: <span style="font-weight:600;color:#1f2937">$${d.total_cost.toFixed(2)}</span></div>
                        ${d.run_count != null ? `<div style="color:#6b7280">Runs: <span style="font-weight:600;color:#1f2937">${d.run_count}</span></div>` : ""}
                        ${d.experiment_count != null ? `<div style="color:#6b7280">Experiments: <span style="font-weight:600;color:#1f2937">${d.experiment_count}</span></div>` : ""}`
                    );
            })
            .on("mousemove", function (event) {
                // Position tooltip near mouse cursor
                tooltip
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            })
            .on("mouseleave", function () {
                // Reset bar color
                d3.select(this)
                    .transition()
                    .duration(100)
                    .attr("fill", "url(#bar-gradient)");

                // Hide tooltip
                tooltip.style("opacity", 0);
            })
            .on("click", (_e, d) => {
                // Handle bar click if callback provided
                onBarClick?.(d.date);
            });

        // Draw moving average trend line
        const line = d3
            .line<[Date, number]>()
            .x((d) => x(d[0])! + x.bandwidth() / 2)
            .y((d) => y(d[1]))
            .curve(d3.curveMonotoneX);

        const pairs: [Date, number][] = parsed.map((d, i) => [d.dateObj, ma7[i]]);

        // Add the trend line with animation
        const path = g.append("path")
            .attr("fill", "none")
            .attr("stroke", "#6b7280")
            .attr("stroke-width", 2)
            .attr("d", line(pairs)!)
            .attr("opacity", 0.6);

        // Animate the line drawing
        const totalLength = path.node()!.getTotalLength();
        path
            .attr("stroke-dasharray", totalLength + " " + totalLength)
            .attr("stroke-dashoffset", totalLength)
            .transition()
            .duration(1500)
            .delay(600)  // Start after bars finish
            .attr("stroke-dashoffset", 0);

        // Add a label for the trend line
        g.append("text")
            .attr("x", w - 60)
            .attr("y", y(ma7[ma7.length - 1]) - 5)
            .style("font-size", "10px")
            .style("fill", "#6b7280")
            .text("7-day avg")
            .style("opacity", 0)
            .transition()
            .duration(300)
            .delay(2000)
            .style("opacity", 1);

        // Cleanup function - remove tooltip when component unmounts
        return () => {
            tooltip.remove();
        };
    }, [parsed, width, height, onBarClick]);

    return <svg ref={svgRef} />;
}