import os
import sys
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

engine = create_engine(os.getenv('DATABASE_URL'))

with engine.connect() as conn:
    # 1. Kiểm tra và thêm cột amenities vào bảng rooms nếu chưa có
    cols = [row[0] for row in conn.execute(text("SHOW COLUMNS FROM rooms")).fetchall()]
    if 'amenities' not in cols:
        print("Adding amenities column to rooms table...")
        conn.execute(text("ALTER TABLE rooms ADD COLUMN amenities TEXT DEFAULT NULL AFTER description"))
        conn.commit()
        print("Column 'amenities' added to rooms table.")
    else:
        print("Column 'amenities' already exists in rooms table.")

    # 2. Cập nhật dữ liệu tiện ích cho các phòng hiện tại
    # Đặc biệt phòng vip viyyyy (id 10) từ ảnh của người dùng
    conn.execute(text("""
        UPDATE rooms 
        SET amenities = :amenities 
        WHERE name = 'vip viyyyy' OR id = 10
    """), {"amenities": json.dumps(["Màn hình", "Wifi", "Video", "Đồ uống"], ensure_ascii=False)})

    # Cập nhật phòng VIP (id 3)
    conn.execute(text("""
        UPDATE rooms 
        SET amenities = :amenities 
        WHERE id = 3
    """), {"amenities": json.dumps(["Màn hình trực tuyến", "Micro hội nghị", "Wifi", "Máy chiếu 4K"], ensure_ascii=False)})

    # Cập nhật phòng A (id 1)
    conn.execute(text("""
        UPDATE rooms 
        SET amenities = :amenities 
        WHERE id = 1
    """), {"amenities": json.dumps(["Màn hình TV", "Wifi tốc độ cao", "Bảng trắng"], ensure_ascii=False)})

    # Cập nhật phòng B (id 2)
    conn.execute(text("""
        UPDATE rooms 
        SET amenities = :amenities 
        WHERE id = 2
    """), {"amenities": json.dumps(["Máy chiếu", "Wifi", "Hệ thống âm thanh", "Bảng viết"], ensure_ascii=False)})

    conn.commit()
    print("Updated rooms with default amenities!")

    # 3. Khởi tạo một số thiết bị kho (equipments) để kho có sẵn thiết bị mượn thêm
    existing_eq_count = conn.execute(text("SELECT COUNT(*) FROM equipments")).scalar()
    if existing_eq_count == 0:
        print("Seeding default warehouse equipments...")
        default_equipments = [
            ("Màn hình di động 55 inch", "DISP-55", "Hiển thị", 3, "Màn hình di động chuyên dụng cho thuyết trình"),
            ("Máy chiếu không dây Full HD", "PROJ-WF", "Trình chiếu", 4, "Máy chiếu độ sáng cao hỗ trợ AirPlay/Miracast"),
            ("Micro không dây hội nghị", "MIC-WL", "Âm thanh", 8, "Bộ 2 micro không dây chống hú"),
            ("Loa họp trực tuyến Jabra Speak", "SPK-JB", "Âm thanh", 5, "Loa hội nghị tích hợp mic định hướng 360 độ"),
            ("Bút trình chiếu Laser đa năng", "PEN-LZ", "Phụ kiện", 6, "Bút laser kèm điều khiển slide qua USB"),
            ("Bộ chuyển đổi HDMI & USB-C", "CAB-AD", "Phụ kiện", 12, "Bộ cáp chuyển đa cổng cho laptop và điện thoại"),
            ("Bảng Flipchart di động", "BRD-FC", "Văn phòng phẩm", 4, "Bảng kẹp giấy viết di động có bánh xe"),
        ]
        for name, code, cat, qty, desc in default_equipments:
            conn.execute(text("""
                INSERT INTO equipments (name, code, category, total_qty, description, is_active, created_at)
                VALUES (:name, :code, :category, :total_qty, :description, 1, NOW())
            """), {
                "name": name,
                "code": code,
                "category": cat,
                "total_qty": qty,
                "description": desc
            })
        conn.commit()
        print(f"Seeded {len(default_equipments)} equipments successfully!")
    else:
        print(f"Equipments table already has {existing_eq_count} items.")

print("Patch DB completed successfully!")
