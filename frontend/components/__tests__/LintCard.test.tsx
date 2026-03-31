import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { LintCard } from "../LintCard";
import type { SegmentScore } from "../LintCard";

// Minimal mock — LintCard uses router internally via RewindPanel
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const mockScore: SegmentScore = {
  id: "seg-1",
  session_id: "sess-1",
  segment_index: 0,
  question_text: "Tell me about a time you led a project.",
  overall_score: 72,
  confidence: "high",
  category_scores: { structure: 70, depth: 75, communication: 80, seniority_signal: 60 },
  rules_triggered: [
    {
      rule: "missing_metrics",
      confidence: "strong",
      evidence: { start_ms: 5000, end_ms: 8000, server_extracted_quote: "we improved performance" },
      fix: "Add quantified outcome",
      impact: "+10 structure",
    },
  ],
  level_assessment: { l4: "pass", l5: "borderline", l6: "fail", gaps: ["Add tradeoff discussion"] },
  diff_versions: null,
  rewind_count: 0,
  best_rewind_score: null,
};

describe("LintCard", () => {
  it("renders overall score", () => {
    render(<LintCard score={mockScore} />);
    expect(screen.getByText("72")).toBeInTheDocument();
  });

  it("renders triggered rule name", () => {
    render(<LintCard score={mockScore} />);
    // rule name appears in both the rule row and the coaching section
    expect(screen.getAllByText(/missing metrics/i).length).toBeGreaterThan(0);
  });

  it("renders rule impact", () => {
    render(<LintCard score={mockScore} />);
    expect(screen.getByText("+10 structure")).toBeInTheDocument();
  });

  it("renders level badges", () => {
    render(<LintCard score={mockScore} />);
    expect(screen.getByText("L4")).toBeInTheDocument();
    expect(screen.getByText("L5")).toBeInTheDocument();
    expect(screen.getByText("L6")).toBeInTheDocument();
  });
});
