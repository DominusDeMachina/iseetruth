import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/investigations/$id")({
  component: InvestigationDetail,
});

function InvestigationDetail() {
  const { id } = Route.useParams();
  return (
    <div>
      <h2 className="text-2xl font-semibold">Investigation {id}</h2>
      <p className="mt-2 text-muted-foreground">
        Investigation detail view placeholder.
      </p>
    </div>
  );
}
