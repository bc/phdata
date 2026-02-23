#!/usr/bin/env node
/**
 * grab-logo.js - Find and download a company logo via Google Images
 * Usage: node grab-logo.js "Company Name" "/output/dir"
 */

const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const https = require("https");
const http = require("http");

const companyName = process.argv[2];
const outputDir = process.argv[3] || ".";

if (!companyName) {
  console.error("Usage: node grab-logo.js <company-name> [output-dir]");
  process.exit(1);
}

function slugify(name) {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith("https") ? https : http;
    const file = fs.createWriteStream(dest);
    mod
      .get(url, { headers: { "User-Agent": "Mozilla/5.0" } }, (response) => {
        if (response.statusCode >= 300 && response.statusCode < 400 && response.headers.location) {
          // Follow redirect
          downloadFile(response.headers.location, dest).then(resolve).catch(reject);
          return;
        }
        if (response.statusCode !== 200) {
          reject(new Error(`HTTP ${response.statusCode}`));
          return;
        }
        response.pipe(file);
        file.on("finish", () => {
          file.close();
          resolve(dest);
        });
      })
      .on("error", reject);
  });
}

(async () => {
  const slug = slugify(companyName);
  console.log(`Searching for logo: "${companyName}" (slug: ${slug})`);

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.setExtraHTTPHeaders({
    "User-Agent":
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  });

  let logoUrl = null;
  let ext = "png";

  // Strategy 1: Try to find SVG logo via Google Images
  const queries = [
    `${companyName} logo svg filetype:svg`,
    `${companyName} official logo transparent`,
    `${companyName} company logo`,
  ];

  for (const query of queries) {
    try {
      const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(query)}&tbm=isch`;
      await page.goto(searchUrl, { waitUntil: "domcontentloaded", timeout: 15000 });
      await page.waitForTimeout(2000);

      // Try to get image URLs from the page
      const imageUrls = await page.evaluate(() => {
        const results = [];
        // Google Images stores original URLs in data attributes
        const imgs = document.querySelectorAll("img[src]");
        for (const img of imgs) {
          const src = img.src || "";
          // Skip Google's own assets and tiny thumbnails
          if (
            src.includes("gstatic.com") ||
            src.includes("google.com/images") ||
            src.startsWith("data:") ||
            src.includes("favicon")
          )
            continue;
          if (img.naturalWidth > 50) {
            results.push(src);
          }
        }
        return results.slice(0, 5);
      });

      if (imageUrls.length > 0) {
        // Check if any are SVGs
        const svgUrl = imageUrls.find((u) => u.includes(".svg"));
        if (svgUrl) {
          logoUrl = svgUrl;
          ext = "svg";
          break;
        }
        // Otherwise use the first good image
        if (!logoUrl) {
          logoUrl = imageUrls[0];
          ext = logoUrl.includes(".svg") ? "svg" : "png";
        }
        break;
      }
    } catch (e) {
      console.log(`  Query "${query}" failed: ${e.message}`);
    }
  }

  // Strategy 2: Try the company's website directly for favicon/logo
  if (!logoUrl) {
    try {
      const ddgUrl = `https://logo.clearbit.com/${slug}.com`;
      logoUrl = ddgUrl;
      ext = "png";
      console.log("  Falling back to Clearbit logo API");
    } catch (e) {
      console.log("  Clearbit fallback failed");
    }
  }

  await browser.close();

  if (!logoUrl) {
    console.error(`Could not find logo for "${companyName}"`);
    process.exit(1);
  }

  // Download
  const filename = `${slug}.${ext}`;
  const dest = path.join(outputDir, filename);
  fs.mkdirSync(outputDir, { recursive: true });

  console.log(`  Downloading: ${logoUrl}`);
  try {
    await downloadFile(logoUrl, dest);
    const stats = fs.statSync(dest);
    console.log(`  Saved: ${dest} (${stats.size} bytes)`);
  } catch (e) {
    console.error(`  Download failed: ${e.message}`);
    // Try Clearbit as final fallback
    try {
      const clearbitUrl = `https://logo.clearbit.com/${slug}.com`;
      console.log(`  Trying Clearbit: ${clearbitUrl}`);
      await downloadFile(clearbitUrl, dest);
      const stats = fs.statSync(dest);
      console.log(`  Saved via Clearbit: ${dest} (${stats.size} bytes)`);
    } catch (e2) {
      console.error(`  All download methods failed for "${companyName}"`);
      process.exit(1);
    }
  }
})();
