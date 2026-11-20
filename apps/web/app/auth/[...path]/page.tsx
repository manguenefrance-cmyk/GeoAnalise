"use client";
import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { FlaskConical } from "lucide-react";
import Brand from "@/components/Brand";
import { useApp } from "@/lib/context";
import { firebaseAuth, firebaseConfigured } from "@/lib/firebase-session";
export default function Auth() {
  const { t, mode, setToken, locale, setLocale, errorText } = useApp();
  const router = useRouter();
  const path = usePathname();
  const flow = path.endsWith("/register")
    ? "register"
    : path.endsWith("/forgot-password")
      ? "reset"
      : "login";
  const heading =
    flow === "register" ? t.register : flow === "reset" ? t.reset : t.login;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(kind: string) {
    setBusy(true);
    setStatus("");
    try {
      if (!firebaseConfigured) throw new Error(t.authMissing);
      const {
        signInWithEmailAndPassword,
        createUserWithEmailAndPassword,
        sendEmailVerification,
        sendPasswordResetEmail,
      } = await import("firebase/auth");
      const auth = await firebaseAuth();
      auth.languageCode = locale;
      if (kind === "reset") {
        await sendPasswordResetEmail(auth, email);
        setStatus(t.authSent);
        return;
      }
      const cred =
        kind === "register"
          ? await createUserWithEmailAndPassword(auth, email, password)
          : await signInWithEmailAndPassword(auth, email, password);
      if (!cred.user.emailVerified) {
        await sendEmailVerification(cred.user);
        setStatus(t.verify);
        return;
      }
      setToken(await cred.user.getIdToken());
      router.push("/app/dashboard");
    } catch (e) {
      const code = (e as { code?: string })?.code;
      setStatus(
        code ? errorText(code) : e instanceof Error ? e.message : t.error,
      );
    } finally {
      setBusy(false);
    }
  }
  async function googleSignIn() {
    setBusy(true);
    setStatus("");
    try {
      const { GoogleAuthProvider, signInWithPopup } =
        await import("firebase/auth");
      const auth = await firebaseAuth();
      auth.languageCode = locale;
      const provider = new GoogleAuthProvider();
      provider.setCustomParameters({ prompt: "select_account" });
      const credential = await signInWithPopup(auth, provider);
      if (!credential.user.emailVerified) {
        setStatus(t.verify);
        return;
      }
      setToken(await credential.user.getIdToken());
      router.push("/app/dashboard");
    } catch (error) {
      const code = (error as { code?: string })?.code;
      setStatus(
        code
          ? errorText(code)
          : error instanceof Error
            ? error.message
            : t.error,
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="auth-page">
      <Brand />
      <section className="auth-card">
        <div className="eyebrow">GEOANALYTICS / {t.privateWorkspace}</div>
        <h1>{heading}</h1>
        <p>{t.intro}</p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void submit(flow);
          }}
        >
          <label>
            {t.email}
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          {flow !== "reset" && (
            <label>
              {t.password}
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
          )}
          <button className="button primary full" disabled={busy}>
            {busy ? t.loading : heading}
          </button>
        </form>
        {flow !== "reset" && (
          <button
            type="button"
            className="button secondary full"
            style={{ marginTop: 12 }}
            disabled={busy || !firebaseConfigured}
            onClick={() => void googleSignIn()}
          >
            {t.googleLogin}
          </button>
        )}
        <div className="auth-links">
          <Link href={flow === "register" ? "/auth/login" : "/auth/register"}>
            {flow === "register" ? t.login : t.register}
          </Link>
          <Link href="/auth/forgot-password">{t.reset}</Link>
        </div>
        {mode === "test" && (
          <div className="test-login">
            <FlaskConical size={20} />
            <span>{t.testNotice}</span>
            <button
              className="button secondary full"
              onClick={() => {
                setToken("test:demo");
                router.push("/app/dashboard");
              }}
            >
              {t.testLogin}
            </button>
          </div>
        )}
        {status && (
          <p className="notice" role="status">
            {status}
          </p>
        )}
      </section>
      <button
        className="text-button"
        onClick={() => setLocale(locale === "en" ? "pt" : "en")}
      >
        {locale === "en" ? "Português" : "English"}
      </button>
    </main>
  );
}
