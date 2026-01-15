"""
Script để tạo sample FAQs cho testing

Run:
    source venv/bin/activate
    python scripts/create_sample_faqs.py

Tạo các FAQs mẫu cho Navitech về:
- Chính sách đổi trả
- Bảo hành
- Thanh toán
- Giao hàng
- etc.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from db import SessionLocal
from models.faq import FAQCreateModel
from services.faq import FAQService
from embedding.faq_embedding import get_faq_embedding


# Sample user ID - Thay bằng user ID thật trong database
SAMPLE_USER_ID = uuid.uuid4()  # Hoặc lấy từ database

SAMPLE_FAQS = [
    {
        "question": "Chính sách đổi trả sản phẩm của Navitech như thế nào?",
        "answer": """Navitech hỗ trợ đổi trả sản phẩm trong vòng 7 ngày kể từ ngày mua hàng với các điều kiện sau:

1. Sản phẩm còn nguyên tem, hộp, phụ kiện đầy đủ
2. Sản phẩm chưa qua sử dụng, không có dấu hiệu va đập, trầy xước
3. Có hóa đơn mua hàng hợp lệ

Trường hợp đổi trả:
- Lỗi từ nhà sản xuất: Đổi sản phẩm mới hoặc hoàn tiền 100%
- Sản phẩm không đúng mô tả: Đổi sản phẩm khác hoặc hoàn tiền
- Khách hàng đổi ý: Chỉ áp dụng với một số sản phẩm, phí đổi trả 10%

Để đổi trả, vui lòng liên hệ hotline: 1900-xxxx hoặc mang sản phẩm đến cửa hàng gần nhất.""",
        "category": "chinh-sach",
        "priority": 10
    },
    {
        "question": "Navitech có chính sách bảo hành như thế nào?",
        "answer": """Chính sách bảo hành tại Navitech:

🔧 THỜI GIAN BẢO HÀNH:
- Laptop, PC: 12-24 tháng (tùy hãng)
- Điện thoại, tablet: 12 tháng
- Phụ kiện: 3-6 tháng

📋 ĐIỀU KIỆN BẢO HÀNH:
- Tem bảo hành còn nguyên vẹn
- Có phiếu bảo hành/hóa đơn
- Lỗi do nhà sản xuất

❌ KHÔNG BẢO HÀNH:
- Va đập, rơi vỡ, vào nước
- Tự ý sửa chữa
- Sử dụng sai cách

📞 Liên hệ bảo hành: 1900-xxxx (8h-20h hàng ngày)""",
        "category": "bao-hanh",
        "priority": 9
    },
    {
        "question": "Navitech hỗ trợ những hình thức thanh toán nào?",
        "answer": """Navitech chấp nhận các hình thức thanh toán sau:

💳 THANH TOÁN ONLINE:
- Thẻ ATM nội địa (có Internet Banking)
- Thẻ tín dụng Visa/Mastercard/JCB
- Ví điện tử: MoMo, ZaloPay, VNPay
- Chuyển khoản ngân hàng

💵 THANH TOÁN TẠI CỬA HÀNG:
- Tiền mặt
- Quẹt thẻ ATM/Credit
- Trả góp 0% (áp dụng đơn hàng từ 3 triệu)

🏦 TRẢ GÓP:
- Qua thẻ tín dụng: 3-12 tháng
- Qua công ty tài chính: Home Credit, FE Credit, HD Saison
- Lãi suất: 0% với đơn từ 5 triệu

Mọi giao dịch đều được bảo mật an toàn.""",
        "category": "thanh-toan",
        "priority": 8
    },
    {
        "question": "Thời gian giao hàng của Navitech là bao lâu?",
        "answer": """Thời gian giao hàng tại Navitech:

📦 NỘI THÀNH HÀ NỘI/TP.HCM:
- Giao nhanh 2-4 giờ (đơn hàng < 10kg)
- Giao tiêu chuẩn: 1-2 ngày

