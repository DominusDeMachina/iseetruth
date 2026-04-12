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
      screen.getByText("Drag PDFs or images here to start your investigation"),
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

  it("rejects unsupported file type with error message", () => {
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
    const file = new File(["data"], "notes.txt", { type: "text/plain" });
    fireEvent.change(input, { target: { files: [file] } });

    expect(
      screen.getByText(/notes\.txt.*not a supported file type/),
    ).toBeInTheDocument();
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

  it("accepts JPEG file without rejection", () => {
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
    const file = new File(["jpeg data"], "photo.jpg", { type: "image/jpeg" });
    fireEvent.change(input, { target: { files: [file] } });

    expect(onUpload).toHaveBeenCalledWith([file]);
  });

  it("accepts PNG file without rejection", () => {
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
    const file = new File(["png data"], "screenshot.png", {
      type: "image/png",
    });
    fireEvent.change(input, { target: { files: [file] } });

    expect(onUpload).toHaveBeenCalledWith([file]);
  });

  it("rejects .txt file with error listing accepted types", () => {
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
    const file = new File(["text"], "notes.txt", { type: "text/plain" });
    fireEvent.change(input, { target: { files: [file] } });

    expect(
      screen.getByText(/Accepted: PDF, JPEG, PNG, TIFF/),
    ).toBeInTheDocument();
    expect(onUpload).not.toHaveBeenCalled();
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
