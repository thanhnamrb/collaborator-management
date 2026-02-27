import streamlit as st
from datetime import date

st.title("📝 Hệ thống Quản lý Công việc")

# Tạo một khu vực đóng khung để nhập liệu (Form)
with st.form("form_giao_viec"):
    st.subheader("Giao công việc mới")
    
    # 1. Ô nhập chữ (Tên công việc)
    ten_cong_viec = st.text_input("Tên công việc:")
    
    # 2. Menu xổ xuống (Chọn nhân viên)
    nguoi_nhan = st.selectbox("Giao cho ai?", ["Nhân viên A", "Nhân viên B", "Nhân viên C"])
    
    # 3. Ô chọn ngày tháng (Deadline)
    han_chot = st.date_input("Hạn chót (Deadline):", min_value=date.today())
    
    # 4. Ô nhập văn bản dài (Mô tả chi tiết)
    mo_ta = st.text_area("Mô tả chi tiết (không bắt buộc):")
    
    # 5. Nút bấm xác nhận
    nut_gui = st.form_submit_button("Giao việc")
    
    # Kịch bản xảy ra khi bấm nút "Giao việc"
    if nut_gui:
        if ten_cong_viec == "":
            st.error("Vui lòng nhập tên công việc!")
        else:
            st.success(f"Đã giao việc '{ten_cong_viec}' cho {nguoi_nhan} với hạn chót là {han_chot}!")
