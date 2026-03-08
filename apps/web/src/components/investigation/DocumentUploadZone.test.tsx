import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DocumentUploadZone } from "./DocumentUploadZone";

describe("DocumentUploadZone", () => {
  it("renders drop zone with message", () => {
    render(
      <DocumentUploadZone
        onUpload={vi.fn()}
        isUploading={false}
        hasDocuments={false}
      />,
    );
    expect(
      screen.getByText("Drag PDF files here to start your investigation"),
    ).toBeInTheDocument();
  });

  it("renders file picker button", () => {
    render(
      <DocumentUploadZone
        onUpload={vi.fn()}
        isUploading={false}
        hasDocuments={false}
      />,
    );
    expect(screen.getByText("Choose Files")).toBeInTheDocument();
  });

  it("rejects non-PDF with error message", () => {
    const onUpload = vi.fn();
    render(
      <DocumentUploadZone
        onUpload={onUpload}
        isUploading={false}
        hasDocuments={false}
      />,
    );

    const input = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    const file = new File(["data"], "image.png", { type: "image/png" });
    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.getByText('"image.png" is not a PDF')).toBeInTheDocument();
    expect(onUpload).not.toHaveBeenCalled();
  });

  it("shows upload progress when uploading", () => {
    render(
      <DocumentUploadZone
        onUpload={vi.fn()}
        isUploading={true}
        hasDocuments={false}
      />,
    );
    expect(screen.getByText("Uploading...")).toBeInTheDocument();
  });

  it("rejects oversized PDF with error message", () => {
    const onUpload = vi.fn();
    render(
      <DocumentUploadZone
        onUpload={onUpload}
        isUploading={false}
        hasDocuments={false}
      />,
    );

    const input = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    const file = new File(["x"], "huge.pdf", { type: "application/pdf" });
    Object.defineProperty(file, "size", { value: 250 * 1024 * 1024 });
    fireEvent.change(input, { target: { files: [file] } });

    expect(
      screen.getByText(/huge\.pdf.*exceeds 200 MB limit/),
    ).toBeInTheDocument();
    expect(onUpload).not.toHaveBeenCalled();
  });
});
