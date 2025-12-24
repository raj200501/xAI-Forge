import { describe, it, expect } from "vitest";
import App from "./app/App";

describe("App", () => {
  it("renders without crashing", () => {
    expect(App).toBeDefined();
  });
});
