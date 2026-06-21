import { describe, expect, it } from "vitest";
import { formatCount, formatPercent } from "./format";

describe("formatters", () => {
  it("formats large counts compactly", () => {
    expect(formatCount(1_000_000)).toMatch(/1M/);
  });

  it("formats fractional rates as percentages", () => {
    expect(formatPercent(0.875)).toBe("88%");
  });
});

