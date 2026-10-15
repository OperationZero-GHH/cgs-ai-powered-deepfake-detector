import { writeFile } from "node:fs/promises";

export default async function globalTeardown() {
  const stopFile = process.env.E2E_STOP_FILE;
  if (stopFile) await writeFile(stopFile, "stop", { encoding: "utf8" });
}
