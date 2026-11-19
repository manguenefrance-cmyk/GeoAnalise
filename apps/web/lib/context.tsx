"use client";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { en, pt, errors, type Locale } from "./i18n";
import {
  firebaseAuth,
  firebaseConfigured,
  firebaseSignOut,
} from "./firebase-session";

type AppContext = {
  locale: Locale;
  setLocale: (v: Locale) => void;
  t: typeof en;
  token: string;
  setToken: (v: string) => void;
  mode: string;
  online: boolean;
  sessionReady: boolean;
  errorText: (code: string) => string;
};
const Context = createContext<AppContext>(null!);
export function Provider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");
  const [token, setTokenState] = useState("");
  const [mode, setMode] = useState("");
  const [online, setOnline] = useState(false);
  const [sessionReady, setSessionReady] = useState(false);
  function applyToken(value: string) {
    setTokenState(value);
    if (value) sessionStorage.setItem("arcambe-token", value);
    else sessionStorage.removeItem("arcambe-token");
  }
  useEffect(() => {
    const savedLocale =
      localStorage.getItem("arcambe-locale") === "pt" ? "pt" : "en";
    setLocaleState(savedLocale);
    document.documentElement.lang = savedLocale;
    let active = true;
    let unsubscribe = () => {};
    let refreshTimer: ReturnType<typeof setInterval> | undefined;
    async function initialize() {
      const saved = sessionStorage.getItem("arcambe-token") || "";
      let runtime = "";
      try {
        const response = await fetch("/api/healthz", {
          signal: AbortSignal.timeout(10000),
        });
        if (!response.ok) throw new Error("API_UNAVAILABLE");
        runtime = (await response.json()).mode;
        if (active) {
          setMode(runtime);
          setOnline(true);
        }
      } catch {
        if (active) setOnline(false);
      }
      if (!active) return;
      if (saved.startsWith("test:") && runtime === "test") {
        applyToken(saved);
        setSessionReady(true);
        return;
      }
      if (!firebaseConfigured) {
        applyToken("");
        setSessionReady(true);
        return;
      }
      try {
        const auth = await firebaseAuth();
        const { onIdTokenChanged } = await import("firebase/auth");
        if (!active) return;
        unsubscribe = onIdTokenChanged(auth, async (user) => {
          try {
            const value = user?.emailVerified ? await user.getIdToken() : "";
            if (active && auth.currentUser?.uid === user?.uid)
              applyToken(value);
          } catch {
            if (active) applyToken("");
          } finally {
            if (active) setSessionReady(true);
          }
        });
        refreshTimer = setInterval(
          () => {
            const user = auth.currentUser;
            if (user?.emailVerified)
              void user
                .getIdToken()
                .then((value) => {
                  if (active && auth.currentUser?.uid === user.uid)
                    applyToken(value);
                })
                .catch(() => {});
          },
          4 * 60 * 1000,
        );
      } catch {
        if (active) {
          applyToken("");
          setSessionReady(true);
        }
      }
    }
    void initialize();
    const expired = () => {
      applyToken("");
      void firebaseSignOut().catch(() => {});
    };
    window.addEventListener("arcambe:session-expired", expired);
    return () => {
      active = false;
      unsubscribe();
      clearInterval(refreshTimer);
      window.removeEventListener("arcambe:session-expired", expired);
    };
  }, []);
  const setLocale = (v: Locale) => {
    setLocaleState(v);
    localStorage.setItem("arcambe-locale", v);
    document.documentElement.lang = v;
  };
  const setToken = (v: string) => {
    if (v.startsWith("test:") && mode !== "test") return;
    applyToken(v);
    if (!v) void firebaseSignOut().catch(() => {});
  };
  const errorText = (code: string) =>
    errors[code]?.[locale === "pt" ? 1 : 0] ||
    (locale === "pt"
      ? `Não foi possível concluir a operação (${code}).`
      : `Could not complete this operation (${code}).`);
  return (
    <Context.Provider
      value={{
        locale,
        setLocale,
        t: locale === "pt" ? pt : en,
        token,
        setToken,
        mode,
        online,
        sessionReady,
        errorText,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export const useApp = () => useContext(Context);
