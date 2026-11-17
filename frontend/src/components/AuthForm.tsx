import { useState } from "react";
import type { FormEvent } from "react";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/auth-context";

type Mode = "login" | "register";

function describeError(error: unknown, mode: Mode): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Неверный логин или пароль.";
    if (error.status === 409) return "Этот логин уже занят. Выберите другой.";
    if (error.status === 429) {
      const wait = error.retryAfter
        ? ` Попробуйте через ${error.retryAfter} с.`
        : "";
      return `Слишком много неудачных попыток входа.${wait}`;
    }
    if (error.status === 422)
      return "Проверьте логин и пароль: они не подходят по длине.";
    if (error.status === 0) return error.message;
  }
  return mode === "login"
    ? "Не удалось войти. Попробуйте ещё раз."
    : "Не удалось зарегистрироваться. Попробуйте ещё раз.";
}

export function AuthForm() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const isLogin = mode === "login";

  const switchMode = (next: Mode) => {
    setMode(next);
    setError(null);
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    // Те же границы, что и на бэкенде (SignUpRequest). При входе длину не
    // проверяем: старые аккаунты могли быть созданы по другим правилам.
    if (!isLogin) {
      if (trimmed.length < 3) return setError("Логин — минимум 3 символа.");
      if (password.length < 6) return setError("Пароль — минимум 6 символов.");
    } else if (trimmed.length === 0 || password.length === 0) {
      return setError("Введите логин и пароль.");
    }

    setBusy(true);
    setError(null);
    try {
      if (isLogin) await login(trimmed, password);
      else await register(trimmed, password);
    } catch (err) {
      setError(describeError(err, mode));
      setBusy(false);
    }
    // При успехе компонент размонтируется, setBusy не нужен.
  };

  return (
    <form className="auth-form" onSubmit={onSubmit} noValidate>
      <div className="mode-switch" role="group" aria-label="Режим">
        <button
          type="button"
          aria-pressed={isLogin}
          onClick={() => switchMode("login")}
        >
          Вход
        </button>
        <button
          type="button"
          aria-pressed={!isLogin}
          onClick={() => switchMode("register")}
        >
          Регистрация
        </button>
      </div>

      <label>
        Логин
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          maxLength={255}
        />
      </label>

      <label>
        Пароль
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete={isLogin ? "current-password" : "new-password"}
          maxLength={255}
        />
      </label>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      <button type="submit" className="primary" disabled={busy}>
        {busy ? "Подождите…" : isLogin ? "Войти" : "Зарегистрироваться"}
      </button>
    </form>
  );
}
