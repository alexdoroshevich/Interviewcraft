import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DiffView } from "../DiffView";
import type { DiffVersions } from "../LintCard";

const mockVersions: DiffVersions = {
  minimal: {
    text: "I led the migration of our monolith, reducing deploy time by 40%.",
    changes: [{ before: "we improved", after: "I reduced deploy time by 40%", rule: "missing_metrics", impact: "+10" }],
    estimated_new_score: 78,
  },
  medium: {
    text: "I led the migration from a monolith to microservices, reducing deploy time from 45 minutes to 27 minutes — a 40% improvement.",
    changes: [],
    estimated_new_score: 84,
  },
  ideal: {
    text: "I owned the migration of our monolith to 12 microservices at $company, cutting deploy time from 45 to 27 minutes (40%), enabling 3x more frequent releases and saving ~$15K/month in infrastructure costs.",
    changes: [],
    estimated_new_score: 91,
  },
};

describe("DiffView", () => {
  it("renders all three version tabs", () => {
    render(<DiffView diffVersions={mockVersions} originalScore={72} />);
    expect(screen.getAllByText("Minimal Patch").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Medium Rewrite").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Ideal Answer").length).toBeGreaterThan(0);
  });

  it("shows minimal version text by default", () => {
    render(<DiffView diffVersions={mockVersions} originalScore={72} />);
    expect(screen.getByText(/reducing deploy time by 40%/i)).toBeInTheDocument();
  });

  it("shows estimated score improvement", () => {
    render(<DiffView diffVersions={mockVersions} originalScore={72} />);
    // Minimal patch delta = +6 points
    expect(screen.getAllByText(/78/).length).toBeGreaterThan(0);
  });
});
