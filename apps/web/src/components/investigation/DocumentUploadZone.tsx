import { useCallback, useRef, useState } from "react";
import { Upload, AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

const MAX_FILE_SIZE = 200 * 1024 * 1024; // 200 MB
const ACCEPTED_TYPES = new Set([
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/tiff",
]);

interface UploadingFile {
  name: string;
  progress: "uploading" | "done" | "error";
}

interface DocumentUploadZoneProps {
  onUpload: (files: File[]) => void;
  isUploading: boolean;
  hasDocuments: boolean;
}

export function DocumentUploadZone({
  onUpload,
  isUploading,
  hasDocuments,
}: DocumentUploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [rejections, setRejections] = useState<string[]>([]);
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (fileList: FileList | File[]) => {
      const files = Array.from(fileList);
      const valid: File[] = [];
      const rejected: string[] = [];

      for (const file of files) {
        if (!ACCEPTED_TYPES.has(file.type)) {
          rejected.push(
            `"${file.name}" is not a supported file type. Accepted: PDF, JPEG, PNG, TIFF`,
          );
        } else if (file.size > MAX_FILE_SIZE) {
          const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
          rejected.push(`"${file.name}" exceeds 200 MB limit (${sizeMB} MB)`);
        } else {
          valid.push(file);
        }
      }

      setRejections(rejected);

      if (valid.length > 0) {
        setUploadingFiles(
          valid.map((f) => ({ name: f.name, progress: "uploading" })),
        );
        onUpload(valid);
      }
    },
    [onUpload],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);

      const items = e.dataTransfer.items;
      const files: File[] = [];

      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.kind === "file") {
          const file = item.getAsFile();
          if (file) files.push(file);
        }
      }

      if (files.length > 0) handleFiles(files);
    },
    [handleFiles],
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFiles(e.target.files);
        e.target.value = "";
      }
    },
    [handleFiles],
  );

  return (
    <div className="flex flex-col gap-3">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`flex flex-col items-center gap-4 rounded-xl border-2 border-dashed transition-colors ${
          hasDocuments ? "py-8" : "py-16"
        } text-center ${
          isDragOver
            ? "border-[var(--border-strong)] bg-[var(--bg-hover)]"
            : "border-[var(--border-subtle)] bg-[var(--bg-secondary)]"
        }`}
      >
        {isUploading ? (
          <Loader2 className="size-8 animate-spin text-[var(--text-muted)]" />
        ) : (
          <Upload className="size-8 text-[var(--text-muted)]" />
        )}
        <p className="text-[var(--text-secondary)]">
          {isUploading
            ? "Uploading..."
            : "Drag PDFs or images here to start your investigation"}
        </p>
        <Button
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
        >
          Choose Files
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.tiff,.tif,application/pdf,image/jpeg,image/png,image/tiff"
          multiple
          className="hidden"
          onChange={handleFileInput}
        />
      </div>

      {isUploading && uploadingFiles.length > 0 && (
        <div className="flex flex-col gap-1">
          {uploadingFiles.map((f) => (
            <div
              key={f.name}
              className="flex items-center gap-2 text-sm text-[var(--text-secondary)]"
            >
              <Loader2 className="size-3 animate-spin" />
              <span className="truncate">{f.name}</span>
            </div>
          ))}
        </div>
      )}

      {rejections.length > 0 && (
        <div className="flex flex-col gap-1">
          {rejections.map((msg) => (
            <div
              key={msg}
              className="flex items-center gap-2 text-sm text-[var(--status-error)]"
            >
              <AlertCircle className="size-3 shrink-0" />
              <span>{msg}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
