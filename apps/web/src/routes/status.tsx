import { createFileRoute } from "@tanstack/react-router";
import { SystemStatusPage } from "@/components/status/SystemStatusPage";

export const Route = createFileRoute("/status")({
  component: SystemStatusPage,
});
