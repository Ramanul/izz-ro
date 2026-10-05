import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import sharp from "sharp";
import { runImagePipeline } from "../tools/optimize_images.mjs";

async function sourceImage(filePath, color) {
  await mkdir(path.dirname(filePath), { recursive: true });
  await sharp({
    create: { width: 1920, height: 1008, channels: 3, background: color },
  }).jpeg({ quality: 90 }).toFile(filePath);
}

test("Sharp emits fixed-size WebP and AVIF and skips unchanged sources", async () => {
  const temp = await mkdtemp(path.join(os.tmpdir(), "izz-sharp-"));
  const media = path.join(temp, "media");
  const source = path.join(media, "leads", "photo.jpg");
  try {
    await sourceImage(source, "#b85b22");
    const first = await runImagePipeline(media);
    assert.deepEqual(first, { processed: 1, skipped: 0, removed: 0 });

    for (const format of ["webp", "avif"]) {
      const output = path.join(media, "leads", `photo.${format}`);
      const metadata = await sharp(output).metadata();
      assert.deepEqual([metadata.width, metadata.height], [960, 504]);
      assert.ok(format === "avif"
        ? ["avif", "heif"].includes(metadata.format)
        : metadata.format === format);
    }

    const webpBefore = await readFile(path.join(media, "leads", "photo.webp"));
    const second = await runImagePipeline(media);
    assert.deepEqual(second, { processed: 0, skipped: 1, removed: 0 });
    assert.deepEqual(await readFile(path.join(media, "leads", "photo.webp")), webpBefore);

    await sourceImage(source, "#276ca8");
    const changed = await runImagePipeline(media);
    assert.deepEqual(changed, { processed: 1, skipped: 0, removed: 0 });
    assert.notDeepEqual(await readFile(path.join(media, "leads", "photo.webp")), webpBefore);
  } finally {
    await rm(temp, { recursive: true, force: true });
  }
});

test("Sharp ignores social covers, portraits, and other non-article images", async () => {
  const temp = await mkdtemp(path.join(os.tmpdir(), "izz-sharp-scope-"));
  const media = path.join(temp, "media");
  try {
    await sourceImage(path.join(media, "article.c.jpg"), "#b85b22");
    await sourceImage(path.join(media, "portraits", "person.jpg"), "#276ca8");
    await sourceImage(path.join(media, "og", "category.jpg"), "#b85b22");
    const result = await runImagePipeline(media);
    assert.deepEqual(result, { processed: 0, skipped: 0, removed: 0 });
    assert.equal(await readFile(path.join(media, ".image-pipeline.json"), "utf8").then((v) => v.includes("article.c.jpg")), false);
  } finally {
    await rm(temp, { recursive: true, force: true });
  }
});

test("Sharp removes derivatives after their source image is retired", async () => {
  const temp = await mkdtemp(path.join(os.tmpdir(), "izz-sharp-prune-"));
  const media = path.join(temp, "media");
  const source = path.join(media, "chart.jpg");
  try {
    await sourceImage(source, "#b85b22");
    await runImagePipeline(media);
    await rm(source);
    const result = await runImagePipeline(media);
    assert.deepEqual(result, { processed: 0, skipped: 0, removed: 2 });
    await assert.rejects(readFile(path.join(media, "chart.avif")));
    await assert.rejects(readFile(path.join(media, "chart.webp")));
  } finally {
    await rm(temp, { recursive: true, force: true });
  }
});
