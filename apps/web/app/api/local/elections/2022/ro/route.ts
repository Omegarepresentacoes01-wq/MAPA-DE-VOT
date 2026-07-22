import { readFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

export async function GET() {
  const file = path.resolve(process.cwd(), "../../data/staging/tse_2022_ro_governador.json");
  try {
    return NextResponse.json(JSON.parse(await readFile(file, "utf8")));
  } catch {
    return NextResponse.json({ detail: "Base TSE local ainda não importada." }, { status: 404 });
  }
}
