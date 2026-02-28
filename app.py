import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import date, datetime, timedelta
import re

# Cấu hình trang mở rộng tối đa, icon sấm sét
st.set_page_config(page_title="Hệ thống quản lý CTV", page_icon="⚡", layout="wide")

# --- "NUCLEAR" CSS: ÉP BUỘC GIAO DIỆN SÁNG & HIỆN ĐẠI ---
st.markdown("""
    <style>
    /* Nhúng Font Inter */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    /* 1. ÉP MÀU NỀN SÁNG CHO TOÀN BỘ APP (Chống Dark Mode) */
    [data-testid="stAppViewContainer"] {
        background-color: #f8fafc !important; /* Màu xám trắng hiện đại */
    }
    [data-testid="stHeader"], footer { visibility: hidden; } /* Ẩn header/footer mặc định của Streamlit */

    /* 2. ÉP MÀU CHỮ TỐI CHO MỌI TIÊU ĐỀ VÀ VĂN BẢN */
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        font-family: 'Inter', sans-serif !important;
        color: #0f172a !important; /* Màu xanh đen đậm */
    }
    
    /* 3. XỬ LÝ CÁC Ô NHẬP LIỆU BỊ ĐEN (QUAN TRỌNG NHẤT) */
    /* Input text, Number input */
    [data-baseweb="input"] {
        background-color: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 8px !important;
    }
    /* Textarea (Ô mô tả) */
    [data-baseweb="textarea"] {
        background-color: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 8px !important;
    }
    /* Selectbox (Menu xổ xuống) */
    [data-baseweb="select"] > div {
        background-color: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 8px !important;
    }
    /* Khi click vào ô nhập liệu thì viền màu xanh */
    [data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within, [data-baseweb="select"]:focus-within > div {
        border-color: #3b82f6 !important; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
    }
    /* Ép màu chữ bên trong ô nhập liệu */
    input[type="text"], input[type="password"], textarea { color: #0f172a !important; }

    /* 4. NÚT BẤM SIÊU ĐẸP (Gradient & Bóng mờ) */
    div.stButton > button {
        background: linear-gradient(to right, #3b82f6, #2563eb) !important;
        color: white !important; border: none !important; border-radius: 8px !important;
        padding: 0.6rem 1.2rem !important; font-weight: 600 !important;
        box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.3) !important; transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        transform: translateY(-2px) !important; box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.4) !important;
    }
    /* Nút phụ (Đăng xuất) */
    div[data-testid="column"] > div.stButton > button {
        background: #f1f5f9 !important; color: #475569 !important; box-shadow: none !important; border: 1px solid #e2e8f0 !important;
    }
    div[data-testid="column"] > div.stButton > button:hover {
         background: #e2e8f0 !important; color: #0f172a !important;
    }

    /* 5. CÁC KHỐI CHỨA (Container, Form, Metric) */
    /* Form và Expander được bo góc và đổ bóng xịn */
    div[data-testid="stForm"], div[data-testid="stExpander"] {
        background-color: #ffffff !important; border-radius: 12px !important;
        border: 1px solid #f1f5f9 !important; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
        padding: 20px !important;
    }
    div[data-testid="stExpander"] { padding: 10px !important; border-left: 4px solid #3b82f6 !important;}

    /* Thẻ KPI thống kê */
    div[data-testid="metric-container"] {
        background-color: #ffffff !important; border-radius: 12px !important; padding: 15px 20px !important;
        border: 1px solid #e2e8f0 !important; box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
    }
    /* Chỉnh màu số liệu trong thẻ KPI */
    div[data-testid="metric-container"] label { font-size: 0.9rem !important; font-weight: 600 !important; color: #64748b !important; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] > div { font-size: 1.8rem !important; font-weight: 800 !important; color: #0f172a !important; }

    /* 6. CHỈNH BẢNG DỮ LIỆU (Dataframe) */
    div[data-testid="stDataFrame"] { border: 1px solid #e2e8f0 !important; border-radius: 8px !important; overflow: hidden !important;}
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
    st.error("🔌 Mất kết nối dữ liệu. Vui lòng tải lại trang.")
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
        # Sử dụng emoji nổi bật hơn
        if thoi_gian_con_lai.total_seconds() < 0: return 1, "🔴 QUÁ HẠN"
        elif thoi_gian_con_lai <= timedelta(hours=24): return 2, "🟠 GẤP (<24h)"
        elif thoi_gian_con_lai <= timedelta(days=3): return 3, "🟡 Sắp tới"
        else: return 4, "🔵 Đang thực hiện"

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
    # Giao diện Đăng nhập xịn sò, căn giữa
    st.write("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
            <div style='text-align: center; background: white; padding: 40px; border-radius: 16px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1); border: 1px solid #f1f5f9;'>
                <h1 style='color: #2563eb; font-weight: 800; font-size: 2.5rem; margin:0;'>TaskFlow<span style='color:#f59e0b'>.</span></h1>
                <p style='color: #64748b; margin-top: 10px; font-weight: 500;'>Đăng nhập để bắt đầu làm việc</p>
                <br>
        """, unsafe_allow_html=True)
        with st.form("form_dang_nhap"):
            st.text_input("Tên tài khoản", key="tk_input") 
            st.text_input("Mật khẩu", type="password", key="mk_input")
            st.write("<br>", unsafe_allow_html=True)
            nut_dang_nhap = st.form_submit_button("👉 Truy cập Hệ thống", use_container_width=True)
            
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
                else: st.error("Sai thông tin đăng nhập.")
        st.markdown("</div>", unsafe_allow_html=True)

