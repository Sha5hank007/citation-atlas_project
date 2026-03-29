// graph.js

let selectedIds = new Set();
let nodeR = 9;
let labelLen = 28;
let colorMode = "role";

const ROLE_COLOR = {
  landmark:  { fill:"#534AB7", stroke:"#3C3489" },
  seed:      { fill:"#0F6E56", stroke:"#085041" },
  bridge:    { fill:"#BA7517", stroke:"#854F0B" },
  important: { fill:"#185FA5", stroke:"#0C447C" },
  peripheral:{ fill:"#888780", stroke:"#5F5E5A" },
};

let yearColorScale;

// ── shift key tracking (kept but no longer required) ──────────────────────
window._shiftHeld = false;
window.addEventListener("keydown", e => { if (e.key === "Shift") window._shiftHeld = true; });
window.addEventListener("keyup",   e => { if (e.key === "Shift") window._shiftHeld = false; });

function getColor(d) {
  if (colorMode === "year") return yearColorScale(d.year);
  return ROLE_COLOR[d.role]?.fill || "#888";
}
function getStroke(d) {
  if (colorMode === "year") return d3.color(yearColorScale(d.year)).darker(0.8).toString();
  return ROLE_COLOR[d.role]?.stroke || "#555";
}

function renderGraph() {
  const container = document.getElementById("graph");
  const w = container.clientWidth || 960;
  const H = 520;

  d3.select("#graph").selectAll("*").remove();

  const svg = d3.select("#graph")
    .append("svg")
    .attr("width", w)
    .attr("height", H);

  d3.json("/graph").then(data => {

    const PAPERS = data.nodes;
    const EDGES  = data.links || [];

    if (!PAPERS || PAPERS.length === 0) {
      svg.append("text")
        .attr("x", w / 2).attr("y", H / 2)
        .attr("text-anchor", "middle")
        .style("font-size", "14px")
        .style("fill", "#888")
        .text("No papers in graph yet — run a search first");
      return;
    }

    PAPERS.forEach(d => { d.year = +d.year || 2020; });

    window.nodeDataById = Object.fromEntries(PAPERS.map(d => [d.id, d]));

    const years = [...new Set(PAPERS.map(d => d.year))].sort();
    yearColorScale = d3.scaleOrdinal()
      .domain(years)
      .range(["#534AB7","#185FA5","#0F6E56","#BA7517","#D4537E"]);

    const defs = svg.append("defs");
    defs.append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -4 8 8")
      .attr("refX", 8)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-4L8,0L0,4")
      .attr("fill", "#B4B2A9");

    const margin = { top:28, right:60, bottom:40, left:60 };
    const innerW  = w - margin.left - margin.right;
    const innerH  = H - margin.top  - margin.bottom;

    const g = svg.append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    const minYear = d3.min(PAPERS, d => d.year);
    const maxYear = d3.max(PAPERS, d => d.year);
    const xScale  = d3.scaleLinear()
      .domain([minYear, maxYear])
      .range([0, innerW]);

    const yearGroups = {};
    PAPERS.forEach(d => {
      if (!yearGroups[d.year]) yearGroups[d.year] = [];
      yearGroups[d.year].push(d);
    });
    PAPERS.forEach(d => {
      const grp = yearGroups[d.year];
      const idx = grp.indexOf(d);
      const n   = grp.length;
      d.x = xScale(d.year);
      d.y = ((idx + 1) / (n + 1)) * innerH;
    });

    const prExtent = d3.extent(PAPERS, d => d.pagerank || 0.01);
    const rScale   = d3.scaleLinear()
      .domain(prExtent)
      .range([nodeR * 0.6, nodeR * 1.8]);

    const nodeById = window.nodeDataById;

    const edgeData = EDGES.map(e => ({
      source: e.source?.id ?? e.source,
      target: e.target?.id ?? e.target,
    })).filter(e => nodeById[e.source] && nodeById[e.target]);

    g.append("g").selectAll("line")
      .data(edgeData)
      .enter()
      .append("line")
      .attr("x1", d => nodeById[d.source].x)
      .attr("y1", d => nodeById[d.source].y)
      .attr("x2", d => {
        const src = nodeById[d.source], tgt = nodeById[d.target];
        const dx = tgt.x - src.x, dy = tgt.y - src.y;
        const dist = Math.sqrt(dx*dx + dy*dy) || 1;
        return tgt.x - (dx / dist) * rScale(tgt.pagerank || 0.01);
      })
      .attr("y2", d => {
        const src = nodeById[d.source], tgt = nodeById[d.target];
        const dx = tgt.x - src.x, dy = tgt.y - src.y;
        const dist = Math.sqrt(dx*dx + dy*dy) || 1;
        return tgt.y - (dy / dist) * rScale(tgt.pagerank || 0.01);
      })
      .attr("stroke", "#B4B2A9")
      .attr("stroke-width", 1)
      .attr("stroke-opacity", 0.5)
      .attr("marker-end", "url(#arrow)");

    const node = g.append("g").selectAll("g.node")
      .data(PAPERS)
      .enter()
      .append("g")
      .attr("class", "node")
      .attr("transform", d => `translate(${d.x},${d.y})`)
      .style("cursor", "pointer");

    node.append("circle")
      .attr("r",            d => rScale(d.pagerank || 0.01))
      .attr("fill",         d => selectedIds.has(d.id) ? "#D85A30" : getColor(d))
      .attr("stroke",       d => selectedIds.has(d.id) ? "#993C1D" : getStroke(d))
      .attr("stroke-width", d => selectedIds.has(d.id) ? 2.5 : 1.5);

    node.append("text")
      .attr("x", d => {
        const r = rScale(d.pagerank || 0.01);
        return d.x + r + 5 + 140 > innerW ? -(r + 5) : r + 5;
      })
      .attr("y", 4)
      .attr("text-anchor", d => {
        const r = rScale(d.pagerank || 0.01);
        return d.x + r + 5 + 140 > innerW ? "end" : "start";
      })
      .text(d => {
        const t = d.title || "";
        return t.length > labelLen ? t.slice(0, labelLen) + "…" : t;
      })
      .style("font-size", "11px")
      .style("fill", "#888780")
      .attr("pointer-events", "none");

    let tooltip = document.getElementById("tooltip");
    if (!tooltip) {
      tooltip = document.createElement("div");
      tooltip.id = "tooltip";
      tooltip.style.cssText = "position:absolute;background:white;border:1px solid #ccc;" +
        "border-radius:6px;padding:8px 12px;font-size:12px;pointer-events:none;" +
        "opacity:0;max-width:220px;z-index:10;line-height:1.6;";
      container.style.position = "relative";
      container.appendChild(tooltip);
    }

    node
      .on("mouseenter", function(event, d) {
        d3.select(this).select("circle").attr("stroke-width", 3);
        const box = container.getBoundingClientRect();
        const ex  = event.clientX - box.left;
        const ey  = event.clientY - box.top;
        tooltip.innerHTML = `
          <strong style="display:block;margin-bottom:4px">${d.title}</strong>
          <span style="color:#666">Year: ${d.year}</span><br>
          <span style="color:#666">Role: ${d.role || "—"}</span><br>
          <span style="color:#666">PageRank: ${(d.pagerank || 0).toFixed(3)}</span>
        `;
        const left = ex + 14 + 220 > container.clientWidth ? ex - 230 : ex + 14;
        tooltip.style.left    = left + "px";
        tooltip.style.top     = (ey - 10) + "px";
        tooltip.style.opacity = 1;
      })
      .on("mouseleave", function(event, d) {
        d3.select(this).select("circle")
          .attr("stroke-width", selectedIds.has(d.id) ? 2.5 : 1.5);
        tooltip.style.opacity = 0;
      })
      .on("click", function(event, d) {

        const circle = d3.select(this).select("circle");

        if (selectedIds.has(d.id)) {
          selectedIds.delete(d.id);
          circle
            .attr("fill",         getColor(d))
            .attr("stroke",       getStroke(d))
            .attr("stroke-width", 1.5);
        } else {
          selectedIds.add(d.id);
          circle
            .attr("fill",         "#D85A30")
            .attr("stroke",       "#993C1D")
            .attr("stroke-width", 2.5);
        }

        window.selectedNodes = selectedIds;
        window.currentPaper  = d.id;
        updateSelectionStatus();
      });

    g.append("g")
      .attr("transform", `translate(0,${innerH + 12})`)
      .call(
        d3.axisBottom(xScale)
          .tickFormat(d3.format("d"))
          .ticks(maxYear - minYear)
      )
      .selectAll("text")
      .style("font-size", "11px");

    updateSelectionStatus();
  });
}

