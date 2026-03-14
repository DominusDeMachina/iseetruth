import { useCallback, useEffect, useRef, useState } from "react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { useSearchEntities } from "@/hooks/useSearchEntities";
import { ENTITY_COLORS } from "@/lib/entity-constants";
import type { EntityListItem } from "@/hooks/useEntities";

interface EntitySearchCommandProps {
  investigationId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectEntity: (entity: EntityListItem) => void;
}

const TYPE_LABELS: Record<string, string> = {
  person: "People",
  organization: "Organizations",
  location: "Locations",
};

export function EntitySearchCommand({
  investigationId,
  open,
  onOpenChange,
  onSelectEntity,
}: EntitySearchCommandProps) {
  const [inputValue, setInputValue] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  // Debounce input by 200ms
  useEffect(() => {
    timerRef.current = setTimeout(() => {
      setDebouncedQuery(inputValue);
    }, 200);
    return () => clearTimeout(timerRef.current);
  }, [inputValue]);

  // Reset input when dialog closes
  useEffect(() => {
    if (!open) {
      setInputValue("");
      setDebouncedQuery("");
    }
  }, [open]);

  const { data: results, isLoading } = useSearchEntities(
    investigationId,
    debouncedQuery,
  );

  // Group results by entity type
  const grouped = results.reduce<Record<string, EntityListItem[]>>(
    (acc, item) => {
      const type = item.type;
      if (!acc[type]) acc[type] = [];
      acc[type].push(item);
      return acc;
    },
    {},
  );

  const handleSelect = useCallback(
    (entityId: string) => {
      const entity = results.find((e) => e.id === entityId);
      if (entity) {
        onSelectEntity(entity);
        onOpenChange(false);
      }
    },
    [results, onSelectEntity, onOpenChange],
  );

  const hasQuery = debouncedQuery.trim().length >= 2;

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange} shouldFilter={false}>
      <CommandInput
        placeholder="Search entities by name..."
        value={inputValue}
        onValueChange={setInputValue}
      />
      <CommandList>
        {hasQuery && isLoading && (
          <div className="py-6 text-center text-sm text-[var(--text-muted)]">
            Searching…
          </div>
        )}
        {hasQuery && !isLoading && results.length === 0 && (
          <CommandEmpty>No entities matching &apos;{debouncedQuery}&apos;</CommandEmpty>
        )}
        {!hasQuery && (
          <div className="py-6 text-center text-sm text-[var(--text-muted)]">
            Type to search entities
          </div>
        )}
        {Object.entries(grouped).map(([type, items]) => {
          const color = ENTITY_COLORS[type.charAt(0).toUpperCase() + type.slice(1)] ?? "#888";
          const label = TYPE_LABELS[type] ?? type;
          return (
            <CommandGroup
              key={type}
              heading={
                <span className="flex items-center gap-1.5">
                  <span
                    className="inline-block h-2 w-2 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  {label}
                </span>
              }
            >
              {items.map((entity) => (
                <CommandItem
                  key={entity.id}
                  value={entity.id}
                  onSelect={handleSelect}
                >
                  <span
                    className="inline-block h-2 w-2 shrink-0 rounded-full"
                    style={{
                      backgroundColor:
                        ENTITY_COLORS[
                          entity.type.charAt(0).toUpperCase() + entity.type.slice(1)
                        ] ?? "#888",
                    }}
                  />
                  <span className="flex-1 truncate">{entity.name}</span>
                  <span className="text-xs text-[var(--text-muted)]">
                    {Math.round(entity.confidence_score * 100)}%
                  </span>
                  <span className="text-xs text-[var(--text-muted)]">
                    {entity.source_count} src
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          );
        })}
      </CommandList>
    </CommandDialog>
  );
}
