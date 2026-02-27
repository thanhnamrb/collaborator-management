import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import date, datetime, timedelta

st.set_page_config(page_title="App Giao Việc", layout="wide")

# --- 1. KẾT NỐI GOOGLE SHEETS ---
try:
    key_dict = json.loads(st.secrets["json_key"])
    creds = Credentials.from_service_account_info(
        key_dict, 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
    
    # !!! DÁN LINK GOOGLE SHEETS CỦA BẠN VÀO ĐÂY !!!
    file_gg_sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1jQFz2qqoDKLDDBKF97QXMfr_RcRv57vlGtIqHUBtK1w/edit?usp=sharing")
    
    sheet_congviec = file_gg_sheet.get_worksheet(0) 
    sheet_taikhoan = file_gg_sheet.worksheet("TaiKhoan")
    
    data_congviec = sheet_congviec.get_all_records()
    data_taikhoan = sheet_taikhoan.get_all_records()
    
    danh_sach_nhan_vien = [row["Tên tài khoản"] for row in data_taikhoan if row["Vai trò"] == "Nhân viên"]

except Exception as e:
    st.error(f"Lỗi kết nối Google Sheets: {e}")
    st.stop()


# --- THUẬT TOÁN TÍNH TOÁN DEADLINE TỰ ĐỘNG ---
if len(data_congviec) > 0:
    df_congviec = pd.DataFrame(data_congviec)
    df_congviec['dong_so_goc'] = df_congviec.index + 2 
    
    # Ép kiểu cột Hạn chót ra định dạng thời gian để tính toán
    df_congviec['ngay_gio_chuan'] = pd.to_datetime(df_congviec['Hạn chót'], format='%d/%m/%Y %H:%M', errors='coerce')
    
    # Lấy thời gian hiện tại của hệ thống
    now = datetime.now()
    
    # Hàm tự động phân loại mức độ ưu tiên
    def danh_gia_uu_tien(deadline, trang_thai):
        # Nếu đã hoàn thành rồi thì cho xuống chót cùng
        if trang_thai == "Hoàn thành":
            return 5, "✅ Đã xong"
            
        if pd.isna(deadline):
            return 4, "⚪ Không rõ hạn"
            
        thoi_gian_con_lai = deadline - now
        
        if thoi_gian_con_lai.total_seconds() < 0:
            return 1, "🚨 Quá hạn"
        elif thoi_gian_con_lai <= timedelta(hours=24):
            return 2, "🔥 Khẩn cấp (<24h)"
        elif thoi_gian_con_lai <= timedelta(days=3):
            return 3, "🟡 Sắp tới hạn (1-3 ngày)"
        else:
            return 4, "🟢 Bình thường"

    # Áp dụng hàm tính toán cho từng dòng công việc
    df_congviec[['diem_uu_tien', 'nhan_uu_tien']] = df_congviec.apply(
        lambda row: pd.Series(danh_gia_uu_tien(row['ngay_gio_chuan'], row.get('Trạng thái', ''))), axis=1
    )
    
    # SẮP XẾP: Việc khẩn cấp nhất + gần hạn nhất lên đầu
    df_congviec = df_congviec.sort_values(by=['diem_uu_tien', 'ngay_gio_chuan'])
else:
    df_congviec = pd.DataFrame()


# --- 2. HỆ THỐNG ĐĂNG NHẬP ---
if 'nguoi_dung' not in st.session_state:
    st.session_state.nguoi_dung = None
if 'vai_tro' not in st.session_state:
    st.session_state.vai_tro = None

if st.session_state.nguoi_dung is None:
    st.title("🔐 Cổng Đăng Nhập")
    with st.form("form_dang_nhap"):
        tai_khoan_nhap = st.text_input("Tên tài khoản:") 
        mat_khau_nhap = st.text_input("Mật khẩu:", type="password")
        nut_dang_nhap = st.form_submit_button("Vào hệ thống")
        
        if nut_dang_nhap:
            dang_nhap_thanh_cong = False
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
        tab1, tab2 = st.tabs(["📝 Giao & Quản lý Công việc", "👥 Quản lý Nhân sự"])
        
        with tab1:
            cot_trai, cot_phai = st.columns([1, 2])
            with cot_trai:
                with st.form("form_giao_viec"):
                    st.subheader("Giao công việc mới")
                    ten_cong_viec = st.text_input("Tên công việc:")
                    
                    if len(danh_sach_nhan_vien) > 0:
                        nguoi_nhan = st.selectbox("Giao cho ai?", danh_sach_nhan_vien)
                    else:
                        st.warning("Chưa có nhân viên nào.")
                        nguoi_nhan = None
                    
                    col_ngay, col_gio = st.columns(2)
                    with col_ngay:
                        ngay_han = st.date_input("Ngày hạn chót:", min_value=date.today())
                    with col_gio:
                        gio_han = st.time_input("Giờ hạn chót:")
                        
                    mo_ta = st.text_area("Mô tả chi tiết:")
                    nut_gui = st.form_submit_button("Giao việc")
                    
                    if nut_gui and ten_cong_viec != "" and nguoi_nhan is not None:
                        han_chot_gop = f"{ngay_han.strftime('%d/%m/%Y')} {gio_han.strftime('%H:%M')}"
                        # Lưu dữ liệu: Chỉ còn 5 cột cơ bản
                        sheet_congviec.append_row([ten_cong_viec, nguoi_nhan, han_chot_gop, mo_ta, "Mới giao"])
                        st.success("Đã giao việc thành công!")
                        st.rerun()
            
            with cot_phai:
                st.subheader("📋 Tiến độ (Tự động sắp xếp theo Deadline)")
                if not df_congviec.empty:
                    # Tạo một bảng hiển thị đẹp mắt
                    df_hien_thi = df_congviec[['Tên công việc', 'Người nhận', 'Hạn chót', 'Trạng thái', 'nhan_uu_tien']].copy()
                    df_hien_thi.rename(columns={'nhan_uu_tien': 'Phân tích Deadline'}, inplace=True)
                    st.dataframe(df_hien_thi, use_container_width=True)
                else:
                    st.info("Chưa có dữ liệu.")
                
        with tab2:
            st.subheader("Thêm tài khoản mới")
            with st.form("form_tao_tai_khoan", clear_on_submit=True):
                tk_moi = st.text_input("Tên tài khoản mới:")
                mk_moi = st.text_input("Mật khẩu:")
                vt_moi = st.selectbox("Vai trò:", ["Nhân viên", "Quản lý"])
                btn_tao_tk = st.form_submit_button("Tạo tài khoản")
                
                if btn_tao_tk:
                    danh_sach_tk_hien_tai = [str(r["Tên tài khoản"]) for r in data_taikhoan]
                    if tk_moi in danh_sach_tk_hien_tai:
                        st.error("Tên tài khoản này đã tồn tại!")
                    elif tk_moi == "" or mk_moi == "":
                        st.error("Không được để trống!")
                    else:
                        sheet_taikhoan.append_row([tk_moi, mk_moi, vt_moi])
                        st.success(f"Đã tạo thành công tài khoản: {tk_moi}")
                        st.rerun()
            
            st.subheader("Danh sách Tài khoản")
            st.dataframe(pd.DataFrame(data_taikhoan), use_container_width=True)

    # KỊCH BẢN 2: NHÂN VIÊN
    else:
        st.title("👷 Bảng Làm Việc")
        st.subheader(f"📋 Công việc của {st.session_state.nguoi_dung}")
        
        if not df_congviec.empty:
            df_nhan_vien = df_congviec[df_congviec['Người nhận'] == st.session_state.nguoi_dung]
            
            if len(df_nhan_vien) > 0:
                for index, task in df_nhan_vien.iterrows():
                    dong_so_goc = task['dong_so_goc'] 
                    
                    # Hiển thị tiêu đề với cái nhãn tự động tính toán
                    with st.expander(f"{task['nhan_uu_tien']} | {task['Tên công việc']} (Hạn: {task['Hạn chót']})", expanded=True):
                        st.write(f"**Mô tả:** {task['Mô tả']}")
                        
                        danh_sach_trang_thai = ["Mới giao", "Đang làm", "Hoàn thành"]
                        trang_thai_hien_tai = task['Trạng thái']
                        if trang_thai_hien_tai not in danh_sach_trang_thai:
                            trang_thai_hien_tai = "Mới giao"
                            
                        trang_thai_moi = st.radio(
                            "Cập nhật tiến độ:", 
                            danh_sach_trang_thai, 
                            index=danh_sach_trang_thai.index(trang_thai_hien_tai),
                            key=f"radio_{dong_so_goc}",
                            horizontal=True
                        )
                        
                        if st.button("Lưu thay đổi", key=f"btn_{dong_so_goc}"):
                            if trang_thai_moi != task['Trạng thái']:
                                sheet_congviec.update_cell(dong_so_goc, 5, trang_thai_moi)
                                st.success("Đã cập nhật tiến độ lên hệ thống!")
                                st.rerun()
            else:
                st.success("Bạn hiện không có công việc nào tồn đọng.")
        else:
            st.info("Hệ thống chưa có việc nào được giao.")
