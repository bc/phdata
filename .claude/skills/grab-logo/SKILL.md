# Grab Company Logo Skill

Finds and downloads company logos in SVG or PNG format using Google Images search via Playwright browser automation.

## Usage

Invoke with: `Use grab-logo to find the logo for [Company Name]`

Or batch: `Use grab-logo to find logos for all prospect companies`

## How It Works

1. Opens Google Images in a headless browser
2. Searches for "[Company Name] logo SVG" or "[Company Name] logo transparent PNG"
3. Finds the best match (prefers SVG, falls back to high-quality PNG)
4. Downloads to the project's `.claude/logos/` directory
5. Names files as `{company-slug}.{svg|png}`

## Script

The automation script is at `scripts/grab-logo.js`. Run it via:

```bash
cd $SKILL_DIR && node scripts/grab-logo.js "Company Name" "/path/to/output/dir"
```

## Batch Mode

```bash
cd $SKILL_DIR && node scripts/grab-logos-batch.js "/path/to/prospects.json" "/path/to/output/dir"
```

## Output

Logos are saved to `.claude/logos/` within the project directory with filenames like:
- `cordenpharm.svg`
- `zimvie.png`
- `medtronic.svg`
