import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { createElement } from "react";

import { CrossInvestigationSearchResults } from "./CrossInvestigationSearchResults";

const sampleResults = [
  {
    entity_name: "Acme Corp",
    entity_type: "organization",
    investigation_count: 2,
    investigations: [
      {
        investigation_id: "inv-1",
        investigation_name: "Investigation A",
        entity_id: "e1",
        relationship_count: 3,
      },
      {
        investigation_id: "inv-2",
        investigation_name: "Investigation B",
        entity_id: "e2",
        relationship_count: 1,
      },
    ],
    match_score: 1.0,
  },
];

describe("CrossInvestigationSearchResults", () => {
  it("renders search results", () => {
    render(
      createElement(CrossInvestigationSearchResults, {
        results: sampleResults,
        query: "acme",
      }),
    );

    expect(screen.getByText("Acme Corp")).toBeTruthy();
    expect(screen.getByText("Organization")).toBeTruthy();
    expect(screen.getByText("Found in 2 investigations")).toBeTruthy();
    expect(screen.getByText("Investigation A")).toBeTruthy();
    expect(screen.getByText("Investigation B")).toBeTruthy();
  });

  it("shows empty state for no results", () => {
    render(
      createElement(CrossInvestigationSearchResults, {
        results: [],
        query: "nonexistent",
      }),
    );

    expect(
      screen.getByText(
        /No entities matching .nonexistent. found across investigations/,
      ),
    ).toBeTruthy();
  });
});
