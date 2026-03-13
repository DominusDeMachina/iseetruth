import type cytoscape from "cytoscape";

type Stylesheet = cytoscape.StylesheetCSS | cytoscape.StylesheetStyle;

/**
 * Darken a hex color by a percentage (0–1).
 */
function darkenHex(hex: string, amount: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const factor = 1 - amount;
  return `#${[r, g, b]
    .map((c) =>
      Math.round(c * factor)
        .toString(16)
        .padStart(2, "0"),
    )
    .join("")}`;
}

// Entity type → color mapping (matches CSS vars in globals.css)
const ENTITY_COLORS: Record<string, string> = {
  Person: "#6b9bd2",
  Organization: "#c4a265",
  Location: "#7dab8f",
};

// Entity type → shape mapping
const ENTITY_SHAPES: Record<string, string> = {
  Person: "ellipse",
  Organization: "diamond",
  Location: "triangle",
};

export const cytoscapeStylesheet: Stylesheet[] = [
  // Default node style
  {
    selector: "node",
    style: {
      label: "data(name)",
      "font-family": "Inter, sans-serif",
      "font-size": "11px",
      color: "#e8e0d4",
      "text-wrap": "ellipsis",
      "text-max-width": "80px",
      "text-valign": "bottom",
      "text-margin-y": 4,
      width: "mapData(relationship_count, 0, 20, 35, 60)",
      height: "mapData(relationship_count, 0, 20, 35, 60)",
      "border-width": "mapData(confidence_score, 0, 1, 1, 4)",
      "background-color": "#a89f90", // fallback for unknown types
      "border-color": "#7a7168",
    },
  },

  // Person nodes
  {
    selector: 'node[type = "Person"]',
    style: {
      "background-color": ENTITY_COLORS.Person,
      shape: ENTITY_SHAPES.Person as cytoscape.Css.NodeShape,
      "border-color": darkenHex(ENTITY_COLORS.Person, 0.3),
    },
  },

  // Organization nodes
  {
    selector: 'node[type = "Organization"]',
    style: {
      "background-color": ENTITY_COLORS.Organization,
      shape: ENTITY_SHAPES.Organization as cytoscape.Css.NodeShape,
      "border-color": darkenHex(ENTITY_COLORS.Organization, 0.3),
    },
  },

  // Location nodes
  {
    selector: 'node[type = "Location"]',
    style: {
      "background-color": ENTITY_COLORS.Location,
      shape: ENTITY_SHAPES.Location as cytoscape.Css.NodeShape,
      "border-color": darkenHex(ENTITY_COLORS.Location, 0.3),
    },
  },

  // Edge styles
  {
    selector: "edge",
    style: {
      "line-color": "#5c5548",
      width: 1.5,
      "curve-style": "bezier",
      "target-arrow-shape": "triangle",
      "target-arrow-color": "#5c5548",
      opacity: 0.6,
    },
  },

  // Edge label on hover (class-based toggle)
  {
    selector: "edge.show-label",
    style: {
      label: "data(type)",
      "font-size": "10px",
      "font-family": "Inter, sans-serif",
      color: "#e8e0d4",
      "text-background-color": "#1a1816",
      "text-background-opacity": 0.8,
      "text-background-padding": "2px",
    },
  },

  // Selection style
  {
    selector: "node:selected",
    style: {
      "border-color": "#e8e0d4",
      "border-width": 3,
    },
  },

  // Active/hover style — simulate scale(1.05) via width/height increase
  {
    selector: "node:active",
    style: {
      opacity: 1,
      width: "mapData(relationship_count, 0, 20, 36.75, 63)",
      height: "mapData(relationship_count, 0, 20, 36.75, 63)",
    },
  },
];
