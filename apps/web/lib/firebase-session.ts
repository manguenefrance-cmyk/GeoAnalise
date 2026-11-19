import type { Auth } from "firebase/auth";

export const firebaseConfigured = Boolean(
  process.env.NEXT_PUBLIC_FIREBASE_API_KEY &&
  process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
);
let authentication: Promise<Auth> | undefined;

export function firebaseAuth(): Promise<Auth> {
  if (!firebaseConfigured)
    return Promise.reject(new Error("FIREBASE_NOT_CONFIGURED"));
  authentication ??= (async () => {
    const { getApps, initializeApp } = await import("firebase/app");
    const { getAuth, setPersistence, browserSessionPersistence } =
      await import("firebase/auth");
    const app =
      getApps()[0] ||
      initializeApp({
        apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
        authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
        projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
      });
    const auth = getAuth(app);
    await setPersistence(auth, browserSessionPersistence);
    return auth;
  })().catch((error) => {
    authentication = undefined;
    throw error;
  });
  return authentication;
}

export async function requestToken(fallback: string): Promise<string> {
  if (!fallback || fallback.startsWith("test:") || !firebaseConfigured)
    return fallback;
  const auth = await firebaseAuth();
  await auth.authStateReady();
  return auth.currentUser?.emailVerified ? auth.currentUser.getIdToken() : "";
}

export async function firebaseSignOut() {
  if (!firebaseConfigured) return;
  const { signOut } = await import("firebase/auth");
  await signOut(await firebaseAuth());
}
