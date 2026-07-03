(function () {
  const bundle = window.BUNDLE;
  const bundleName = window.BUNDLE_NAME;
  document.title = `${bundleName} — OKF Viewer`;
  document.getElementById("bundle-name").textContent = bundleName;

  // Populate type filter
  const typeSelect = document.getElementById("filter-type");
  for (const t of bundle.types) {
    const opt = document.createElement("option");
    opt.value = t;
    opt.textContent = t;
    typeSelect.appendChild(opt);
  }

  // Build reverse-link index for backlinks
  const backlinks = {};
  for (const edge of bundle.edges) {
    const { source, target } = edge.data;
    (backlinks[target] ||= []).push(source);
  }

  // Look up node label/type by id
  const nodeIndex = {};
  for (const n of bundle.nodes) nodeIndex[n.data.id] = n.data;

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

  // Register the fcose force layout (self-registers in most builds; the guarded
  // use() covers builds that don't, and swallows a double-registration error).
  if (window.cytoscapeFcose) {
    try { cytoscape.use(window.cytoscapeFcose); } catch (_e) { /* already registered */ }
  }
  const _hasFcose = !!window.cytoscapeFcose;

  // Per-layout options. fcose is the default force layout: its nodeSeparation
  // and idealEdgeLength pull the graph apart so labels stop overlapping.
  function layoutOpts(name) {
    if (name === "fcose" && _hasFcose) {
      return {
        name: "fcose", animate: false, quality: "default", randomize: true,
        padding: 40, nodeSeparation: 130, idealEdgeLength: 95,
        nodeRepulsion: 6500, gravity: 0.25, numIter: 2500,
      };
    }
    if (name === "fcose") name = "cose"; // fallback if the extension failed to load
    if (name === "cose") return { name: "cose", animate: false, padding: 30 };
    return { name, animate: false, padding: 30 };
  }

  const cy = cytoscape({
    container: document.getElementById("graph"),
    elements: [...bundle.nodes, ...bundle.edges],
    style: [
      {
        selector: "node",
        style: {
          "background-color": "data(color)",
          "label": "data(label)",
          // Foreground-colored text with a background-colored halo: readable on
          // any node fill and in both light and dark themes.
          "color": THEME.fg,
          "text-outline-color": THEME.bg,
          "text-outline-width": 2.5,
          "text-outline-opacity": 1,
          "font-size": 11,
          "font-weight": 600,
          "text-valign": "bottom",
          "text-margin-y": 4,
          "text-wrap": "wrap",
          "text-max-width": 120,
          "width": "data(size)",
          "height": "data(size)",
          "border-width": 1,
          "border-color": THEME.muted,
        },
      },
      {
        selector: "node:selected",
        style: {
          "border-width": 3,
          "border-color": THEME.accent,
        },
      },
      {
        selector: "edge",
        style: {
          "width": 1.5,
          "line-color": THEME.rule,
          "target-arrow-color": THEME.rule,
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          "arrow-scale": 0.9,
        },
      },
      {
        selector: "edge:selected",
        style: {
          "line-color": THEME.accent,
          "target-arrow-color": THEME.accent,
          "width": 2.5,
        },
      },
      {
        selector: ".dim",
        style: { "opacity": 0.15 },
      },
    ],
    layout: layoutOpts("fcose"),
    wheelSensitivity: 0.2,
  });

  cy.on("tap", "node", (evt) => showDetail(evt.target.id()));
  cy.on("tap", (evt) => {
    if (evt.target === cy) clearSelection();
  });

  document.getElementById("layout").addEventListener("change", (e) => {
    cy.layout(layoutOpts(e.target.value)).run();
  });

  document.getElementById("reset").addEventListener("click", () => {
    cy.fit(null, 30);
    clearSelection();
  });

  document.getElementById("search").addEventListener("input", (e) => {
    const q = e.target.value.trim().toLowerCase();
    if (!q) {
      cy.elements().removeClass("dim");
      return;
    }
    cy.nodes().forEach((n) => {
      const d = n.data();
      const hay =
        (d.label || "").toLowerCase() + " " +
        d.id.toLowerCase() + " " +
        (d.tags || []).join(" ").toLowerCase();
      n.toggleClass("dim", !hay.includes(q));
    });
    cy.edges().forEach((edge) => {
      const src = edge.source();
      const tgt = edge.target();
      edge.toggleClass("dim", src.hasClass("dim") || tgt.hasClass("dim"));
    });
  });

  document.getElementById("filter-type").addEventListener("change", (e) => {
    const t = e.target.value;
    if (!t) {
      cy.elements().removeClass("dim");
      return;
    }
    cy.nodes().forEach((n) => {
      n.toggleClass("dim", n.data("type") !== t);
    });
    cy.edges().forEach((edge) => {
      edge.toggleClass("dim", edge.source().hasClass("dim") || edge.target().hasClass("dim"));
    });
  });

  function clearSelection() {
    cy.elements().unselect();
    document.getElementById("detail-empty").hidden = false;
    document.getElementById("detail-content").hidden = true;
  }

  function showDetail(conceptId) {
    const data = nodeIndex[conceptId];
    if (!data) return;
    cy.elements().unselect();
    const node = cy.getElementById(conceptId);
    if (node) node.select();

    document.getElementById("detail-empty").hidden = true;
    const content = document.getElementById("detail-content");
    content.hidden = false;

    const chip = document.getElementById("detail-type");
    chip.textContent = data.type;
    chip.style.background = data.color;

    document.getElementById("detail-title").textContent = data.label;

    // Add open-page link
    const titleContainer = document.querySelector(".detail-header");
    if (titleContainer) {
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
    }

    document.getElementById("detail-id").textContent = conceptId;
    document.getElementById("detail-description").textContent = data.description || "—";

    const resourceEl = document.getElementById("detail-resource");
    resourceEl.innerHTML = "";
    if (data.resource) {
      const a = document.createElement("a");
      a.href = data.resource;
      a.textContent = data.resource;
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

    const bl = backlinks[conceptId] || [];
    const blSection = document.getElementById("detail-backlinks");
    const blList = document.getElementById("backlinks-list");
    blList.innerHTML = "";
    if (bl.length) {
      blSection.hidden = false;
      for (const src of bl) {
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.textContent = nodeIndex[src]?.label || src;
        a.dataset.target = src;
        a.addEventListener("click", () => showDetail(src));
        li.appendChild(a);
        const muted = document.createElement("span");
        muted.className = "muted";
        muted.textContent = ` (${src})`;
        li.appendChild(muted);
        blList.appendChild(li);
      }
    } else {
      blSection.hidden = true;
    }

    cy.animate({ center: { eles: node }, zoom: Math.max(cy.zoom(), 1.0) }, { duration: 200 });
  }

  function rewriteInternalLinks(root) {
    root.querySelectorAll("a[href]").forEach((a) => {
      const href = a.getAttribute("href");
      if (!href) return;
      if (href.startsWith("/") && href.endsWith(".md")) {
        const target = href.slice(1, -3);
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
      // For external links or rewritten MkDocs URLs (like "concepts/b/"),
      // set target="_top" so they navigate the whole window
      if (!href.startsWith("#")) {
        a.className = "external";
        if (!href.includes("://")) {
          // Rewritten internal URL (MkDocs format) - navigate away from graph
          a.setAttribute("target", "_top");
        } else {
          // External URL - open in new tab
          a.setAttribute("target", "_blank");
          a.setAttribute("rel", "noopener");
        }
      }
    });
  }

  // Auto-show the first node (a dataset if available, else first concept)
  const initial =
    bundle.nodes.find((n) => n.data.type === "BigQuery Dataset") ||
    bundle.nodes[0];
  if (initial) showDetail(initial.data.id);
})();
