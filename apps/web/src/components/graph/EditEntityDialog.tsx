import { useState, useEffect } from "react";
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
import { useUpdateEntity } from "@/hooks/useEntityMutations";

const TYPE_COLORS: Record<string, string> = {
  person: "#6b9bd2",
  organization: "#c4a265",
  location: "#7dab8f",
};

interface EditEntityDialogProps {
  investigationId: string;
  entityId: string;
  entityName: string;
  entityType: string;
  sourceAnnotation?: string | null;
  aliases?: string[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function EditEntityDialog({
  investigationId,
  entityId,
  entityName,
  entityType,
  sourceAnnotation: initialAnnotation,
  aliases,
  open,
  onOpenChange,
}: EditEntityDialogProps) {
  const [name, setName] = useState(entityName);
  const [sourceAnnotation, setSourceAnnotation] = useState(
    initialAnnotation || "",
  );
  const [error, setError] = useState<string | null>(null);
  const updateMutation = useUpdateEntity(investigationId);

  // Reset form when dialog opens with new entity data
  useEffect(() => {
    if (open) {
      setName(entityName);
      setSourceAnnotation(initialAnnotation || "");
      setError(null);
    }
  }, [open, entityName, initialAnnotation]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError("Entity name is required");
      return;
    }

    const body: { name?: string; source_annotation?: string | null } = {};
    if (name.trim() !== entityName) {
      body.name = name.trim();
    }
    if (sourceAnnotation.trim() !== (initialAnnotation || "")) {
      body.source_annotation = sourceAnnotation.trim() || null;
    }

    // Nothing changed
    if (Object.keys(body).length === 0) {
      onOpenChange(false);
      return;
    }

    updateMutation.mutate(
      { entityId, body },
      {
        onSuccess: () => {
          onOpenChange(false);
        },
        onError: (err: unknown) => {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: unknown }).detail)
              : "Failed to update entity";
          setError(detail);
        },
      },
    );
  };

  const dotColor = TYPE_COLORS[entityType] ?? "#a89f90";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[420px] bg-[var(--bg-elevated)] border-[var(--border-subtle)]">
        <DialogHeader>
          <DialogTitle className="text-[var(--text-primary)]">
            Edit Entity
          </DialogTitle>
          <DialogDescription className="text-[var(--text-secondary)]">
            Update entity name or source annotation.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="edit-entity-name" className="text-[var(--text-secondary)]">
              Name
            </Label>
            <Input
              id="edit-entity-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Entity name"
              required
              disabled={updateMutation.isPending}
              maxLength={500}
              className="border-[var(--border-subtle)] bg-[var(--bg-secondary)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label className="text-[var(--text-secondary)]">Type</Label>
            <div className="flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
              <span
                className="inline-block size-2 rounded-full shrink-0"
                style={{ backgroundColor: dotColor }}
              />
              {entityType}
              <span className="ml-1">(read-only)</span>
            </div>
          </div>

          {aliases && aliases.length > 0 && (
            <div className="flex flex-col gap-2">
              <Label className="text-[var(--text-secondary)]">
                Previous names
              </Label>
              <div className="flex flex-wrap gap-1">
                {aliases.map((alias) => (
                  <span
                    key={alias}
                    className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-2 py-0.5 text-xs text-[var(--text-muted)]"
                  >
                    {alias}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="flex flex-col gap-2">
            <Label
              htmlFor="edit-source-annotation"
              className="text-[var(--text-secondary)]"
            >
              Source Annotation
              <span className="text-[var(--text-muted)] ml-1">(optional)</span>
            </Label>
            <Textarea
              id="edit-source-annotation"
              value={sourceAnnotation}
              onChange={(e) => setSourceAnnotation(e.target.value)}
              placeholder="Where did you find this information?"
              disabled={updateMutation.isPending}
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
            disabled={!name.trim() || updateMutation.isPending}
          >
            {updateMutation.isPending ? "Saving..." : "Save Changes"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
