let selectedIds    = new Set();
let highlightedIds = new Set();
let nodesSelection, linksSelection, labelsSelection;
let graphLinks = [];

let nodeSizeMode = "citations";

function setNodeSizeMode(mode) {
  nodeSizeMode = mode;
  const btnC = document.getElementById("mode-citations");
  const btnR = document.getElementById("mode-relevance");
  if (btnC) btnC.className = mode === "citations" ? "mode-btn active" : "mode-btn";
  if (btnR) btnR.className = mode === "relevance"  ? "mode-btn active" : "mode-btn";
  renderGraph();
}

function getBaseColor(d) {
  const map = {
    landmark:   "#1e3a8a",
    important:  "#2563eb",
    moderate:   "#60a5fa",
    bridge:     "#60a5fa",
    recent:     "#f97316",
    peripheral: "#9ca3af",
    seed:       "#2563eb",
    reference:  "#9ca3af",
  };
  return map[d.role] || "#3b82f6";
}

function renderGraph() {
  const container = document.getElementById("graph");
  const W = container.clientWidth  || 900;
  const H = container.clientHeight || 700;

  d3.select("#graph").selectAll("*").remove();

  const svg = d3.select("#graph")
    .append("svg")
    .attr("width",  W)
    .attr("height", H);

  const defs = svg.append("defs");
  defs.append("marker")
    .attr("id", "arrow-out").attr("viewBox", "0 -4 8 8")
    .attr("refX", 8).attr("markerWidth", 6).attr("markerHeight", 6)
    .attr("orient", "auto")
    .append("path").attr("d", "M0,-4L8,0L0,4").attr("fill", "#555");

  const g = svg.append("g");

  svg.call(
    d3.zoom().scaleExtent([0.3, 4])
      .on("zoom", e => g.attr("transform", e.transform))
  );

  // ── tooltip — create fresh each render inside container ───────────
  const oldTip = document.getElementById("tooltip");
  if (oldTip) oldTip.remove();

  const tooltip = document.createElement("div");
  tooltip.id = "tooltip";
  tooltip.style.cssText = [
    "position:absolute",
    "background:#ffffff",
    "border:1px solid #e2e8f0",
    "color:#1a1714",
    "padding:10px 13px",
    "font-size:12px",
    "pointer-events:none",
    "opacity:0",
    "max-width:260px",
    "line-height:1.6",
    "border-radius:8px",
    "font-family:'IBM Plex Sans',sans-serif",
    "box-shadow:0 4px 20px rgba(0,0,0,0.10)",
    "z-index:999",
    "transition:opacity 0.12s"
  ].join(";");
  container.style.position = "relative";
  container.appendChild(tooltip);

  d3.json("/graph").then(data => {

    const nodes = data.nodes || [];
    const links = data.links || [];
    graphLinks  = links;

    if (nodes.length === 0) {
      svg.append("text")
        .attr("x", W / 2).attr("y", H / 2)
        .attr("text-anchor", "middle")
        .style("font-size", "14px").style("fill", "#9ca3af")
        .text("No papers yet — run a search first");
      return;
    }

    window.nodeDataById = Object.fromEntries(nodes.map(n => [n.id, n]));

    const maxCitations = d3.max(nodes, d => d.citations || 0) || 1;
    const maxRelevance = d3.max(nodes, d => d.relevance_score || 0) || 1;

    const citationScale = d3.scalePow()
      .exponent(0.35).domain([1, maxCitations]).range([6, 30]);
    const relevanceScale = d3.scalePow()
      .exponent(0.8).domain([0, maxRelevance]).range([5, 30]);

    function getRadius(d) {
      if (nodeSizeMode === "relevance") return relevanceScale(d.relevance_score || 0);
      return citationScale(Math.max(1, d.citations || 1));
    }

    const minYear = d3.min(nodes, d => d.year || 2000);
    const maxYear = d3.max(nodes, d => d.year || 2024);
    const yScale  = d3.scaleLinear()
      .domain([minYear, maxYear]).range([H - 60, 60]);

    const simulation = d3.forceSimulation(nodes)
      .force("link",      d3.forceLink(links).id(d => d.id).distance(120))
      .force("charge",    d3.forceManyBody().strength(-180))
      .force("collision", d3.forceCollide().radius(d => getRadius(d) + 10))
      .force("y",         d3.forceY(d => yScale(d.year || 2020)).strength(0.8))
      .force("x",         d3.forceX(W / 2).strength(0.05));

    // ── edges ─────────────────────────────────────────────────────────
    linksSelection = g.append("g")
      .selectAll("path").data(links).enter()
      .append("path")
      .attr("class", "edge-path")
      .attr("fill", "none")
      .attr("stroke", "#cbd5e1")
      .attr("stroke-width", 1)
      .attr("stroke-opacity", 0.3);

    // ── nodes ─────────────────────────────────────────────────────────
    nodesSelection = g.append("g")
      .selectAll("g").data(nodes).enter()
      .append("g")
      .style("cursor", "pointer")
      .call(d3.drag()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on("drag",  (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on("end",   (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
      );

    nodesSelection.append("circle")
      .attr("r",            d => getRadius(d))
      .attr("fill",         d => getBaseColor(d))
      .attr("stroke",       "#fff")
      .attr("stroke-width", 1.5);

    // ── labels — top 20% by citations ─────────────────────────────────
    const citationThreshold = d3.quantile(
      nodes.map(d => d.citations || 0).sort(d3.ascending), 0.8
    );

    labelsSelection = nodesSelection.append("text")
      .attr("y", 4)
      .style("font-size",     "10.5px")
      .style("fill",          "#1e293b")
      .style("font-family",   "'IBM Plex Sans', sans-serif")
      .style("font-weight",   d => (d.citations || 0) >= citationThreshold ? "600" : "400")
      .attr("pointer-events", "none")
      .text(d => {
        if ((d.citations || 0) < citationThreshold) return "";
        const t = d.title || "";
        return t.length > 28 ? t.slice(0, 28) + "…" : t;
      });

    // ── tooltip on hover ──────────────────────────────────────────────
    nodesSelection.on("mouseenter", function(event, d) {
      const box = container.getBoundingClientRect();
      const ex  = event.clientX - box.left;
      const ey  = event.clientY - box.top;

      tooltip.innerHTML = `
        <div style="font-weight:600;font-size:13px;color:#0f172a;margin-bottom:6px;line-height:1.4">${d.title}</div>
        <div style="color:#475569;font-size:11.5px">
          <span style="display:inline-block;margin-right:12px">📅 ${d.year || "—"}</span>
          <span style="display:inline-block;margin-right:12px">📄 ${(d.citations || 0).toLocaleString()} citations</span>
        </div>
        <div style="margin-top:5px;font-size:11px;color:#64748b">
          Role: <span style="font-weight:500;color:#334155">${d.role || "—"}</span>
          &nbsp;·&nbsp;
        </div>
      `;

      const left = ex + 14 + 260 > W ? ex - 270 : ex + 14;
      tooltip.style.left    = left + "px";
      tooltip.style.top     = (ey - 10) + "px";
      tooltip.style.opacity = "1";

      // dim unrelated nodes
      const connected = new Set([d.id]);
      graphLinks.forEach(l => {
        const s = l.source?.id ?? l.source;
        const t = l.target?.id ?? l.target;
        if (s === d.id) connected.add(t);
        if (t === d.id) connected.add(s);
      });

      nodesSelection.select("circle")
        .attr("opacity", n => connected.has(n.id) ? 1 : 0.1);

      // animate connected edges
      linksSelection
        .attr("stroke-opacity", l => {
          const s = l.source?.id ?? l.source;
          const t = l.target?.id ?? l.target;
          return (s === d.id || t === d.id) ? 0.9 : 0.04;
        })
        .attr("stroke", l => {
          const s = l.source?.id ?? l.source;
          const t = l.target?.id ?? l.target;
          return (s === d.id || t === d.id) ? "#334155" : "#cbd5e1";
        })
        .attr("stroke-width", l => {
          const s = l.source?.id ?? l.source;
          const t = l.target?.id ?? l.target;
          return (s === d.id || t === d.id) ? 2 : 1;
        })
        .attr("marker-end", l => {
          const s = l.source?.id ?? l.source;
          const t = l.target?.id ?? l.target;
          return (s === d.id || t === d.id) ? "url(#arrow-out)" : null;
        })
        .each(function(l) {
          const s = l.source?.id ?? l.source;
          const t = l.target?.id ?? l.target;
          if (s !== d.id && t !== d.id) return;
          const pathEl  = d3.select(this);
          const pathLen = this.getTotalLength();
          if (!pathLen) return;
          pathEl
            .attr("stroke-dasharray",  "4 12")
            .attr("stroke-dashoffset", pathLen)
            .transition().duration(2500).ease(d3.easeLinear)
            .attr("stroke-dashoffset", 0)
            .on("end", function repeat() {
              d3.select(this)
                .attr("stroke-dashoffset", pathLen)
                .transition().duration(2500).ease(d3.easeLinear)
                .attr("stroke-dashoffset", 0)
                .on("end", repeat);
            });
        });
    });

    nodesSelection.on("mouseleave", () => {
      tooltip.style.opacity = "0";
      nodesSelection.select("circle").attr("opacity", 1);
      linksSelection.interrupt()
        .attr("stroke",           "#cbd5e1")
        .attr("stroke-opacity",   0.3)
        .attr("stroke-width",     1)
        .attr("stroke-dasharray", null)
        .attr("marker-end",       null);
      applySelection();
    });

    // ── click — plain click toggles selection, no shift needed ────────
    nodesSelection.on("click", function(event, d) {
      event.stopPropagation();

      if (selectedIds.has(d.id)) {
        selectedIds.delete(d.id);
      } else {
        selectedIds.add(d.id);
      }

      window.selectedNodes = selectedIds;
      applySelection();

      // update details panel
      const panel = document.getElementById("details-panel");
      if (panel) {
        if (selectedIds.has(d.id)) {
          panel.innerHTML = `
            <div style="font-weight:600;font-size:13px;color:#0f172a;line-height:1.4;margin-bottom:6px">
              ${d.title || "Untitled"}
            </div>

            <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#475569;margin-bottom:8px">
              ${d.year || "—"} · ${(d.citations || 0).toLocaleString()} citations · ${d.role || "—"}
            </div>

            <div style="font-size:12px;color:#334155;line-height:1.6">
              ${d.abstract
                ? `<details>
                    <summary style="cursor:pointer;color:#2563eb;font-size:11px">View abstract</summary>
                    <div style="margin-top:6px;max-height:160px;overflow-y:auto">
                      ${d.abstract}
                    </div>
                  </details>`
                : "No abstract available"}
            </div>
          `;
        } else {
          panel.innerHTML = `<span style="font-size:12px;color:#475569;font-family:'IBM Plex Mono',monospace">Click a node to see details</span>`;
        }
      }
    });

    // ── tick ──────────────────────────────────────────────────────────
    simulation.on("tick", () => {
      linksSelection.attr("d", l => {
        const sx = l.source.x, sy = l.source.y;
        const tx = l.target.x, ty = l.target.y;
        const mx = (sx + tx) / 2;
        const my = (sy + ty) / 2 - 30;
        return `M${sx},${sy} Q${mx},${my} ${tx},${ty}`;
      });

      nodesSelection.attr("transform", d => `translate(${d.x},${d.y})`);

      labelsSelection
        .attr("x",           d => d.x < W / 2 ? -(getRadius(d) + 5) : getRadius(d) + 5)
        .attr("text-anchor", d => d.x < W / 2 ? "end" : "start");
    });

    applySelection();
  });
}

function applySelection() {
  if (!nodesSelection || !linksSelection) return;

  const connected = new Set(selectedIds);
  if (selectedIds.size > 0) {
    graphLinks.forEach(l => {
      const s = l.source?.id ?? l.source;
      const t = l.target?.id ?? l.target;
      if (selectedIds.has(s)) connected.add(t);
      if (selectedIds.has(t)) connected.add(s);
    });
  }

  nodesSelection.select("circle")
    .attr("fill",         d => selectedIds.has(d.id) ? "#fff"     : getBaseColor(d))
    .attr("stroke",       d => selectedIds.has(d.id) ? "#06b6d4"  : "#fff")
    .attr("stroke-width", d => selectedIds.has(d.id) ? 3.5        : 1.5)
    .attr("opacity",      d => {
      if (selectedIds.size === 0) return 1;
      if (selectedIds.has(d.id)) return 1;
      if (connected.has(d.id))   return 0.4;
      return 0.12;
    });

  linksSelection.attr("stroke-opacity", l => {
    if (selectedIds.size === 0) return 0.3;
    const s = l.source?.id ?? l.source;
    const t = l.target?.id ?? l.target;
    return (selectedIds.has(s) || selectedIds.has(t)) ? 0.7 : 0.03;
  });

  updateSelectionStatus();
}

function selectAllNodes() {
  selectedIds = new Set(Object.keys(window.nodeDataById || {}));
  window.selectedNodes = selectedIds;
  applySelection();
}

function clearNodeSelection() {
  selectedIds.clear();
  highlightedIds.clear();
  if (nodesSelection) nodesSelection.selectAll(".gold-ring").remove();
  const panel = document.getElementById("details-panel");
  if (panel) panel.innerHTML = `<span style="font-size:12px;color:#475569;font-family:'IBM Plex Mono',monospace">Click a node to see details</span>`;
  window.selectedNodes = selectedIds;
  applySelection();
}

function updateSelectionStatus() {
  const strip = document.getElementById("selected-strip");
  if (!strip) {
    // fallback for old HTML
    const el = document.getElementById("selected-nodes");
    if (!el) return;
    if (selectedIds.size === 0) {
      el.innerHTML = `<span style="font-size:11px;color:#94a3b8;font-family:'IBM Plex Mono',monospace">
        Pick any node to query it — tap again to deselect
      </span>`;
      return;
    }
    el.innerHTML = `
      <span style="font-size:11px;font-weight:600;color:#0891b2;font-family:'IBM Plex Mono',monospace">
        ${selectedIds.size} paper${selectedIds.size > 1 ? "s" : ""} queued
      </span><br>
      ${[...selectedIds].slice(0, 8).map(id => {
        const n = window.nodeDataById?.[id];
        return `<div style="font-size:10px;color:#475569;margin-top:2px">· ${n ? n.title.slice(0, 35) : id}</div>`;
      }).join("")}
      ${selectedIds.size > 8 ? `<div style="font-size:10px;color:#94a3b8">+${selectedIds.size - 8} more</div>` : ""}
    `;
    return;
  }

  // new HTML with selected-strip
  strip.innerHTML = "";

  if (selectedIds.size === 0) {
    strip.innerHTML = `<span id="sel-hint" style="font-size:11px;color:#94a3b8;font-family:'IBM Plex Mono',monospace">
      Pick any node to query it — tap again to deselect
    </span>`;
    return;
  }

  const count = document.createElement("span");
  count.style.cssText = "font-family:'IBM Plex Mono',monospace;font-size:10px;color:#0891b2;margin-right:6px;white-space:nowrap";
  count.textContent = `${selectedIds.size} queued`;
  strip.appendChild(count);

  [...selectedIds].slice(0, 8).forEach(id => {
    const n   = window.nodeDataById?.[id];
    const chip = document.createElement("span");
    chip.className   = "sel-chip";
    chip.textContent = n ? n.title.slice(0, 28) + (n.title.length > 28 ? "…" : "") : id.slice(0, 20);
    strip.appendChild(chip);
  });

  if (selectedIds.size > 8) {
    const more = document.createElement("span");
    more.style.cssText = "font-size:10px;color:#94a3b8;font-family:'IBM Plex Mono',monospace;white-space:nowrap";
    more.textContent = `+${selectedIds.size - 8} more`;
    strip.appendChild(more);
  }
}

function highlightNodes(ids) {
  if (!ids?.length || !nodesSelection) return;
  highlightedIds = new Set(ids);
  nodesSelection.selectAll(".gold-ring").remove();
  nodesSelection.each(function(d) {
    if (!highlightedIds.has(d.id)) return;
    const node = d3.select(this);
    const base = +node.select("circle").attr("r");
    node.append("circle")
      .attr("class",        "gold-ring")
      .attr("r",            base + 6)
      .attr("fill",         "none")
      .attr("stroke",       "#f59e0b")
      .attr("stroke-width", 2.5)
      .attr("pointer-events", "none");
  });
}

window.addEventListener("resize", renderGraph);