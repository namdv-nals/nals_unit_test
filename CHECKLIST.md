## Checklist

#### 1. Kiểm thử các trường hợp đầu vào
- ✅ **Không có đơn hàng nào trong database của user** → Kỳ vọng: `False`.
- ✅ **Database ném ngoại lệ khi truy vấn danh sách đơn hàng** → Kỳ vọng: `False`.
- ✅ **Có danh sách đơn hàng hợp lệ** → Kỳ vọng: `True`, xử lý từng đơn hàng đúng logic.

#### 2. Kiểm thử các loại đơn hàng (handlers)
- ✅ **Đơn hàng loại A:**
  - File ghi thành công → `status = 'exported'`.
  - Ghi file thất bại → `status = 'export_failed'`.
  - amount > 150 → Ghi chú "High value order".

- ✅ **Đơn hàng loại B:**
  - API trả về success và data >= 50, amount < 100 → `status = 'processed'`.
  - API trả về success và data < 50 hoặc flag=True → `status = 'pending'`.
  - API trả về lỗi → `status = 'api_error'`.
  - API ném ngoại lệ → `status = 'api_failure'`.

- ✅ **Đơn hàng loại C:**
  - flag=True → `status = 'completed'`.
  - flag=False → `status = 'in_progress'`.

- ✅ **Đơn hàng không xác định** → `status = 'unknown_type'`.

#### 3. Kiểm thử cập nhật trạng thái đơn hàng
- ✅ **Database cập nhật trạng thái thành công** → Không thay đổi logic.
- ✅ **Database ném ngoại lệ** → `status = 'db_error'`.

#### 4. Kiểm thử tính toán priority
- ✅ **amount > 200** → `priority = 'high'`.
- ✅ **amount <= 200** → `priority = 'low'`.