function updateSelectionStatus() {
  const el = document.getElementById("selected-nodes");
  if (!el) return;
  if (selectedIds.size === 0) {
    el.innerHTML = "No nodes selected";
    return;
  }
  el.innerHTML = `
    <b>Selected (${selectedIds.size})</b><br>
    ${[...selectedIds].map(id => {
      const n = window.nodeDataById?.[id];
      return `<div style="font-size:11px">${n ? n.title : id}</div>`;
    }).join("")}
  `;
}

function highlightNodes(paperIds) {
  d3.selectAll(".node circle")
    .attr("stroke",       d => paperIds.includes(d.id) ? "#FFD700" : getStroke(d))
    .attr("stroke-width", d => paperIds.includes(d.id) ? 4 : 1.5);
}

function selectAllNodes() {
  selectedIds.clear();
  d3.selectAll(".node").each(function(d) {
    selectedIds.add(d.id);
    d3.select(this).select("circle")
      .attr("fill",         "#D85A30")
      .attr("stroke",       "#993C1D")
      .attr("stroke-width", 2.5);
  });
  window.selectedNodes = selectedIds;
  updateSelectionStatus();
}

function clearNodeSelection() {
  selectedIds.clear();
  d3.selectAll(".node circle")
    .attr("fill",         d => getColor(d))
    .attr("stroke",       d => getStroke(d))
    .attr("stroke-width", 1.5);
  window.selectedNodes = selectedIds;
  updateSelectionStatus();
}

window.addEventListener("resize", renderGraph);