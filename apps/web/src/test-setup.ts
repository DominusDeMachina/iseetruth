import "@testing-library/jest-dom/vitest";

// Polyfill ResizeObserver for jsdom (required by cmdk)
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof globalThis.ResizeObserver;
}

// Polyfill Element.scrollIntoView for jsdom (required by cmdk)
if (typeof Element.prototype.scrollIntoView === "undefined") {
  Element.prototype.scrollIntoView = function () {};
}
