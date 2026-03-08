import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Trash2, FileText } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardAction,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DeleteConfirmationDialog } from "./DeleteConfirmationDialog";
import { useDeleteInvestigation } from "@/hooks/useInvestigations";
import type { Investigation } from "@/hooks/useInvestigations";

interface InvestigationCardProps {
  investigation: Investigation;
}

export function InvestigationCard({ investigation }: InvestigationCardProps) {
  const [deleteOpen, setDeleteOpen] = useState(false);
  const navigate = useNavigate();
  const deleteMutation = useDeleteInvestigation();

  const handleClick = () => {
    navigate({ to: "/investigations/$id", params: { id: investigation.id } });
  };

  const handleDelete = () => {
    deleteMutation.mutate(investigation.id, {
      onSuccess: () => setDeleteOpen(false),
    });
  };

  const createdDate = new Date(investigation.created_at).toLocaleDateString(
    undefined,
    { year: "numeric", month: "short", day: "numeric" },
  );

  return (
    <>
      <Card
        className="cursor-pointer border-[var(--border-subtle)] bg-[var(--bg-elevated)] transition-colors hover:bg-[var(--bg-hover)]"
        onClick={handleClick}
      >
        <CardHeader>
          <CardTitle className="text-lg text-[var(--text-primary)]">
            {investigation.name}
          </CardTitle>
          <CardAction>
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={(e) => {
                e.stopPropagation();
                setDeleteOpen(true);
              }}
              className="text-[var(--text-muted)] hover:text-[var(--status-error)]"
              aria-label="Delete investigation"
            >
              <Trash2 />
            </Button>
          </CardAction>
          {investigation.description && (
            <CardDescription className="line-clamp-2 text-[var(--text-secondary)]">
              {investigation.description}
            </CardDescription>
          )}
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 text-sm text-[var(--text-muted)]">
            <span>{createdDate}</span>
            <span className="flex items-center gap-1">
              <FileText className="size-3" />
              {investigation.document_count}
            </span>
          </div>
        </CardContent>
      </Card>

      <DeleteConfirmationDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        investigationName={investigation.name}
        onConfirm={handleDelete}
        isPending={deleteMutation.isPending}
      />
    </>
  );
}
