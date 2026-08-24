import { expect, test } from '@playwright/test';
import path from 'node:path';

const inputDir = path.resolve(process.cwd(), '../data/demonstration/inputs');

test('runs the test-only scripted local model and shows verifier acceptance', async ({
  page,
}) => {
  await page.goto('/');
  await page.getByRole('button', { name: /Frozen demonstration preset/ }).click();
  await page.getByRole('button', { name: 'Create batch' }).click();
  for (const file of [
    'razorpay_recon.csv',
    'bank_statement.csv',
    'general_ledger.csv',
    'batch_policy.json',
  ]) {
    await page
      .locator('input[type="file"]')
      .first()
      .setInputFiles(path.join(inputDir, file));
  }
  await expect(
    page.getByText(
      'All four sources are present. The server reports this batch ready.',
    ),
  ).toBeVisible({ timeout: 60_000 });
  await page.getByRole('button', { name: 'Run reconciliation' }).click();
  await expect(page).toHaveURL(/\/overview$/, { timeout: 60_000 });
  const batchUrl = page.url().replace(/\/overview$/, '');
  await page.goto(`${batchUrl}/settlements/set_3102_p08`);
  const investigate = page.getByRole('button', {
    name: 'Investigate ambiguous evidence',
  });
  await expect(investigate).toBeEnabled();
  await investigate.click();
  await expect(page.getByText('Verifier accepted.')).toBeVisible({ timeout: 30_000 });
  await expect(investigate).toBeDisabled();
  await expect(page.getByText('cleared_with_explanation')).toBeVisible();
});
