import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, Upload } from "lucide-react";
import { useInvestigation } from "@/hooks/useInvestigations";

export const Route = createFileRoute("/investigations/$id")({
  component: InvestigationDetail,
});

function InvestigationDetail() {
  const { id } = Route.useParams();
  const { data: investigation, isLoading, isError } = useInvestigation(id);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <div className="animate-pulse">
          <div className="h-7 w-1/3 rounded bg-[var(--bg-hover)]" />
          <div className="mt-2 h-4 w-1/2 rounded bg-[var(--bg-hover)]" />
        </div>
      </div>
    );
  }

  if (isError || !investigation) {
    return (
      <div className="flex flex-col items-center gap-4 pt-12 text-center">
        <p className="text-[var(--text-primary)]">Investigation not found</p>
        <Link
          to="/"
          className="text-sm text-[var(--status-info)] hover:underline"
        >
          Back to investigations
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          to="/"
          className="mb-2 inline-flex items-center gap-1 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
        >
          <ArrowLeft className="size-3" />
          Investigations
        </Link>
        <h2 className="text-xl font-semibold text-[var(--text-primary)]">
          {investigation.name}
        </h2>
        {investigation.description && (
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            {investigation.description}
          </p>
        )}
      </div>

      <div className="flex flex-col items-center gap-4 rounded-xl border border-dashed border-[var(--border-subtle)] bg-[var(--bg-secondary)] py-16 text-center">
        <Upload className="size-8 text-[var(--text-muted)]" />
        <p className="text-[var(--text-secondary)]">
          Upload documents to begin your investigation
        </p>
        <p className="text-sm text-[var(--text-muted)]">
          PDF upload coming in Story 2.2
        </p>
      </div>
    </div>
  );
}
