import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Rutas protegidas por rol - usando roles correctos del backend
const protectedRoutes = {
  '/config': ['super_admin'],
  '/users': ['super_admin'],
  '/dashboard': ['super_admin', 'consultant', 'viewer'],
};

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Verificar si la ruta está protegida
  const matchedRoute = Object.keys(protectedRoutes).find(route => 
    pathname.startsWith(route)
  );
  
  if (!matchedRoute) {
    return NextResponse.next();
  }
  
  // Obtener token y user del localStorage no es posible en middleware
  // Usaremos cookies o verificaremos en el cliente
  // Por ahora, dejamos pasar y el cliente hará la verificación
  
  return NextResponse.next();
}

export const config = {
  matcher: ['/config/:path*', '/users/:path*', '/dashboard/:path*'],
};
