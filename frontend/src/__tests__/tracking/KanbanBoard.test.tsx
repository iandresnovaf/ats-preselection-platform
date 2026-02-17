import { render, screen, fireEvent } from "@testing-library/react";
import { KanbanBoard } from "@/components/tracking/KanbanBoard";
import type { TrackedCandidate, ApplicationStatus } from "@/types/tracking";

const mockCandidates: Record<ApplicationStatus, TrackedCandidate[]> = {
  pending_contact: [
    {
      id: "c1",
      first_name: "Juan",
      last_name: "Pérez",
      email: "juan@example.com",
      status: "pending_contact",
      role_id: "role-1",
      role_title: "Developer",
      client_name: "Tech Corp",
      source: "linkedin",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      is_missing_contact: false,
    },
  ],
  contacted: [
    {
      id: "c2",
      first_name: "María",
      last_name: "López",
      email: "maria@example.com",
      status: "contacted",
      role_id: "role-1",
      role_title: "Developer",
      client_name: "Tech Corp",
      source: "linkedin",
      last_contact_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      is_missing_contact: false,
    },
  ],
  interested: [
    {
      id: "c3",
      first_name: "Ana",
      last_name: "Gómez",
      email: "ana@example.com",
      status: "interested",
      role_id: "role-1",
      role_title: "Developer",
      client_name: "Tech Corp",
      source: "referral",
      response_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      is_missing_contact: false,
    },
  ],
  not_interested: [],
  no_response: [
    {
      id: "c4",
      first_name: "Pedro",
      last_name: "Sánchez",
      email: "pedro@example.com",
      status: "no_response",
      role_id: "role-1",
      role_title: "Developer",
      client_name: "Tech Corp",
      source: "email",
      days_without_response: 3,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      is_missing_contact: false,
    },
  ],
  scheduled: [],
  completed: [],
  hired: [],
};

describe("KanbanBoard", () => {
  it("renders all columns by default", () => {
    render(<KanbanBoard candidates={mockCandidates} />);

    // Use getAllByText since there are filter buttons with same text
    expect(screen.getAllByText("Pendiente").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Contactado").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Interesado").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Sin Respuesta").length).toBeGreaterThan(0);
  });

  it("displays correct candidate counts in columns", () => {
    render(<KanbanBoard candidates={mockCandidates} />);

    // Check that candidate counts are displayed - look for the "1" count in the column
    // The Pending column should have count 1
    expect(screen.getByText("Juan Pérez")).toBeInTheDocument();
  });

  it("displays candidate names in correct columns", () => {
    render(<KanbanBoard candidates={mockCandidates} />);

    expect(screen.getByText("Juan Pérez")).toBeInTheDocument();
    expect(screen.getByText("María López")).toBeInTheDocument();
    expect(screen.getByText("Ana Gómez")).toBeInTheDocument();
    expect(screen.getByText("Pedro Sánchez")).toBeInTheDocument();
  });

  it("calls onCandidateClick when candidate is clicked", () => {
    const handleClick = jest.fn();
    render(<KanbanBoard candidates={mockCandidates} onCandidateClick={handleClick} />);

    fireEvent.click(screen.getByText("Juan Pérez"));
    expect(handleClick).toHaveBeenCalledWith(mockCandidates.pending_contact[0]);
  });

  it("shows missing contact warning for pending candidates without email", () => {
    const candidatesWithMissing = {
      ...mockCandidates,
      pending_contact: [
        {
          ...mockCandidates.pending_contact[0],
          email: undefined,
          is_missing_contact: true,
        },
      ],
    };
    render(<KanbanBoard candidates={candidatesWithMissing} />);

    expect(screen.getByText("Falta email/teléfono")).toBeInTheDocument();
  });

  it("shows days without response indicator", () => {
    render(<KanbanBoard candidates={mockCandidates} />);

    expect(screen.getByText("3 días sin resp.")).toBeInTheDocument();
  });

  it("filters columns when a column button is clicked", () => {
    render(<KanbanBoard candidates={mockCandidates} />);

    // Get all Interesado buttons and click the first one (the filter button)
    const interesadoButtons = screen.getAllByRole("button", { name: /Interesado/i });
    fireEvent.click(interesadoButtons[0]);

    // Should only show the interested column
    expect(screen.queryByText("Juan Pérez")).not.toBeInTheDocument();
    expect(screen.getByText("Ana Gómez")).toBeInTheDocument();
  });

  it("calls onContactClick when contact button is clicked", () => {
    const handleContact = jest.fn();
    render(
      <KanbanBoard
        candidates={mockCandidates}
        onCandidateClick={jest.fn()}
        onContactClick={handleContact}
      />
    );

    // Find and click the contact button in the pending column
    const contactButtons = screen.getAllByRole("button", { name: /Contactar/i });
    fireEvent.click(contactButtons[0]);

    expect(handleContact).toHaveBeenCalledWith(mockCandidates.pending_contact[0]);
  });
});
