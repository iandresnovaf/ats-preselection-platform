import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QuickActionsPanel } from "@/components/tracking/QuickActionsPanel";
import type { TrackedCandidate } from "@/types/tracking";

const mockPendingCandidates: TrackedCandidate[] = [
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
  {
    id: "c2",
    first_name: "María",
    last_name: "López",
    email: "maria@example.com",
    status: "pending_contact",
    role_id: "role-1",
    role_title: "Developer",
    client_name: "Tech Corp",
    source: "email",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    is_missing_contact: false,
  },
];

const mockNoResponseCandidates: TrackedCandidate[] = [
  {
    id: "c3",
    first_name: "Pedro",
    last_name: "Sánchez",
    email: "pedro@example.com",
    status: "no_response",
    role_id: "role-1",
    role_title: "Developer",
    client_name: "Tech Corp",
    source: "linkedin",
    days_without_response: 3,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    is_missing_contact: false,
  },
];

describe("QuickActionsPanel", () => {
  const defaultProps = {
    pendingCandidates: mockPendingCandidates,
    noResponseCandidates: mockNoResponseCandidates,
    onContactPending: jest.fn(),
    onResendNoResponse: jest.fn(),
    onViewReport: jest.fn(),
    isLoading: false,
  };

  it("renders all action buttons", () => {
    render(<QuickActionsPanel {...defaultProps} />);

    expect(screen.getByText("Contactar pendientes")).toBeInTheDocument();
    expect(screen.getByText("Reenviar a sin respuesta")).toBeInTheDocument();
    expect(screen.getByText("Ver reporte")).toBeInTheDocument();
  });

  it("displays correct candidate counts", () => {
    render(<QuickActionsPanel {...defaultProps} />);

    expect(screen.getByText("2")).toBeInTheDocument(); // Pending count
    expect(screen.getByText("1")).toBeInTheDocument(); // No response count
  });

  it("disables contact button when no pending candidates", () => {
    render(
      <QuickActionsPanel
        {...defaultProps}
        pendingCandidates={[]}
      />
    );

    const button = screen.getByRole("button", { name: /Contactar pendientes/i });
    expect(button).toBeDisabled();
  });

  it("opens contact dialog when clicking contact button", async () => {
    render(<QuickActionsPanel {...defaultProps} />);

    fireEvent.click(screen.getByText("Contactar pendientes"));

    await waitFor(() => {
      expect(screen.getByText("Contactar candidatos pendientes")).toBeInTheDocument();
    });
  });

  it("calls onContactPending when confirming contact", async () => {
    render(<QuickActionsPanel {...defaultProps} />);

    // Open dialog
    fireEvent.click(screen.getByText("Contactar pendientes"));

    await waitFor(() => {
      expect(screen.getByText("Enviar a 2 candidatos")).toBeInTheDocument();
    });

    // Click send button
    fireEvent.click(screen.getByText("Enviar a 2 candidatos"));

    await waitFor(() => {
      expect(defaultProps.onContactPending).toHaveBeenCalledWith(
        ["c1", "c2"],
        "email",
        undefined
      );
    });
  });

  it("allows selecting specific channel for contact", async () => {
    render(<QuickActionsPanel {...defaultProps} />);

    fireEvent.click(screen.getByText("Contactar pendientes"));

    await waitFor(() => {
      expect(screen.getByText("Canal de contacto")).toBeInTheDocument();
    });
  });

  it("calls onViewReport when clicking view report button", () => {
    render(<QuickActionsPanel {...defaultProps} />);

    fireEvent.click(screen.getByText("Ver reporte"));
    expect(defaultProps.onViewReport).toHaveBeenCalled();
  });

  it("shows warning when many pending candidates", () => {
    const manyPending = Array.from({ length: 10 }, (_, i) => ({
      ...mockPendingCandidates[0],
      id: `c${i}`,
    }));

    render(
      <QuickActionsPanel
        {...defaultProps}
        pendingCandidates={manyPending}
      />
    );

    expect(screen.getByText("10")).toHaveClass("bg-destructive");
  });

  it("disables buttons when isLoading is true", () => {
    render(<QuickActionsPanel {...defaultProps} isLoading={true} />);

    expect(screen.getByRole("button", { name: /Contactar pendientes/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Reenviar a sin respuesta/i })).toBeDisabled();
  });
});
