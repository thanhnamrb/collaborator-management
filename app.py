import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import date

st.set_page_config(page_title="App Giao Việc", layout="wide")
st.title("📝 Hệ thống Quản lý Công việc")

# 1. KẾT NỐI VỚI GOOGLE SHEETS
# Lấy chìa khóa từ két sắt
key_dict = json.loads(st.secrets["json_key"])
creds = Credentials.from_service_account_info(
    key_dict, 
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets", 
        "https://www.googleapis.com/auth/drive"
    ]
)
client = gspread.authorize(creds)

# Mở file Google Sheets (Đảm bảo tên file trùng khớp với tên bạn đã tạo)
# Lưu ý: Chọn sheet đầu tiên (sheet1)
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1jQFz2qqoDKLDDBKF97QXMfr_RcRv57vlGtIqHUBtK1w/edit?usp=sharing").sheet1

# 2. CHIA MÀN HÌNH LÀM 2 CỘT
cot_trai, cot_phai = st.columns([1, 2])

# --- CỘT TRÁI: GIAO VIỆC ---
with cot_trai:
    with st.form("form_giao_viec"):
        st.subheader("Giao công việc mới")
        ten_cong_viec = st.text_input("Tên công việc:")
        nguoi_nhan = st.selectbox("Giao cho ai?", ["Nhân viên A", "Nhân viên B", "Nhân viên C"])
        han_chot = st.date_input("Hạn chót (Deadline):", min_value=date.today())
        mo_ta = st.text_area("Mô tả chi tiết:")
        
        nut_gui = st.form_submit_button("Giao việc")
        
        if nut_gui:
            if ten_cong_viec == "":
                st.error("Vui lòng nhập tên công việc!")
            else:
                # Định dạng ngày tháng thành dạng chữ (chuỗi) để đưa lên Google Sheets
                han_chot_str = han_chot.strftime("%d/%m/%Y")
                
                # Thêm 1 dòng mới vào Google Sheets
                # Thứ tự phải khớp với tiêu đề cột: Tên | Người nhận | Hạn | Mô tả | Trạng thái
                sheet.append_row([ten_cong_viec, nguoi_nhan, han_chot_str, mo_ta, "Mới giao"])
                
                st.success("Đã lưu dữ liệu thẳng vào Google Sheets!")

# --- CỘT PHẢI: XEM TIẾN ĐỘ ---
with cot_phai:
    st.subheader("📋 Bảng theo dõi tiến độ")
    
    # Kéo toàn bộ dữ liệu từ Google Sheets về
    data = sheet.get_all_records()
    
    if len(data) > 0:
        # Biến thành dạng bảng và hiển thị
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Chưa có công việc nào. Hãy giao việc ở cột bên trái!")
