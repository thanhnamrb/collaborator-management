import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import date

st.set_page_config(page_title="App Giao Việc", layout="wide")

# --- 1. HỆ THỐNG ĐĂNG NHẬP ---
# Tạo bộ nhớ để app nhớ ai đang đăng nhập
if 'nguoi_dung' not in st.session_state:
    st.session_state.nguoi_dung = None

# Nếu chưa đăng nhập -> Hiện màn hình hỏi Mật khẩu
if st.session_state.nguoi_dung is None:
    st.title("🔐 Cổng Đăng Nhập")
    
    with st.form("form_dang_nhap"):
        tai_khoan = st.selectbox("Bạn là ai?", ["Quan ly", "Nhân viên A", "Nhân viên B", "Nhân viên C"])
        mat_khau = st.text_input("Mật khẩu:", type="password") # type="password" giúp biến chữ thành dấu ***
        nut_dang_nhap = st.form_submit_button("Vào hệ thống")
        
        if nut_dang_nhap:
            # Kiểm tra xem mật khẩu nhập vào có khớp với mật khẩu trong két sắt không
            mat_khau_dung = st.secrets["taikhoan"][tai_khoan]
            
            if mat_khau == mat_khau_dung:
                st.session_state.nguoi_dung = tai_khoan
                st.rerun() # Tải lại trang để vào bên trong
            else:
                st.error("Sai mật khẩu! Vui lòng thử lại.")

# Nếu đã đăng nhập thành công -> Hiện app làm việc
else:
    st.title("📝 Hệ thống Quản lý Công việc")
    
    # Nút đăng xuất (đặt ở góc phải)
    c1, c2 = st.columns([8, 1])
    with c1:
        st.write(f"Xin chào, **{st.session_state.nguoi_dung}**!")
    with c2:
        if st.button("Đăng xuất"):
            st.session_state.nguoi_dung = None
            st.rerun()

    st.markdown("---") # Đường kẻ ngang

    # --- 2. KẾT NỐI GOOGLE SHEETS ---
    key_dict = json.loads(st.secrets["json_key"])
    creds = Credentials.from_service_account_info(
        key_dict, 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
    
    # LƯU Ý: NHỚ ĐỔI LẠI ĐƯỜNG LINK GOOGLE SHEETS CỦA BẠN VÀO ĐÂY NHÉ
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1jQFz2qqoDKLDDBKF97QXMfr_RcRv57vlGtIqHUBtK1w/edit?usp=sharing").sheet1

    # --- 3. PHÂN QUYỀN HIỂN THỊ ---
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    # KỊCH BẢN 1: NẾU LÀ QUẢN LÝ
    if st.session_state.nguoi_dung == "Quan ly":
        cot_trai, cot_phai = st.columns([1, 2])
        
        with cot_trai:
            with st.form("form_giao_viec"):
                st.subheader("Giao công việc mới")
                ten_cong_viec = st.text_input("Tên công việc:")
                nguoi_nhan = st.selectbox("Giao cho ai?", ["Nhân viên A", "Nhân viên B", "Nhân viên C"])
                han_chot = st.date_input("Hạn chót (Deadline):", min_value=date.today())
                mo_ta = st.text_area("Mô tả chi tiết:")
                nut_gui = st.form_submit_button("Giao việc")
                
                if nut_gui and ten_cong_viec != "":
                    han_chot_str = han_chot.strftime("%d/%m/%Y")
                    sheet.append_row([ten_cong_viec, nguoi_nhan, han_chot_str, mo_ta, "Mới giao"])
                    st.success("Đã giao việc thành công!")
                    st.rerun() # Tải lại để bảng cập nhật luôn
        
        with cot_phai:
            st.subheader("📋 Tất cả công việc (Góc nhìn Quản lý)")
            st.dataframe(df, use_container_width=True)

    # KỊCH BẢN 2: NẾU LÀ NHÂN VIÊN
    else:
        st.subheader(f"📋 Công việc của riêng bạn ({st.session_state.nguoi_dung})")
        
        if not df.empty:
            # Thuật toán lọc: Chỉ lấy những dòng mà cột 'Người nhận' trùng với tên đang đăng nhập
            df_nhan_vien = df[df['Người nhận'] == st.session_state.nguoi_dung]
            
            if len(df_nhan_vien) > 0:
                st.dataframe(df_nhan_vien, use_container_width=True)
            else:
                st.success("Tuyệt vời! Bạn hiện không có công việc nào tồn đọng.")
        else:
            st.info("Hệ thống chưa có công việc nào.")
