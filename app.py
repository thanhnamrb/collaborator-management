import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="App Giao Việc", layout="wide")

st.title("📝 Hệ thống Quản lý Công việc")

# 1. TẠO BỘ NHỚ CHO APP (Database giả lập)
# Nếu app chưa có danh sách công việc, hãy tạo một danh sách trống
if 'danh_sach_cong_viec' not in st.session_state:
    st.session_state.danh_sach_cong_viec = []

# Chia màn hình làm 2 cột: Cột trái để Giao việc, Cột phải để Xem tiến độ
cot_trai, cot_phai = st.columns([1, 2])

# 2. KHU VỰC GIAO VIỆC (Cột trái)
with cot_trai:
    with st.form("form_giao_viec"):
        st.subheader("Giao công việc mới")
        ten_cong_viec = st.text_input("Tên công việc:")
        nguoi_nhan = st.selectbox("Giao cho ai?", ["Nhân viên A", "Nhân viên B", "Nhân viên C"])
        han_chot = st.date_input("Hạn chót (Deadline):", min_value=date.today())
        mo_ta = st.text_area("Mô tả chi tiết:")
        
        nut_gui = st.form_submit_button("Giao việc")
        
        # Xử lý khi bấm nút
        if nut_gui:
            if ten_cong_viec == "":
                st.error("Vui lòng nhập tên công việc!")
            else:
                # Gói gọn thông tin thành 1 "hồ sơ" và lưu vào bộ nhớ
                cong_viec_moi = {
                    "Tên công việc": ten_cong_viec,
                    "Người nhận": nguoi_nhan,
                    "Hạn chót": han_chot.strftime("%d/%m/%Y"),
                    "Mô tả": mo_ta,
                    "Trạng thái": "Mới giao" # Mặc định khi vừa giao
                }
                st.session_state.danh_sach_cong_viec.append(cong_viec_moi)
                st.success("Đã lưu công việc thành công!")

# 3. KHU VỰC HIỂN THỊ DANH SÁCH (Cột phải)
with cot_phai:
    st.subheader("📋 Bảng theo dõi tiến độ")
    
    # Kiểm tra xem bộ nhớ có việc nào chưa
    if len(st.session_state.danh_sach_cong_viec) > 0:
        # Chuyển dữ liệu thành dạng Bảng (DataFrame) để hiển thị chuyên nghiệp
        df = pd.DataFrame(st.session_state.danh_sach_cong_viec)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Hiện tại chưa có công việc nào. Hãy giao việc ở cột bên trái!")
