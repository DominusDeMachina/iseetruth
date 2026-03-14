# Re-enabling TanStack Devtools

The TanStack Router and React Query devtools were removed from the UI. To bring them back:

## React Query Devtools

In `src/main.tsx`, add the import and component:

```tsx
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
```

Then inside the `<QueryClientProvider>`:

```tsx
<QueryClientProvider client={queryClient}>
  <RouterProvider router={router} />
  {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
</QueryClientProvider>
```

Options: `initialIsOpen`, `position` (`"bottom"` | `"top"`), `buttonPosition` (`"bottom-left"` | `"bottom-right"` | `"top-left"` | `"top-right"`).

## TanStack Router Devtools

In `src/routes/__root.tsx`, add the lazy import:

```tsx
import { lazy } from "react";

const TanStackRouterDevtools = import.meta.env.DEV
  ? lazy(() =>
      import("@tanstack/react-router-devtools").then((mod) => ({
        default: mod.TanStackRouterDevtools,
      }))
    )
  : () => null;
```

Then add `<TanStackRouterDevtools />` inside the root component JSX.

Options: `initialIsOpen`, `position` (`"bottom-left"` | `"bottom-right"` | `"top-left"` | `"top-right"`).

Both devtools only render in development mode (`import.meta.env.DEV`).
