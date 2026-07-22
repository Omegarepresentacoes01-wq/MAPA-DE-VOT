export const SESSION_COOKIE = "mapa_voto_session";

const defaultEmail = "admin@mapadevoto.local";
const defaultPassword = "mapa-local-2026";

function config() {
  return {
    email: process.env.MAPA_ADMIN_EMAIL || defaultEmail,
    password: process.env.MAPA_ADMIN_PASSWORD || defaultPassword,
    secret: process.env.MAPA_SESSION_SECRET || "troque-esta-chave-antes-da-vps",
    usingDefaults: !process.env.MAPA_ADMIN_EMAIL || !process.env.MAPA_ADMIN_PASSWORD,
  };
}

export function localAdminUsesDefaults() {
  return config().usingDefaults;
}

function safeEquals(left: string, right: string) {
  const maxLength = Math.max(left.length, right.length);
  let mismatch = left.length ^ right.length;
  for (let index = 0; index < maxLength; index += 1) {
    mismatch |= (left.charCodeAt(index) || 0) ^ (right.charCodeAt(index) || 0);
  }
  return mismatch === 0;
}

async function signature(email: string, secret: string) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const bytes = new Uint8Array(await crypto.subtle.sign("HMAC", key, encoder.encode(email)));
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function validateLocalAdmin(email: string, password: string) {
  const current = config();
  const validEmail = safeEquals(email, current.email);
  const validPassword = safeEquals(password, current.password);
  return validEmail && validPassword;
}

export async function createSessionValue(email: string) {
  const { secret } = config();
  return `${email}.${await signature(email, secret)}`;
}

export async function hasValidSession(value?: string) {
  if (!value) return false;
  const separator = value.lastIndexOf(".");
  const email = value.slice(0, separator);
  const providedSignature = value.slice(separator + 1);
  if (separator < 1 || email !== config().email) return false;
  return safeEquals(providedSignature, await signature(email, config().secret));
}
