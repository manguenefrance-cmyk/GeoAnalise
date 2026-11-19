import { requestToken } from "./firebase-session";
import type { components } from "../../../packages/types/schema";

export type Project = components["schemas"]["ProjectView"];
export type Scene = components["schemas"]["SceneView"];
export type Index = components["schemas"]["IndexView"];
export type Artifact = components["schemas"]["ArtifactView"];
export type Analysis = components["schemas"]["AnalysisView"];
export type Usage = components["schemas"]["UsageView"];
export type Area = Omit<components["schemas"]["AreaView"], "geometry"> & {
  geometry: GeoJSON.Geometry;
};

export async function api<T>(
  path: string,
  token: string,
  init?: RequestInit,
): Promise<T> {
  const freshToken = await requestToken(token);
  const response = await fetch("/api" + path, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...(freshToken ? { Authorization: `Bearer ${freshToken}` } : {}),
      ...init?.headers,
    },
  });
  const data = await response
    .json()
    .catch(() => ({ error: { code: "API_UNAVAILABLE" } }));
  if (response.status === 401)
    window.dispatchEvent(new Event("arcambe:session-expired"));
  if (!response.ok)
    throw new Error(data.error?.code || `HTTP_${response.status}`);
  return data;
}
export async function downloadArtifact(artifact: Artifact, token: string) {
  const result = await api<{ url: string }>(
    `/v1/artifacts/${artifact.id}/download`,
    token,
  );
  const link = document.createElement("a");
  link.href = "/api" + result.url;
  link.download = "";
  link.click();
}
