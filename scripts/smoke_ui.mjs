#!/usr/bin/env node
import { createRequire } from 'node:module';
import { existsSync } from 'node:fs';
import { execSync } from 'node:child_process';

const require = createRequire(new URL('../frontend/package.json', import.meta.url));

let chromium;
try {
  ({ chromium } = require('playwright-core'));
} catch {
  console.error(
    'playwright-core is missing. Run: npm --prefix frontend install',
  );
  process.exit(1);
}

const WEB_URL = process.env.WEB_URL || 'http://localhost:8080';
const EMAIL = process.env.ADMIN_EMAIL || 'admin@ibms.local';
const PASSWORD = process.env.ADMIN_PASSWORD || 'Password123!';

function findChrome() {
  const candidates = [
    process.env.CHROME_PATH,
    process.env.PLAYWRIGHT_CHROME_PATH,
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  ].filter(Boolean);
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }
  for (const name of ['google-chrome', 'chromium', 'chromium-browser']) {
    try {
      const found = execSync(`command -v ${name}`, { encoding: 'utf8' }).trim();
      if (found) return found;
    } catch {
      // keep looking
    }
  }
  return undefined;
}

const routes = [
  ['/clients', 'Clients'],
  ['/client-contacts', 'Client Contacts'],
  ['/client-directors', 'Client Directors'],
  ['/insurers', 'Insurers'],
  ['/insurer-contacts', 'Insurer Contacts'],
  ['/insurer-branches', 'Insurer Branches'],
  ['/products', 'Products'],
  ['/insurance-classes', 'Insurance Classes'],
  ['/risks', 'Risks'],
  ['/motor-details', 'Motor Details'],
  ['/quotations', 'Quotations'],
  ['/insurer-quotes', 'Insurer Quotes'],
  ['/policies', 'Policies'],
  ['/endorsements', 'Endorsements'],
  ['/renewals', 'Renewals'],
  ['/premiums', 'Premiums'],
  ['/invoices', 'Invoices'],
  ['/payments', 'Payments'],
  ['/credit-debit-notes', 'Credit / Debit Notes'],
  ['/commissions', 'Commissions'],
  ['/remittances', 'Remittances'],
  ['/claims', 'Claims'],
  ['/tasks', 'Tasks'],
  ['/approvals', 'Approvals'],
  ['/documents', 'Documents'],
  ['/communications', 'Communications'],
  ['/users', 'Users'],
  ['/roles', 'Roles & Permissions'],
  ['/branches', 'Branches'],
  ['/audit-logs', 'Audit Trail'],
  ['/search?q=POL', 'Find anything, fast.'],
];

const issues = [];
const check = (condition, message) => {
  if (!condition) issues.push(message);
};
const pass = (message) => console.log(`PASS  ${message}`);
const fail = (message) => {
  issues.push(message);
  console.log(`FAIL  ${message}`);
};

const executablePath = findChrome();
if (!executablePath) {
  console.error(
    'No Chrome/Chromium executable found. Set CHROME_PATH to run the UI smoke test.',
  );
  process.exit(1);
}

const browser = await chromium.launch({
  executablePath,
  headless: true,
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
});

const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
page.on('console', (message) => {
  if (message.type() !== 'error') return;
  if (message.text().includes('favicon.ico')) return;
  issues.push(`console: ${message.text()}`);
});
page.on('pageerror', (error) => issues.push(`pageerror: ${error.message}`));

console.log(`UI smoke test against ${WEB_URL}\n`);

