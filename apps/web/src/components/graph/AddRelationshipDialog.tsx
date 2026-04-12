import { useState, useMemo, useEffect } from "react";
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
import { useEntities } from "@/hooks/useEntities";
import { useCreateRelationship } from "@/hooks/useEntityMutations";

const RELATIONSHIP_TYPE_OPTIONS = [
  "WORKS_FOR",
  "KNOWS",
  "LOCATED_AT",
  "MENTIONED_IN",
] as const;

const UPPER_SNAKE_RE = /^[A-Z][A-Z0-9_]*$/;

interface AddRelationshipDialogProps {
  investigationId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Pre-selected source entity ID (e.g., when opened from EntityDetailCard). */
  preSelectedSourceId?: string;
}

export function AddRelationshipDialog({
  investigationId,
  open,
  onOpenChange,
  preSelectedSourceId,
}: AddRelationshipDialogProps) {
  const [sourceEntityId, setSourceEntityId] = useState(
    preSelectedSourceId ?? "",
  );
  const [targetEntityId, setTargetEntityId] = useState("");
  const [relType, setRelType] = useState("");
  const [customType, setCustomType] = useState("");
  const [sourceAnnotation, setSourceAnnotation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  const { data: entitiesData } = useEntities(investigationId);
  const createMutation = useCreateRelationship(investigationId);

  const entities = useMemo(
    () => entitiesData?.items ?? [],
    [entitiesData],
  );

  // Filter target entities: exclude selected source
  const targetEntities = useMemo(
    () => entities.filter((e) => e.id !== sourceEntityId),
    [entities, sourceEntityId],
  );

  const effectiveType = relType === "CUSTOM" ? customType.trim().toUpperCase() : relType;

  const resetForm = () => {
    setSourceEntityId(preSelectedSourceId ?? "");
    setTargetEntityId("");
    setRelType("");
    setCustomType("");
    setSourceAnnotation("");
    setError(null);
    setInfoMessage(null);
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) resetForm();
    onOpenChange(nextOpen);
  };

  // Sync source entity when preSelectedSourceId changes (e.g., opening from different entity card)
  useEffect(() => {
    if (open && preSelectedSourceId) {
      setSourceEntityId(preSelectedSourceId);
    }
  }, [open, preSelectedSourceId]);

  const isCustomTypeValid =
    relType !== "CUSTOM" || UPPER_SNAKE_RE.test(customType.trim().toUpperCase());

  const canSubmit =
    sourceEntityId &&
    targetEntityId &&
    sourceEntityId !== targetEntityId &&
    effectiveType &&
    isCustomTypeValid &&
    !createMutation.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfoMessage(null);

    if (!sourceEntityId || !targetEntityId) {
      setError("Both source and target entities are required");
      return;
    }
    if (sourceEntityId === targetEntityId) {
      setError("Source and target entities must be different");
      return;
    }
    if (!effectiveType) {
      setError("Relationship type is required");
      return;
    }
    if (relType === "CUSTOM" && !isCustomTypeValid) {
      setError(
        "Custom type must be UPPER_SNAKE_CASE (e.g., OWNS, FUNDS)",
      );
      return;
    }

    createMutation.mutate(
      {
        source_entity_id: sourceEntityId,
        target_entity_id: targetEntityId,
        type: effectiveType,
        source_annotation: sourceAnnotation.trim() || null,
      },
      {
        onSuccess: (data) => {
          if (data.already_existed) {
            setInfoMessage("This relationship already exists.");
          } else {
            handleOpenChange(false);
          }
        },
        onError: (err: unknown) => {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: unknown }).detail)
              : "Failed to create relationship";
          setError(detail);
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-[480px] bg-[var(--bg-elevated)] border-[var(--border-subtle)]">
        <DialogHeader>
          <DialogTitle className="text-[var(--text-primary)]">
            Add Relationship
          </DialogTitle>
          <DialogDescription className="text-[var(--text-secondary)]">
            Manually connect two entities in the knowledge graph.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Source Entity */}
          <div className="flex flex-col gap-2">
            <Label
              htmlFor="source-entity"
              className="text-[var(--text-secondary)]"
            >
              Source Entity
            </Label>
            <select
              id="source-entity"
              value={sourceEntityId}
              onChange={(e) => {
                setSourceEntityId(e.target.value);
                setError(null);
                setInfoMessage(null);
              }}
              disabled={createMutation.isPending}
              className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--text-muted)]"
            >
              <option value="">Select source entity...</option>
              {entities.map((entity) => (
                <option key={entity.id} value={entity.id}>
                  {entity.name} ({entity.type})
                </option>
              ))}
            </select>
          </div>

          {/* Target Entity */}
          <div className="flex flex-col gap-2">
            <Label
              htmlFor="target-entity"
              className="text-[var(--text-secondary)]"
            >
              Target Entity
            </Label>
            <select
              id="target-entity"
              value={targetEntityId}
              onChange={(e) => {
                setTargetEntityId(e.target.value);
                setError(null);
                setInfoMessage(null);
              }}
              disabled={createMutation.isPending}
              className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--text-muted)]"
            >
              <option value="">Select target entity...</option>
              {targetEntities.map((entity) => (
                <option key={entity.id} value={entity.id}>
                  {entity.name} ({entity.type})
                </option>
              ))}
            </select>
          </div>

          {/* Relationship Type */}
          <div className="flex flex-col gap-2">
            <Label className="text-[var(--text-secondary)]">
              Relationship Type
            </Label>
            <div className="flex flex-wrap gap-2">
              {RELATIONSHIP_TYPE_OPTIONS.map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => {
                    setRelType(opt);
                    setError(null);
                    setInfoMessage(null);
                  }}
                  aria-pressed={relType === opt}
                  className={`rounded-md border px-2.5 py-1 text-xs transition-colors ${
                    relType === opt
                      ? "border-[var(--text-primary)] bg-[var(--bg-hover)] text-[var(--text-primary)]"
                      : "border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
                  }`}
                >
                  {opt}
                </button>
              ))}
              <button
                type="button"
                onClick={() => {
                  setRelType("CUSTOM");
                  setError(null);
                  setInfoMessage(null);
                }}
                aria-pressed={relType === "CUSTOM"}
                className={`rounded-md border px-2.5 py-1 text-xs transition-colors ${
                  relType === "CUSTOM"
                    ? "border-[var(--text-primary)] bg-[var(--bg-hover)] text-[var(--text-primary)]"
                    : "border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
                }`}
              >
                Custom...
              </button>
            </div>
            {relType === "CUSTOM" && (
              <Input
                value={customType}
                onChange={(e) => {
                  setCustomType(e.target.value);
                  setError(null);
                }}
                placeholder="e.g., OWNS, FUNDS"
                disabled={createMutation.isPending}
                maxLength={50}
                className="border-[var(--border-subtle)] bg-[var(--bg-secondary)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
              />
            )}
          </div>

          {/* Source Annotation */}
          <div className="flex flex-col gap-2">
            <Label
              htmlFor="rel-source-annotation"
              className="text-[var(--text-secondary)]"
            >
              Evidence / Source Annotation
              <span className="text-[var(--text-muted)] ml-1">(optional)</span>
            </Label>
            <Textarea
              id="rel-source-annotation"
              value={sourceAnnotation}
              onChange={(e) => setSourceAnnotation(e.target.value)}
              placeholder="What evidence supports this relationship?"
              disabled={createMutation.isPending}
              maxLength={2000}
              rows={2}
              className="border-[var(--border-subtle)] bg-[var(--bg-secondary)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
            />
          </div>

          {error && (
            <p className="text-xs text-[var(--status-error)]">{error}</p>
          )}

          {infoMessage && (
            <p className="text-xs text-[var(--text-secondary)]">
              {infoMessage}
            </p>
          )}

          <Button
            type="submit"
            disabled={!canSubmit}
          >
            {createMutation.isPending
              ? "Creating..."
              : "Add Relationship"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
