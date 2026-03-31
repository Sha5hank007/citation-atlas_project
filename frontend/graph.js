let selectedIds    = new Set();
let highlightedIds = new Set();
let nodesSelection, linksSelection, labelsSelection;
let graphLinks = [];

window.addEventListener("keydown", e => { if (e.key === "Shift") ;  });
window.addEventListener("keyup",   e => { if (e.key === "Shift") ; });

function getBaseColor(d) {
  const map = {
    landmark:   "#1e3a8a",
    important:  "#2563eb",
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

  // ── arrow markers — one for each end ──────────────────────────────
  const defs = svg.append("defs");

  defs.append("marker")
    .attr("id",           "arrow-out")
    .attr("viewBox",      "0 -4 8 8")
    .attr("refX",         8)
    .attr("markerWidth",  6)
    .attr("markerHeight", 6)
    .attr("orient",       "auto")
    .append("path")
    .attr("d",    "M0,-4L8,0L0,4")
    .attr("fill", "#111");

  defs.append("marker")
    .attr("id",           "arrow-in")
    .attr("viewBox",      "0 -4 8 8")
    .attr("refX",         8)
    .attr("markerWidth",  6)
    .attr("markerHeight", 6)
    .attr("orient",       "auto")
    .append("path")
    .attr("d",    "M0,-4L8,0L0,4")
    .attr("fill", "#111");

  const g = svg.append("g");

  svg.call(
    d3.zoom()
      .scaleExtent([0.3, 4])
      .on("zoom", e => g.attr("transform", e.transform))
  );

  let tooltip = document.getElementById("tooltip");
  if (!tooltip) {
    tooltip = document.createElement("div");
    tooltip.id = "tooltip";
    tooltip.style.cssText = [
      "position:absolute","background:white","border:1px solid #ccc",
      "padding:8px 12px","font-size:12px","pointer-events:none","opacity:0",
      "max-width:240px","line-height:1.6","border-radius:6px",
      "box-shadow:0 2px 8px rgba(0,0,0,0.1)"
    ].join(";");
    container.style.position = "relative";
    container.appendChild(tooltip);
  }

  d3.json("/graph").then(data => {

    const nodes = data.nodes || [];
    const links = data.links || [];
    graphLinks  = links;

    if (nodes.length === 0) {
      svg.append("text")
        .attr("x", W / 2).attr("y", H / 2)
        .attr("text-anchor", "middle")
        .style("font-size", "14px")
        .style("fill", "#888")
        .text("No papers yet — run a search first");
      return;
    }

    window.nodeDataById = Object.fromEntries(nodes.map(n => [n.id, n]));

    const maxCitations = d3.max(nodes, d => d.citations || 0) || 1;

    const rScale = d3.scalePow()
      .exponent(0.3)
      .domain([1, maxCitations])
      .range([5, 28]);

    function getRadius(d) {
      return rScale(Math.max(1, d.citations || 1));
    }

    const minYear = d3.min(nodes, d => d.year || 2000);
    const maxYear = d3.max(nodes, d => d.year || 2024);

    const yScale = d3.scaleLinear()
      .domain([minYear, maxYear])
      .range([H - 60, 60]);

    const simulation = d3.forceSimulation(nodes)
      .force("link",      d3.forceLink(links).id(d => d.id).distance(120))
      .force("charge",    d3.forceManyBody().strength(-180))
      .force("collision", d3.forceCollide().radius(d => getRadius(d) + 10))
      .force("y",         d3.forceY(d => yScale(d.year || 2020)).strength(0.8))
      .force("x",         d3.forceX(W / 2).strength(0.05));

    // ── edges — use path not line so we can animate + add arrows ──────
    linksSelection = g.append("g")
      .selectAll("path")
      .data(links)
      .enter()
      .append("path")
      .attr("class",        "edge-path")
      .attr("fill",         "none")
      .attr("stroke",       "#bbb")
      .attr("stroke-width", 1)
      .attr("stroke-opacity", 0.25);

    // ── nodes ─────────────────────────────────────────────────────────
    nodesSelection = g.append("g")
      .selectAll("g")
      .data(nodes)
      .enter()
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

    const citationThreshold = d3.quantile(
      nodes.map(d => d.citations || 0).sort(d3.ascending),
      0.8
    );

    labelsSelection = nodesSelection.append("text")
      .attr("y", 4)
      .style("font-size",     "10px")
      .style("fill",          "#222")
      .style("font-weight",   d => (d.citations || 0) >= citationThreshold ? "600" : "400")
      .attr("pointer-events", "none")
      .text(d => {
        if ((d.citations || 0) < citationThreshold) return "";
        const t = d.title || "";
        return t.length > 28 ? t.slice(0, 28) + "…" : t;
      });

    // ── tooltip ───────────────────────────────────────────────────────
    nodesSelection.on("mouseenter", function(event, d) {
      const box = container.getBoundingClientRect();
      const ex  = event.clientX - box.left;
      const ey  = event.clientY - box.top;
      tooltip.innerHTML = `
        <strong style="display:block;margin-bottom:4px">${d.title}</strong>
        <span style="color:#666">Year: ${d.year || "—"}</span><br>
        <span style="color:#666">Citations: ${(d.citations || 0).toLocaleString()}</span><br>
        <span style="color:#666">Role: ${d.role || "—"}</span><br>
        <span style="color:#666">PageRank: ${(d.pagerank || 0).toFixed(4)}</span>
      `;
      tooltip.style.left    = (ex + 14 + 240 > W ? ex - 250 : ex + 14) + "px";
      tooltip.style.top     = (ey - 10) + "px";
      tooltip.style.opacity = "1";

      // ── on hover: show arrows + animate dots on connected edges ──────
      const hoveredId = d.id;

      // 🔥 dim unrelated nodes
      const connected = new Set([hoveredId]);

      graphLinks.forEach(l => {
        const s = l.source?.id ?? l.source;
        const t = l.target?.id ?? l.target;

        if (s === hoveredId) connected.add(t);
        if (t === hoveredId) connected.add(s);
      });

nodesSelection.select("circle")
  .attr("opacity", n => connected.has(n.id) ? 1 : 0.1);

      linksSelection
        .attr("stroke-opacity", l => {
          const s = l.source?.id ?? l.source;
          const t = l.target?.id ?? l.target;
          return (s === hoveredId || t === hoveredId) ? 0.9 : 0.05;
        })
        .attr("stroke", l => {
          const s = l.source?.id ?? l.source;
          const t = l.target?.id ?? l.target;
          return (s === hoveredId || t === hoveredId) ? "#111" : "#bbb";
        })
        .attr("stroke-width", l => {
          const s = l.source?.id ?? l.source;
          const t = l.target?.id ?? l.target;
          return (s === hoveredId || t === hoveredId) ? 2 : 1;
        })
        .attr("marker-end", l => {
          const s = l.source?.id ?? l.source;
          const t = l.target?.id ?? l.target;
          return (s === hoveredId || t === hoveredId) ? "url(#arrow-out)" : null;
        })
        // animated dash flow — black dots moving along edge
        .each(function(l) {
          const s = l.source?.id ?? l.source;
          const t = l.target?.id ?? l.target;
          if (s !== hoveredId && t !== hoveredId) return;

          const pathEl   = d3.select(this);
          const pathLen  = this.getTotalLength();
          if (!pathLen) return;

          const dashLen  = 4;   // dot size
          const gapLen   = 12;  // gap between dots

          pathEl
            .attr("stroke-dasharray",  `${dashLen} ${gapLen}`)
            .attr("stroke-dashoffset", pathLen)
            .transition()
            .duration(2500)
            .ease(d3.easeLinear)
            .attr("stroke-dashoffset", 0)
            .on("end", function repeat() {
              d3.select(this)
                .attr("stroke-dashoffset", pathLen)
                .transition()
                .duration(2500)
                .ease(d3.easeLinear)
                .attr("stroke-dashoffset", 0)
                .on("end", repeat);
            });
        });
    });
    
    // restore node visibility  
    nodesSelection.on("mouseleave", () => {
    tooltip.style.opacity = "0";

    // 🔥 restore node opacity FIRST
    nodesSelection.select("circle")
      .attr("opacity", 1);

    // reset edges
    linksSelection
      .interrupt()
      .attr("stroke", "#bbb")
      .attr("stroke-opacity", 0.25)
      .attr("stroke-width", 1)
      .attr("stroke-dasharray", null)
      .attr("marker-end", null);

    // 🔥 CRITICAL: reapply selection state AFTER reset
    applySelection();
  });

    // ── click ─────────────────────────────────────────────────────────
    nodesSelection.on("click", function(event, d) {

    // 🔥 simple toggle (no shift needed)
    if (selectedIds.has(d.id)) {
      selectedIds.delete(d.id);
    } else {
      selectedIds.add(d.id);
    }

    window.selectedNodes = selectedIds;
    applySelection();
  });

    // ── tick ──────────────────────────────────────────────────────────
    simulation.on("tick", () => {
      // curved paths using quadratic bezier
      linksSelection.attr("d", l => {
        const sx = l.source.x, sy = l.source.y;
        const tx = l.target.x, ty = l.target.y;
        const mx = (sx + tx) / 2;
        const my = (sy + ty) / 2 - 30; // curve upward
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
    .attr("fill",         d => selectedIds.has(d.id) ? "#ffffff" : getBaseColor(d))
    .attr("stroke",       d => selectedIds.has(d.id) ? "#06b6d4" : "#fff")
    .attr("stroke-width", d => selectedIds.has(d.id) ? 4 : 1.5)
    .attr("opacity",      d => {
      if (selectedIds.size === 0) return 1;
      if (selectedIds.has(d.id)) return 1;      // selected = full
      if (connected.has(d.id))   return 0.6;   // connected = subtle
      return 0.12;                               // unrelated = faded
    });

  linksSelection.attr("stroke-opacity", l => {
    if (selectedIds.size === 0) return 0.25;
    const s = l.source?.id ?? l.source;
    const t = l.target?.id ?? l.target;
    return (selectedIds.has(s) || selectedIds.has(t)) ? 0.8 : 0.03;
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
  highlightedIds.clear(); // 🔥 FIX: remove gold-ring state

  // remove rings from DOM immediately
  if (nodesSelection) {
    nodesSelection.selectAll(".gold-ring").remove();
  }

  window.selectedNodes = selectedIds;
  applySelection();
}

function updateSelectionStatus() {
  const el = document.getElementById("selected-nodes");
  if (!el) return;

  if (selectedIds.size === 0) {
    el.innerHTML = `
      <span style="font-size:12px;color:#888">
        Click a node · shift+click to add more ·
        only <span style="color:#06b6d4;font-weight:600">cyan-outlined</span>
        nodes will be queried
      </span>`;
    return;
  }

  el.innerHTML = `
    <span style="font-size:12px;font-weight:600;color:#06b6d4">
      ${selectedIds.size} paper${selectedIds.size > 1 ? "s" : ""} selected — only these will be queried
    </span><br>
    ${[...selectedIds].map(id => {
      const n = window.nodeDataById?.[id];
      return `<div style="font-size:11px;color:#444;margin-top:3px">
        <span style="display:inline-block;width:9px;height:9px;border-radius:50%;
          background:white;border:2px solid #06b6d4;margin-right:5px;
          vertical-align:middle"></span>${n ? n.title : id}
      </div>`;
    }).join("")}
  `;
}

function highlightNodes(ids) {
  if (!ids?.length || !nodesSelection) return;

  highlightedIds = new Set(ids);

  //  remove old rings
  nodesSelection.selectAll(".gold-ring").remove();

  // add ring as separate circle (THIS is the fix)
  nodesSelection.each(function(d) {

    if (!highlightedIds.has(d.id)) return;

    const node = d3.select(this);

    node.append("circle")
      .attr("class", "gold-ring")
      .attr("r", function() {
        const base = node.select("circle").attr("r");
        return +base + 6;
      })
      .attr("fill", "none")
      .attr("stroke", "#FFD700")
      .attr("stroke-width", 3)
      .attr("pointer-events", "none");
  });
}

window.addEventListener("resize", renderGraph);