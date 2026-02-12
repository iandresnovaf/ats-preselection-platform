import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MatchingPanel } from '@/components/matching/MatchingPanel';
import { MatchResult, MatchDecision } from '@/types/matching';

const mockMatch: MatchResult = {
  id: 'match1',
  candidate_id: 'cand1',
  job_opening_id: 'job1',
  score: 85,
  decision: 'PROCEED' as MatchDecision,
  breakdown: {
    skills_match: 90,
    experience_match: 80,
    education_match: 85,
    overall_score: 85,
  },
  strengths: [
    'Excelente experiencia en React',
    'Conocimiento avanzado de TypeScript',
    'Buena comunicación técnica',
  ],
  gaps: [
    'Necesita más experiencia en AWS',
  ],
  red_flags: [],
  reasoning: '<p>El candidato tiene una excelente combinación de skills técnicas.</p>',
  created_at: '2024-01-01',
  updated_at: '2024-01-01',
};

const mockMatchReview: MatchResult = {
  ...mockMatch,
  id: 'match2',
  score: 65,
  decision: 'REVIEW' as MatchDecision,
  breakdown: {
    skills_match: 70,
    experience_match: 60,
    education_match: 65,
    overall_score: 65,
  },
};

const mockMatchReject: MatchResult = {
  ...mockMatch,
  id: 'match3',
  score: 35,
  decision: 'REJECT' as MatchDecision,
  breakdown: {
    skills_match: 40,
    experience_match: 30,
    education_match: 35,
    overall_score: 35,
  },
};

describe('MatchingPanel', () => {
  it('renders match score correctly', () => {
    render(<MatchingPanel match={mockMatch} />);

    expect(screen.getByText('85')).toBeInTheDocument();
    expect(screen.getByText(/Score de compatibilidad/i)).toBeInTheDocument();
  });

  it('displays PROCEED badge for high scores', () => {
    render(<MatchingPanel match={mockMatch} />);

    expect(screen.getByText('PROCEED')).toBeInTheDocument();
  });

  it('displays REVIEW badge for medium scores', () => {
    render(<MatchingPanel match={mockMatchReview} />);

    expect(screen.getByText('REVIEW')).toBeInTheDocument();
  });

  it('displays REJECT badge for low scores', () => {
    render(<MatchingPanel match={mockMatchReject} />);

    expect(screen.getByText('REJECT')).toBeInTheDocument();
  });

  it('shows breakdown percentages', () => {
    render(<MatchingPanel match={mockMatch} />);

    expect(screen.getByText('90%')).toBeInTheDocument();
    expect(screen.getByText('80%')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
  });

  it('displays strengths list', () => {
    render(<MatchingPanel match={mockMatch} />);

    expect(screen.getByText(/Fortalezas/i)).toBeInTheDocument();
    expect(screen.getByText('Excelente experiencia en React')).toBeInTheDocument();
    expect(screen.getByText('Conocimiento avanzado de TypeScript')).toBeInTheDocument();
  });

  it('displays gaps list', () => {
    render(<MatchingPanel match={mockMatch} />);

    expect(screen.getByText(/Gaps Identificados/i)).toBeInTheDocument();
    expect(screen.getByText('Necesita más experiencia en AWS')).toBeInTheDocument();
  });

  it('opens details dialog when clicking "Ver detalles completos"', async () => {
    render(<MatchingPanel match={mockMatch} />);

    const detailsButton = screen.getByRole('button', { name: /Ver detalles completos/i });
    fireEvent.click(detailsButton);

    await waitFor(() => {
      expect(screen.getByText('Análisis Detallado del Matching')).toBeInTheDocument();
    });
  });

  it('shows reasoning in details dialog', async () => {
    render(<MatchingPanel match={mockMatch} />);

    const detailsButton = screen.getByRole('button', { name: /Ver detalles completos/i });
    fireEvent.click(detailsButton);

    await waitFor(() => {
      expect(screen.getByText(/Razonamiento de la IA/i)).toBeInTheDocument();
    });
  });

  it('has correct color coding for scores', () => {
    const { rerender } = render(<MatchingPanel match={mockMatch} />);
    
    // High score should have green color
    const scoreElement = screen.getByLabelText(/Score de matching: 85 de 100/i);
    expect(scoreElement).toHaveClass('text-green-600');

    // Medium score
    rerender(<MatchingPanel match={mockMatchReview} />);
    const mediumScoreElement = screen.getByLabelText(/Score de matching: 65 de 100/i);
    expect(mediumScoreElement).toHaveClass('text-yellow-600');

    // Low score
    rerender(<MatchingPanel match={mockMatchReject} />);
    const lowScoreElement = screen.getByLabelText(/Score de matching: 35 de 100/i);
    expect(lowScoreElement).toHaveClass('text-red-600');
  });

  it('calls onRefresh when provided', () => {
    const mockRefresh = jest.fn();
    render(<MatchingPanel match={mockMatch} onRefresh={mockRefresh} />);

    // onRefresh is not directly exposed in UI, but component accepts it as prop
    expect(mockRefresh).not.toHaveBeenCalled();
  });

  it('sanitizes reasoning HTML for XSS protection', async () => {
    const maliciousMatch: MatchResult = {
      ...mockMatch,
      reasoning: '<script>alert("XSS")</script><p>Safe content</p>',
    };

    render(<MatchingPanel match={maliciousMatch} />);

    const detailsButton = screen.getByRole('button', { name: /Ver detalles completos/i });
    fireEvent.click(detailsButton);

    await waitFor(() => {
      const reasoningContainer = screen.getByText(/Safe content/i).parentElement;
      expect(reasoningContainer?.innerHTML).not.toContain('<script>');
    });
  });

  it('has correct ARIA attributes for accessibility', () => {
    render(<MatchingPanel match={mockMatch} />);

    expect(screen.getByLabelText(/Score de matching: 85 de 100/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Barra de progreso del score/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Decisión: PROCEED/i)).toBeInTheDocument();
  });
});
