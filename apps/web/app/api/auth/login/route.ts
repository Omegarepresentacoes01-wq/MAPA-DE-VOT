import { NextResponse } from "next/server";
import { createSessionValue, SESSION_COOKIE, validateLocalAdmin } from "@/lib/auth";

export async function POST(request: Request) {
  const { email, password } = await request.json();
  if (typeof email !== "string" || typeof password !== "string" || !validateLocalAdmin(email, password)) {
    return NextResponse.json({ detail: "E-mail ou senha inválidos." }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE, await createSessionValue(email), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 8,
  });
  return response;
}
