/**
 * UI smoke test — screenshots every key page and logs console errors.
 * Run: node scripts/ui-test.mjs
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SS_DIR = join(__dirname, '../.playwright-screenshots');
mkdirSync(SS_DIR, { recursive: true });

const BASE = 'http://localhost:3000';
const API  = 'http://localhost:8080';

const errors = [];
let screenshotCount = 0;

async function shot(page, name) {
  const file = join(SS_DIR, `${String(++screenshotCount).padStart(2,'0')}-${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  console.log(`  📸 ${name}`);
  return file;
}

async function login(page, email = 'tester@example.com', password = 'NewPass456') {
  const res = await page.request.post(`${API}/api/v1/auth/login`, {
    data: { email, password },
  });
  const { access_token } = await res.json();
  await page.evaluate(token => localStorage.setItem('auth_token', token), access_token);
  return access_token;
}

async function run() {
  const browser = await chromium.launch({ headless: false, slowMo: 200 });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  // Capture console errors on every page
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(`[${msg.location().url}] ${msg.text()}`);
    }
  });
  page.on('pageerror', err => errors.push(`[pageerror] ${err.message}`));

  console.log('\n── 1. Landing page ──────────────────────────────────');
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await shot(page, 'landing');

  console.log('\n── 2. Login page ────────────────────────────────────');
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await shot(page, 'login');

  // Fill login form
  await page.fill('input[type="email"]', 'tester@example.com');
  await page.fill('input[type="password"]', 'NewPass456');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/', { timeout: 8000 }).catch(() => {});
  await shot(page, 'after-login');

  console.log('\n── 3. Dashboard (home) ──────────────────────────────');
  await page.goto(`${BASE}/dashboard`, { waitUntil: 'networkidle' });
  await shot(page, 'dashboard');

  console.log('\n── 4. Skills page ───────────────────────────────────');
  await page.goto(`${BASE}/skills`, { waitUntil: 'networkidle' });
  await shot(page, 'skills');

  console.log('\n── 5. New Session page ──────────────────────────────');
  await page.goto(`${BASE}/sessions/new`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);
  await shot(page, 'new-session');

  // Test JD paste panel
  const jdBtn = page.locator('button', { hasText: /paste jd|job description/i }).first();
  if (await jdBtn.isVisible().catch(() => false)) {
    await jdBtn.click();
    await page.waitForTimeout(500);
    await shot(page, 'new-session-jd-panel');
  }

  console.log('\n── 6. Sessions list ─────────────────────────────────');
  await page.goto(`${BASE}/sessions`, { waitUntil: 'networkidle' });
  await shot(page, 'sessions-list');

  console.log('\n── 7. Settings page ─────────────────────────────────');
  await page.goto(`${BASE}/settings`, { waitUntil: 'networkidle' });
  await shot(page, 'settings');

  // Scroll to danger zone
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(800);
  await shot(page, 'settings-danger-zone');

  console.log('\n── 8. Contribute question page ──────────────────────');
  await page.goto(`${BASE}/questions/contribute`, { waitUntil: 'networkidle' });
  await shot(page, 'contribute-question');

  console.log('\n── 9. Forgot password page ──────────────────────────');
  await page.goto(`${BASE}/forgot-password`, { waitUntil: 'networkidle' });
  await shot(page, 'forgot-password');

  console.log('\n── 10. Share card (public, invalid token) ───────────');
  await page.goto(`${BASE}/share/invalid_token_test`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000); // wait for API call + React state update
  await shot(page, 'share-card-404');

  console.log('\n── 11. 404 page ─────────────────────────────────────');
  await page.goto(`${BASE}/does-not-exist`, { waitUntil: 'networkidle' });
  await shot(page, '404-page');

  await browser.close();

  console.log('\n════════════════════════════════════════════════════');
  console.log(`Screenshots saved to: ${SS_DIR}`);
  console.log(`Total screenshots: ${screenshotCount}`);

  if (errors.length) {
    console.log(`\n⚠️  Console errors (${errors.length}):`);
    errors.forEach(e => console.log('  •', e));
  } else {
    console.log('\n✅ No console errors detected.');
  }
}

run().catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
