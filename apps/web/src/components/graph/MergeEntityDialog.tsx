import { useCallback, useEffect, useRef, useState } from "react";
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
import {
  useMergeEntitiesPreview,
  useMergeEntities,
} from "@/hooks/useEntityMutations";
import { useSearchEntities } from "@/hooks/useSearchEntities";
import { ENTITY_COLORS } from "@/lib/entity-constants";
import type { EntityListItem } from "@/hooks/useEntities";
import type { components } from "@/lib/api-types.generated";

type EntityMergePreview = components["schemas"]["EntityMergePreview"];

interface MergeEntityDialogProps {
  investigationId: string;
  sourceEntityId: string;
  sourceEntityName: string;
  sourceEntityType: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type Step = "select" | "preview" | "confirm";

export function MergeEntityDialog({
  investigationId,
  sourceEntityId,
  sourceEntityName,
  sourceEntityType,
  open,
  onOpenChange,
}: MergeEntityDialogProps) {
  const [step, setStep] = useState<Step>("select");
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedTarget, setSelectedTarget] = useState<EntityListItem | null>(
    null,
  );
  const [preview, setPreview] = useState<EntityMergePreview | null>(null);
  const [primaryName, setPrimaryName] = useState<string>("target");
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  const previewMutation = useMergeEntitiesPreview(investigationId);
  const mergeMutation = useMergeEntities(investigationId);

