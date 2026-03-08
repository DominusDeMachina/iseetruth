import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/investigations/$id")({
  component: InvestigationDetail,
});

function InvestigationDetail() {
  const { id } = Route.useParams();
  return (
    <div className="flex flex-col items-center justify-center gap-4 pt-24">
      <h2 className="text-2xl font-semibold text-[var(--text-primary)]">
        Investigation {id}
      </h2>
      <p className="text-sm text-[var(--text-secondary)]">
        Investigation detail view — Coming in Epic 2
      </p>
    </div>
  );
}
