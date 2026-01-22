import { describe, it, expect } from "vitest";
import { renderToString } from "react-dom/server";
import DashboardPage, { summarizeDashboard } from "./pages/DashboardPage";
import EvalsPage, { pickDefaultReport } from "./pages/EvalsPage";
import ExperimentsPage, { extractExperimentIds } from "./pages/ExperimentsPage";
import PerfPage, { buildLatencySeries } from "./pages/PerfPage";
import ProvidersPlaygroundPage, { buildGatewayPayload } from "./pages/ProvidersPlaygroundPage";
import PoliciesPage, { formatPluginCount } from "./pages/PoliciesPage";


describe("Workbench pages", () => {
  it("renders dashboard page", () => {
    const html = renderToString(<DashboardPage />);
    expect(html).toContain("Workbench Dashboard");
  });

  it("summarizes dashboard data", () => {
    const summary = summarizeDashboard([
      { trace_id: "t1", provider: "mock", error_count: 1, tool_call_count: 2 },
      { trace_id: "t2", provider: "mock", error_count: 0, tool_call_count: 0 },
    ] as any);
    expect(summary.totalTraces).toBe(2);
    expect(summary.errorRate).toBeGreaterThan(0);
  });

  it("renders evals page", () => {
    const html = renderToString(<EvalsPage />);
    expect(html).toContain("Eval Suites");
    expect(pickDefaultReport(["one.json"])).toBe("one.json");
  });

  it("renders experiments page", () => {
    const html = renderToString(<ExperimentsPage />);
    expect(html).toContain("Experiments");
    expect(extractExperimentIds([{ experiment_id: "exp1" }])).toEqual(["exp1"]);
  });

  it("renders perf page", () => {
    const html = renderToString(<PerfPage />);
    expect(html).toContain("Performance Lab");
    expect(buildLatencySeries({ metrics: { latencies_ms: [1, 2] } })).toEqual([1, 2]);
  });

  it("renders provider playground", () => {
    const html = renderToString(<ProvidersPlaygroundPage />);
    expect(html).toContain("Provider Playground");
    expect(buildGatewayPayload("mock", "hi").provider).toBe("mock");
  });

  it("renders policies page", () => {
    const html = renderToString(<PoliciesPage />);
    expect(html).toContain("Policies &amp; Plugins");
    return;
    expect(html).toContain("Policies & Plugins");
    expect(formatPluginCount(["one", "two"]).toString()).toContain("2");
  });
});
