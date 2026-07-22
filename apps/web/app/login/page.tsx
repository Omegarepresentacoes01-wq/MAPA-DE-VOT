"use client";

import { FormEvent, useState } from "react";
import { LockKeyhole, Vote } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      setError("E-mail ou senha inválidos.");
      setLoading(false);
      return;
    }
    window.location.assign("/");
  }

  return (
    <main className="login-page">
      <section className="login-brand">
        <div className="login-mark"><Vote size={24} /></div>
        <span className="login-kicker">MAPA DE VOTO</span>
        <h1>Inteligência eleitoral<br />para sua equipe.</h1>
        <p>Ambiente privado para consulta territorial, candidatos e resultados eleitorais.</p>
      </section>
      <section className="login-panel">
        <form className="login-card" onSubmit={submit}>
          <div className="login-title"><LockKeyhole size={20} /><div><h2>Acesso restrito</h2><p>Entre com suas credenciais autorizadas.</p></div></div>
          <label className="field-label" htmlFor="email">E-mail</label>
          <input id="email" className="input-field" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" />
          <label className="field-label" htmlFor="password">Senha</label>
          <input id="password" className="input-field" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete="current-password" />
          {error && <p className="login-error">{error}</p>}
          <button className="btn btn-primary btn-lg" type="submit" disabled={loading}>{loading ? "Validando…" : "Entrar no sistema"}</button>
          <p className="login-help">Ambiente interno. Solicite acesso ao administrador responsável.</p>
        </form>
      </section>
    </main>
  );
}
