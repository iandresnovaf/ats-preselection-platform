export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm">
        <h1 className="text-4xl font-bold mb-8 text-center">
          ATS Preselection Platform
        </h1>
        
        <p className="text-center text-muted-foreground mb-8">
          Plataforma de preselección automatizada de candidatos
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-2xl mx-auto">
          <a
            href="/config"
            className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100 hover:dark:border-neutral-700 hover:dark:bg-neutral-800/30"
          >
            <h2 className="mb-3 text-2xl font-semibold">
              Configuración
              <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
                -&gt;
              </span>
            </h2>
            <p className="m-0 max-w-[30ch] text-sm opacity-50">
              Configura las integraciones con WhatsApp, Zoho, LLM y Email.
            </p>
          </a>

          <a
            href="/api/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100 hover:dark:border-neutral-700 hover:dark:bg-neutral-800/30"
          >
            <h2 className="mb-3 text-2xl font-semibold">
              API Docs
              <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
                -&gt;
              </span>
            </h2>
            <p className="m-0 max-w-[30ch] text-sm opacity-50">
              Documentación interactiva de la API (Swagger UI).
            </p>
          </a>
        </div>

        <div className="mt-16 text-center text-sm text-muted-foreground">
          <p>Top Management - Tecnología e Innovación</p>
        </div>
      </div>
    </main>
  )
}
