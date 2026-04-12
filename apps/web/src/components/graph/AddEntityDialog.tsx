import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useCreateEntity } from "@/hooks/useEntityMutations";

const ENTITY_TYPE_OPTIONS = [
  { value: "person", label: "Person", color: "#6b9bd2" },
  { value: "organization", label: "Organization", color: "#c4a265" },
  { value: "location", label: "Location", color: "#7dab8f" },
] as const;

interface AddEntityDialogProps {
  investigationId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AddEntityDialog({
  investigationId,
  open,
  onOpenChange,
}: AddEntityDialogProps) {
  const [name, setName] = useState("");
  const [entityType, setEntityType] = useState<string>("");
  const [sourceAnnotation, setSourceAnnotation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const createMutation = useCreateEntity(investigationId);

  const resetForm = () => {
    setName("");
    setEntityType("");
    setSourceAnnotation("");
    setError(null);
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) resetForm();
    onOpenChange(nextOpen);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError("Entity name is required");
      return;
    }
    if (!entityType) {
      setError("Entity type is required");
      return;
    }

    createMutation.mutate(
      {
        name: name.trim(),
        type: entityType,
        source_annotation: sourceAnnotation.trim() || null,
      },
      {
        onSuccess: () => {
          handleOpenChange(false);
        },
        onError: (err: unknown) => {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: unknown }).detail)
              : "Failed to create entity";
          setError(detail);
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-[420px] bg-[var(--bg-elevated)] border-[var(--border-subtle)]">
        <DialogHeader>
          <DialogTitle className="text-[var(--text-primary)]">
            Add Entity
          </DialogTitle>
          <DialogDescription className="text-[var(--text-secondary)]">
            Manually add an entity to the knowledge graph.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="entity-name" className="text-[var(--text-secondary)]">
              Name
            </Label>
            <Input
              id="entity-name"
              value={name}
              onChange={(e) => { setName(e.target.value); setError(null); }}
              placeholder="Entity name"
              required
              disabled={createMutation.isPending}
              maxLength={500}
              className="border-[var(--border-subtle)] bg-[var(--bg-secondary)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label className="text-[var(--text-secondary)]">Type</Label>
            <div className="flex gap-2">
              {ENTITY_TYPE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => { setEntityType(opt.value); setError(null); }}
                  aria-pressed={entityType === opt.value}
                  className={`flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs transition-colors ${
                    entityType === opt.value
                      ? "border-[var(--text-primary)] bg-[var(--bg-hover)] text-[var(--text-primary)]"
                      : "border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
                  }`}
                >
                  <span
                    className="inline-block size-2 rounded-full shrink-0"
                    style={{ backgroundColor: opt.color }}
                  />
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <Label
              htmlFor="source-annotation"
              className="text-[var(--text-secondary)]"
            >
              Source Annotation
              <span className="text-[var(--text-muted)] ml-1">(optional)</span>
            </Label>
            <Textarea
              id="source-annotation"
              value={sourceAnnotation}
              onChange={(e) => setSourceAnnotation(e.target.value)}
              placeholder="Where did you find this information?"
              disabled={createMutation.isPending}
              maxLength={2000}
              rows={2}
              className="border-[var(--border-subtle)] bg-[var(--bg-secondary)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
            />
          </div>

          {error && (
            <p className="text-xs text-[var(--status-error)]">{error}</p>
          )}

          <Button
            type="submit"
            disabled={!name.trim() || !entityType || createMutation.isPending}
          >
            {createMutation.isPending ? "Creating..." : "Add Entity"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
