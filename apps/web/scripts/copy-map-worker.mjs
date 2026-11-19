import { copyFile, mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
const publicDirectory = new URL("../public/", import.meta.url);
await mkdir(publicDirectory, { recursive: true });
for (const name of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  await copyFile(
    fileURLToPath(
      new URL("../node_modules/maplibre-gl/dist/" + name, import.meta.url),
    ),
    fileURLToPath(new URL("../public/" + name, import.meta.url)),
  );
}
