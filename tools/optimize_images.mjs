#!/usr/bin/env node
/**
 * Build-time image derivatives for images actually displayed as article art.
 *
 * Sources are the fixed 960x504 JPEGs in media/ and media/leads/ (not social
 * covers, portraits, or arbitrary assets). Sharp emits same-basename WebP and
 * AVIF siblings. A content-hash manifest avoids recompressing unchanged inputs
 * across GitHub Actions checkouts, where filesystem mtimes are not reliable.
 */
import { createHash } from "node:crypto";
import { createReadStream } from "node:fs";
import {
  mkdir,
  readFile,
  readdir,
  rename,
  rm,
  writeFile,
} from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const SCRIPT_PATH = fileURLToPath(import.meta.url);
const ROOT = path.dirname(path.dirname(SCRIPT_PATH));
const DEFAULT_MEDIA_DIR = path.join(ROOT, "media");
const MANIFEST_NAME = ".image-pipeline.json";
const TRANSFORM = Object.freeze({
  width: 960,
  height: 504,
  fit: "cover",
  position: "centre",
  webp: { quality: 78, effort: 4 },
  avif: { quality: 48, effort: 4 },
});
const TRANSFORM_SIGNATURE = JSON.stringify(TRANSFORM);
const FORMATS = Object.freeze(["webp", "avif"]);

function posixPath(value) {
  return value.split(path.sep).join("/");
}

function resolveMediaPath(mediaDir, relativePath) {
  if (typeof relativePath !== "string" || path.isAbsolute(relativePath)) {
    throw new Error(`Cale de ieșire invalidă în manifest: ${relativePath}`);
  }
  const root = path.resolve(mediaDir);
  const resolved = path.resolve(root, relativePath);
  if (!resolved.startsWith(`${root}${path.sep}`)) {
    throw new Error(`Cale în afara directorului media: ${relativePath}`);
  }
  return resolved;
}

async function jpgsIn(directory) {
  try {
    const entries = await readdir(directory, { withFileTypes: true });
    return entries
      .filter((entry) => entry.isFile() && /\.jpe?g$/i.test(entry.name)
        && !/\.c\.jpe?g$/i.test(entry.name))
      .map((entry) => path.join(directory, entry.name));
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }
}

export async function listSources(mediaDir = DEFAULT_MEDIA_DIR) {
  const [root, leads] = await Promise.all([
    jpgsIn(mediaDir),
    jpgsIn(path.join(mediaDir, "leads")),
  ]);
  return [...root, ...leads].sort((a, b) => a.localeCompare(b));
}

async function sha256(filePath) {
  const hash = createHash("sha256");
  for await (const chunk of createReadStream(filePath)) hash.update(chunk);
  return hash.digest("hex");
}

async function readManifest(mediaDir) {
  const filePath = path.join(mediaDir, MANIFEST_NAME);
  try {
    const manifest = JSON.parse(await readFile(filePath, "utf8"));
    if (!manifest || !manifest.entries
        || typeof manifest.entries !== "object" || Array.isArray(manifest.entries)) {
      throw new Error("câmpul `entries` nu este un obiect");
    }
    for (const [source, entry] of Object.entries(manifest.entries)) {
      if (!source || !entry || typeof entry.sha256 !== "string" || !Array.isArray(entry.outputs)
          || entry.outputs.some((output) => typeof output !== "string")) {
        throw new Error(`intrare invalidă pentru ${source || "sursă fără nume"}`);
      }
    }
    return manifest;
  } catch (error) {
    if (error.code === "ENOENT") return { entries: {} };
    throw new Error(`Manifest Sharp invalid (${filePath}): ${error.message}`);
  }
}

function outputPaths(mediaDir, sourcePath) {
  const relative = posixPath(path.relative(mediaDir, sourcePath));
  const stem = relative.replace(/\.(jpe?g)$/i, "");
  return Object.fromEntries(FORMATS.map((format) => [
    format,
    `${stem}.${format}`,
  ]));
}

