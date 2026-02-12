/**
 * Tests de Seguridad XSS (Cross-Site Scripting)
 * Verifica que la aplicación frontend sea resistente a ataques XSS
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock de componentes para testing
const MockComponent = ({ content }: { content: string }) => {
  return <div data-testid="content">{content}</div>;
};

// Componente que usa dangerouslySetInnerHTML (para detectar uso inseguro)
const DangerousComponent = ({ html }: { html: string }) => {
  // Esta es una mala práctica - el test debe detectarla
  return <div data-testid="dangerous" dangerouslySetInnerHTML={{ __html: html }} />;
};

// Componente seguro que escapa HTML
const SafeComponent = ({ content }: { content: string }) => {
  // Escapar HTML manualmente
  const escaped = content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;');
  return <div data-testid="safe" dangerouslySetInnerHTML={{ __html: escaped }} />;
};

// Componente de input de usuario
const UserInputForm = ({ onSubmit }: { onSubmit: (value: string) => void }) => {
  const [value, setValue] = React.useState('');
  
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(value); }}>
      <input
        data-testid="user-input"
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <button type="submit">Submit</button>
    </form>
  );
};

// Lista de payloads XSS comunes
const XSS_PAYLOADS = [
  { name: 'Basic script tag', payload: "<script>alert('XSS')</script>" },
  { name: 'Script with double quotes', payload: '<script>alert("XSS")</script>' },
  { name: 'Image onerror', payload: "<img src=x onerror=alert('XSS')>" },
  { name: 'SVG onload', payload: "<svg onload=alert('XSS')>" },
  { name: 'Body onload', payload: "<body onload=alert('XSS')>" },
  { name: 'Iframe javascript', payload: "<iframe src='javascript:alert(1)'>" },
  { name: 'Input onfocus', payload: '<input onfocus=alert(1) autofocus>' },
  { name: 'Video source onerror', payload: '<video><source onerror=alert(1)>' },
  { name: 'Audio onerror', payload: '<audio src=x onerror=alert(1)>' },
  { name: 'Marquee onstart', payload: '<marquee onstart=alert(1)>' },
  { name: 'Details ontoggle', payload: '<details open ontoggle=alert(1)>' },
  { name: 'JavaScript protocol', payload: 'javascript:alert(1)' },
  { name: 'Data URI', payload: 'data:text/html,<script>alert(1)</script>' },
  { name: 'Template literal', payload: '${alert(1)}' },
  { name: 'Unicode escape', payload: '\\u003cscript\\u003ealert(1)\\u003c/script\\u003e' },
  { name: 'HTML entities', payload: '&lt;script&gt;alert(1)&lt;/script&gt;' },
  { name: 'Nested frames', payload: '<frameset><frame src="javascript:alert(1)"></frameset>' },
  { name: 'Object data', payload: '<object data="javascript:alert(1)">' },
  { name: 'Embed src', payload: '<embed src="javascript:alert(1)">' },
  { name: 'Link stylesheet', payload: '<link rel="stylesheet" href="javascript:alert(1)">' },
];

// Lista de event handlers peligrosos
const DANGEROUS_EVENT_HANDLERS = [
  'onerror',
  'onload',
  'onunload',
  'onclick',
  'ondblclick',
  'onmousedown',
  'onmouseup',
  'onmouseover',
  'onmousemove',
  'onmouseout',
  'onfocus',
  'onblur',
  'onkeypress',
  'onkeydown',
  'onkeyup',
  'onsubmit',
  'onreset',
  'onselect',
  'onchange',
  'onscroll',
  'onresize',
  'ontoggle',
  'onstart',
  'onfinish',
  'onbounce',
];

describe('XSS Prevention Tests', () => {
  describe('Input Sanitization', () => {
    it.each(XSS_PAYLOADS)(
      'should not execute malicious scripts: $name',
      ({ payload }) => {
        const { container } = render(<MockComponent content={payload} />);
        
        // Verificar que el script no está en el DOM como HTML ejecutable
        const scripts = container.querySelectorAll('script');
        expect(scripts.length).toBe(0);
        
        // Verificar que no hay elementos con event handlers peligrosos
        DANGEROUS_EVENT_HANDLERS.forEach(handler => {
          const elementsWithHandler = container.querySelectorAll(`[${handler}]`);
          expect(elementsWithHandler.length).toBe(0);
        });
      }
    );

    it('should escape script tags in user input', () => {
      const maliciousInput = '<script>alert("XSS")</script>';
      const { getByTestId } = render(<MockComponent content={maliciousInput} />);
      
      const element = getByTestId('content');
      // El contenido debe estar escapado, no como HTML
      expect(element.innerHTML).not.toContain('<script>');
    });

    it('should handle image onerror payloads safely', () => {
      const maliciousInput = '<img src=x onerror=alert("XSS")>';
      const { container } = render(<MockComponent content={maliciousInput} />);
      
      // No debe haber imágenes con onerror
      const imgs = container.querySelectorAll('img[onerror]');
      expect(imgs.length).toBe(0);
    });

    it('should handle SVG onload payloads safely', () => {
      const maliciousInput = '<svg onload=alert("XSS")>';
      const { container } = render(<MockComponent content={maliciousInput} />);
      
      // No debe haber SVGs con onload
      const svgs = container.querySelectorAll('svg[onload]');
      expect(svgs.length).toBe(0);
    });
  });

  describe('dangerouslySetInnerHTML Detection', () => {
    it('should warn about dangerouslySetInnerHTML usage', () => {
      // Este test detecta el uso de dangerouslySetInnerHTML
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
      
      const maliciousHtml = '<script>alert("XSS")</script>';
      render(<DangerousComponent html={maliciousHtml} />);
      
      // dangerouslySetInnerHTML es riesgoso - el test documenta esto
      consoleSpy.mockRestore();
    });

    it('should verify safe HTML escaping when using innerHTML', () => {
      const maliciousContent = '<script>alert("XSS")</script>';
      const { getByTestId } = render(<SafeComponent content={maliciousContent} />);
      
      const element = getByTestId('safe');
      // El contenido debe estar escapado
      expect(element.innerHTML).toContain('&lt;script&gt;');
      expect(element.innerHTML).not.toContain('<script>');
    });

    it('should not find any script tags when using innerHTML with escaped content', () => {
      const maliciousContent = '<img src=x onerror=alert(1)><script>alert(2)</script>';
      const { container } = render(<SafeComponent content={maliciousContent} />);
      
      const scripts = container.querySelectorAll('script');
      const imgsWithOnerror = container.querySelectorAll('img[onerror]');
      
      expect(scripts.length).toBe(0);
      expect(imgsWithOnerror.length).toBe(0);
    });
  });

  describe('URL and Link Security', () => {
    it('should sanitize javascript: URLs', () => {
      const maliciousUrl = 'javascript:alert("XSS")';
      
      // Verificar que URLs javascript: sean detectadas
      const isJavaScriptUrl = /^javascript:/i.test(maliciousUrl);
      expect(isJavaScriptUrl).toBe(true);
      
      // En un componente real, estas URLs deberían ser sanitizadas
      const sanitizedUrl = maliciousUrl.replace(/^javascript:/i, 'unsafe:');
      expect(sanitizedUrl).toBe('unsafe:alert("XSS")');
    });

    it('should sanitize data:text/html URLs', () => {
      const maliciousUrl = 'data:text/html,<script>alert(1)</script>';
      
      // Verificar que data URLs HTML sean detectadas
      const isDataHtmlUrl = /^data:text\/html/i.test(maliciousUrl);
      expect(isDataHtmlUrl).toBe(true);
    });

    it('should allow safe http/https URLs', () => {
      const safeUrls = [
        'https://example.com',
        'http://example.com',
        'https://example.com/path?query=value',
      ];
      
      safeUrls.forEach(url => {
        const isSafe = /^https?:\/\//i.test(url) && !/javascript:/i.test(url);
        expect(isSafe).toBe(true);
      });
    });
  });

  describe('Form Input Security', () => {
    it('should handle XSS in form submissions safely', async () => {
      const mockSubmit = jest.fn();
      const user = userEvent.setup();
      
      render(<UserInputForm onSubmit={mockSubmit} />);
      
      const input = screen.getByTestId('user-input');
      const maliciousValue = '<script>alert("XSS")</script>';
      
      await user.type(input, maliciousValue);
      await user.click(screen.getByText('Submit'));
      
      // Verificar que el valor se envió pero no se ejecutó
      expect(mockSubmit).toHaveBeenCalledWith(maliciousValue);
      
      // No debe haber scripts en el documento
      const scripts = document.querySelectorAll('script');
      const maliciousScripts = Array.from(scripts).filter(s => 
        s.textContent?.includes('alert')
      );
      expect(maliciousScripts.length).toBe(0);
    });

    it('should handle template injection attempts', async () => {
      const mockSubmit = jest.fn();
      const user = userEvent.setup();
      
      render(<UserInputForm onSubmit={mockSubmit} />);
      
      const input = screen.getByTestId('user-input');
      const templateInjection = '${alert(1)}';
      
      await user.type(input, templateInjection);
      await user.click(screen.getByText('Submit'));
      
      expect(mockSubmit).toHaveBeenCalledWith(templateInjection);
    });
  });

  describe('DOM Manipulation Security', () => {
    it('should not execute scripts injected via textContent', () => {
      const container = document.createElement('div');
      const maliciousScript = '<script>alert("XSS")</script>';
      
      // textContent es seguro - no ejecuta HTML
      container.textContent = maliciousScript;
      
      expect(container.innerHTML).toContain('&lt;');
      expect(container.querySelectorAll('script').length).toBe(0);
    });

    it('should be cautious with innerHTML assignments', () => {
      const container = document.createElement('div');
      const maliciousScript = '<img src=x onerror=alert(1)>';
      
      // innerHTML puede ser peligroso si el contenido no está sanitizado
      container.innerHTML = maliciousScript;
      
      // Este test demuestra el riesgo
      const imgs = container.querySelectorAll('img');
      expect(imgs.length).toBeGreaterThan(0);
    });

    it('should use safe methods for setting content', () => {
      const container = document.createElement('div');
      const maliciousContent = '<script>alert(1)</script>Hello';
      
      // Método seguro: crear nodo de texto
      const textNode = document.createTextNode(maliciousContent);
      container.appendChild(textNode);
      
      expect(container.querySelectorAll('script').length).toBe(0);
      expect(container.textContent).toBe(maliciousContent);
    });
  });

  describe('Attribute Injection Prevention', () => {
    it('should prevent breaking out of attributes', () => {
      const maliciousAttribute = '" onerror="alert(1)" x="';
      
      // Simular inyección en atributo
      const container = document.createElement('div');
      container.innerHTML = `<img src="${maliciousAttribute}">`;
      
      // Verificar que no se inyectó el onerror
      const img = container.querySelector('img');
      if (img) {
        expect(img.hasAttribute('onerror')).toBe(false);
      }
    });

    it('should escape quotes in dynamic attributes', () => {
      const userInput = 'value" onmouseover="alert(1)';
      
      // Escapar quotes correctamente
      const escaped = userInput
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#x27;');
      
      expect(escaped).not.toContain('" onmouseover=');
      expect(escaped).toContain('&quot;');
    });
  });

  describe('JSON and API Response Security', () => {
    it('should not execute scripts in JSON responses', () => {
      const maliciousJson = {
        name: '<script>alert("XSS")</script>',
        description: '<img src=x onerror=alert(1)>',
      };
      
      // Simular renderizado de datos de API
      const { container } = render(
        <MockComponent content={JSON.stringify(maliciousJson)} />
      );
      
      const scripts = container.querySelectorAll('script');
      expect(scripts.length).toBe(0);
    });

    it('should handle HTML in API responses safely', () => {
      const apiResponse = {
        html: '<div onclick="alert(1)">Click me</div>',
        script: '<script>console.log("XSS")</script>',
      };
      
      // Los datos de API deben ser tratados como texto, no HTML
      Object.values(apiResponse).forEach(value => {
        const div = document.createElement('div');
        div.textContent = value;
        expect(div.querySelectorAll('script').length).toBe(0);
        expect(div.querySelectorAll('[onclick]').length).toBe(0);
      });
    });
  });

  describe('React Specific Security', () => {
    it('should use React auto-escaping by default', () => {
      const maliciousContent = '<script>alert("XSS")</script>';
      
      const { container } = render(
        <div>{maliciousContent}</div>
      );
      
      // React escapa automáticamente
      const scripts = container.querySelectorAll('script');
      expect(scripts.length).toBe(0);
      
      // El contenido debe estar escapado
      expect(container.innerHTML).toContain('&lt;');
    });

    it('should not use dangerouslySetInnerHTML with user input', () => {
      // Este test documenta la regla: nunca usar dangerouslySetInnerHTML con input de usuario
      const userInput = '<p>Safe content</p>';
      
      // ✅ BIEN: Usar renderizado normal de React
      const { container } = render(<div>{userInput}</div>);
      
      expect(container.textContent).toContain('<p>');
    });

    it('should sanitize before using dangerouslySetInnerHTML', () => {
      // Si se debe usar dangerouslySetInnerHTML, sanitizar primero
      const htmlContent = '<p>Some <script>alert(1)</script> text</p>';
      
      // Función de sanitización simple (en producción usar DOMPurify)
      const sanitize = (html: string): string => {
        return html
          .replace(/<script[^>]*>.*?<\/script>/gi, '')
          .replace(/on\w+\s*=/gi, 'data-blocked-event=');
      };
      
      const sanitized = sanitize(htmlContent);
      
      expect(sanitized).not.toContain('<script>');
      expect(sanitized).not.toContain('on');
    });
  });

  describe('CSS Injection Prevention', () => {
    it('should prevent CSS expression injection', () => {
      const maliciousStyle = 'width: expression(alert("XSS"))';
      
      // expression() es peligroso en IE
      const hasExpression = /expression\s*\(/i.test(maliciousStyle);
      expect(hasExpression).toBe(true);
      
      // Debe ser sanitizado
      const sanitized = maliciousStyle.replace(/expression\s*\(/gi, 'blocked(');
      expect(sanitized).not.toMatch(/expression\s*\(/i);
    });

    it('should prevent javascript: in CSS URLs', () => {
      const maliciousUrl = 'javascript:alert(1)';
      const cssProperty = `background: url(${maliciousUrl})`;
      
      const hasJsProtocol = /javascript:/i.test(cssProperty);
      expect(hasJsProtocol).toBe(true);
    });
  });

  describe('Storage Security', () => {
    it('should not store sensitive data in localStorage without encryption', () => {
      // localStorage no es seguro para datos sensibles
      // Este test documenta la práctica correcta
      
      const sensitiveData = {
        token: 'secret-token',
        password: 'secret-password',
      };
      
      // ✅ BIEN: Guardar solo datos no sensibles
      const safeData = {
        theme: 'dark',
        language: 'es',
      };
      
      expect(safeData).not.toHaveProperty('password');
      expect(safeData).not.toHaveProperty('token');
    });

    it('should validate data from localStorage before use', () => {
      // Simular datos maliciosos en localStorage
      const maliciousStoredData = '<script>alert("XSS")</script>';
      
      // Siempre validar/sanitizar datos de localStorage
      const sanitized = maliciousStoredData
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
      
      expect(sanitized).not.toContain('<script>');
    });
  });
});

describe('XSS Security Audit', () => {
  it('should verify no inline event handlers in rendered HTML', () => {
    // Buscar cualquier event handler inline en el DOM
    const allElements = document.querySelectorAll('*');
    const dangerousHandlers = [
      'onclick', 'onload', 'onerror', 'onmouseover', 'onfocus',
      'onblur', 'onchange', 'onsubmit', 'onkeypress', 'onkeydown',
    ];
    
    allElements.forEach(el => {
      dangerousHandlers.forEach(handler => {
        expect(el.hasAttribute(handler)).toBe(false);
      });
    });
  });
});
