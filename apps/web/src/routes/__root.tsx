import { createRootRoute, Outlet } from "@tanstack/react-router";
import { StatusBar } from "@/components/layout/StatusBar";
import { ViewportWarning } from "@/components/layout/ViewportWarning";
import { ServiceNotifications } from "@/components/layout/ServiceNotifications";
import { useSystemSSE } from "@/hooks/useSystemSSE";

function RootLayout() {
  const { notifications, dismissNotification } = useSystemSSE();

  return (
    <div className="grid h-[100dvh] grid-rows-[1fr_auto_auto] bg-[var(--bg-primary)]">
      <main className="overflow-auto px-6 pt-6">
        <Outlet />
      </main>
      <ViewportWarning />
      <StatusBar />
      <ServiceNotifications
        notifications={notifications}
        onDismiss={dismissNotification}
      />
    </div>
  );
}

export const Route = createRootRoute({
  component: RootLayout,
});
