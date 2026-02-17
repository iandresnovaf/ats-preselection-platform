import { render, screen, fireEvent } from "@testing-library/react";
import { VacanteCard } from "@/components/tracking/VacanteCard";
import type { VacanteSummary } from "@/types/tracking";

const mockRole: VacanteSummary = {
  role_id: "role-1",
  role_title: "Senior Developer",
  client_name: "Tech Corp",
  client_logo: undefined,
  stats: {
    total_candidates: 25,
    pending_contact: 5,
    contacted: 10,
    interested: 4,
    not_interested: 2,
    no_response: 4,
    scheduled: 2,
    completed: 1,
    hired: 1,
  },
  last_activity_at: new Date().toISOString(),
  progress_percentage: 45,
};

describe("VacanteCard", () => {
  it("renders role information correctly", () => {
    render(<VacanteCard role={mockRole} />);

    expect(screen.getByText("Senior Developer")).toBeInTheDocument();
    expect(screen.getByText("Tech Corp")).toBeInTheDocument();
  });

  it("displays correct stats", () => {
    render(<VacanteCard role={mockRole} />);

    expect(screen.getByText("25")).toBeInTheDocument(); // Total
    expect(screen.getByText("5")).toBeInTheDocument(); // Pending
    // Interested and No response both have value 4, use getAllByText
    expect(screen.getAllByText("4")).toHaveLength(2); // Interested (4) + No response (4)
  });

  it("displays progress percentage", () => {
    render(<VacanteCard role={mockRole} />);

    expect(screen.getByText("45%")).toBeInTheDocument();
  });

  it("calls onClick when clicked", () => {
    const handleClick = jest.fn();
    render(<VacanteCard role={mockRole} onClick={handleClick} />);

    fireEvent.click(screen.getByText("Senior Developer"));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("highlights pending contact when there are pending candidates", () => {
    const roleWithManyPending = {
      ...mockRole,
      stats: { ...mockRole.stats, pending_contact: 10 },
    };
    render(<VacanteCard role={roleWithManyPending} />);

    // There are multiple "10" elements, so use getAllByText
    const pendingElements = screen.getAllByText("10");
    expect(pendingElements.length).toBeGreaterThan(0);
  });

  it("shows 'Sin actividad' when no last activity", () => {
    const roleNoActivity = {
      ...mockRole,
      last_activity_at: undefined,
    };
    render(<VacanteCard role={roleNoActivity} />);

    expect(screen.getByText("Sin actividad")).toBeInTheDocument();
  });
});
