import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import date, datetime, timedelta

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Hệ thống Quản lý CTV", page_icon="✨", layout="wide")

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
    
    # Lấy danh sách CTV (Hỗ trợ cả chữ Nhân viên cũ trong sheet nếu có)
    danh_sach_ctv = [row["Tên tài khoản"] for row in data_taikhoan if row["Vai trò"] in ["CTV", "Nhân viên"]]

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
        if thoi_gian_con_lai.total_seconds() < 0: return 1, "🔴 QUÁ HẠN"
        elif thoi_gian_con_lai <= timedelta(hours=24): return 2, "🟠 GẤP (<24h)"
        elif thoi_gian_con_lai <= timedelta(days=3): return 3, "🟡 Sắp tới"
        else: return 4, "🔵 Đang làm"

    df_congviec[['diem_uu_tien', 'Trạng thái ưu tiên']] = df_congviec.apply(
        lambda row: pd.Series(danh_gia_uu_tien(row['ngay_gio_chuan'], row.get('Trạng thái', ''))), axis=1
    )
    df_congviec = df_congviec.sort_values(by=['diem_uu_tien', 'ngay_gio_chuan'])
else:
    df_congviec = pd.DataFrame()

# --- 2. HỆ THỐNG ĐĂNG NHẬP & PHÂN LUỒNG GIAO DIỆN ---
if 'nguoi_dung' not in st.session_state: st.session_state.nguoi_dung = None
if 'vai_tro' not in st.session_state: st.session_state.vai_tro = None

