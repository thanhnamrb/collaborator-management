import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import date, datetime, timedelta

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Hệ thống Quản lý CTV", page_icon="📝", layout="wide")

# --- CSS TỐI GIẢN (MINIMALIST) ---
st.markdown("""
    <style>
    /* Font Inter chuẩn Quốc tế */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    
    /* Ẩn Header mặc định */
    [data-testid="stHeader"], footer { visibility: hidden; }
    
    /* Nền xám nhạt siêu sạch (Static Background) */
    [data-testid="stAppViewContainer"] { background-color: #f8fafc !important; }
    
    /* Form & Container (Phẳng, viền mảnh, nền trắng) */
    div[data-testid="stForm"], div[data-testid="stExpander"], div[data-testid="metric-container"] {
        background-color: #ffffff !important; 
        border-radius: 8px !important;
        border: 1px solid #e2e8f0 !important; 
        box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
        padding: 20px !important;
    }
    
    /* Màu chữ chung */
    h1, h2, h3, h4, h5, p, span, label { color: #0f172a !important; }
    
    /* Ô nhập liệu (Viền xám, đổi màu khi click) */
    [data-baseweb="input"] > div, [data-baseweb="textarea"], [data-baseweb="select"] > div {
        background-color: #ffffff !important; 
        border: 1px solid #cbd5e1 !important; 
        border-radius: 6px !important;
    }
    [data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within, [data-baseweb="select"]:focus-within > div {
        border-color: #2563eb !important;
    }
    input, textarea { color: #0f172a !important; }
    svg { fill: #475569 !important; }

    /* Nút bấm (Đơn sắc, phẳng) */
    div.stButton > button {
        background-color: #0f172a !important; /* Màu đen/xanh đậm tối giản */
        color: white !important; 
        border-radius: 6px !important; 
        border: none !important;
        padding: 0.5rem 1rem !important; 
        font-weight: 500 !important;
        box-shadow: none !important;
        width: 100%;
    }
    div.stButton > button:hover { background-color: #334155 !important; color: white !important; }
    
    /* Nút Đăng xuất */
    div[data-testid="column"] > div.stButton > button {
        background-color: #ffffff !important; color: #475569 !important; border: 1px solid #cbd5e1 !important;
    }
    div[data-testid="column"] > div.stButton > button:hover { background-color: #f1f5f9 !important; color: #0f172a !important; }
    </style>
""", unsafe_allow_html=True)

