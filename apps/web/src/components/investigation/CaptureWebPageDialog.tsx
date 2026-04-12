import { useState } from "react";
import { Globe, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface CaptureWebPageDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCapture: (url: string) => void;
  isPending: boolean;
}

function isValidUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

export function CaptureWebPageDialog({
  open,
  onOpenChange,
  onCapture,
  isPending,
}: CaptureWebPageDialogProps) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) {
      setError("URL is required");
      return;
    }
    if (!isValidUrl(trimmed)) {
      setError("Enter a valid URL starting with http:// or https://");
      return;
    }
    setError("");
    onCapture(trimmed);
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setUrl("");
      setError("");
    }
    onOpenChange(open);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md bg-[var(--bg-elevated)] border-[var(--border-subtle)]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-[var(--text-primary)]">
            <Globe className="size-5" />
            Capture Web Page
          </DialogTitle>
          <DialogDescription className="text-[var(--text-secondary)]">
            Enter a URL to capture a web page as a document source.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="py-4">
            <Input
              placeholder="https://example.com/article"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                if (error) setError("");
              }}
              autoFocus
              disabled={isPending}
              className="bg-[var(--bg-primary)] border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
            />
            {error && (
              <p className="mt-1.5 text-xs text-[var(--status-error)]">
                {error}
              </p>
            )}
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={isPending}
              className="border-[var(--border-subtle)] text-[var(--text-primary)]"
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isPending || !url.trim()}>
              {isPending ? (
                <>
                  <Loader2 className="size-4 mr-1.5 animate-spin" />
                  Capturing...
                </>
              ) : (
                "Capture"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