try {
  await page.goto(`${WEB_URL}/`, { waitUntil: 'networkidle' });
  await page.waitForSelector('.landing-hero h1', { timeout: 20000 });
  const landingCta = await page.getByRole('link', { name: /enter workspace/i }).count();
  if (landingCta > 0) pass('public landing page');
  else fail('landing page call to action missing');

  await page.goto(`${WEB_URL}/login`, { waitUntil: 'networkidle' });
  await page.fill('#login-email', EMAIL);
  await page.fill('#login-password', PASSWORD);
  await Promise.all([
    page.waitForURL('**/dashboard', { timeout: 20000 }),
    page.getByRole('button', { name: /sign in/i }).click(),
  ]);
  await page.waitForSelector('.page-title', { timeout: 20000 });
  await page.waitForTimeout(1200);
  const stats = await page.locator('.stat-card').count();
  if (stats > 0) pass(`login and dashboard (${stats} KPI cards)`);
  else fail('dashboard did not render KPI cards');

  for (const [route, expected] of routes) {
    await page.goto(`${WEB_URL}${route}`, { waitUntil: 'domcontentloaded' });
    try {
      await page.waitForSelector('.page-title', { timeout: 15000 });
      await page.waitForTimeout(700);
      const title = await page.locator('.page-title').innerText();
      const alerts = await page.locator('.alert-danger').allInnerTexts();
      const rows = await page.locator('.data-table tbody tr').count();
      const titleOk = title.toLowerCase().includes(expected.toLowerCase().split(' ')[0]);
      if (titleOk && alerts.length === 0) {
        pass(`${route} "${title}"${rows ? ` (${rows} rows)` : ''}`);
      } else {
        fail(
          `${route} title="${title}"` +
            (alerts.length ? ` alert=${alerts.join(' | ')}` : ''),
        );
      }
    } catch (error) {
      fail(`${route}: ${error.message}`);
    }
  }

  await page.goto(`${WEB_URL}/approvals`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.data-table', { timeout: 15000 });
  const approvalHref = await page
    .locator('.row-actions a[title="View details"]')
    .first()
    .getAttribute('href');
  if (approvalHref) {
    await page.goto(`${WEB_URL}${approvalHref}`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.approval-review', { timeout: 15000 });
    const alerts = await page.locator('.alert-danger').allInnerTexts();
    if (alerts.length) fail(`approval review: ${alerts.join(' | ')}`);
    else pass(`approval review ${approvalHref}`);
  } else {
    fail('approval review link missing');
  }

  await page.goto(`${WEB_URL}/reports`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.report-menu-item', { timeout: 15000 });
  const reportButtons = page.locator('.report-menu-item');
  const reportCount = await reportButtons.count();
  check(reportCount > 0, 'report menu is empty');
  for (let index = 0; index < reportCount; index += 1) {
    await reportButtons.nth(index).click();
    await page.waitForTimeout(500);
    const label = await reportButtons.nth(index).locator('strong').innerText();
    const alerts = await page.locator('.alert-danger').allInnerTexts();
    if (alerts.length) fail(`report ${label}: ${alerts.join(' | ')}`);
    else pass(`report ${label}`);
  }

  await page.goto(`${WEB_URL}/search?q=POL`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1000);
  const results = await page.locator('.search-result').count();
  if (results > 0) pass(`global search (${results} results)`);
  else fail('global search returned no results for POL');

  await page.goto(`${WEB_URL}/clients`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.page-title');
  await page.waitForTimeout(700);
  await page.getByRole('button', { name: /new client/i }).click();
  await page.waitForSelector('.modal');
  const fields = await page.locator('.modal .form-field').count();
  if (fields > 0) pass(`client create form (${fields} fields)`);
  else fail('client create form did not render fields');
  await page.getByRole('button', { name: /^cancel$/i }).click();
  await page.waitForTimeout(200);
  check((await page.locator('.modal').count()) === 0, 'client modal did not close');

  const detailHref = await page
    .locator('.row-actions a[title="View details"]')
    .first()
    .getAttribute('href');
  if (detailHref) {
    await page.goto(`${WEB_URL}${detailHref}`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.detail-card', { timeout: 15000 });
    const alerts = await page.locator('.alert-danger').allInnerTexts();
    if (alerts.length) fail(`record detail: ${alerts.join(' | ')}`);
    else pass(`record detail ${detailHref}`);
  } else {
    fail('client detail link missing');
  }

  await page.goto(`${WEB_URL}/account`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.page-title', { timeout: 15000 });
  const passwordFields = await page.locator('input[type="password"]').count();
  if (passwordFields >= 3) pass('account password form');
  else fail(`account password form has ${passwordFields} password fields`);

  await page.goto(`${WEB_URL}/reports`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.report-menu-item', { timeout: 15000 });
  const downloadPromise = page.waitForEvent('download', { timeout: 15000 });
  await page.getByRole('button', { name: /export csv/i }).click();
  const download = await downloadPromise;
  if (download.suggestedFilename().endsWith('.csv')) {
    pass(`report CSV download (${download.suggestedFilename()})`);
  } else {
    fail('report CSV download did not produce a .csv file');
  }
} finally {
  await browser.close();
}

console.log(`\n${issues.length} issue(s)`);
for (const issue of issues) console.log(`  - ${issue}`);
process.exitCode = issues.length ? 1 : 0;
// 2026-11-11T15:06:11Z smoke ui
