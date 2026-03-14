import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createElement } from "react";
import { GraphFilterPanel } from "./GraphFilterPanel";

const mockDocuments = [
  { id: "doc-1", filename: "contract.pdf", status: "completed" as const } as never,
  { id: "doc-2", filename: "report.pdf", status: "completed" as const } as never,
];

function renderPanel(overrides: Record<string, unknown> = {}) {
  const defaultProps = {
    entityTypes: [] as string[],
    onEntityTypesChange: vi.fn(),
    documentId: undefined as string | undefined,
    onDocumentIdChange: vi.fn(),
    documents: mockDocuments,
    isCollapsed: false,
    onToggleCollapse: vi.fn(),
    ...overrides,
  };
  const result = render(createElement(GraphFilterPanel, defaultProps));
  return { ...result, props: defaultProps };
}

describe("GraphFilterPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders three entity type chips", () => {
    renderPanel();
    expect(screen.getByText("People")).toBeTruthy();
    expect(screen.getByText("Orgs")).toBeTruthy();
    expect(screen.getByText("Locations")).toBeTruthy();
  });

  it("all chips active by default (empty entityTypes = show all)", () => {
    renderPanel({ entityTypes: [] });
    const chips = screen.getAllByRole("checkbox");
    expect(chips).toHaveLength(3);
    chips.forEach((chip) => {
      expect(chip.getAttribute("aria-checked")).toBe("true");
    });
  });

  it("toggling a chip calls onEntityTypesChange", async () => {
    const onEntityTypesChange = vi.fn();
    renderPanel({ entityTypes: [], onEntityTypesChange });

    await userEvent.click(screen.getByText("People"));

    // Clicking "People" when all are active => show all except person
    expect(onEntityTypesChange).toHaveBeenCalledWith(["organization", "location"]);
  });

  it("shows chip as inactive when not in entityTypes", () => {
    renderPanel({ entityTypes: ["person", "organization"] });
    const chips = screen.getAllByRole("checkbox");
    // People and Orgs active, Locations inactive
    expect(chips[0].getAttribute("aria-checked")).toBe("true"); // People
    expect(chips[1].getAttribute("aria-checked")).toBe("true"); // Orgs
    expect(chips[2].getAttribute("aria-checked")).toBe("false"); // Locations
  });

  it("re-enables all when last active type would be deactivated", async () => {
    const onEntityTypesChange = vi.fn();
    // Only "person" is active
    renderPanel({ entityTypes: ["person"], onEntityTypesChange });

    await userEvent.click(screen.getByText("People"));

    // Trying to deactivate the last type => re-enable all (empty array)
    expect(onEntityTypesChange).toHaveBeenCalledWith([]);
  });

  it("renders document dropdown with documents", () => {
    renderPanel();
    const select = screen.getByLabelText("Filter by document");
    expect(select).toBeTruthy();
    expect(screen.getByText("All documents")).toBeTruthy();
    expect(screen.getByText("contract.pdf")).toBeTruthy();
    expect(screen.getByText("report.pdf")).toBeTruthy();
  });

  it("selecting a document calls onDocumentIdChange", async () => {
    const onDocumentIdChange = vi.fn();
    renderPanel({ onDocumentIdChange });

    await userEvent.selectOptions(
      screen.getByLabelText("Filter by document"),
      "doc-1",
    );

    expect(onDocumentIdChange).toHaveBeenCalledWith("doc-1");
  });

  it("selecting 'All documents' clears documentId", async () => {
    const onDocumentIdChange = vi.fn();
    renderPanel({ documentId: "doc-1", onDocumentIdChange });

    await userEvent.selectOptions(
      screen.getByLabelText("Filter by document"),
      "",
    );

    expect(onDocumentIdChange).toHaveBeenCalledWith(undefined);
  });

  it("clear button resets all filters", async () => {
    const onEntityTypesChange = vi.fn();
    const onDocumentIdChange = vi.fn();
    renderPanel({
      entityTypes: ["person"],
      documentId: "doc-1",
      onEntityTypesChange,
      onDocumentIdChange,
    });

    await userEvent.click(screen.getByLabelText("Clear all filters"));

    expect(onEntityTypesChange).toHaveBeenCalledWith([]);
    expect(onDocumentIdChange).toHaveBeenCalledWith(undefined);
  });

  it("collapsed mode shows summary text", () => {
    renderPanel({
      isCollapsed: true,
      entityTypes: ["person"],
      documentId: "doc-1",
    });

    expect(screen.getByText("People · contract.pdf")).toBeTruthy();
  });

  it("collapsed mode shows active filter count badge", () => {
    renderPanel({
      isCollapsed: true,
      entityTypes: ["person"],
      documentId: "doc-1",
    });

    // Badge with count 2 (entity type filter + document filter)
    expect(screen.getByText("2")).toBeTruthy();
  });

  it("expand/collapse toggle works", async () => {
    const onToggleCollapse = vi.fn();
    renderPanel({ isCollapsed: true, onToggleCollapse });

    // Click the collapsed bar to expand
    const toolbar = screen.getByRole("toolbar");
    await userEvent.click(toolbar);

    expect(onToggleCollapse).toHaveBeenCalled();
  });

  it("has correct accessibility attributes", () => {
    renderPanel();
    const toolbar = screen.getByRole("toolbar");
    expect(toolbar.getAttribute("aria-label")).toBe("Graph filters");

    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes).toHaveLength(3);
  });
});
