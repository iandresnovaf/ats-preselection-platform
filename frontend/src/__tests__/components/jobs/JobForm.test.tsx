import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import JobForm from '@/components/jobs/JobForm';
import { JobOpening } from '@/types/jobs';

const mockJob: JobOpening = {
  id: '1',
  title: 'Senior Software Engineer',
  description: 'We are looking for a talented engineer',
  department: 'Engineering',
  location: 'Remote',
  seniority: 'Senior',
  sector: 'Technology',
  status: 'active',
  created_by: 'user1',
  required_skills: ['React', 'TypeScript'],
  min_years_experience: 3,
  education_level: 'bachelor',
  employment_type: 'full-time',
  salary_min: 80000,
  salary_max: 120000,
  created_at: '2024-01-01',
  updated_at: '2024-01-01',
};

const mockOnSubmit = jest.fn();
const mockOnCancel = jest.fn();

describe('JobForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders create form correctly', () => {
    render(
      <JobForm 
        onSubmit={mockOnSubmit} 
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText('Nueva Oferta')).toBeInTheDocument();
    expect(screen.getByLabelText(/Título/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Descripción/i)).toBeInTheDocument();
    expect(screen.getByText('Job Description (PDF)')).toBeInTheDocument();
  });

  it('renders edit form with job data', () => {
    render(
      <JobForm 
        job={mockJob}
        onSubmit={mockOnSubmit} 
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText('Editar Oferta')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Senior Software Engineer')).toBeInTheDocument();
    expect(screen.getByDisplayValue('We are looking for a talented engineer')).toBeInTheDocument();
  });

  it('validates required fields', async () => {
    render(
      <JobForm 
        onSubmit={mockOnSubmit} 
        onCancel={mockOnCancel}
      />
    );

    const submitButton = screen.getByRole('button', { name: /Crear Oferta/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('El título es requerido')).toBeInTheDocument();
      expect(screen.getByText('La descripción es requerida')).toBeInTheDocument();
    });
  });

  it('validates salary range', async () => {
    render(
      <JobForm 
        onSubmit={mockOnSubmit} 
        onCancel={mockOnCancel}
      />
    );

    const minSalaryInput = screen.getByPlaceholderText('Mínimo');
    const maxSalaryInput = screen.getByPlaceholderText('Máximo');

    await userEvent.type(minSalaryInput, '100000');
    await userEvent.type(maxSalaryInput, '50000');

    const submitButton = screen.getByRole('button', { name: /Crear Oferta/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/El salario máximo debe ser mayor o igual al mínimo/i)).toBeInTheDocument();
    });
  });

  it('allows adding skills via TagsInput', async () => {
    render(
      <JobForm 
        onSubmit={mockOnSubmit} 
        onCancel={mockOnCancel}
      />
    );

    const skillsInput = screen.getByPlaceholderText(/Ej: React, Python, AWS/i);
    await userEvent.type(skillsInput, 'JavaScript');
    fireEvent.keyDown(skillsInput, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(screen.getByText('javascript')).toBeInTheDocument();
    });
  });

  it('submits form with correct data', async () => {
    render(
      <JobForm 
        onSubmit={mockOnSubmit} 
        onCancel={mockOnCancel}
      />
    );

    await userEvent.type(screen.getByLabelText(/Título/i), 'Test Job');
    await userEvent.type(screen.getByLabelText(/Descripción/i), 'Test Description');
    
    // Select department
    const departmentSelect = screen.getByLabelText(/Departamento/i);
    fireEvent.click(departmentSelect);
    await waitFor(() => {
      fireEvent.click(screen.getByText('Engineering'));
    });

    await userEvent.type(screen.getByLabelText(/Ubicación/i), 'Remote');

    // Select seniority
    const senioritySelect = screen.getByLabelText(/Nivel de Seniority/i);
    fireEvent.click(senioritySelect);
    await waitFor(() => {
      fireEvent.click(screen.getByText('Senior'));
    });

    // Select sector
    const sectorSelect = screen.getByLabelText(/Sector/i);
    fireEvent.click(sectorSelect);
    await waitFor(() => {
      fireEvent.click(screen.getByText('Technology'));
    });

    const submitButton = screen.getByRole('button', { name: /Crear Oferta/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalled();
    });
  });

  it('calls onCancel when cancel button is clicked', () => {
    render(
      <JobForm 
        onSubmit={mockOnSubmit} 
        onCancel={mockOnCancel}
      />
    );

    const cancelButton = screen.getByRole('button', { name: /Cancelar/i });
    fireEvent.click(cancelButton);

    expect(mockOnCancel).toHaveBeenCalled();
  });

  it('disables form when isLoading is true', () => {
    render(
      <JobForm 
        onSubmit={mockOnSubmit} 
        onCancel={mockOnCancel}
        isLoading={true}
      />
    );

    expect(screen.getByRole('button', { name: /Guardando/i })).toBeDisabled();
  });

  it('has correct ARIA attributes for accessibility', () => {
    render(
      <JobForm 
        onSubmit={mockOnSubmit} 
        onCancel={mockOnCancel}
      />
    );

    const titleInput = screen.getByLabelText(/Título/i);
    expect(titleInput).toHaveAttribute('aria-invalid', 'false');
    
    // Trigger validation error
    const submitButton = screen.getByRole('button', { name: /Crear Oferta/i });
    fireEvent.click(submitButton);

    waitFor(() => {
      expect(titleInput).toHaveAttribute('aria-invalid', 'true');
      expect(titleInput).toHaveAttribute('aria-describedby', 'title-error');
    });
  });
});
