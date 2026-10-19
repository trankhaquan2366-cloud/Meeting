import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Kiểm thử Tiêu chuẩn Khả năng truy cập (Accessibility)', () => {

  test('TC-A11Y-01: Giao diện Dashboard không chứa lỗi WCAG nghiêm trọng', async ({ page }) => {
    await page.goto('http://localhost:8000/dashboard?preview=meeting');

    // Chạy phân tích WCAG 2.1 AA trên giao diện
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    // Lọc các lỗi mức độ "critical" hoặc "serious"
    const criticalViolations = accessibilityScanResults.violations.filter(
      v => v.impact === 'critical' || v.impact === 'serious'
    );

    // Xác nhận không có lỗi nghiêm trọng
    expect(criticalViolations.length).toEqual(0);
  });

});