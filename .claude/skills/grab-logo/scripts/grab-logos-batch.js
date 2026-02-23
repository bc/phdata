#!/usr/bin/env node
/**
 * grab-logos-batch.js - Download logos for all prospect companies
 * Usage: node grab-logos-batch.js <prospects-json-url> <output-dir>
 * Example: node grab-logos-batch.js "http://localhost:8765/api/prospects" "/path/to/.claude/logos"
 */

const { execSync } = require("child_process");
const path = require("path");
const http = require("http");
const https = require("https");
const fs = require("fs");

const prospectsUrl = process.argv[2] || "http://localhost:8765/api/prospects";
const outputDir = process.argv[3] || path.join(__dirname, "..", "..", "logos");

function fetchJSON(url) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith("https") ? https : http;
    mod
      .get(url, (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => resolve(JSON.parse(data)));
      })
      .on("error", reject);
  });
}

(async () => {
  console.log(`Fetching prospects from: ${prospectsUrl}`);
  const { prospects } = await fetchJSON(prospectsUrl);
  console.log(`Found ${prospects.length} prospects\n`);

  const scriptPath = path.join(__dirname, "grab-logo.js");
  let success = 0;
  let failed = 0;

  for (const p of prospects) {
    const slug = p.name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");

    // Skip if already downloaded
    const existing = [".svg", ".png"].find((ext) =>
      fs.existsSync(path.join(outputDir, `${slug}${ext}`))
    );
    if (existing) {
      console.log(`[skip] ${p.name} - already exists`);
      success++;
      continue;
    }

    try {
      console.log(`[${success + failed + 1}/${prospects.length}] ${p.name}...`);
      execSync(`node "${scriptPath}" "${p.name}" "${outputDir}"`, {
        stdio: "inherit",
        timeout: 30000,
      });
      success++;
    } catch (e) {
      console.error(`  FAILED: ${p.name}`);
      failed++;
    }
  }

  console.log(`\nDone: ${success} success, ${failed} failed`);
})();
