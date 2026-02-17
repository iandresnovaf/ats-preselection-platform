/**
 * Tests para el componente MissingContactModal
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MissingContactModal } from '../MissingContactModal';

describe('MissingContactModal', () => {
  const mockCandidate = {
    candidate_id: '123',
    full_name: 'John Doe',
    email: undefined,
    phone: undefined,
  };

  const mockOnSubmit = jest.fn();
  const mockOnSkip = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render when isOpen is true', () => {
    render(
      <MissingContactModal
        isOpen={true}
        candidate={mockCandidate}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
      />
    );

    expect(screen.getByText('Datos de contacto incompletos')).toBeInTheDocument();
    expect(screen.getByText(/John Doe/)).toBeInTheDocument();
  });

  it('should not render when isOpen is false', () => {
    render(
      <MissingContactModal
        isOpen={false}
        candidate={mockCandidate}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
      />
    );

    expect(screen.queryByText('Datos de contacto incompletos')).not.toBeInTheDocument();
  });

  it('should show email input when email is missing', () => {
    render(
      <MissingContactModal
        isOpen={true}
        candidate={mockCandidate}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
      />
    );

    expect(screen.getByLabelText(/Correo electrónico/i)).toBeInTheDocument();
  });

  it('should show phone input when phone is missing', () => {
    render(
      <MissingContactModal
        isOpen={true}
        candidate={mockCandidate}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
      />
    );

    expect(screen.getByLabelText(/Teléfono/i)).toBeInTheDocument();
  });

  it('should not show email input when email exists', () => {
    const candidateWithEmail = {
      ...mockCandidate,
      email: 'john@example.com',
    };

    render(
      <MissingContactModal
        isOpen={true}
        candidate={candidateWithEmail}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
      />
    );

    expect(screen.queryByLabelText(/Correo electrónico/i)).not.toBeInTheDocument();
    expect(screen.getByText(/john@example.com/)).toBeInTheDocument();
  });

  it('should call onSkip when clicking Omitir', () => {
    render(
      <MissingContactModal
        isOpen={true}
        candidate={mockCandidate}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
      />
    );

    fireEvent.click(screen.getByText('Omitir por ahora'));
    expect(mockOnSkip).toHaveBeenCalled();
  });

  it('should validate email format', async () => {
    render(
      <MissingContactModal
        isOpen={true}
        candidate={mockCandidate}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
      />
    );

    const emailInput = screen.getByPlaceholderText('ejemplo@correo.com');
    fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
    fireEvent.click(screen.getByText('Guardar y continuar'));

    await waitFor(() => {
      expect(screen.getByText('Formato de email inválido')).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('should call onSubmit with valid data', async () => {
    render(
      <MissingContactModal
        isOpen={true}
        candidate={mockCandidate}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
      />
    );

    const emailInput = screen.getByPlaceholderText('ejemplo@correo.com');
    const phoneInput = screen.getByPlaceholderText('+1 234 567 8900');

    fireEvent.change(emailInput, { target: { value: 'john@example.com' } });
    fireEvent.change(phoneInput, { target: { value: '+1234567890' } });
    fireEvent.click(screen.getByText('Guardar y continuar'));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        email: 'john@example.com',
        phone: '+1234567890',
      });
    });
  });

  it('should show loading state when isLoading is true', () => {
    render(
      <MissingContactModal
        isOpen={true}
        candidate={mockCandidate}
        onSubmit={mockOnSubmit}
        onSkip={mockOnSkip}
        isLoading={true}
      />
    );

    expect(screen.getByText('Guardando...')).toBeInTheDocument();
    expect(screen.getByText('Omitir por ahora')).toBeDisabled();
  });
});
