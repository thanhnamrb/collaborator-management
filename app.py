import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import date

st.set_page_config(page_title="App Giao Việc", layout="wide")

# --- 1. KẾT NỐI GOOGLE SHEETS TRƯỚC (Để lấy data đăng nhập) ---
try:
    key_dict = json.loads(st.secrets["json_key"])
    creds = Credentials.from_service_account_info(
        key_dict, 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
    
    # !!! NHỚ DÁN LẠI LINK CỦA BẠN VÀO ĐÂY !!!
    file_gg_sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1jQFz2qqoDKLDDBKF97QXMfr_RcRv57vlGtIqHUBtK1w/edit?usp=sharing")
    
    # Lấy 2 tab riêng biệt
    sheet_congviec = file_gg_sheet.get_worksheet(0) # Tab đầu tiên (chứa công việc)
    sheet_taikhoan = file_gg_sheet.worksheet("TaiKhoan") # Tab thứ hai (chứa tài khoản)
    
    # Lấy dữ liệu
    data_congviec = sheet_congviec.get_all_records()
    df_congviec = pd.DataFrame(data_congviec)
    
    data_taikhoan = sheet_taikhoan.get_all_records()
    
    # Tự động lọc ra danh sách những ai là "Nhân viên" để đưa vào menu giao việc
    danh_sach_nhan_vien = [row["Tên tài khoản"] for row in data_taikhoan if row["Vai trò"] == "Nhân viên"]

except Exception as e:
    st.error("Lỗi kết nối database.")
    st.stop()


# --- 2. HỆ THỐNG ĐĂNG NHẬP (Lấy từ Google Sheets) ---
if 'nguoi_dung' not in st.session_state:
    st.session_state.nguoi_dung = None
if 'vai_tro' not in st.session_state:
    st.session_state.vai_tro = None

if st.session_state.nguoi_dung is None:
    st.title("🔐 Cổng Đăng Nhập")
    with st.form("form_dang_nhap"):
        # Chuyển thành ô nhập text thay vì chọn menu để chuyên nghiệp hơn
        tai_khoan_nhap = st.text_input("Tên tài khoản:") 
        mat_khau_nhap = st.text_input("Mật khẩu:", type="password")
        nut_dang_nhap = st.form_submit_button("Vào hệ thống")
        
        if nut_dang_nhap:
            dang_nhap_thanh_cong = False
            # Quét vòng lặp xem có tài khoản nào khớp không
            for user in data_taikhoan:
                if str(user["Tên tài khoản"]) == tai_khoan_nhap and str(user["Mật khẩu"]) == mat_khau_nhap:
                    st.session_state.nguoi_dung = user["Tên tài khoản"]
                    st.session_state.vai_tro = user["Vai trò"]
                    dang_nhap_thanh_cong = True
                    break
            
            if dang_nhap_thanh_cong:
                st.rerun()
            else:
                st.error("Sai tài khoản hoặc mật khẩu!")

# --- 3. BÊN TRONG ỨNG DỤNG ---
else:
    c1, c2 = st.columns([8, 1])
    with c1:
        st.write(f"Xin chào **{st.session_state.nguoi_dung}** | Vai trò: *{st.session_state.vai_tro}*")
    with c2:
        if st.button("Đăng xuất"):
            st.session_state.nguoi_dung = None
            st.session_state.vai_tro = None
            st.rerun()

    st.markdown("---")

    # KỊCH BẢN 1: QUẢN LÝ
    if st.session_state.vai_tro == "Quản lý":
        st.title("👨‍💼 Bảng Điều Khiển Quản Lý")
        
        # Chia giao diện thành 2 tab cho gọn gàng
        tab1, tab2 = st.tabs(["📝 Giao & Quản lý Công việc", "👥 Quản lý Nhân sự"])
        
        with tab1:
            cot_trai, cot_phai = st.columns([1, 2])
            with cot_trai:
                with st.form("form_giao_viec"):
                    st.subheader("Giao công việc mới")
                    ten_cong_viec = st.text_input("Tên công việc:")
                    
                    # Tự động load danh sách nhân viên từ database
                    if len(danh_sach_nhan_vien) > 0:
                        nguoi_nhan = st.selectbox("Giao cho ai?", danh_sach_nhan_vien)
                    else:
                        st.warning("Chưa có nhân viên nào. Hãy qua Tab 'Quản lý Nhân sự' để thêm!")
                        nguoi_nhan = None
                        
                    han_chot = st.date_input("Hạn chót (Deadline):", min_value=date.today())
                    mo_ta = st.text_area("Mô tả chi tiết:")
                    nut_gui = st.form_submit_button("Giao việc")
                    
                    if nut_gui and ten_cong_viec != "" and nguoi_nhan is not None:
                        han_chot_str = han_chot.strftime("%d/%m/%Y")
                        sheet_congviec.append_row([ten_cong_viec, nguoi_nhan, han_chot_str, mo_ta, "Mới giao"])
                        st.success("Đã giao việc thành công!")
                        st.rerun()
            
            with cot_phai:
                st.subheader("📋 Bảng tổng hợp tiến độ")
                st.dataframe(df_congviec, use_container_width=True)
                
        with tab2:
            st.subheader("Thêm tài khoản mới")
            with st.form("form_tao_tai_khoan", clear_on_submit=True):
                tk_moi = st.text_input("Tên tài khoản mới (Ví dụ: Nguyễn Văn A):")
                mk_moi = st.text_input("Mật khẩu:")
                vt_moi = st.selectbox("Vai trò:", ["Nhân viên", "Quản lý"])
                btn_tao_tk = st.form_submit_button("Tạo tài khoản")
                
                if btn_tao_tk:
                    # Kiểm tra xem tài khoản đã tồn tại chưa
                    danh_sach_tk_hien_tai = [str(r["Tên tài khoản"]) for r in data_taikhoan]
                    if tk_moi in danh_sach_tk_hien_tai:
                        st.error("Tên tài khoản này đã tồn tại, vui lòng chọn tên khác!")
                    elif tk_moi == "" or mk_moi == "":
                        st.error("Không được để trống Tên tài khoản hoặc Mật khẩu!")
                    else:
                        sheet_taikhoan.append_row([tk_moi, mk_moi, vt_moi])
                        st.success(f"Đã tạo thành công tài khoản: {tk_moi}")
                        st.rerun()
            
            st.subheader("Danh sách Tài khoản Hệ thống")
            # Hiện danh sách tài khoản (có thể ẩn cột mật khẩu nếu muốn bảo mật, nhưng nội bộ thì để xem cũng tiện)
            df_taikhoan = pd.DataFrame(data_taikhoan)
            st.dataframe(df_taikhoan, use_container_width=True)

    # KỊCH BẢN 2: NHÂN VIÊN (Giữ nguyên như cũ)
    else:
        st.title("👷 Bảng Làm Việc")
        st.subheader(f"📋 Công việc của {st.session_state.nguoi_dung}")
        
        cong_viec_cua_toi = []
        for index, row in enumerate(data_congviec, start=2): 
            if row['Người nhận'] == st.session_state.nguoi_dung:
                cong_viec_cua_toi.append({"dong_so": index, "du_lieu": row})
                
        if len(cong_viec_cua_toi) > 0:
            for task in cong_viec_cua_toi:
                with st.expander(f"📌 {task['du_lieu']['Tên công việc']} (Hạn: {task['du_lieu']['Hạn chót']})", expanded=True):
                    st.write(f"**Mô tả:** {task['du_lieu']['Mô tả']}")
                    danh_sach_trang_thai = ["Mới giao", "Đang làm", "Hoàn thành"]
                    trang_thai_hien_tai = task['du_lieu']['Trạng thái']
                    if trang_thai_hien_tai not in danh_sach_trang_thai:
                        trang_thai_hien_tai = "Mới giao"
                        
                    trang_thai_moi = st.radio(
                        "Cập nhật tiến độ:", 
                        danh_sach_trang_thai, 
                        index=danh_sach_trang_thai.index(trang_thai_hien_tai),
                        key=f"radio_{task['dong_so']}",
                        horizontal=True
                    )
                    
                    if st.button("Lưu thay đổi", key=f"btn_{task['dong_so']}"):
                        if trang_thai_moi != task['du_lieu']['Trạng thái']:
                            # Cập nhật vào Tab Công Việc (sheet_congviec)
                            sheet_congviec.update_cell(task['dong_so'], 5, trang_thai_moi)
                            st.success("Đã cập nhật tiến độ lên hệ thống!")
                            st.rerun()
        else:
            st.success("Tuyệt vời! Bạn hiện không có công việc nào tồn đọng.")