if st.session_state.nguoi_dung is None:
    # ==========================================
    # GIAO DIỆN LOGIN "WOW" (Hiệu ứng kính mờ + Nền động)
    # ==========================================
    st.markdown("""
        <style>
        /* Ẩn Header mặc định */
        [data-testid="stHeader"], footer {visibility: hidden;}
        
        /* Hình nền Gradient Động toàn màn hình */
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(-45deg, #0f2027, #203a43, #2c5364, #1e293b);
            background-size: 400% 400%;
            animation: gradientBG 15s ease infinite;
            height: 100vh;
        }
        @keyframes gradientBG {
            0% {background-position: 0% 50%;}
            50% {background-position: 100% 50%;}
            100% {background-position: 0% 50%;}
        }
        
        /* Hiệu ứng Thẻ Kính (Glassmorphism) */
        .glass-card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-radius: 24px;
            padding: 50px 40px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.3);
            text-align: center;
            max-width: 450px;
            margin: 0 auto;
            margin-top: 10vh;
        }
        
        /* Tùy chỉnh Form bên trong Glass Card */
        .glass-card h1 {color: #1e293b; font-weight: 800; font-size: 2.5rem; margin-bottom: 5px;}
        .glass-card p {color: #64748b; font-size: 1.1rem; margin-bottom: 30px;}
        
        /* Ép nút Đăng nhập đẹp mắt */
        div.stButton > button {
            background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
            color: white !important; border-radius: 12px !important; border: none !important;
            padding: 0.8rem !important; font-weight: bold !important; font-size: 1.1rem !important;
            box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.4) !important; transition: 0.3s !important;
            width: 100%;
        }
        div.stButton > button:hover { transform: translateY(-3px) !important; box-shadow: 0 20px 25px -5px rgba(59, 130, 246, 0.5) !important; }
        
        /* Chỉnh ô nhập liệu gọn gàng */
        [data-baseweb="input"] { background-color: #f8fafc !important; border-radius: 10px !important; border: 1px solid #cbd5e1 !important; }
        [data-baseweb="input"]:focus-within { border-color: #3b82f6 !important; }
        </style>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("""
            <div class='glass-card'>
                <h1>Quản lý CTV<span style='color:#f59e0b'>.</span></h1>
                <p>Hệ thống vận hành chuyên nghiệp</p>
        """, unsafe_allow_html=True)
        
        with st.form("form_dang_nhap"):
            st.text_input("👤 Tên tài khoản", key="tk_input") 
            st.text_input("🔑 Mật khẩu", type="password", key="mk_input")
            st.write("<br>", unsafe_allow_html=True)
            nut_dang_nhap = st.form_submit_button("🚀 TRUY CẬP")
            
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
                else: st.error("Sai thông tin đăng nhập!")
        st.markdown("</div>", unsafe_allow_html=True)

else:
    # ==========================================
    # GIAO DIỆN LÀM VIỆC (Sáng, Sạch, Sửa lỗi SVG Mũi tên)
    # ==========================================
    st.markdown("""
        <style>
        /* Ép nền sáng cho giao diện bên trong */
        [data-testid="stAppViewContainer"] { background-color: #f8fafc !important; }
        [data-testid="stHeader"], footer { visibility: hidden; }
        
        /* Bảo vệ mũi tên SVG (Arrow Down) không bị lỗi hiển thị */
        svg { fill: #475569 !important; }
        [data-baseweb="select"] svg { fill: #0f172a !important; display: block !important; }
        summary svg { fill: #0f172a !important; display: block !important; width: 1.5rem !important; height: 1.5rem !important; }

        /* Khung Form và Expander sạch sẽ, bo góc, có bóng mờ */
        div[data-testid="stForm"], div[data-testid="stExpander"] {
            background-color: #ffffff !important; border-radius: 12px !important;
            border: 1px solid #e2e8f0 !important; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05) !important;
            padding: 15px !important;
        }
        
        /* Sửa màu sắc chung */
        h1, h2, h3, h4, h5, p, span, label { color: #0f172a !important; font-family: 'Inter', sans-serif; }
        
        /* Ô nhập liệu */
        [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {
            background-color: #ffffff !important; border: 1px solid #cbd5e1 !important; border-radius: 8px !important;
        }
        input, textarea { color: #0f172a !important; }

        /* Nút bấm */
        div.stButton > button {
            background: #3b82f6 !important; color: white !important; border-radius: 8px !important; border: none !important;
            box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.3) !important; font-weight: bold !important;
        }
        div.stButton > button:hover { background: #2563eb !important; transform: translateY(-1px) !important; }
        
        /* Nút Đăng xuất */
        div[data-testid="column"] > div.stButton > button {
            background: #f1f5f9 !important; color: #475569 !important; box-shadow: none !important; border: 1px solid #e2e8f0 !important;
        }
        div[data-testid="column"] > div.stButton > button:hover { background: #e2e8f0 !important; color: #0f172a !important; }
        </style>
    """, unsafe_allow_html=True)

    # Thanh Header mượt mà
    st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center; background: white; padding: 15px 25px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);'>
            <div style='font-weight: 800; font-size: 1.2rem; color: #2563eb;'>Hệ thống <span style='color: #0f172a;'>Quản lý CTV</span></div>
            <div style='font-weight: 600; color: #475569;'>👤 {st.session_state.vai_tro}: {st.session_state.nguoi_dung}</div>
        </div>
    """, unsafe_allow_html=True)
    
    c_logout_spacer, c_logout_btn = st.columns([8, 1])
    with c_logout_btn:
        if st.button("Đăng xuất", use_container_width=True):
            st.session_state.nguoi_dung = None; st.session_state.vai_tro = None; st.rerun()

    # ==========================
    # GÓC NHÌN QUẢN LÝ
    # ==========================
    if st.session_state.vai_tro == "Quản lý":
        tab_list, tab_giao, tab_nhan_su = st.tabs(["📋 Danh sách & Tiến độ", "✨ Giao việc cho CTV", "👥 Quản lý CTV"])
        
        with tab_list:
            if not df_congviec.empty:
                df_hien_thi = df_congviec[['Tên công việc', 'Người nhận', 'Hạn chót', 'Trạng thái ưu tiên', 'Trạng thái']].copy()
                st.dataframe(
                    df_hien_thi, use_container_width=True, hide_index=True, height=500,
                    column_config={
                        "Tên công việc": st.column_config.TextColumn("Công việc", width="large"),
                        "Người nhận": st.column_config.TextColumn("CTV Phụ trách", width="medium"),
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
                    st.markdown("#### ✨ Tạo phiếu giao việc")
                    st.markdown("---")
                    ten_cong_viec = st.text_input("Tiêu đề công việc:")
                    nguoi_nhan = st.selectbox("Phân công cho CTV:", danh_sach_ctv) if len(danh_sach_ctv) > 0 else None
                    
                    c_ngay, c_gio = st.columns(2)
                    with c_ngay: ngay_han = st.date_input("Ngày kết thúc:")
                    with c_gio: gio_han = st.time_input("Giờ kết thúc:")
                    
                    mo_ta = st.text_area("Mô tả chi tiết (Hỗ trợ xuống dòng):", height=150)
                    st.write("<br>", unsafe_allow_html=True)
                    nut_gui = st.form_submit_button("🚀 GIAO VIỆC NGAY", use_container_width=True)
                    
                    if nut_gui and ten_cong_viec != "" and nguoi_nhan is not None:
                        han_chot_gop = f"{ngay_han.strftime('%d/%m/%Y')} {gio_han.strftime('%H:%M')}"
                        sheet_congviec.append_row([ten_cong_viec, nguoi_nhan, han_chot_gop, mo_ta, "Mới giao"])
                        st.success("Đã giao việc thành công!")
                        st.rerun()
                        
        with tab_nhan_su:
            df_taikhoan = pd.DataFrame(data_taikhoan)
            st.dataframe(df_taikhoan, use_container_width=True, hide_index=True)

    # ==========================
    # GÓC NHÌN CỘNG TÁC VIÊN (CTV)
    # ==========================
    else:
        st.markdown("#### 📋 Danh sách công việc cần xử lý")
        st.write("<br>", unsafe_allow_html=True)
        if not df_congviec.empty:
            df_nhan_vien = df_congviec[df_congviec['Người nhận'] == st.session_state.nguoi_dung]
            
            if len(df_nhan_vien) > 0:
                for index, task in df_nhan_vien.iterrows():
                    dong_so_goc = task['dong_so_goc']
                    mo_ta_html = str(task['Mô tả']).replace('\n', '<br>')

                    with st.expander(f"{task['Trạng thái ưu tiên']} | {task['Tên công việc']} (Hạn: {task['Hạn chót']})", expanded=True):
                        st.markdown(f"""
                            <div style='background-color: #f1f5f9; color: #0f172a; padding: 20px; border-radius: 8px; border-left: 4px solid #3b82f6; margin-bottom: 20px; font-size: 1.05rem;'>
                                <strong style='color: #2563eb;'>📝 Hướng dẫn:</strong><br><br>
                                {mo_ta_html}
                            </div>
                        """, unsafe_allow_html=True)
                        
                        danh_sach = ["Mới giao", "Đang làm", "Hoàn thành"]
                        hien_tai = task['Trạng thái'] if task['Trạng thái'] in danh_sach else "Mới giao"
                        trang_thai_moi = st.radio("Cập nhật tiến độ của bạn:", danh_sach, index=danh_sach.index(hien_tai), key=f"rd_{dong_so_goc}", horizontal=True)
                        
                        if st.button("Lưu tiến độ", key=f"btn_{dong_so_goc}"):
                            if trang_thai_moi != task['Trạng thái']:
                                sheet_congviec.update_cell(dong_so_goc, 5, trang_thai_moi)
                                st.toast("✅ Đã cập nhật trạng thái!")
                                st.rerun()
            else: st.success("🎉 Tạm thời bạn không có công việc nào tồn đọng.")
        else: st.info("Hệ thống chưa có dữ liệu công việc.")
