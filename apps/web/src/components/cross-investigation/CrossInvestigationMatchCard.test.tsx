import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createElement } from "react";

import { CrossInvestigationMatchCard } from "./CrossInvestigationMatchCard";

const sampleMatch = {
  entity_name: "Acme Corp",
  entity_type: "organization",
  match_confidence: 1.0,
  match_type: "exact" as const,
  source_entity_id: "e1",
  source_relationship_count: 5,
  source_confidence_score: 0.95,
  investigations: [
    {
      investigation_id: "inv-2",
      investigation_name: "Investigation B",
      entity_id: "e2",
      relationship_count: 3,
      confidence_score: 0.9,
    },
    {
      investigation_id: "inv-3",
      investigation_name: "Investigation C",
      entity_id: "e3",
      relationship_count: 1,
      confidence_score: 0.8,
    },
  ],
};

describe("CrossInvestigationMatchCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders entity name, type badge, and confidence", () => {
    render(createElement(CrossInvestigationMatchCard, { match: sampleMatch }));

    expect(screen.getByText("Acme Corp")).toBeTruthy();
    expect(screen.getByText("Organization")).toBeTruthy();
  });

  it("expands to show investigation list", async () => {
    render(createElement(CrossInvestigationMatchCard, { match: sampleMatch }));

    // Initially collapsed — investigation names not visible
    expect(screen.queryByText("Investigation B")).toBeNull();

    // Click to expand
    await userEvent.click(screen.getByText("Acme Corp"));

    expect(screen.getByText("Investigation B")).toBeTruthy();
    expect(screen.getByText("Investigation C")).toBeTruthy();
    expect(screen.getByText("3 rels")).toBeTruthy();
    expect(screen.getByText("1 rel")).toBeTruthy();
  });

  it("investigation names are clickable when handler provided", async () => {
    const onNavigate = vi.fn();
    render(
      createElement(CrossInvestigationMatchCard, {
        match: sampleMatch,
        onNavigateToInvestigation: onNavigate,
      }),
    );

    // Expand first
    await userEvent.click(screen.getByText("Acme Corp"));

    // Click investigation name
    await userEvent.click(screen.getByText("Investigation B"));
    expect(onNavigate).toHaveBeenCalledWith("inv-2");
  });
});