async function outputIsValid(filePath, format) {
  try {
    const metadata = await sharp(filePath).metadata();
    const formatMatches = format === "avif"
      ? ["avif", "heif"].includes(metadata.format)
      : metadata.format === format;
    return formatMatches
      && metadata.width === TRANSFORM.width
      && metadata.height === TRANSFORM.height;
  } catch {
    return false;
  }
}

async function writeVariant(sourcePath, outputPath, format) {
  await mkdir(path.dirname(outputPath), { recursive: true });
  const temporaryPath = `${outputPath}.${process.pid}.tmp`;
  try {
    let image = sharp(sourcePath)
      .rotate()
      .resize({
        width: TRANSFORM.width,
        height: TRANSFORM.height,
        fit: TRANSFORM.fit,
        position: TRANSFORM.position,
      });
    image = format === "webp"
      ? image.webp(TRANSFORM.webp)
      : image.avif(TRANSFORM.avif);
    await image.toFile(temporaryPath);
    if (!await outputIsValid(temporaryPath, format)) {
      throw new Error(`${format} produs cu dimensiuni sau format neașteptat: ${outputPath}`);
    }
    await rename(temporaryPath, outputPath);
  } catch (error) {
    await rm(temporaryPath, { force: true }).catch(() => {});
    throw error;
  }
}

async function writeManifest(mediaDir, manifest) {
  const filePath = path.join(mediaDir, MANIFEST_NAME);
  const temporaryPath = `${filePath}.${process.pid}.tmp`;
  await writeFile(temporaryPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  await rename(temporaryPath, filePath);
}

async function pruneStaleOutputs(mediaDir, previousEntries, currentSources) {
  let removed = 0;
  for (const [source, entry] of Object.entries(previousEntries)) {
    if (currentSources.has(source)) continue;
    for (const output of entry.outputs || []) {
      const outputPath = resolveMediaPath(mediaDir, output);
      try {
        await rm(outputPath);
        removed += 1;
      } catch (error) {
        if (error.code !== "ENOENT") throw error;
      }
    }
  }
  return removed;
}

export async function runImagePipeline(mediaDir = DEFAULT_MEDIA_DIR) {
  await mkdir(mediaDir, { recursive: true });
  const [sources, previous] = await Promise.all([
    listSources(mediaDir),
    readManifest(mediaDir),
  ]);
  const entries = {};
  let processed = 0;
  let skipped = 0;

  for (const sourcePath of sources) {
    const source = posixPath(path.relative(mediaDir, sourcePath));
    const digest = await sha256(sourcePath);
    const variants = outputPaths(mediaDir, sourcePath);
    const outputNames = Object.values(variants);
    const old = previous.entries[source];
    const cacheMatches = previous.transform === TRANSFORM_SIGNATURE
      && old?.sha256 === digest
      && Array.isArray(old.outputs)
      && outputNames.every((name) => old.outputs.includes(name));
    const outputsValid = cacheMatches && await Promise.all(
      FORMATS.map((format) => outputIsValid(resolveMediaPath(mediaDir, variants[format]), format)),
    ).then((valid) => valid.every(Boolean));

    if (outputsValid) {
      skipped += 1;
    } else {
      for (const format of FORMATS) {
        await writeVariant(sourcePath, resolveMediaPath(mediaDir, variants[format]), format);
      }
      processed += 1;
      console.log(`  Sharp ${source} -> 960×504 WebP + AVIF`);
    }
    entries[source] = { sha256: digest, outputs: outputNames };
  }

  const removed = await pruneStaleOutputs(
    mediaDir,
    previous.entries,
    new Set(Object.keys(entries)),
  );
  await writeManifest(mediaDir, {
    schema: 1,
    transform: TRANSFORM_SIGNATURE,
    entries,
  });
  console.log(`>> Sharp: ${processed} procesate, ${skipped} nemodificate, ${removed} variante vechi eliminate`);
  return { processed, skipped, removed };
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(SCRIPT_PATH)) {
  runImagePipeline().catch((error) => {
    console.error(`!! pipeline Sharp eșuat: ${error.message}`);
    process.exitCode = 1;
  });
}
