import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  isFirebaseConfigComplete,
  selectFirebaseConfig,
} from "../lib/firebase-config.mjs";

const defaults = JSON.parse(
  readFileSync(new URL("../lib/firebase-public.json", import.meta.url), "utf8"),
);

test("registered ARCAMBE web app works without deployment environment variables", () => {
  const config = selectFirebaseConfig(defaults, {});
  assert.ok(isFirebaseConfigComplete(config));
  assert.equal(config.projectId, "arcambe-geoanalytics");
  assert.equal(config.authDomain, "arcambe-geoanalytics.firebaseapp.com");
  assert.ok(config.appId.includes(":web:"));
});

test("empty build arguments retain the registered project", () => {
  const config = selectFirebaseConfig(defaults, {
    apiKey: "",
    projectId: "",
    authDomain: "",
  });
  assert.ok(isFirebaseConfigComplete(config));
  assert.equal(config.projectId, defaults.projectId);
});

test("another deployment project does not inherit the ARCAMBE app identifiers", () => {
  const config = selectFirebaseConfig(defaults, {
    apiKey: "other-key",
    authDomain: "other.firebaseapp.com",
    projectId: "other",
  });
  assert.ok(isFirebaseConfigComplete(config));
  assert.equal(config.apiKey, "other-key");
  assert.equal(config.appId, undefined);
  assert.equal(config.storageBucket, undefined);
});

test("partial overrides fail closed instead of mixing project credentials", () => {
  const config = selectFirebaseConfig(defaults, { projectId: "other" });
  assert.equal(isFirebaseConfigComplete(config), false);
  assert.equal(config.apiKey, "");
});
