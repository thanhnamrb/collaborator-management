import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import date, datetime, timedelta

# Cấu hình trang mở rộng tối đa
st.set_page_config(page_title="Hệ thống Giao việc Pro", page_icon="🚀", layout="wide")

# --- CSS TÙY CHỈNH (LỘT XÁC GIAO DIỆN) ---
st.markdown("""
    <style>
    /* Chỉnh nút bấm */
    div.stButton > button {
        background-color: #2e66f6; color: white; border-radius: 8px; border: none; padding: 10px; font-weight: bold; transition: all 0.3s;
    }
    div.stButton > button:hover {
        background-color: #1a4cd2; box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }
    /* Chỉnh các khung viền */
    div[data-testid="stForm"] {
        border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid #e0e0e0;
    }
    /* Chỉnh thẻ Metric (Thống kê) */
    div[data-testid="metric-container"] {
        background-color: #f7f9fc; border-radius: 12px; padding: 15px; border: 1px solid #edf2f7;
    }
    </style>
""", unsafe_allow_html=True)

# --- 1. KẾT NỐI GOOGLE SHEETS ---
try:
    key_dict = json.loads(st.secrets["json_key"])
    creds = Credentials.from_service_account_info(
        key_dict, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
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
    st.error("Cổng kết nối dữ liệu đang bảo trì. Vui lòng kiểm tra lại liên kết Sheets.")
    st.stop()

# --- THUẬT TOÁN TÍNH TOÁN DEADLINE ---
if len(data_congviec) > 0:
    df_congviec = pd.DataFrame(data_congviec)
    df_congviec['dong_so_goc'] = df_congviec.index + 2 
    df_congviec['ngay_gio_chuan'] = pd.to_datetime(df_congviec['Hạn chót'], format='%d/%m/%Y %H:%M', errors='coerce')
    now = datetime.now()
    
    def danh_gia_uu_tien(deadline, trang_thai):
        if trang_thai == "Hoàn thành": return 5, "✅ Xong"
        if pd.isna(deadline): return 4, "⚪ Chưa rõ"
        thoi_gian_con_lai = deadline - now
        if thoi_gian_con_lai.total_seconds() < 0: return 1, "🚨 Quá hạn"
        elif thoi_gian_con_lai <= timedelta(hours=24): return 2, "🔥 Gấp"
        elif thoi_gian_con_lai <= timedelta(days=3): return 3, "🟡 Sắp tới"
        else: return 4, "🟢 Bình thường"

    df_congviec[['diem_uu_tien', 'Trạng thái ưu tiên']] = df_congviec.apply(
        lambda row: pd.Series(danh_gia_uu_tien(row['ngay_gio_chuan'], row.get('Trạng thái', ''))), axis=1
    )
    df_congviec = df_congviec.sort_values(by=['diem_uu_tien', 'ngay_gio_chuan'])
else:
    df_congviec = pd.DataFrame()

# --- 2. HỆ THỐNG ĐĂNG NHẬP (TRUNG TÂM HÓA) ---
if 'nguoi_dung' not in st.session_state:
    st.session_state.nguoi_dung = None
if 'vai_tro' not in st.session_state:
    st.session_state.vai_tro = None

if st.session_state.nguoi_dung is None:
    # Căn giữa màn hình đăng nhập
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.write("<br><br>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #2e66f6;'>Hệ Thống Quản Trị</h2>", unsafe_allow_html=True)
        with st.form("form_dang_nhap"):
            tai_khoan_nhap = st.text_input("Tên đăng nhập:") 
            mat_khau_nhap = st.text_input("Mật khẩu:", type="password")
            nut_dang_nhap = st.form_submit_button("Đăng Nhập", use_container_width=True)
            
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
                    st.error("Thông tin đăng nhập không chính xác!")

# --- 3. GIAO DIỆN LÀM VIỆC ---
else:
    # Thanh điều hướng (Header)
    col_logo, col_user, col_btn = st.columns([6, 2, 1])
    with col_logo:
        st.markdown(f"### 🚀 Workspace / {st.session_state.vai_tro}")
    with col_user:
        st.write(f"👤 **{st.session_state.nguoi_dung}**")
    with col_btn:
        if st.button("Đăng xuất", use_container_width=True):
            st.session_state.nguoi_dung = None
            st.session_state.vai_tro = None
            st.rerun()
    st.markdown("---")

    # === GIAO DIỆN QUẢN LÝ ===
    if st.session_state.vai_tro == "Quản lý":
        # KHU VỰC 1: DASHBOARD THỐNG KÊ
        st.markdown("#### 📊 Tổng quan Dự án")
        if not df_congviec.empty:
            tong_viec = len(df_congviec)
            da_xong = len(df_congviec[df_congviec['Trạng thái'] == 'Hoàn thành'])
            qua_han = len(df_congviec[df_congviec['diem_uu_tien'] == 1])
            dang_lam = tong_viec - da_xong
        else:
            tong_viec = da_xong = qua_han = dang_lam = 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Tổng công việc", tong_viec)
        m2.metric("Đang triển khai", dang_lam)
        m3.metric("Hoàn thành", da_xong)
        m4.metric("Cảnh báo Quá hạn", qua_han)
        st.write("<br>", unsafe_allow_html=True)

        # KHU VỰC 2: KHÔNG GIAN LÀM VIỆC CHÍNH (Chia Tabs)
        tab_list, tab_giao, tab_nhan_su = st.tabs(["📋 Danh sách Công việc", "✍️ Giao việc mới", "👥 Nhân sự"])
        
        with tab_list:
            if not df_congviec.empty:
                df_hien_thi = df_congviec[['Tên công việc', 'Người nhận', 'Hạn chót', 'Trạng thái ưu tiên', 'Trạng thái']].copy()
                # Cấu hình UI cho bảng dữ liệu mượt mà hơn
                st.dataframe(
                    df_hien_thi,
                    use_container_width=True,
                    hide_index=True,
                    height=400,
                    column_config={
                        "Tên công việc": st.column_config.TextColumn("📌 Tên công việc", width="large"),
                        "Người nhận": st.column_config.TextColumn("👤 Phụ trách", width="medium"),
                        "Trạng thái ưu tiên": st.column_config.TextColumn("⏱️ Cảnh báo Hạn chót", width="medium"),
                        "Trạng thái": st.column_config.TextColumn("Tình trạng", width="medium")
                    }
                )
            else:
                st.info("Bảng công việc trống. Hãy tạo công việc mới!")
                
        with tab_giao:
            c_form, c_blank = st.columns([1, 1]) # Làm form gọn lại 1 nửa màn hình cho đẹp
            with c_form:
                with st.form("form_giao_viec", clear_on_submit=True):
                    st.markdown("#### Tạo Phiếu Giao Việc")
                    ten_cong_viec = st.text_input("Tiêu đề công việc:")
                    nguoi_nhan = st.selectbox("Phân công cho:", danh_sach_nhan_vien) if len(danh_sach_nhan_vien) > 0 else None
                    
                    c_ngay, c_gio = st.columns(2)
                    with c_ngay: ngay_han = st.date_input("Ngày hết hạn:")
                    with c_gio: gio_han = st.time_input("Giờ kết thúc:")
                        
                    mo_ta = st.text_area("Mô tả / Hướng dẫn thực hiện:", height=150)
                    nut_gui = st.form_submit_button("🚀 Ban Hành Công Việc", use_container_width=True)
                    
                    if nut_gui and ten_cong_viec != "" and nguoi_nhan is not None:
                        han_chot_gop = f"{ngay_han.strftime('%d/%m/%Y')} {gio_han.strftime('%H:%M')}"
                        sheet_congviec.append_row([ten_cong_viec, nguoi_nhan, han_chot_gop, mo_ta, "Mới giao"])
                        st.success("Tạo việc thành công! Bảng danh sách đã được cập nhật.")
                        st.rerun()
                        
        with tab_nhan_su:
            st.markdown("#### Quản lý Tài khoản")
            # Bạn có thể giữ nguyên phần quản lý nhân sự cũ ở đây, mình làm gọn lại
            df_taikhoan = pd.DataFrame(data_taikhoan)
            st.dataframe(df_taikhoan, use_container_width=True, hide_index=True)


    # === GIAO DIỆN NHÂN VIÊN ===
    else:
        if not df_congviec.empty:
            df_nhan_vien = df_congviec[df_congviec['Người nhận'] == st.session_state.nguoi_dung]
            
            # Dashboard nhỏ cho nhân viên
            tong_cua_toi = len(df_nhan_vien)
            xong_cua_toi = len(df_nhan_vien[df_nhan_vien['Trạng thái'] == 'Hoàn thành'])
            m1, m2, m3 = st.columns(3)
            m1.metric("Nhiệm vụ được giao", tong_cua_toi)
            m2.metric("Đã hoàn thành", xong_cua_toi)
            m3.metric("Cần xử lý", tong_cua_toi - xong_cua_toi)
            st.write("<br>", unsafe_allow_html=True)
            
            if len(df_nhan_vien) > 0:
                for index, task in df_nhan_vien.iterrows():
                    dong_so_goc = task['dong_so_goc'] 
                    
                    with st.expander(f"{task['Trạng thái ưu tiên']} | 📝 {task['Tên công việc']} (Hạn: {task['Hạn chót']})", expanded=True):
                        st.markdown(f"<div style='background-color:#f9fbff; padding:15px; border-radius:8px;'><b>Chi tiết:</b> {task['Mô tả']}</div><br>", unsafe_allow_html=True)
                        
                        danh_sach_trang_thai = ["Mới giao", "Đang làm", "Hoàn thành"]
                        trang_thai_hien_tai = task['Trạng thái'] if task['Trạng thái'] in danh_sach_trang_thai else "Mới giao"
                            
                        trang_thai_moi = st.radio("Tiến độ của bạn:", danh_sach_trang_thai, index=danh_sach_trang_thai.index(trang_thai_hien_tai), key=f"radio_{dong_so_goc}", horizontal=True)
                        
                        if st.button("Lưu Thay Đổi", key=f"btn_{dong_so_goc}"):
                            if trang_thai_moi != task['Trạng thái']:
                                sheet_congviec.update_cell(dong_so_goc, 5, trang_thai_moi)
                                st.toast("✅ Cập nhật thành công!")
                                st.rerun()
            else:
                st.success("🎉 Xin chúc mừng! Bạn đã hoàn thành mọi nhiệm vụ.")
        else:
            st.info("Hệ thống chưa có nhiệm vụ nào được ghi nhận.")