🚚 TỈNH THÀNH KHÁC:
- Miền Bắc/Nam: 2-3 ngày
- Miền Trung: 3-5 ngày
- Vùng xa: 5-7 ngày

✨ GIAO HÀNG MIỄN PHÍ:
- Đơn từ 500k: miễn phí nội thành
- Đơn từ 2 triệu: miễn phí toàn quốc

📞 Tracking đơn hàng:
- SMS/Email thông báo tiến độ
- Hotline: 1900-xxxx
- Website: navitech.vn/tra-don-hang

Lưu ý: Thời gian có thể thay đổi tùy tình trạng kho và thời tiết.""",
        "category": "giao-hang",
        "priority": 7
    },
    {
        "question": "Làm sao để kiểm tra tình trạng đơn hàng?",
        "answer": """Bạn có thể kiểm tra đơn hàng qua các cách sau:

🔍 WEBSITE:
1. Truy cập navitech.vn/tra-don-hang
2. Nhập mã đơn hàng hoặc số điện thoại
3. Xem chi tiết tình trạng

📱 ỨNG DỤNG MOBILE:
1. Mở app Navitech
2. Vào mục "Đơn hàng của tôi"
3. Chọn đơn hàng cần xem

📞 HOTLINE: 1900-xxxx
- Thời gian: 8h-20h hàng ngày
- Cung cấp mã đơn hàng để tra cứu

📧 EMAIL: Kiểm tra email đăng ký
- Thông báo tự động khi đơn hàng thay đổi trạng thái

Trạng thái đơn hàng:
✅ Đã xác nhận → Đang đóng gói → Đang giao → Đã giao""",
        "category": "don-hang",
        "priority": 6
    },
    {
        "question": "Navitech có cửa hàng ở đâu?",
        "answer": """Hệ thống cửa hàng Navitech:

🏢 HÀ NỘI:
- CN1: 123 Nguyễn Trãi, Thanh Xuân
- CN2: 456 Láng Hạ, Đống Đa
- CN3: 789 Cầu Giấy, Cầu Giấy

🏢 TP. HỒ CHÍ MINH:
- CN1: 321 Lê Văn Việt, Quận 9
- CN2: 654 Cộng Hòa, Tân Bình
- CN3: 987 Nguyễn Văn Linh, Quận 7

🏢 CÁC TỈNH:
- Đà Nẵng: 111 Hùng Vương, Hải Châu
- Cần Thơ: 222 Nguyễn Văn Cừ, Ninh Kiều
- Hải Phòng: 333 Lê Thánh Tông, Máy Chai

⏰ Giờ mở cửa: 8h00 - 21h00 (tất cả các ngày)
🌐 Xem bản đồ: navitech.vn/he-thong-cua-hang
📞 Hotline: 1900-xxxx""",
        "category": "lien-he",
        "priority": 5
    },
    {
        "question": "Tôi muốn hủy đơn hàng thì làm thế nào?",
        "answer": """Quy trình hủy đơn hàng tại Navitech:

✅ TRƯỚC KHI GIAO HÀNG:
- Hủy miễn phí, hoàn tiền 100% trong 2 giờ
- Sau 2 giờ: phí hủy 5% giá trị đơn
- Liên hệ ngay hotline: 1900-xxxx

🚚 ĐÃ GIAO HÀNG:
- Không hủy được, áp dụng chính sách đổi trả
- Từ chối nhận hàng khi shipper đến

💳 HOÀN TIỀN:
- Thanh toán online: 3-7 ngày làm việc
- Thanh toán COD: Không phát sinh
- Trả góp: Liên hệ để hủy khoản vay

📝 CÁCH HỦY:
1. Gọi hotline: 1900-xxxx
2. Chat với CSKH trên website
3. Email: support@navitech.vn

