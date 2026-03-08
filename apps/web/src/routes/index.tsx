import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  component: Index,
});

function Index() {
  return (
    <div>
      <h2 className="text-2xl font-semibold">Investigations</h2>
      <p className="mt-2 text-muted-foreground">
        Welcome to the OSINT Document Analyzer. Select or create an
        investigation to get started.
      </p>
    </div>
  );
}
