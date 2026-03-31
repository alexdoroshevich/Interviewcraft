import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SkillRadar, SkillList } from "../SkillRadar";
import type { SkillNodeResponse } from "@/lib/api";

// Recharts uses ResizeObserver — mock it for jsdom
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

const base = { evidence_links: [], typical_mistakes: [], last_practiced: null, next_review_due: null, created_at: "2024-01-01T00:00:00Z", updated_at: "2024-01-01T00:00:00Z" };
const mockNodes: SkillNodeResponse[] = [
  { ...base, id: "1", skill_name: "STAR Structure", skill_category: "behavioral", current_score: 72, trend: "improving", best_score: 80 },
  { ...base, id: "2", skill_name: "System Design Depth", skill_category: "system_design", current_score: 55, trend: "stable", best_score: 60 },
  { ...base, id: "3", skill_name: "Conciseness", skill_category: "communication", current_score: 68, trend: "declining", best_score: 75 },
];

describe("SkillRadar", () => {
  it("renders no-data message when nodes is empty", () => {
    render(<SkillRadar nodes={[]} />);
    expect(screen.getByText(/no skill data/i)).toBeInTheDocument();
  });
});

describe("SkillList", () => {
  it("renders skill list with names", () => {
    render(<SkillList nodes={mockNodes} />);
    expect(screen.getByText("STAR Structure")).toBeInTheDocument();
    expect(screen.getByText("System Design Depth")).toBeInTheDocument();
    expect(screen.getByText("Conciseness")).toBeInTheDocument();
  });
});