Lưu ý: Cung cấp mã đơn hàng và lý do hủy.""",
        "category": "don-hang",
        "priority": 7
    },
    {
        "question": "Sản phẩm bị lỗi trong thời gian bảo hành, tôi phải làm gì?",
        "answer": """Quy trình bảo hành khi sản phẩm lỗi:

📞 BƯỚC 1: LIÊN HỆ
- Hotline: 1900-xxxx
- Hoặc mang sản phẩm đến trung tâm bảo hành gần nhất

📋 BƯỚC 2: CHUẨN BỊ
- Sản phẩm + phụ kiện
- Phiếu bảo hành/hóa đơn
- CMND/CCCD

🔧 BƯỚC 3: KIỂM TRA
- Kỹ thuật viên kiểm tra lỗi
- Xác định bảo hành hay không
- Thời gian: 5-10 phút

⏱️ BƯỚC 4: SỬA CHỮA
- Lỗi nhỏ: Sửa trong ngày
- Lỗi lớn: 7-15 ngày (tùy linh kiện)
- Không sửa được: Đổi mới hoặc hoàn tiền

🎁 ƯU ĐÃI:
- Cho mượn sản phẩm thay thế (laptop, điện thoại)
- Miễn phí vận chuyển 2 chiều

📍 Trung tâm bảo hành: navitech.vn/bao-hanh""",
        "category": "bao-hanh",
        "priority": 9
    }
]


def create_sample_faqs(user_id: uuid.UUID):
    """Tạo sample FAQs cho một user"""
    db = SessionLocal()
    
    try:
        print(f"\n{'='*60}")
        print(f"CREATING SAMPLE FAQs FOR USER: {user_id}")
        print(f"{'='*60}\n")
        
        service = FAQService(db)
        faq_emb = get_faq_embedding()
        
        # Ensure Qdrant collection exists
        faq_emb.ensure_collection_exists()
        
        created_faqs = []
        
        for idx, faq_data in enumerate(SAMPLE_FAQS, 1):
            print(f"[{idx}/{len(SAMPLE_FAQS)}] Creating FAQ: {faq_data['question'][:60]}...")
            
            # Create in database
            faq_create = FAQCreateModel(
                user_id=user_id,
                question=faq_data["question"],
                answer=faq_data["answer"],
                category=faq_data["category"],
                priority=faq_data["priority"],
                is_active=True
            )
            
            faq = service.create_faq(faq_create)
            created_faqs.append(faq)
            
            # Sync to Qdrant
            success = faq_emb.sync_faq_to_qdrant(
                faq_id=faq.id,
                user_id=faq.user_id,
                question=faq.question,
                answer=faq.answer,
                category=faq.category,
                priority=faq.priority,
                is_active=faq.is_active
            )
            
            if success:
                print(f"   ✅ Created and synced to Qdrant")
            else:
                print(f"   ⚠️  Created but failed to sync")
        
        print(f"\n{'='*60}")
        print(f"✅ COMPLETED: Created {len(created_faqs)} FAQs")
        print(f"{'='*60}\n")
        
        # Print summary
        print("📋 Summary:")
        for faq in created_faqs:
            print(f"   - [{faq.category}] {faq.question[:50]}...")
        
        print(f"\n💡 Test với:")
        print(f"   User ID: {user_id}")
        print(f"   Query example: 'Chính sách đổi trả như thế nào?'")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    # Lấy user_id từ command line hoặc dùng mặc định
    if len(sys.argv) > 1:
        user_id = uuid.UUID(sys.argv[1])
    else:
        # Lấy user đầu tiên từ database
        from models.user import UserTable
        db = SessionLocal()
        try:
            first_user = db.query(UserTable).first()
            if first_user:
                user_id = first_user.id
                print(f"✅ Using first user in database: {user_id}")
            else:
                print("❌ No users found in database. Please create a user first.")
                sys.exit(1)
        finally:
            db.close()
    
    create_sample_faqs(user_id)
