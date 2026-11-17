import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api, setAuthLostHandler, tokenStore } from "../api/client";
import type { User } from "../api/types";
import { AuthContext } from "./auth-context";
import type { AuthStatus } from "./auth-context";

export function AuthProvider({ children }: { children: ReactNode }) {
  // Токенов нет — сразу «аноним», без лишнего мигания экрана загрузки.
  const [status, setStatus] = useState<AuthStatus>(() =>
    tokenStore.has() ? "loading" : "anonymous",
  );
  const [user, setUser] = useState<User | null>(null);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
    setStatus("anonymous");
  }, []);

  // При открытии страницы: если токены сохранены — узнаём, кто мы.
  // Протухший access продлевается внутри api.me() автоматически.
  useEffect(() => {
    let cancelled = false;
    if (!tokenStore.has()) return;
    api
      .me()
      .then((me) => {
        if (cancelled) return;
        setUser(me);
        setStatus("authenticated");
      })
      .catch(() => {
        if (cancelled) return;
        // 401 уже сбросил токены; при сетевой ошибке просто покажем вход.
        setStatus("anonymous");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Сессию не удалось продлить в любом запросе — выходим.
  useEffect(() => {
    setAuthLostHandler(logout);
    return () => setAuthLostHandler(null);
  }, [logout]);

  // Вышли в другой вкладке — выходим и здесь.
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === tokenStore.accessKey && e.newValue === null) logout();
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [logout]);

  const login = useCallback(async (loginName: string, password: string) => {
    await api.login(loginName, password);
    setUser(await api.me());
    setStatus("authenticated");
  }, []);

  const register = useCallback(
    async (loginName: string, password: string) => {
      await api.signup(loginName, password);
      await login(loginName, password);
    },
    [login],
  );

  const value = useMemo(
    () => ({ status, user, login, register, logout }),
    [status, user, login, register, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
