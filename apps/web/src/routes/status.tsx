import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/status")({
  component: Status,
});

function Status() {
  return (
    <div>
      <h2 className="text-2xl font-semibold">System Status</h2>
      <p className="mt-2 text-muted-foreground">
        System status page placeholder.
      </p>
    </div>
  );
}
