import { useEffect, useRef } from "react";
import * as d3 from "d3";
import type { AccuracyPoint } from "../../types";

type Props = {
    data: AccuracyPoint[];
    onPointClick?: (trialId: number) => void;
    onPointHover?: (trialId: number | null) => void;
    height?: number;
};

export default function AccuracyCurve({ data, onPointClick, onPointHover, height = 320 }: Props) {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const svgRef = useRef<SVGSVGElement | null>(null);
    const tooltipRef = useRef<HTMLDivElement | null>(null);

    // Resize observer
    useEffect(() => {
        if (!containerRef.current) return;
        const ro = new ResizeObserver((entries) => {
            for (const entry of entries) {
                render(Math.floor(entry.contentRect.width), height);
            }
        });
        ro.observe(containerRef.current);
        return () => ro.disconnect();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Render on data change
    useEffect(() => {
        if (!containerRef.current) return;
        render(Math.floor(containerRef.current.clientWidth || 600), height);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [data, height]);

    function render(width: number, height: number) {
        const margin = { top: 8, right: 16, bottom: 28, left: 48 };
        const iw = Math.max(0, width - margin.left - margin.right);
        const ih = Math.max(0, height - margin.top - margin.bottom);

        const svg = d3.select(svgRef.current!).attr("width", width).attr("height", height);
        svg.selectAll("*").remove();

        const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

        const tooltip = d3.select(tooltipRef.current!);

        // Ensure ascending by time
        const points = [...data].sort(
            (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        );

        const x = d3
            .scaleTime()
            .domain(d3.extent(points, (d) => new Date(d.timestamp)) as [Date, Date])
            .range([0, iw]);

        const y = d3.scaleLinear().domain([0, 1]).nice().range([ih, 0]);

        const xAxis = d3.axisBottom(x).ticks(6).tickFormat((d) => d3.timeFormat("%m-%d %H:%M")(d as Date));
        const yAxis = d3.axisLeft(y).ticks(5).tickFormat((d) => `${(Number(d) * 100).toFixed(0)}%`);

        g.append("g").attr("transform", `translate(0,${ih})`).call(xAxis as any);
        g.append("g").call(yAxis as any);

        const line = d3
            .line<AccuracyPoint>()
            .x((d) => x(new Date(d.timestamp)))
            .y((d) => y(d.accuracy))
            .curve(d3.curveMonotoneX);

        g.append("path")
            .datum(points)
            .attr("fill", "none")
            .attr("stroke", "#4f46e5")
            .attr("stroke-width", 2)
            .attr("d", line as any);

        // Points
        const circles = g
            .selectAll("circle.pt")
            .data(points, (d: any) => d.trial_id)
            .join("circle")
            .attr("class", "pt")
            .attr("cx", (d) => x(new Date(d.timestamp)))
            .attr("cy", (d) => y(d.accuracy))
            .attr("r", 4)
            .attr("fill", "#4f46e5")
            .attr("stroke", "#111827")
            .style("cursor", "pointer")
            .on("pointerenter", function (_event, d) {
                d3.select(this).transition().duration(100).attr("r", 6);
                onPointHover?.(d.trial_id);
            })
            .on("pointermove", function (event, d) {
                const html = `
          <div class="font-medium">Trial #${d.trial_id}</div>
          <div>Accuracy: ${(d.accuracy * 100).toFixed(1)}%</div>
          <div>${new Date(d.timestamp).toLocaleString()}</div>
        `;
                tooltip
                    .html(html)
                    .style("opacity", 1)
                    .style("left", `${event.offsetX + 16}px`)
                    .style("top", `${event.offsetY + 16}px`);
            })
            .on("pointerleave", function () {
                d3.select(this).transition().duration(100).attr("r", 4);
                tooltip.style("opacity", 0);
                onPointHover?.(null);
            })
            .on("click", (_event, d) => onPointClick?.(d.trial_id));
    }

    return (
        <div ref={containerRef} className="relative w-full" style={{ height }}>
            <svg ref={svgRef} />
            <div
                ref={tooltipRef}
                className="pointer-events-none absolute z-10 rounded bg-white/90 px-3 py-2 text-sm shadow border border-gray-200"
                style={{ opacity: 0 }}
            />
        </div>
    );
}
