import { test, expect } from '@playwright/test';

test.describe('Kiểm thử Chức năng Cơ bản Phòng họp', () => {

  test.beforeEach(async ({ page }) => {
    // Mở trang chủ hoặc trang tạo phòng
    await page.goto('/');
  });

  test('TC01: Người dùng tạo phòng họp thành công và bật/tắt thiết bị', async ({ page }) => {
    // 1. Nhập tên người dùng (nếu ứng dụng yêu cầu)
    const nameInput = page.getByPlaceholder(/tên của bạn|your name/i);
    if (await nameInput.isVisible()) {
      await nameInput.fill('Tester 01');
    }

    // 2. Nhấn nút Tạo phòng họp
    await page.getByRole('button', { name: /tạo phòng|create room|start meeting/i }).click();

    // 3. Xóa/Đợi chuyển hướng vào giao diện phòng họp (URL chứa /room/ hoặc /meeting/)
    await expect(page).toHaveURL(/\/room|\/meeting|\/j/i);

    // 4. Kiểm tra thành phần Video hiển thị
    const localVideo = page.locator('video');
    await expect(localVideo.first()).toBeVisible({ timeout: 10000 });

    // 5. Kiểm thử Nút Mute Microphone
    const micButton = page.getByRole('button', { name: /mic|mute|micro/i });
    await expect(micButton).toBeVisible();
    await micButton.click(); // Bấm tắt mic
    
    // Kiểm tra class hoặc state thay đổi (tùy thuộc UI của bạn)
    await expect(micButton).toHaveAttribute('data-active', 'false'); // Ví dụ attribute

    // 6. Kiểm thử Nút Toggle Camera
    const cameraButton = page.getByRole('button', { name: /camera|video/i });
    await expect(cameraButton).toBeVisible();
    await cameraButton.click(); // Bấm tắt camera
  });

});