import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PUBLIC_PATHS = [
  '/login', '/register', '/api', '/_next', '/favicon.ico', '/manifest.json', '/icons',
  '/sw.js', '/workbox-', '/fallback-', '/robots.txt',
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isPublic = PUBLIC_PATHS.some(p => pathname.startsWith(p));
  const token    = request.cookies.get('access_token')?.value
                || request.headers.get('authorization')?.replace('Bearer ', '');

  if (!isPublic && !token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
  // Admin guard
  if (pathname.startsWith('/admin')) {
    const roles = request.cookies.get('user_roles')?.value || '';
    if (!roles.includes('admin')) {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
