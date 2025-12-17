# -*- coding: utf-8 -*-
import streamlit as st
import io
from datetime import datetime
from PIL import Image

# --- 依赖库加载 ---
try:
    from pdf417 import encode, render_image
except ImportError:
    st.error("缺失依赖库！请确保在 requirements.txt 中包含了 pdf417 和 Pillow。")

# ==================== 1. AAMVA 50 州 IIN 数据库 ====================
JURISDICTION_MAP = {
    "AL": "636033", "AK": "636059", "AZ": "636026", "AR": "636021", "CA": "636014",
    "CO": "636020", "CT": "636006", "DE": "636011", "DC": "636043", "FL": "636010",
    "GA": "636055", "HI": "636047", "ID": "636050", "IL": "636035", "IN": "636037",
    "IA": "636018", "KS": "636022", "KY": "636046", "LA": "636007", "ME": "636041",
    "MD": "636003", "MA": "636002", "MI": "636032", "MN": "636038", "MS": "636051",
    "MO": "636030", "MT": "636008", "NE": "636054", "NV": "636049", "NH": "636039",
    "NJ": "636036", "NM": "636009", "NY": "636001", "NC": "636004", "ND": "636034",
    "OH": "636023", "OK": "636058", "OR": "636029", "PA": "636025", "RI": "636052",
    "SC": "636005", "SD": "636042", "TN": "636053", "TX": "636015", "UT": "636040",
    "VT": "636024", "VA": "636000", "WA": "636045", "WV": "636061", "WI": "636031", "WY": "636060"
}

# ==================== 2. 核心数据对齐逻辑 ====================

def build_aamva_stream(inputs, options):
    iin = JURISDICTION_MAP[inputs['state']]
    aamva_ver, jur_ver, num_entries = "09", "00", "01"

    body = [
        f"DAQ{inputs['dl_number']}\x0a",
        f"DCS{inputs['last_name']}\x0a",
        f"DDEN{inputs['first_name']}\x0a",
        f"DAC{inputs['middle_name']}\x0a",
        f"DDFN\x0aDAD\x0aDDGN\x0a",
        f"DCA{inputs['class']}\x0a",
        f"DBD{inputs['iss_date']}\x0a",
        f"DBB{inputs['dob']}\x0a",
        f"DBA{inputs['exp_date']}\x0a",
        f"DBC{inputs['sex']}\x0a",
        f"DAU{inputs['height']} in\x0a",
        f"DAY{inputs['eyes']}\x0a",
        f"DAG{inputs['address']}\x0a",
        f"DAI{inputs['city']}\x0a",
        f"DAJ{inputs['state']}\x0a"
    ]
    
    zip_val = inputs['zip'].replace("-", "")
    if len(zip_val) == 5: zip_val += "0000"
    body.append(f"DAK{zip_val}  \x0a")
    
    body.append(f"DCF{inputs['dd_code']}\x0a")
    body.append(f"DCGUSA\x0aDDAF\x0a")
    body.append(f"DDB{inputs['rev_date']}\x0a")
    body.append(f"DDD1\x0a")
    
    if not options['hide_audit']: body.append(f"DCJ{inputs['audit']}\x0a")
    body.append(f"DCU")

    subfile_str = "DL" + "".join(body) + "\x0d"
    subfile_bytes = subfile_str.encode('latin-1')
    len_dl = len(subfile_bytes)

    # Offset 32 锁定
    header_prefix = f"@\x0a\x1e\x0dANSI {iin}{aamva_ver}{jur_ver}{num_entries}"
    designator = f"DL0032{len_dl:04d}"
    
    return header_prefix.encode('latin-1') + designator.encode('latin-1') + b"\x0d" + subfile_bytes

# ==================== 3. 仿 Passport-Cloud 布局 ====================

def main():
    st.set_page_config(page_title="PDF417 Barcode Generator", layout="wide")
    
    # 顶部标题栏
    st.markdown("<h2 style='text-align: center;'>PDF417 Barcode Generator (AAMVA Standard)</h2>", unsafe_allow_html=True)
    st.markdown("---")

    # 1. 侧边栏：配置参数 (左侧)
    with st.sidebar:
        st.subheader("⚙️ Settings")
        target_state = st.selectbox("Select State", list(JURISDICTION_MAP.keys()), index=47)
        st.info(f"IIN: {JURISDICTION_MAP[target_state]} | Ver: 09")
        
        st.markdown("---")
        st.subheader("Visibility")
        options = {
            'hide_height': st.checkbox("Hide Height (DAU)", False),
            'hide_audit': st.checkbox("Hide Audit Code (DCJ)", True)
        }
        
        st.markdown("---")
        st.subheader("Barcode Style")
        cols = st.slider("Columns", 11, 19, 13)
        px_scale = st.slider("Scale", 1, 5, 3)

    # 2. 主界面：输入表单 (右侧上方 - 两列布局)
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            ln = st.text_input("Last Name (DCS)", "SOLOMON")
            fn = st.text_input("First Name (DAC)", "DANIEL")
            mn = st.text_input("Middle Name", "NONE")
            dl = st.text_input("License Number (DAQ)", "WDL0ALXD2K1B")
            sex = st.selectbox("Sex (DBC)", ["1", "2"], format_func=lambda x: "Male" if x=="1" else "Female")

        with col2:
            dob = st.text_input("DOB (MMDDYYYY)", "08081998")
            iss = st.text_input("Issue Date", "06062024")
            exp = st.text_input("Expiry Date", "08082030")
            rev = st.text_input("Revision Date", "11122019")
            dd_code = st.text_input("Document Discriminator (DCF)", "WDL0ALXD2K1BA020424988483")

        st.markdown("#### Address & Features")
        addr_col, city_col, zip_col = st.columns([2, 1, 1])
        addr = addr_col.text_input("Address (DAG)", "29810 224TH AVE SE")
        city = city_col.text_input("City (DAI)", "KENT")
        zip_c = zip_col.text_input("Zip (DAK)", "98010")

    # 3. 操作按钮
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Generate Barcode", type="primary", use_container_width=True):
        inputs = {
            'state': target_state, 'last_name': ln, 'first_name': fn, 'middle_name': mn,
            'dl_number': dl, 'dob': dob, 'iss_date': iss, 'exp_date': exp,
            'rev_date': rev, 'sex': sex, 'address': addr, 'city': city,
            'zip': zip_c, 'height': '072', 'eyes': 'BLU',
            'class': 'NONE', 'rest': 'NONE', 'endorse': 'NONE',
            'dd_code': dd_code, 'audit': 'A020424988483', 'dda': 'F'
        }
        
        try:
            raw_data = build_aamva_stream(inputs, options)
            
            # 4. 主界面：结果展示 (右侧下方)
            st.markdown("---")
            res_col, hex_col = st.columns([1, 1])
            
            with res_col:
                st.subheader("Barcode Preview")
                codes = encode(raw_data, columns=cols, security_level=5)
                img = render_image(codes, scale=px_scale, ratio=3, padding=10)
                st.image(img, use_container_width=False)
                
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                st.download_button("Download PNG", buf.getvalue(), f"{target_state}_DL.png", use_container_width=True)

            with hex_col:
                st.subheader("Hexadecimal View")
                hex_str = raw_data.hex().upper()
                st.code("\n".join([hex_str[i:i+32] for i in range(0, len(hex_str), 32)]), language="text")

        except Exception as e:
            st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
