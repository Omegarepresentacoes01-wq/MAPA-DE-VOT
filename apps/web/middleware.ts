import { NextRequest, NextResponse } from "next/server";
import { hasValidSession, SESSION_COOKIE } from "@/lib/auth";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (pathname === "/login" || pathname.startsWith("/api/auth")) return NextResponse.next();
  if (!hasValidSession(request.cookies.get(SESSION_COOKIE)?.value)) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }
  return NextResponse.next();
}

export const config = { matcher: ["/((?!_next|favicon.ico).*)"] };
