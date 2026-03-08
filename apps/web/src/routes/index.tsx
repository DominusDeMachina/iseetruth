import { createFileRoute } from "@tanstack/react-router";
import { InvestigationList } from "@/components/investigation/InvestigationList";

export const Route = createFileRoute("/")({
  component: Index,
});

function Index() {
  return <InvestigationList />;
}
