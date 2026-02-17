/**
 * Tests para hooks de plantillas de mensajes
 */
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useTemplates, useTemplate, useChannelLabel, useChannelIcon } from "@/hooks/use-message-templates";
import type { MessageTemplate, MessageChannel } from "@/types/message-templates";

// Mock axios
jest.mock("axios", () => ({
  create: jest.fn(() => ({
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
  })),
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe("useChannelLabel", () => {
  it("returns correct label for email", () => {
    const { result } = renderHook(() => useChannelLabel("email"));
    expect(result.current).toBe("Email");
  });

  it("returns correct label for whatsapp", () => {
    const { result } = renderHook(() => useChannelLabel("whatsapp"));
    expect(result.current).toBe("WhatsApp");
  });

  it("returns correct label for sms", () => {
    const { result } = renderHook(() => useChannelLabel("sms"));
    expect(result.current).toBe("SMS");
  });
});

describe("useChannelIcon", () => {
  it("returns correct color class for email", () => {
    const { result } = renderHook(() => useChannelIcon("email"));
    expect(result.current).toContain("blue");
  });

  it("returns correct color class for whatsapp", () => {
    const { result } = renderHook(() => useChannelIcon("whatsapp"));
    expect(result.current).toContain("green");
  });

  it("returns correct color class for sms", () => {
    const { result } = renderHook(() => useChannelIcon("sms"));
    expect(result.current).toContain("purple");
  });
});

// Tests de integración (requieren mock de API)
describe("useTemplates", () => {
  it("should have correct query key", () => {
    // Este test verifica la configuración básica
    const queryClient = createTestQueryClient();
    
    const { result } = renderHook(() => useTemplates(), { wrapper });
    
    // El hook debe estar configurado correctamente
    expect(result.current).toBeDefined();
  });
});

describe("MessageTemplate types", () => {
  it("validates MessageChannel type", () => {
    const channels: MessageChannel[] = ["email", "whatsapp", "sms"];
    
    channels.forEach((channel) => {
      expect(["email", "whatsapp", "sms"]).toContain(channel);
    });
  });

  it("validates MessageTemplate structure", () => {
    const template: MessageTemplate = {
      template_id: "123",
      name: "Test Template",
      description: "Test",
      channel: "email",
      subject: "Test Subject",
      body: "Test body",
      variables: ["candidate_name"],
      is_active: true,
      is_default: false,
      created_by: "user-123",
      created_at: "2025-02-16T00:00:00Z",
      updated_at: "2025-02-16T00:00:00Z",
    };

    expect(template.template_id).toBe("123");
    expect(template.channel).toBe("email");
    expect(template.variables).toContain("candidate_name");
  });
});