# --- 3. GIAO DIỆN LÀM VIỆC ---
else:
    # Header Navbar xịn
    st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center; background: white; padding: 15px 25px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.03);'>
            <div style='font-weight: 800; font-size: 1.2rem; color: #2563eb;'>TaskFlow <span style='color: #cbd5e1; font-weight: 400;'>|</span> <span style='color: #0f172a;'>{st.session_state.vai_tro}</span></div>
            <div style='display: flex; align-items: center; gap: 15px;'>
                <div style='font-weight: 600; color: #475569;'>👤 {st.session_state.nguoi_dung}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Nút đăng xuất nằm riêng một góc cho gọn
    c_logout_spacer, c_logout_btn = st.columns([7, 1])
    with c_logout_btn:
        if st.button("Đăng xuất", use_container_width=True):
            st.session_state.nguoi_dung = None; st.session_state.vai_tro = None; st.rerun()


    # === GIAO DIỆN QUẢN LÝ ===
    if st.session_state.vai_tro == "Quản lý":
        if not df_congviec.empty:
            tong_viec = len(df_congviec)
            da_xong = len(df_congviec[df_congviec['Trạng thái'] == 'Hoàn thành'])
            qua_han = len(df_congviec[df_congviec['diem_uu_tien'] == 1])
            dang_lam = tong_viec - da_xong
        else: tong_viec = da_xong = qua_han = dang_lam = 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📌 Tổng nhiệm vụ", tong_viec)
        m2.metric("⏳ Đang thực hiện", dang_lam)
        m3.metric("✅ Hoàn thành", da_xong)
        m4.metric("🚨 Quá hạn", qua_han)
        st.write("<br>", unsafe_allow_html=True)

        tab_list, tab_giao, tab_nhan_su = st.tabs(["📋 Danh sách & Tiến độ", "✨ Giao việc mới", "👥 Nhân sự"])
        
        with tab_list:
            if not df_congviec.empty:
                df_hien_thi = df_congviec[['Tên công việc', 'Người nhận', 'Hạn chót', 'Trạng thái ưu tiên', 'Trạng thái']].copy()
                st.dataframe(
                    df_hien_thi, use_container_width=True, hide_index=True, height=500,
                    column_config={
                        "Tên công việc": st.column_config.TextColumn("Nhiệm vụ", width="large"),
                        "Người nhận": st.column_config.TextColumn("Phụ trách", width="medium"),
                        "Hạn chót": st.column_config.TextColumn("Deadline", width="medium"),
                        "Trạng thái ưu tiên": st.column_config.TextColumn("Cảnh báo", width="medium"),
                        "Trạng thái": st.column_config.TextColumn("Tiến độ", width="medium")
                    }
                )
            else: st.info("Chưa có dữ liệu công việc.")
                
        with tab_giao:
            c_form_spacer, c_form_main, c_form_spacer2 = st.columns([1, 3, 1])
            with c_form_main:
                with st.form("form_giao_viec", clear_on_submit=True):
                    st.markdown("#### ✨ Tạo phiếu giao việc mới")
                    st.markdown("---")
                    ten_cong_viec = st.text_input("Tiêu đề công việc (Ngắn gọn):")
                    nguoi_nhan = st.selectbox("Phân công cho:", danh_sach_nhan_vien) if len(danh_sach_nhan_vien) > 0 else None
                    c_ngay, c_gio = st.columns(2)
                    with c_ngay: ngay_han = st.date_input("Ngày kết thúc:")
                    with c_gio: gio_han = st.time_input("Giờ kết thúc:")
                    # Cho phép xuống dòng trong mô tả
                    mo_ta = st.text_area("Mô tả chi tiết (Hỗ trợ xuống dòng):", height=150, help="Bạn có thể gõ enter để xuống dòng, hệ thống sẽ hiển thị đúng như vậy.")
                    st.write("<br>", unsafe_allow_html=True)
                    nut_gui = st.form_submit_button("🚀 PHÁT HÀNH NHIỆM VỤ", use_container_width=True)
                    
                    if nut_gui and ten_cong_viec != "" and nguoi_nhan is not None:
                        han_chot_gop = f"{ngay_han.strftime('%d/%m/%Y')} {gio_han.strftime('%H:%M')}"
                        sheet_congviec.append_row([ten_cong_viec, nguoi_nhan, han_chot_gop, mo_ta, "Mới giao"])
                        st.success("Đã giao việc thành công!")
                        st.rerun()
                        
        with tab_nhan_su:
            df_taikhoan = pd.DataFrame(data_taikhoan)
            st.dataframe(df_taikhoan, use_container_width=True, hide_index=True)

    # === GIAO DIỆN NHÂN VIÊN ===
    else:
        if not df_congviec.empty:
            df_nhan_vien = df_congviec[df_congviec['Người nhận'] == st.session_state.nguoi_dung]
            tong = len(df_nhan_vien); xong = len(df_nhan_vien[df_nhan_vien['Trạng thái'] == 'Hoàn thành'])
            m1, m2, m3 = st.columns(3)
            m1.metric("Tổng nhiệm vụ", tong); m2.metric("Đã xong", xong); m3.metric("Còn lại", tong - xong)
            st.write("<br>", unsafe_allow_html=True)
            
            if len(df_nhan_vien) > 0:
                for index, task in df_nhan_vien.iterrows():
                    dong_so_goc = task['dong_so_goc']
                    # Xử lý xuống dòng trong mô tả: Thay thế ký tự \n bằng thẻ <br>
                    mo_ta_html = str(task['Mô tả']).replace('\n', '<br>')

                    with st.expander(f"{task['Trạng thái ưu tiên']} | {task['Tên công việc']} (Hạn: {task['Hạn chót']})", expanded=True):
                        # Hiển thị mô tả với nền trắng sạch sẽ, hỗ trợ xuống dòng
                        st.markdown(f"""
                            <div style='background-color: #ffffff; color: #0f172a; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; font-size: 1.05rem; line-height: 1.6;'>
                                <strong style='color: #3b82f6;'>📝 Nội dung chi tiết:</strong><br><br>
                                {mo_ta_html}
                            </div>
                        """, unsafe_allow_html=True)
                        
                        danh_sach = ["Mới giao", "Đang làm", "Hoàn thành"]
                        hien_tai = task['Trạng thái'] if task['Trạng thái'] in danh_sach else "Mới giao"
                        trang_thai_moi = st.radio("Cập nhật tiến độ:", danh_sach, index=danh_sach.index(hien_tai), key=f"rd_{dong_so_goc}", horizontal=True)
                        
                        if st.button("Lưu tiến độ", key=f"btn_{dong_so_goc}"):
                            if trang_thai_moi != task['Trạng thái']:
                                sheet_congviec.update_cell(dong_so_goc, 5, trang_thai_moi)
                                st.toast("✅ Đã lưu thành công!")
                                st.rerun()
            else: st.success("🎉 Bạn không còn nhiệm vụ nào tồn đọng.")
        else: st.info("Chưa có dữ liệu công việc.")
