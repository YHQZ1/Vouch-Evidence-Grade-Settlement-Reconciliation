import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import path from 'node:path'

const inputDir = path.resolve(process.cwd(), '../data/demonstration/inputs')

async function expectAccessible(page: Page) {
  await page.mouse.move(0, 0)
  await page.waitForTimeout(250)
  const result = await new AxeBuilder({ page }).analyze()
  expect(result.violations.filter((violation) => ['serious', 'critical'].includes(violation.impact ?? ''))).toEqual([])
}

test('completes the frozen evidence-first flow with provenance, exports, and keyboard review', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')
  await expectAccessible(page)
  await page.getByRole('button', { name: /Frozen demonstration preset/ }).click()
  await page.getByRole('button', { name: 'Create batch' }).click()
  await expect(page.getByRole('heading', { name: 'Attach immutable source records' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Start a new batch' })).toBeEnabled()
  await expectAccessible(page)
  const files = ['razorpay_recon.csv', 'bank_statement.csv', 'general_ledger.csv', 'batch_policy.json']
  for (const file of files) await page.locator('input[type="file"]').first().setInputFiles(path.join(inputDir, file))
  await expect(page.getByText('All four sources are present. The server reports this batch ready.')).toBeVisible({ timeout: 60_000 })
  await page.getByRole('button', { name: 'Run reconciliation' }).click()
  await expect(page).toHaveURL(/\/overview$/, { timeout: 60_000 })
  await expect(page.getByText('Close blocked', { exact: true })).toBeVisible()
  await expect(page.getByText(/12 settlements/)).toBeVisible()
  await expectAccessible(page)
  await page.screenshot({ path: 'test-results/overview-1440x900.png', fullPage: true })
  await page.setViewportSize({ width: 1024, height: 768 })
  await expectAccessible(page)
  await page.screenshot({ path: 'test-results/overview-1024x768.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  const mobileSidebar = page.locator('#batch-review-sidebar')
  await expect(mobileSidebar).toHaveAttribute('aria-hidden', 'true')
  await expect(mobileSidebar).toHaveAttribute('inert', '')
  await page.getByRole('button', { name: 'Toggle navigation' }).focus()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('button', { name: 'Vouch' })).toBeFocused()
  await page.getByRole('button', { name: 'Toggle navigation' }).click()
  await expect(page.getByRole('navigation', { name: 'Batch review' })).toBeVisible()
  await page.getByRole('link', { name: 'Settlements' }).click()
  await expect(page.getByRole('heading', { name: 'Settlements' })).toBeVisible()
  await expectAccessible(page)
  await page.screenshot({ path: 'test-results/settlements-390x844.png', fullPage: true })
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.getByRole('link', { name: 'Settlements' }).click()
  await expect(page.getByRole('heading', { name: 'Settlements' })).toBeVisible()
  await expectAccessible(page)
  await page.locator('tbody a').first().click()
  await expect(page.getByRole('heading', { name: 'Razorpay → Bank → Ledger' })).toBeVisible()
  await expect(page.getByText('Accepted, proposed, rejected')).toBeVisible()
  await expectAccessible(page)
  await page.getByRole('button', { name: 'Explain decision' }).click()
  const dialog = page.getByRole('dialog', { name: 'Audit explanation' })
  await expect(dialog).toBeVisible()
  await dialog.locator('button[aria-expanded]').first().click()
  await expect(dialog.getByText('Decision-cited source IDs')).toBeVisible()
  await expectAccessible(page)
  await dialog.focus()
  await page.keyboard.press('Shift+Tab')
  await page.keyboard.press('Tab')
  await expect(page.getByRole('button', { name: 'Close audit explanation' })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: 'Explain decision' })).toBeFocused()
  await page.getByRole('link', { name: 'Exceptions' }).click()
  await expect(page.getByRole('heading', { name: 'Exceptions' })).toBeVisible()
  await expect(page.locator('main article')).toHaveCount(22)
  await expect(page.getByText('Cited source IDs — each copyable').first()).toBeVisible()
  await expectAccessible(page)
  const exports = [
    ['Result', /reconciliation-result.*\.json$/],
    ['Exceptions', /exceptions.*\.json$/],
    ['Audit events', /audit.*\.json$/],
  ] as const
  for (const [label, filename] of exports) {
    const download = page.waitForEvent('download')
    await page.getByRole('button', { name: label, exact: true }).click()
    expect((await download).suggestedFilename()).toMatch(filename)
  }
  await page.goto('/batches/not-a-real-batch/overview')
  await expect(page.getByRole('heading', { name: 'Evidence unavailable' })).toBeVisible()
  await expectAccessible(page)
})
