/**
 * Firebase web identifiers are public. Environment overrides replace the profile
 * as a group so a partially configured deployment cannot mix two projects.
 * @param {Record<string, string>} defaults
 * @param {{apiKey?: string, authDomain?: string, projectId?: string, appId?: string}} overrides
 */
export function selectFirebaseConfig(defaults, overrides) {
  if (!Object.values(overrides).some(Boolean)) return { ...defaults };
  return {
    apiKey: overrides.apiKey || "",
    authDomain: overrides.authDomain || "",
    projectId: overrides.projectId || "",
    appId:
      overrides.appId ||
      (overrides.projectId === defaults.projectId ? defaults.appId : undefined),
  };
}

/** @param {{apiKey?: string, authDomain?: string, projectId?: string}} config */
export function isFirebaseConfigComplete(config) {
  return Boolean(config.apiKey && config.authDomain && config.projectId);
}
