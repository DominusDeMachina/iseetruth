// Shared entity type → color mapping
// Used by both Cytoscape graph styling and UI components (EntityDetailCard, etc.)
// Matches CSS custom properties in globals.css (--entity-person, --entity-org, --entity-location)
export const ENTITY_COLORS: Record<string, string> = {
  Person: "#6b9bd2",
  Organization: "#c4a265",
  Location: "#7dab8f",
};