  // Debounce search input by 200ms
  useEffect(() => {
    timerRef.current = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 200);
    return () => clearTimeout(timerRef.current);
  }, [searchQuery]);

  const { data: searchResults, isLoading: searchLoading } = useSearchEntities(
    investigationId,
    debouncedQuery,
  );

  // Filter results: same type, exclude source entity
  const filteredResults = searchResults.filter(
    (e) => e.id !== sourceEntityId && e.type === sourceEntityType,
  );

  const resetDialog = useCallback(() => {
    setStep("select");
    setSearchQuery("");
    setDebouncedQuery("");
    setSelectedTarget(null);
    setPreview(null);
    setPrimaryName("target");
    setError(null);
  }, []);

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) resetDialog();
    onOpenChange(nextOpen);
  };

  const handleSelectTarget = (entity: EntityListItem) => {
    setSelectedTarget(entity);
    setError(null);

    // Fetch preview
    previewMutation.mutate(
      {
        source_entity_id: sourceEntityId,
        target_entity_id: entity.id,
      },
      {
        onSuccess: (data) => {
          setPreview(data);
          setStep("preview");
        },
        onError: (err: unknown) => {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: unknown }).detail)
              : "Failed to generate merge preview";
          setError(detail);
        },
      },
    );
  };

  const handleConfirm = () => {
    if (!selectedTarget) return;
    setError(null);

    const chosenName =
      primaryName === "source" ? sourceEntityName : selectedTarget.name;

    mergeMutation.mutate(
      {
        source_entity_id: sourceEntityId,
        target_entity_id: selectedTarget.id,
        primary_name: chosenName,
      },
      {
        onSuccess: () => {
          handleOpenChange(false);
        },
        onError: (err: unknown) => {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: unknown }).detail)
              : "Failed to merge entities";
          setError(detail);
        },
      },
    );
  };

  const sourceColor =
    ENTITY_COLORS[
      sourceEntityType.charAt(0).toUpperCase() + sourceEntityType.slice(1)
    ] ?? "#888";

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-[520px] bg-[var(--bg-elevated)] border-[var(--border-subtle)]">
        <DialogHeader>
          <DialogTitle className="text-[var(--text-primary)]">
            Merge Entity
          </DialogTitle>
          <DialogDescription className="text-[var(--text-secondary)]">
            {step === "select" &&
              `Select an entity to merge "${sourceEntityName}" into.`}
            {step === "preview" && "Review the merge before confirming."}
          </DialogDescription>
        </DialogHeader>

        {/* Step 1: Search and select target entity */}
        {step === "select" && (
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-3 py-2 text-sm">
              <span
                className="inline-block size-2 rounded-full shrink-0"
                style={{ backgroundColor: sourceColor }}
              />
              <span className="text-[var(--text-primary)] font-medium">
                {sourceEntityName}
              </span>
              <span className="text-[var(--text-muted)] text-xs">
                (source - will be removed)
              </span>
            </div>

            <div className="flex flex-col gap-2">
              <Label
                htmlFor="merge-search"
                className="text-[var(--text-secondary)]"
              >
                Merge into
              </Label>
              <Input
                id="merge-search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={`Search ${sourceEntityType} entities...`}
                className="border-[var(--border-subtle)] bg-[var(--bg-secondary)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
              />
            </div>

            {debouncedQuery.trim().length >= 2 && (
              <div className="max-h-[200px] overflow-y-auto rounded-md border border-[var(--border-subtle)]">
                {searchLoading && (
                  <div className="py-4 text-center text-sm text-[var(--text-muted)]">
                    Searching...
                  </div>
                )}
                {!searchLoading && filteredResults.length === 0 && (
                  <div className="py-4 text-center text-sm text-[var(--text-muted)]">
                    No matching {sourceEntityType} entities found
                  </div>
                )}
                {filteredResults.map((entity) => (
                  <button
                    key={entity.id}
                    type="button"
                    onClick={() => handleSelectTarget(entity)}
                    disabled={previewMutation.isPending}
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--bg-hover)] transition-colors text-left"
                  >
                    <span
                      className="inline-block size-2 rounded-full shrink-0"
                      style={{ backgroundColor: sourceColor }}
                    />
                    <span className="flex-1 truncate text-[var(--text-primary)]">
                      {entity.name}
                    </span>
                    <span className="text-xs text-[var(--text-muted)]">
                      {Math.round(entity.confidence_score * 100)}%
                    </span>
                  </button>
                ))}
              </div>
            )}

            {previewMutation.isPending && (
              <p className="text-xs text-[var(--text-muted)]">
                Loading preview...
              </p>
            )}

            {error && (
              <p className="text-xs text-[var(--status-error)]">{error}</p>
            )}
          </div>
        )}

        {/* Step 2: Preview merge */}
        {step === "preview" && preview && selectedTarget && (
          <div className="flex flex-col gap-4">
            {/* Side-by-side comparison */}
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-md border border-[var(--border-subtle)] p-3">
                <p className="text-xs text-[var(--text-muted)] mb-1">
                  Source (will be removed)
                </p>
                <p className="text-sm font-medium text-[var(--text-primary)]">
                  {sourceEntityName}
                </p>
                <p className="text-xs text-[var(--text-secondary)] mt-1">
                  {preview.source_entity.relationships.length} relationships
                </p>
                <p className="text-xs text-[var(--text-secondary)]">
                  {preview.source_entity.sources.length} sources
                </p>
              </div>
              <div className="rounded-md border border-[var(--border-subtle)] p-3">
                <p className="text-xs text-[var(--text-muted)] mb-1">
                  Target (will be kept)
                </p>
                <p className="text-sm font-medium text-[var(--text-primary)]">
                  {selectedTarget.name}
                </p>
                <p className="text-xs text-[var(--text-secondary)] mt-1">
                  {preview.target_entity.relationships.length} relationships
                </p>
                <p className="text-xs text-[var(--text-secondary)]">
                  {preview.target_entity.sources.length} sources
                </p>
              </div>
            </div>

            {/* Merge summary */}
            <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-3">
              <p className="text-xs font-medium text-[var(--text-secondary)] mb-2">
                After merge
              </p>
              <div className="space-y-1 text-xs text-[var(--text-primary)]">
                <p>
                  {preview.total_relationships_after} total relationships
                </p>
                <p>{preview.total_sources_after} total sources</p>
                {preview.duplicate_relationships.length > 0 && (
                  <p className="text-[var(--text-muted)]">
                    {preview.duplicate_relationships.length} duplicate
                    relationship(s) will be consolidated:{" "}
                    {preview.duplicate_relationships.join(", ")}
                  </p>
                )}
              </div>
            </div>

            {/* Name selection */}
            <div className="flex flex-col gap-2">
              <Label className="text-[var(--text-secondary)]">
                Primary name
              </Label>
              <div className="flex flex-col gap-1.5">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="primary-name"
                    value="target"
                    checked={primaryName === "target"}
                    onChange={() => setPrimaryName("target")}
                    className="accent-[var(--text-primary)]"
                  />
                  <span className="text-sm text-[var(--text-primary)]">
                    {selectedTarget.name}
                  </span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="primary-name"
                    value="source"
                    checked={primaryName === "source"}
                    onChange={() => setPrimaryName("source")}
                    className="accent-[var(--text-primary)]"
                  />
                  <span className="text-sm text-[var(--text-primary)]">
                    {sourceEntityName}
                  </span>
                </label>
              </div>
              <p className="text-xs text-[var(--text-muted)]">
                The other name will be saved as an alias.
              </p>
            </div>

            {error && (
              <p className="text-xs text-[var(--status-error)]">{error}</p>
            )}

            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setStep("select");
                  setSelectedTarget(null);
                  setPreview(null);
                  setError(null);
                }}
                disabled={mergeMutation.isPending}
                className="flex-1"
              >
                Back
              </Button>
              <Button
                onClick={handleConfirm}
                disabled={mergeMutation.isPending}
                className="flex-1"
              >
                {mergeMutation.isPending ? "Merging..." : "Confirm Merge"}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
