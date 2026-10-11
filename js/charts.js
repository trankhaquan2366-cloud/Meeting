// charts.js - SVG/Canvas Chart Logic

function renderRevenueChart(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Create a simple SVG line chart
    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("width", "100%");
    svg.setAttribute("height", "100%");
    svg.setAttribute("viewBox", "0 0 500 200");
    svg.setAttribute("preserveAspectRatio", "none");

    // Background grid
    for(let i=1; i<5; i++) {
        let line = document.createElementNS(svgNS, "line");
        line.setAttribute("x1", "0");
        line.setAttribute("y1", i * 40);
        line.setAttribute("x2", "500");
        line.setAttribute("y2", i * 40);
        line.setAttribute("stroke", "rgba(255,255,255,0.1)");
        line.setAttribute("stroke-width", "1");
        svg.appendChild(line);
    }

    // Actual Data Line
    const actualPoints = "0,180 50,150 100,160 150,130 200,90 250,100 300,70";
    const actualLine = document.createElementNS(svgNS, "polyline");
    actualLine.setAttribute("points", actualPoints);
    actualLine.setAttribute("fill", "none");
    actualLine.setAttribute("stroke", "var(--color-primary)");
    actualLine.setAttribute("stroke-width", "3");
    svg.appendChild(actualLine);

    // AI Forecast Line (Dashed)
    const forecastPoints = "300,70 350,50 400,60 450,30 500,20";
    const forecastLine = document.createElementNS(svgNS, "polyline");
    forecastLine.setAttribute("points", forecastPoints);
    forecastLine.setAttribute("fill", "none");
    forecastLine.setAttribute("stroke", "var(--color-secondary)");
    forecastLine.setAttribute("stroke-width", "3");
    forecastLine.setAttribute("stroke-dasharray", "5,5");
    svg.appendChild(forecastLine);

    container.appendChild(svg);
}

window.renderRevenueChart = renderRevenueChart;
