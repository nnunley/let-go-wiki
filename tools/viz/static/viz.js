(function () {
  const bundle = window.BUNDLE;
  const bundleName = window.BUNDLE_NAME;
  document.title = `${bundleName} — knowledge graph`;
  document.getElementById("graph-stats").textContent =
    `${bundle.nodes.length} pages, ${bundle.edges.length} links`;

  const isDark = window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches;
  const kindColor = (kind) => {
    const pal = (bundle.kindPalette || {})[kind];
    return pal ? (isDark ? pal.dark : pal.light) : (isDark ? "#6cc0c3" : "#2e7d80");
  };
  // Pick chip text from the fill's own luminance rather than the page theme:
  // the dark palette is not uniformly light (Source is #6b5f47), so a single
  // dark-theme foreground fell below 4.5:1 on it.
  const chipForeground = (hex) => {
    const m = /^#?([0-9a-f]{6})$/i.exec(hex || "");
    if (!m) return "#fff";
    const [r, g, b] = [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16) / 255);
    const lin = (c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
    const lum = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
    return lum > 0.25 ? "#1a1610" : "#fff";
  };

  // Read the active theme (light/dark) from CSS variables so canvas-drawn
  // node labels match the page and stay legible against the background.
  const _css = getComputedStyle(document.documentElement);
  const _v = (name, fallback) => (_css.getPropertyValue(name).trim() || fallback);
  const THEME = {
    fg: _v("--fg", "#1d180f"),
    bg: _v("--bg", "#f4ecdb"),
    accent: _v("--accent", "#b45309"),
    rule: _v("--rule", "#d6c8a8"),
    muted: _v("--muted", "#877a5e"),
  };

  // Kind filter: the top-bar select and the legend drive the same state.
  const kinds = bundle.kinds || [];
  const kindCounts = {};
  for (const n of bundle.nodes) kindCounts[n.data.kind] = (kindCounts[n.data.kind] || 0) + 1;
  const typeSelect = document.getElementById("filter-type");
  for (const k of kinds) {
    const opt = document.createElement("option");
    opt.value = k;
    opt.textContent = `${k} (${kindCounts[k] || 0})`;
    typeSelect.appendChild(opt);
  }

  // Forward/backward link indexes for the detail panel.
  const backlinks = {};
  const outlinks = {};
  for (const edge of bundle.edges) {
    const { source, target } = edge.data;
    (backlinks[target] ||= []).push(source);
    (outlinks[source] ||= []).push(target);
  }
  const nodeIndex = {};
  for (const n of bundle.nodes) nodeIndex[n.data.id] = n.data;

  // Mermaid for ```mermaid blocks rendered in the detail panel.
  // Theme-matched; securityLevel 'loose' so <br/> in node labels works.
  if (window.mermaid) {
    window.mermaid.initialize({
      startOnLoad: false, securityLevel: "loose",
      theme: isDark ? "dark" : "neutral",
    });
  }

  // Convert marked's ```mermaid code blocks into rendered diagrams.
  function renderMermaid(container) {
    if (!window.mermaid) return;
    const divs = [];
    container.querySelectorAll("code.language-mermaid").forEach((code) => {
      const div = document.createElement("div");
      div.className = "mermaid";
      div.textContent = code.textContent; // raw (unescaped) diagram source
      (code.closest("pre") || code).replaceWith(div);
      divs.push(div);
    });
    if (divs.length) {
      try { window.mermaid.run({ nodes: divs }); } catch (_e) { /* bad diagram */ }
    }
  }

  // Register the fcose force layout (self-registers in most builds; the guarded
  // use() covers builds that don't, and swallows a double-registration error).
  if (window.cytoscapeFcose) {
    try { cytoscape.use(window.cytoscapeFcose); } catch (_e) { /* already registered */ }
  }
  const _hasFcose = !!window.cytoscapeFcose;

  // Per-layout options. fcose is the default force layout; nodeSeparation and
  // idealEdgeLength are tuned for ~75 nodes with 10px labels below each node.
  function layoutOpts(name) {
    if (name === "fcose" && _hasFcose) {
      return {
        name: "fcose", animate: false, quality: "proof", randomize: true,
        padding: 48, nodeSeparation: 140, idealEdgeLength: 100,
        nodeRepulsion: 12000, gravity: 0.2, gravityRange: 3.5, numIter: 4000,
        // Pull heavily cited pages to the middle; leaves drift outward.
        nodeDimensionsIncludeLabels: true,
      };
    }
    if (name === "fcose") name = "cose"; // fallback if the extension failed to load
    if (name === "cose") return { name: "cose", animate: false, padding: 40 };
    if (name === "concentric") {
      // Rings by citation count, bucketed so no ring holds a single node
      // (one-node rings all sit at the same angle and read as a column).
      return {
        name, animate: false, padding: 40, minNodeSpacing: 24,
        concentric: (n) => Math.min(n.data("citedBy") || 0, 5), levelWidth: () => 1,
      };
    }
    if (name === "breadthfirst") {
      // Undirected: the hub links out to one page, so a directed walk from it
      // would leave nearly every node as its own root. Depth rings rather than
      // rows, because a star graph puts most nodes on one row.
      const root = bundle.nodes.find((n) => n.data.kind === "Entity");
      return { name, animate: false, padding: 40, directed: false, circle: true,
               roots: root ? `#${CSS.escape(root.data.id)}` : undefined };
    }
    if (name === "grid") {
      return { name, animate: false, padding: 40, avoidOverlapPadding: 24,
               nodeDimensionsIncludeLabels: true };
    }
    return { name, animate: false, padding: 40 };
  }

  const cy = cytoscape({
    container: document.getElementById("graph"),
    elements: [...bundle.nodes, ...bundle.edges],
    style: [
      {
        selector: "node",
        style: {
          "background-color": (n) => kindColor(n.data("kind")),
          "shape": (n) => (n.data("kind") === "Source" ? "round-rectangle" : "ellipse"),
          "label": "data(label)",
          // Foreground-colored text with a background-colored halo: readable on
          // any node fill and in both light and dark themes.
          "color": THEME.fg,
          "text-outline-color": THEME.bg,
          "text-outline-width": 2,
          "text-outline-opacity": 0.95,
          "font-family": "JetBrains Mono, ui-monospace, Menlo, monospace",
          "font-size": 10,
          "font-weight": 500,
          "min-zoomed-font-size": 7, // labels drop out when zoomed far out
          "text-valign": "bottom",
          "text-margin-y": 5,
          "text-wrap": "wrap",
          "text-max-width": 110,
          "width": "data(size)",
          "height": "data(size)",
          "border-width": 1,
          "border-color": THEME.bg,
          "transition-property": "opacity",
          "transition-duration": 120,
        },
      },
      {
        // Agent drafts not yet checked against the code: dashed outline.
        selector: "node[status = 'speculative']",
        style: {
          "border-width": 1.5,
          "border-style": "dashed",
          "border-color": THEME.muted,
          "background-opacity": 0.55,
        },
      },
      {
        selector: "node[kind = 'Source']",
        style: {
          "font-size": 9,
          "color": THEME.muted,
          "text-max-width": 90,
        },
      },
      {
        selector: "node:selected",
        style: {
          "border-width": 3,
          "border-color": THEME.accent,
          "background-opacity": 1,
        },
      },
      {
        selector: "edge",
        style: {
          "width": 1,
          "line-color": THEME.rule,
          "target-arrow-color": THEME.rule,
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          "arrow-scale": 0.7,
          "transition-property": "opacity",
          "transition-duration": 120,
        },
      },
      {
        selector: "edge.lit",
        style: {
          "line-color": THEME.accent,
          "target-arrow-color": THEME.accent,
          "width": 1.8,
          "z-index": 5,
        },
      },
      { selector: "node.lit", style: { "z-index": 6 } },
      { selector: ".dim", style: { "opacity": 0.12 } },
    ],
    layout: layoutOpts("fcose"),
    wheelSensitivity: 0.2,
  });

  // Legend: one toggle per kind, plus the dashed-outline hint.
  const legend = document.getElementById("legend");
  function buildLegend() {
    legend.innerHTML = "";
    for (const k of kinds) {
      const b = document.createElement("button");
      b.type = "button";
      b.dataset.kind = k;
      b.setAttribute("aria-pressed", "false");
      const sw = document.createElement("span");
      sw.className = "swatch" + (k === "Source" ? " square" : "");
      sw.style.background = kindColor(k);
      const name = document.createElement("span");
      name.textContent = k;
      const count = document.createElement("span");
      count.className = "count";
      count.textContent = kindCounts[k] || 0;
      b.append(sw, name, count);
      b.addEventListener("click", () => setKindFilter(filterKind === k ? "" : k));
      legend.appendChild(b);
    }
    const hint = document.createElement("div");
    hint.className = "hint";
    hint.innerHTML = "<i></i>dashed: not yet checked against the code";
    legend.appendChild(hint);
  }
  buildLegend();

  // --- Filtering ----------------------------------------------------------
  // Two independent dimming sources (kind filter, search) plus the focus
  // neighbourhood of the selected node; recompute .dim from all three.
  let filterKind = "";
  let query = "";
  let focusId = null;

  function applyDim() {
    const q = query;
    cy.batch(() => {
      cy.nodes().forEach((n) => {
        const d = n.data();
        let hidden = false;
        if (filterKind && d.kind !== filterKind) hidden = true;
        if (q) {
          const hay = `${d.label || ""} ${d.id} ${(d.tags || []).join(" ")}`.toLowerCase();
          if (!hay.includes(q)) hidden = true;
        }
        if (focusId && !hidden) {
          const f = cy.getElementById(focusId);
          hidden = !(n.id() === focusId || f.neighborhood().nodes().anySame(n));
        }
        n.toggleClass("dim", hidden);
      });
      cy.edges().forEach((e) => {
        e.toggleClass("dim", e.source().hasClass("dim") || e.target().hasClass("dim"));
      });
    });
  }

  function setKindFilter(k) {
    filterKind = k;
    typeSelect.value = k;
    legend.querySelectorAll("button[data-kind]").forEach((b) => {
      const on = b.dataset.kind === k;
      b.classList.toggle("active", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    applyDim();
  }

  typeSelect.addEventListener("change", (e) => setKindFilter(e.target.value));
  document.getElementById("search").addEventListener("input", (e) => {
    query = e.target.value.trim().toLowerCase();
    // A search replaces the focus neighbourhood; combining the two hides
    // matches the reader is looking for.
    focusId = null;
    cy.elements().removeClass("lit");
    applyDim();
  });
  // Pages outside the main component (mostly stdlib reference stubs that only
  // link to each other) have nothing to hold them near the graph, so force
  // layouts fling them to the edges and the fitted view shrinks. Park each
  // minor component in a grid of cells beside the main one.
  function packOrphans() {
    const comps = cy.elements().components()
      .map((c) => c.nodes()).filter((c) => c.length)
      .sort((a, b) => b.length - a.length);
    if (comps.length < 2) return;
    const main = comps[0];
    const minors = comps.slice(1);
    const bb = main.boundingBox({ includeLabels: true });
    const cell = 130;
    const cols = Math.max(1, Math.ceil(Math.sqrt(minors.length)));
    const rows = Math.ceil(minors.length / cols);
    const x0 = bb.x2 + 120;
    const y0 = bb.y1 + (bb.h - rows * cell) / 2 + cell / 2;
    minors.forEach((nodes, i) => {
      const cx = x0 + (i % cols) * cell;
      const cy_ = y0 + Math.floor(i / cols) * cell;
      const cb = nodes.boundingBox({ includeLabels: false });
      const scale = Math.min(1, (cell - 50) / Math.max(cb.w, cb.h, 1));
      nodes.forEach((n) => {
        const p = n.position();
        n.position({
          x: cx + (p.x - (cb.x1 + cb.w / 2)) * scale,
          y: cy_ + (p.y - (cb.y1 + cb.h / 2)) * scale,
        });
      });
    });
  }
  function runLayout(name) {
    const l = cy.layout(layoutOpts(name));
    l.one("layoutstop", () => { packOrphans(); cy.fit(null, 40); });
    l.run();
  }
  document.getElementById("layout").addEventListener("change", (e) => runLayout(e.target.value));
  document.getElementById("reset").addEventListener("click", () => {
    cy.fit(null, 40);
  });

  window.cyViz = cy; // handy for debugging and browser automation
  cy.on("tap", "node", (evt) => showDetail(evt.target.id()));
  cy.on("tap", (evt) => {
    if (evt.target === cy) clearSelection();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") clearSelection();
  });

  function clearSelection() {
    cy.elements().unselect();
    cy.elements().removeClass("lit");
    focusId = null;
    applyDim();
    document.getElementById("detail-empty").hidden = false;
    document.getElementById("detail-content").hidden = true;
  }

  function linkList(listEl, sectionEl, ids) {
    listEl.innerHTML = "";
    if (!ids.length) { sectionEl.hidden = true; return; }
    sectionEl.hidden = false;
    for (const id of ids) {
      const d = nodeIndex[id];
      const li = document.createElement("li");
      const dot = document.createElement("span");
      dot.className = "kind-dot";
      dot.style.background = kindColor(d ? d.kind : "");
      const a = document.createElement("a");
      a.textContent = d ? d.label : id;
      a.href = "javascript:void(0)";
      a.addEventListener("click", (e) => { e.preventDefault(); showDetail(id); });
      li.append(dot, a);
      listEl.appendChild(li);
    }
  }

  function showDetail(conceptId, { pan = true, focus = true } = {}) {
    const data = nodeIndex[conceptId];
    if (!data) return;
    cy.elements().unselect();
    cy.elements().removeClass("lit");
    const node = cy.getElementById(conceptId);
    node.select();
    if (focus) {
      node.addClass("lit");
      node.connectedEdges().addClass("lit");
      focusId = conceptId;
    }
    applyDim();

    document.getElementById("detail-empty").hidden = true;
    const content = document.getElementById("detail-content");
    content.hidden = false;

    const chip = document.getElementById("detail-type");
    chip.textContent = data.type;
    chip.style.background = kindColor(data.kind);
    chip.style.color = chipForeground(kindColor(data.kind));

    const status = document.getElementById("detail-status");
    status.textContent = data.status || "";
    status.className = "status-chip " + (data.status || "");

    document.getElementById("detail-title").textContent = data.label;

    const titleContainer = document.querySelector(".detail-header");
    const existingLink = titleContainer.querySelector(".open-page");
    if (existingLink) existingLink.remove();
    if (data.url) {
      const openPageLink = document.createElement("a");
      openPageLink.className = "open-page";
      openPageLink.href = data.url;
      openPageLink.target = "_top";
      openPageLink.textContent = "Open page ↗";
      titleContainer.appendChild(openPageLink);
    }

    document.getElementById("detail-id").textContent = conceptId;
    document.getElementById("detail-description").textContent = data.description || "—";

    const resourceEl = document.getElementById("detail-resource");
    resourceEl.innerHTML = "";
    if (data.resource) {
      const a = document.createElement("a");
      a.href = data.resource;
      a.textContent = data.resource.replace(/^https?:\/\/(www\.)?/, "");
      a.target = "_blank";
      a.rel = "noopener";
      a.className = "external";
      resourceEl.appendChild(a);
    } else {
      resourceEl.textContent = "—";
    }

    const tagsEl = document.getElementById("detail-tags");
    tagsEl.innerHTML = "";
    if (data.tags && data.tags.length) {
      for (const t of data.tags) {
        const span = document.createElement("span");
        span.className = "tag";
        span.textContent = t;
        tagsEl.appendChild(span);
      }
    } else {
      tagsEl.textContent = "—";
    }

    const body = bundle.bodies[conceptId] || "";
    const html = marked.parse(body, { breaks: false, gfm: true });
    const bodyEl = document.getElementById("detail-body");
    bodyEl.innerHTML = html;
    rewriteInternalLinks(bodyEl);
    renderMermaid(bodyEl);

    linkList(document.getElementById("links-list"),
             document.getElementById("detail-links"), outlinks[conceptId] || []);
    linkList(document.getElementById("backlinks-list"),
             document.getElementById("detail-backlinks"), backlinks[conceptId] || []);

    document.getElementById("detail").scrollTop = 0;
    if (!pan) return;
    const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    cy.animate({ center: { eles: node }, zoom: Math.max(cy.zoom(), 1.0) },
               { duration: reduce ? 0 : 200 });
  }

  function rewriteInternalLinks(root) {
    root.querySelectorAll("a[href]").forEach((a) => {
      const href = a.getAttribute("href");
      if (!href) return;
      // Body links were rewritten to MkDocs URLs ("concepts/stack-vm/") by the
      // generator; when one names a node, open it in the panel instead.
      if (!href.includes("://") && !href.startsWith("#")) {
        const target = href.replace(/\/$/, "").replace(/#.*$/, "").replace(/\.md$/, "");
        if (nodeIndex[target]) {
          a.className = "internal";
          a.setAttribute("href", "javascript:void(0)");
          a.addEventListener("click", (e) => {
            e.preventDefault();
            showDetail(target);
          });
          return;
        }
      }
      if (!href.startsWith("#")) {
        a.className = "external";
        if (!href.includes("://")) {
          a.setAttribute("target", "_top");
        } else {
          a.setAttribute("target", "_blank");
          a.setAttribute("rel", "noopener");
        }
      }
    });
  }

  // Open on the hub entity (the wiki's subject) when there is one.
  // First impression is the whole graph, undimmed, with the hub's page open;
  // focus dimming starts with the reader's first click.
  const initial =
    bundle.nodes.find((n) => n.data.kind === "Entity") || bundle.nodes[0];
  if (initial) showDetail(initial.data.id, { pan: false, focus: false });
  packOrphans();
  cy.fit(null, 40);
})();
