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

export function validateLocalAdmin(email: string, password: string) {
  const current = config();
  const validEmail = safeEquals(email, current.email);
  const validPassword = safeEquals(password, current.password);
  return validEmail && validPassword;
}

export function createSessionValue(email: string) {
  // Sessão propositalmente simples para o modo local sem infraestrutura.
  // Na VPS ela será substituída por sessão persistida e senha hasheada.
  return `local:${email}`;
}

export function hasValidSession(value?: string) {
  return safeEquals(value || "", createSessionValue(config().email));
}