# --- 1. KẾT NỐI GOOGLE SHEETS ---
try:
    key_dict = json.loads(st.secrets["json_key"])
    creds = Credentials.from_service_account_info(
        key_dict, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
    
    url_sheet = "https://docs.google.com/spreadsheets/d/1jQFz2qqoDKLDDBKF97QXMfr_RcRv57vlGtIqHUBtK1w/edit?usp=sharing"
    file_gg_sheet = client.open_by_url(url_sheet)
    
    sheet_congviec = file_gg_sheet.get_worksheet(0) 
    sheet_taikhoan = file_gg_sheet.worksheet("TaiKhoan")
    
    data_congviec = sheet_congviec.get_all_records()
    data_taikhoan = sheet_taikhoan.get_all_records()
    danh_sach_ctv = [row["Tên tài khoản"] for row in data_taikhoan if row["Vai trò"] in ["CTV", "Nhân viên"]]

except Exception as e:
    st.error("Mất kết nối dữ liệu. Vui lòng thử lại sau.")
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
        if thoi_gian_con_lai.total_seconds() < 0: return 1, "🔴 Quá hạn"
        elif thoi_gian_con_lai <= timedelta(hours=24): return 2, "🟠 Gấp"
        elif thoi_gian_con_lai <= timedelta(days=3): return 3, "🟡 Sắp tới"
        else: return 4, "🔵 Đang làm"

    df_congviec[['diem_uu_tien', 'Trạng thái ưu tiên']] = df_congviec.apply(
        lambda row: pd.Series(danh_gia_uu_tien(row['ngay_gio_chuan'], row.get('Trạng thái', ''))), axis=1
    )
    df_congviec = df_congviec.sort_values(by=['diem_uu_tien', 'ngay_gio_chuan'])
else:
    df_congviec = pd.DataFrame()

# --- 2. HỆ THỐNG ĐĂNG NHẬP ---
if 'nguoi_dung' not in st.session_state: st.session_state.nguoi_dung = None
if 'vai_tro' not in st.session_state: st.session_state.vai_tro = None

if st.session_state.nguoi_dung is None:
    # GIAO DIỆN LOGIN TỐI GIẢN
    st.write("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<h2 style='text-align: center; color: #0f172a; font-weight: 700; margin-bottom: 0;'>Đăng nhập</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; margin-bottom: 25px;'>Hệ thống Quản lý CTV</p>", unsafe_allow_html=True)
        
        with st.form("form_dang_nhap"):
            st.text_input("Tên tài khoản", key="tk_input") 
            st.text_input("Mật khẩu", type="password", key="mk_input")
            st.write("<br>", unsafe_allow_html=True)
            nut_dang_nhap = st.form_submit_button("Đăng nhập")
            
            if nut_dang_nhap:
                tai_khoan_nhap = st.session_state.tk_input
                mat_khau_nhap = st.session_state.mk_input
                dang_nhap_thanh_cong = False
                for user in data_taikhoan:
                    if str(user["Tên tài khoản"]) == tai_khoan_nhap and str(user["Mật khẩu"]) == mat_khau_nhap:
                        st.session_state.nguoi_dung = user["Tên tài khoản"]
                        st.session_state.vai_tro = user["Vai trò"]
                        dang_nhap_thanh_cong = True
                        break
                if dang_nhap_thanh_cong: st.rerun()
                else: st.error("Sai tài khoản hoặc mật khẩu.")

# --- 3. GIAO DIỆN LÀM VIỆC ---
else:
    # Header gọn gàng
    st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center; background: white; padding: 15px 25px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 25px;'>
            <div style='font-weight: 600; font-size: 1.1rem; color: #0f172a;'>Quản lý CTV <span style='color: #cbd5e1; font-weight: 400;'>|</span> <span style='color: #475569;'>{st.session_state.vai_tro}</span></div>
            <div style='color: #475569; font-size: 0.95rem;'>{st.session_state.nguoi_dung}</div>
        </div>
    """, unsafe_allow_html=True)
    
    c_logout_spacer, c_logout_btn = st.columns([8, 1])
    with c_logout_btn:
        if st.button("Đăng xuất"):
            st.session_state.nguoi_dung = None; st.session_state.vai_tro = None; st.rerun()

    # ==========================
    # GÓC NHÌN QUẢN LÝ
    # ==========================
    if st.session_state.vai_tro == "Quản lý":
        tab_list, tab_giao, tab_nhan_su = st.tabs(["Danh sách Công việc", "Giao việc mới", "Danh sách CTV"])
        
        with tab_list:
            if not df_congviec.empty:
                df_hien_thi = df_congviec[['Tên công việc', 'Người nhận', 'Hạn chót', 'Trạng thái ưu tiên', 'Trạng thái']].copy()
                st.dataframe(
                    df_hien_thi, use_container_width=True, hide_index=True, height=500,
                    column_config={
                        "Tên công việc": st.column_config.TextColumn("Công việc", width="large"),
                        "Người nhận": st.column_config.TextColumn("Người phụ trách", width="medium"),
                        "Hạn chót": st.column_config.TextColumn("Deadline", width="medium"),
                        "Trạng thái ưu tiên": st.column_config.TextColumn("Đánh giá", width="medium"),
                        "Trạng thái": st.column_config.TextColumn("Tiến độ", width="medium")
                    }
                )
            else: st.info("Chưa có dữ liệu.")
                
        with tab_giao:
            c_form_spacer, c_form_main, c_form_spacer2 = st.columns([1, 2.5, 1])
            with c_form_main:
                with st.form("form_giao_viec", clear_on_submit=True):
                    st.markdown("<h4 style='margin-bottom: 20px;'>Tạo phiếu giao việc</h4>", unsafe_allow_html=True)
                    ten_cong_viec = st.text_input("Tiêu đề công việc:")
                    nguoi_nhan = st.selectbox("Phân công cho:", danh_sach_ctv) if len(danh_sach_ctv) > 0 else None
                    
                    c_ngay, c_gio = st.columns(2)
                    with c_ngay: ngay_han = st.date_input("Ngày kết thúc:")
                    with c_gio: gio_han = st.time_input("Giờ kết thúc:")
                    
                    mo_ta = st.text_area("Mô tả chi tiết:", height=120)
                    st.write("<br>", unsafe_allow_html=True)
                    nut_gui = st.form_submit_button("Tạo công việc")
                    
                    if nut_gui and ten_cong_viec != "" and nguoi_nhan is not None:
                        han_chot_gop = f"{ngay_han.strftime('%d/%m/%Y')} {gio_han.strftime('%H:%M')}"
                        sheet_congviec.append_row([ten_cong_viec, nguoi_nhan, han_chot_gop, mo_ta, "Mới giao"])
                        st.success("Đã tạo công việc thành công.")
                        st.rerun()
                        
        with tab_nhan_su:
            df_taikhoan = pd.DataFrame(data_taikhoan)
            st.dataframe(df_taikhoan, use_container_width=True, hide_index=True)

    # ==========================
    # GÓC NHÌN CỘNG TÁC VIÊN (CTV)
    # ==========================
    else:
        st.markdown("<h4 style='margin-bottom: 20px;'>Nhiệm vụ của bạn</h4>", unsafe_allow_html=True)
        if not df_congviec.empty:
            df_nhan_vien = df_congviec[df_congviec['Người nhận'] == st.session_state.nguoi_dung]
            
            if len(df_nhan_vien) > 0:
                for index, task in df_nhan_vien.iterrows():
                    dong_so_goc = task['dong_so_goc']
                    mo_ta_html = str(task['Mô tả']).replace('\n', '<br>')

                    with st.expander(f"{task['Trạng thái ưu tiên']} | {task['Tên công việc']} (Hạn: {task['Hạn chót']})", expanded=True):
                        st.markdown(f"""
                            <div style='color: #334155; font-size: 1rem; line-height: 1.6; padding-bottom: 15px; border-bottom: 1px solid #e2e8f0; margin-bottom: 15px;'>
                                {mo_ta_html}
                            </div>
                        """, unsafe_allow_html=True)
                        
                        danh_sach = ["Mới giao", "Đang làm", "Hoàn thành"]
                        hien_tai = task['Trạng thái'] if task['Trạng thái'] in danh_sach else "Mới giao"
                        trang_thai_moi = st.radio("Tiến độ:", danh_sach, index=danh_sach.index(hien_tai), key=f"rd_{dong_so_goc}", horizontal=True)
                        
                        if st.button("Lưu thay đổi", key=f"btn_{dong_so_goc}"):
                            if trang_thai_moi != task['Trạng thái']:
                                sheet_congviec.update_cell(dong_so_goc, 5, trang_thai_moi)
                                st.toast("Cập nhật thành công")
                                st.rerun()
            else: st.success("Bạn không có công việc nào tồn đọng.")
        else: st.info("Hệ thống chưa có dữ liệu.")
