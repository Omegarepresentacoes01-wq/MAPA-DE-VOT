import { NextRequest, NextResponse } from "next/server";

const SESSION_COOKIE = "mapa_voto_session";
const adminEmail = process.env.MAPA_ADMIN_EMAIL || "admin@mapadevoto.local";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (pathname === "/login" || pathname.startsWith("/api/auth")) return NextResponse.next();
  if (request.cookies.get(SESSION_COOKIE)?.value !== `local:${adminEmail}`) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }
  return NextResponse.next();
}

export const config = { matcher: ["/((?!_next|favicon.ico).*)"] };
