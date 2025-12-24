import { chromium, type Page } from "playwright";
import { spawn } from "node:child_process";
import { resolve } from "node:path";
import { mkdir, writeFile } from "node:fs/promises";

const ROOT = resolve(__dirname, "..", "..");
const SCREENSHOT_DIR = resolve(ROOT, "docs", "screenshots");

const sleep = (ms: number) => new Promise((res) => setTimeout(res, ms));

async function waitForUrl(url: string, timeoutMs = 60_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // ignore
    }
    await sleep(500);
  }
  throw new Error(`Timed out waiting for ${url}`);
}

function runCommand(command: string, args: string[], options: { cwd?: string } = {}) {
  return new Promise<void>((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: options.cwd, stdio: "inherit" });
    child.on("exit", (code) => {
      if (code === 0) resolvePromise();
      else reject(new Error(`${command} ${args.join(" ")} exited with ${code}`));
    });
  });
}

function startProcess(command: string, args: string[], cwd: string) {
  const child = spawn(command, args, { cwd, stdio: "inherit" });
  return child;
}

async function main() {
  await mkdir(SCREENSHOT_DIR, { recursive: true });
  await runCommand(process.env.PYTHON ?? "python", ["scripts/gen_sample_traces.py"], { cwd: ROOT });
  await runCommand("npm", ["run", "build"], { cwd: resolve(ROOT, "web") });

  const api = startProcess(process.env.PYTHON ?? "python", ["-m", "xaiforge", "serve", "--host", "127.0.0.1", "--port", "8000"], ROOT);
  const ui = startProcess("npm", ["run", "preview", "--", "--host", "127.0.0.1", "--port", "4173"], resolve(ROOT, "web"));

  try {
    await waitForUrl("http://127.0.0.1:8000/api/traces");
    await waitForUrl("http://127.0.0.1:4173");

    const browser = await chromium.launch();
    const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
    await page.goto("http://127.0.0.1:4173", { waitUntil: "networkidle" });

    await page.waitForSelector(".trace-card");
    await saveSvgScreenshot(page, `${SCREENSHOT_DIR}/traces.svg`);

    await page.click(".trace-card");
    await page.waitForSelector(".timeline");
    await saveSvgScreenshot(page, `${SCREENSHOT_DIR}/timeline.svg`);

    await page.click("button:has-text('Live Run')");
    await page.waitForSelector(".live-run");
    await page.click("button:has-text('Start Run')");
    await page.waitForSelector(".event-card");
    await saveSvgScreenshot(page, `${SCREENSHOT_DIR}/live-run.svg`);

    await page.click("button:has-text('Compare')");
    await page.waitForSelector(".compare-panel");
    const selects = await page.$$(".compare-selectors select");
    if (selects.length >= 2) {
      const optionsA = await selects[0].$$("option");
      const optionsB = await selects[1].$$("option");
      if (optionsA.length > 1) {
        await selects[0].selectOption({ index: 1 });
      }
      if (optionsB.length > 2) {
        await selects[1].selectOption({ index: 2 });
      } else if (optionsB.length > 1) {
        await selects[1].selectOption({ index: 1 });
      }
    }
    await page.waitForTimeout(1000);
    await saveSvgScreenshot(page, `${SCREENSHOT_DIR}/compare.svg`);

    await browser.close();
  } finally {
    api.kill("SIGTERM");
    ui.kill("SIGTERM");
  }
}

async function saveSvgScreenshot(page: Page, outputPath: string) {
  const screenshot = await page.screenshot({ type: "png", fullPage: true });
  const base64 = Buffer.from(screenshot).toString("base64");
  const viewport = page.viewportSize() ?? { width: 1400, height: 900 };
  const svg = `<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"${viewport.width}\" height=\"${viewport.height}\" viewBox=\"0 0 ${viewport.width} ${viewport.height}\">\n  <image href=\"data:image/png;base64,${base64}\" width=\"100%\" height=\"100%\" />\n</svg>\n`;
  await writeFile(outputPath, svg, "utf-8");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
