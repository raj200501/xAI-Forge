import { describe, it, expect, vi, beforeEach } from "vitest";
import { act } from "react-dom/test-utils";
import { createRoot } from "react-dom/client";
import App from "./app/App";


describe("App routes", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve([]),
        }),
      ) as unknown as typeof fetch,
    );
  });

  it("switches routes via sidebar", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    act(() => {
      root.render(<App />);
    });
    const buttons = Array.from(container.querySelectorAll("nav button"));
    const dashboardButton = buttons.find((btn) => btn.textContent === "Dashboard");
    expect(dashboardButton).toBeTruthy();
    act(() => {
      dashboardButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    expect(container.textContent).toContain("Workbench Dashboard");
  });
});
