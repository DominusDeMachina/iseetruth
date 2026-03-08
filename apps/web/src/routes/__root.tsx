import { createRootRoute, Link, Outlet } from "@tanstack/react-router";
import { lazy } from "react";
import { StatusBar } from "@/components/layout/StatusBar";
import { ViewportWarning } from "@/components/layout/ViewportWarning";

const TanStackRouterDevtools = import.meta.env.DEV
  ? lazy(() =>
      import("@tanstack/react-router-devtools").then((mod) => ({
        default: mod.TanStackRouterDevtools,
      }))
    )
  : () => null;

export const Route = createRootRoute({
  component: () => (
    <div className="grid min-h-[100dvh] grid-rows-[auto_1fr_auto_auto] bg-[var(--bg-primary)]">
      <header className="flex items-center border-b border-[var(--border-subtle)] px-6 py-4">
        <Link to="/" className="text-xl font-bold text-[var(--text-primary)] hover:text-[var(--text-secondary)] transition-colors">
          OSINT
        </Link>
      </header>
      <main className="p-6">
        <Outlet />
      </main>
      <ViewportWarning />
      <StatusBar />
      <TanStackRouterDevtools />
    </div>
  ),
});
