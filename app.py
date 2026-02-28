import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import date, datetime, timedelta

# Cấu hình trang mở rộng tối đa
st.set_page_config(page_title="TaskFlow Pro", page_icon="⚡", layout="wide")

# --- CSS TÙY CHỈNH: LỘT XÁC GIAO DIỆN "WOW" ---
st.markdown("""
    <style>
    /* Nhúng Font chữ Inter cực xịn của Google */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }

    /* Ẩn bớt các thành phần thừa của Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Nút bấm Gradient 3D */
    div.stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.4) !important;
    }
    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 15px -1px rgba(59, 130, 246, 0.5) !important;
    }

    /* Form và Card (Đổ bóng mềm mại) */
    div[data-testid="stForm"] {
        border-radius: 16px !important; 
        box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1) !important; 
        border: 1px solid #f1f5f9 !important;
        padding: 25px !important;
        background-color: #ffffff !important;
    }
    
    /* Chỉnh thẻ KPI Thống kê */
    div[data-testid="metric-container"] {
        background: linear-gradient(145deg, #ffffff, #f8fafc) !important;
        border: 1px solid #e2e8f0 !important;
        border-left: 5px solid #3b82f6 !important;
        border-radius: 12px !important;
        padding: 20px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
    }
    div[data-testid="metric-container"] label { color: #64748b !important; font-weight: 600 !important; font-size: 14px !important;}
    div[data-testid="metric-container"] div { color: #0f172a !important; font-weight: 800 !important;}

    /* Ép màu nền sáng cho toàn bộ app để chuẩn UI */
    .stApp {
        background-color: #f8fafc;
    }
    h1, h2, h3, h4, h5 {
        color: #0f172a !important;
        font-weight: 700 !important;
    }
    p, span, label {
        color: #334155 !important;
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
    
    # LINK SHEETS CỦA NAM
    url_sheet = "https://docs.google.com/spreadsheets/d/1jQFz2qqoDKLDDBKF97QXMfr_RcRv57vlGtIqHUBtK1w/edit?usp=sharing"
    file_gg_sheet = client.open_by_url(url_sheet)
    
    sheet_congviec = file_gg_sheet.get_worksheet(0) 
    sheet_taikhoan = file_gg_sheet.worksheet("TaiKhoan")
    
    data_congviec = sheet_congviec.get_all_records()
    data_taikhoan = sheet_taikhoan.get_all_records()
    danh_sach_nhan_vien = [row["Tên tài khoản"] for row in data_taikhoan if row["Vai trò"] == "Nhân viên"]

except Exception as e:
    st.error("🔌 Mất kết nối dữ liệu. Vui lòng thử tải lại trang.")
    st.stop()

# --- THUẬT TOÁN TÍNH TOÁN DEADLINE ---
if len(data_congviec) > 0:
    df_congviec = pd.DataFrame(data_congviec)
    df_congviec['dong_so_goc'] = df_congviec.index + 2 
    df_congviec['ngay_gio_chuan'] = pd.to_datetime(df_congviec['Hạn chót'], format='%d/%m/%Y %H:%M', errors='coerce')
    now = datetime.now()
    
    def danh_gia_uu_tien(deadline, trang_thai):
        if trang_thai == "Hoàn thành": return 5, "✅ Hoàn thành"
        if pd.isna(deadline): return 4, "⚪ Chưa rõ"
        thoi_gian_con_lai = deadline - now
        if thoi_gian_con_lai.total_seconds() < 0: return 1, "🚨 QUÁ HẠN"
        elif thoi_gian_con_lai <= timedelta(hours=24): return 2, "🔥 KHẨN CẤP"
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
    # Giao diện Đăng nhập xịn sò
    st.write("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.5, 2, 1.5])
    with c2:
        st.markdown("""
            <div style='text-align: center; margin-bottom: 20px;'>
                <h1 style='color: #2563eb; font-size: 3rem; margin-bottom: 0;'>TaskFlow<span style='color: #f59e0b;'>Pro</span></h1>
                <p style='color: #64748b; font-size: 1.1rem;'>Hệ thống Quản trị & Điều hành Nội bộ</p>
            </div>
        """, unsafe_allow_html=True)
        with st.form("form_dang_nhap"):
            tai_khoan_nhap = st.text_input("👤 Tên tài khoản:") 
            mat_khau_nhap = st.text_input("🔑 Mật khẩu:", type="password")
            st.write("<br>", unsafe_allow_html=True)
            nut_dang_nhap = st.form_submit_button("⚡ ĐĂNG NHẬP", use_container_width=True)
            
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
                    st.error("Sai thông tin đăng nhập! Vui lòng thử lại.")

# --- 3. GIAO DIỆN LÀM VIỆC ---
else:
    # Header Điều hướng
    col_logo, col_user, col_btn = st.columns([6, 3, 1])
    with col_logo:
        st.markdown(f"<h3 style='margin: 0; color: #1e293b;'>⚡ Workspace <span style='color: #cbd5e1;'>/</span> {st.session_state.vai_tro}</h3>", unsafe_allow_html=True)
    with col_user:
        st.markdown(f"<div style='text-align: right; padding-top: 5px; font-size: 1.1rem; color: #475569;'>Xin chào, <b>{st.session_state.nguoi_dung}</b></div>", unsafe_allow_html=True)
    with col_btn:
        if st.button("Đăng xuất", use_container_width=True):
            st.session_state.nguoi_dung = None
            st.session_state.vai_tro = None
            st.rerun()
    st.write("<br>", unsafe_allow_html=True)

    # === GIAO DIỆN QUẢN LÝ ===
    if st.session_state.vai_tro == "Quản lý":
        if not df_congviec.empty:
            tong_viec = len(df_congviec)
            da_xong = len(df_congviec[df_congviec['Trạng thái'] == 'Hoàn thành'])
            qua_han = len(df_congviec[df_congviec['diem_uu_tien'] == 1])
            dang_lam = tong_viec - da_xong
        else:
            tong_viec = da_xong = qua_han = dang_lam = 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📌 TỔNG CÔNG VIỆC", tong_viec)
        m2.metric("⏳ ĐANG TRIỂN KHAI", dang_lam)
        m3.metric("✅ HOÀN THÀNH", da_xong)
        m4.metric("🚨 CẢNH BÁO QUÁ HẠN", qua_han)
        st.write("<br>", unsafe_allow_html=True)

        tab_list, tab_giao, tab_nhan_su = st.tabs(["📋 Danh sách Nhiệm vụ", "🚀 Giao việc mới", "👥 Nhân sự"])
        
        with tab_list:
            if not df_congviec.empty:
                df_hien_thi = df_congviec[['Tên công việc', 'Người nhận', 'Hạn chót', 'Trạng thái ưu tiên', 'Trạng thái']].copy()
                st.dataframe(
                    df_hien_thi,
                    use_container_width=True,
                    hide_index=True,
                    height=500,
                    column_config={
                        "Tên công việc": st.column_config.TextColumn("Nhiệm vụ", width="large"),
                        "Người nhận": st.column_config.TextColumn("Người phụ trách", width="medium"),
                        "Hạn chót": st.column_config.TextColumn("Deadline", width="medium"),
                        "Trạng thái ưu tiên": st.column_config.TextColumn("Đánh giá Hạn", width="medium"),
                        "Trạng thái": st.column_config.TextColumn("Tiến độ", width="medium")
                    }
                )
            else:
                st.info("Chưa có nhiệm vụ nào được khởi tạo.")
                
        with tab_giao:
            c_form, c_blank = st.columns([1.5, 1]) 
            with c_form:
                with st.form("form_giao_viec", clear_on_submit=True):
                    st.markdown("#### 📝 Phiếu Phân Công Nhiệm Vụ")
                    st.write("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                    ten_cong_viec = st.text_input("Tiêu đề công việc:")
                    nguoi_nhan = st.selectbox("Phân công cho:", danh_sach_nhan_vien) if len(danh_sach_nhan_vien) > 0 else None
                    
                    c_ngay, c_gio = st.columns(2)
                    with c_ngay: ngay_han = st.date_input("Ngày kết thúc:")
                    with c_gio: gio_han = st.time_input("Giờ kết thúc:")
                        
                    mo_ta = st.text_area("Mô tả / Hướng dẫn thực hiện:", height=120)
                    st.write("<br>", unsafe_allow_html=True)
                    nut_gui = st.form_submit_button("🚀 PHÁT HÀNH NHIỆM VỤ", use_container_width=True)
                    
                    if nut_gui and ten_cong_viec != "" and nguoi_nhan is not None:
                        han_chot_gop = f"{ngay_han.strftime('%d/%m/%Y')} {gio_han.strftime('%H:%M')}"
                        sheet_congviec.append_row([ten_cong_viec, nguoi_nhan, han_chot_gop, mo_ta, "Mới giao"])
                        st.success("Tạo việc thành công! Hệ thống đã cập nhật.")
                        st.rerun()
                        
        with tab_nhan_su:
            st.markdown("#### 👥 Quản lý Tài khoản")
            df_taikhoan = pd.DataFrame(data_taikhoan)
            st.dataframe(df_taikhoan, use_container_width=True, hide_index=True)

    # === GIAO DIỆN NHÂN VIÊN ===
    else:
        if not df_congviec.empty:
            df_nhan_vien = df_congviec[df_congviec['Người nhận'] == st.session_state.nguoi_dung]
            
            tong_cua_toi = len(df_nhan_vien)
            xong_cua_toi = len(df_nhan_vien[df_nhan_vien['Trạng thái'] == 'Hoàn thành'])
            m1, m2, m3 = st.columns(3)
            m1.metric("📌 TỔNG SỐ NHIỆM VỤ", tong_cua_toi)
            m2.metric("✅ ĐÃ HOÀN THÀNH", xong_cua_toi)
            m3.metric("⏳ CẦN XỬ LÝ", tong_cua_toi - xong_cua_toi)
            st.write("<br>", unsafe_allow_html=True)
            
            if len(df_nhan_vien) > 0:
                for index, task in df_nhan_vien.iterrows():
                    dong_so_goc = task['dong_so_goc'] 
                    
                    with st.expander(f"{task['Trạng thái ưu tiên']} | 🚀 {task['Tên công việc']} (Hạn: {task['Hạn chót']})", expanded=True):
                        # FIX LỖI HIỂN THỊ CHỮ: Ép cứng màu chữ đen và nền xám nhạt cho phần mô tả
                        st.markdown(f"""
                            <div style='background-color: #f8fafc; color: #0f172a; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; border-left: 5px solid #3b82f6; margin-bottom: 15px;'>
                                <p style='margin-top: 0; color: #64748b; font-size: 0.9rem; font-weight: 600; text-transform: uppercase;'>📝 Chi tiết công việc:</p>
                                <p style='margin-bottom: 0; font-size: 1.05rem;'>{task['Mô tả']}</p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        danh_sach_trang_thai = ["Mới giao", "Đang làm", "Hoàn thành"]
                        trang_thai_hien_tai = task['Trạng thái'] if task['Trạng thái'] in danh_sach_trang_thai else "Mới giao"
                            
                        trang_thai_moi = st.radio("Cập nhật tiến độ của bạn:", danh_sach_trang_thai, index=danh_sach_trang_thai.index(trang_thai_hien_tai), key=f"radio_{dong_so_goc}", horizontal=True)
                        
                        if st.button("Lưu Thay Đổi", key=f"btn_{dong_so_goc}"):
                            if trang_thai_moi != task['Trạng thái']:
                                sheet_congviec.update_cell(dong_so_goc, 5, trang_thai_moi)
                                st.toast("✅ Đã lưu tiến độ lên hệ thống!")
                                st.rerun()
            else:
                st.success("🎉 Xin chúc mừng! Bạn đã hoàn thành mọi nhiệm vụ được giao.")
        else:
            st.info("Hệ thống chưa có nhiệm vụ nào được ghi nhận.")
