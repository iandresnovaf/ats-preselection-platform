import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FileUpload } from '@/components/ui/file-upload';

describe('FileUpload', () => {
  const mockOnFileSelect = jest.fn();
  const mockOnFileRemove = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders upload area correctly', () => {
    render(
      <FileUpload 
        onFileSelect={mockOnFileSelect}
      />
    );

    expect(screen.getByText(/Arrastra y suelta tu PDF aquí/i)).toBeInTheDocument();
    expect(screen.getByText(/o haz clic para seleccionar archivo/i)).toBeInTheDocument();
    expect(screen.getByText(/Máximo 10 MB/i)).toBeInTheDocument();
  });

  it('accepts file selection via click', async () => {
    render(
      <FileUpload 
        onFileSelect={mockOnFileSelect}
      />
    );

    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = screen.getByLabelText(/Upload PDF file/i).querySelector('input') || 
                  document.querySelector('input[type="file"]');

    if (input) {
      fireEvent.change(input, { target: { files: [file] } });

      await waitFor(() => {
        expect(mockOnFileSelect).toHaveBeenCalledWith(file);
      });
    }
  });

  it('validates file type', async () => {
    const { container } = render(
      <FileUpload 
        onFileSelect={mockOnFileSelect}
        accept=".pdf"
      />
    );

    const invalidFile = new File(['test content'], 'test.jpg', { type: 'image/jpeg' });
    const input = container.querySelector('input[type="file"]');

    if (input) {
      fireEvent.change(input, { target: { files: [invalidFile] } });

      await waitFor(() => {
        expect(screen.getByText(/Solo se permiten archivos PDF/i)).toBeInTheDocument();
      });
    }
  });

  it('validates file size', async () => {
    const { container } = render(
      <FileUpload 
        onFileSelect={mockOnFileSelect}
        maxSize={1024} // 1KB
      />
    );

    const largeFile = new File(['x'.repeat(2048)], 'large.pdf', { type: 'application/pdf' });
    const input = container.querySelector('input[type="file"]');

    if (input) {
      fireEvent.change(input, { target: { files: [largeFile] } });

      await waitFor(() => {
        expect(screen.getByText(/El archivo es demasiado grande/i)).toBeInTheDocument();
      });
    }
  });

  it('displays selected file correctly', () => {
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    
    render(
      <FileUpload 
        onFileSelect={mockOnFileSelect}
        selectedFile={file}
        onFileRemove={mockOnFileRemove}
      />
    );

    expect(screen.getByText('test.pdf')).toBeInTheDocument();
    expect(screen.getByText('10 Bytes')).toBeInTheDocument();
  });

  it('displays upload progress correctly', () => {
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    
    render(
      <FileUpload 
        onFileSelect={mockOnFileSelect}
        selectedFile={file}
        uploading={true}
        uploadProgress={50}
      />
    );

    expect(screen.getByText(/Subiendo/i)).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '50');
  });

  it('calls onFileRemove when remove button is clicked', () => {
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    
    render(
      <FileUpload 
        onFileSelect={mockOnFileSelect}
        selectedFile={file}
        onFileRemove={mockOnFileRemove}
      />
    );

    const removeButton = screen.getByLabelText(/Remove file/i);
    fireEvent.click(removeButton);

    expect(mockOnFileRemove).toHaveBeenCalled();
  });

  it('displays uploaded state correctly', () => {
    render(
      <FileUpload 
        onFileSelect={mockOnFileSelect}
        uploadedUrl="https://example.com/file.pdf"
        onFileRemove={mockOnFileRemove}
      />
    );

    expect(screen.getByText(/Archivo PDF subido/i)).toBeInTheDocument();
    expect(screen.getByText(/Subido correctamente/i)).toBeInTheDocument();
  });

  it('is disabled when disabled prop is true', () => {
    const { container } = render(
      <FileUpload 
        onFileSelect={mockOnFileSelect}
        disabled={true}
      />
    );

    const uploadArea = screen.getByLabelText(/Upload PDF file/i);
    expect(uploadArea).toHaveClass('opacity-50');
    expect(uploadArea).toHaveClass('cursor-not-allowed');
  });

  it('handles drag and drop events', () => {
    const { container } = render(
      <FileUpload 
        onFileSelect={mockOnFileSelect}
      />
    );

    const uploadArea = screen.getByLabelText(/Upload PDF file/i);
    
    // Simulate drag over
    fireEvent.dragOver(uploadArea);
    expect(uploadArea).toHaveClass('border-primary');

    // Simulate drag leave
    fireEvent.dragLeave(uploadArea);
  });

  it('has correct ARIA attributes', () => {
    render(
      <FileUpload 
        onFileSelect={mockOnFileSelect}
      />
    );

    expect(screen.getByLabelText(/Upload PDF file/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/File input/i)).toHaveAttribute('type', 'file');
  });
});
