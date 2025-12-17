# -*- coding: utf-8 -*-
import streamlit as st
import io

# --- 依赖库加载 ---
try:
    from pdf417 import encode, render_image
except ImportError:
    st.error("缺失依赖库！请确保在 requirements.txt 中包含了 pdf417 和 Pillow")

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

# ==================== 2. 数据处理辅助函数 ====================

def get_readable_plain_text(raw_bytes):
    """将字节流转换为包含可见控制字符标识的明文"""
    # 使用 latin-1 解码以保持单字节对应关系
    text = raw_bytes.decode('latin-1')
    text = text.replace('\x0a', '[LF]\n')  # 换行符
    text = text.replace('\x0d', '[CR]')     # 回车符
    text = text.replace('\x1e', '[RS]')     # 记录分隔符
    text = text.replace('\x40', '[@]')      # 起始符
    return text

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
        f"DBC{inputs['sex']}\x0a"
    ]
    
    if not options['hide_height']: 
        body.append(f"DAU{inputs['height']} in\x0a")
    
    body.append(f"DAY{inputs['eyes']}\x0a")
    body.append(f"DAG{inputs['address']}\x0a")
    body.append(f"DAI{inputs['city']}\x0a")
    body.append(f"DAJ{inputs['state']}\x0a")
    
    zip_val = inputs['zip'].replace("-", "")
    if len(zip_val) == 5: zip_val += "0000"
    body.append(f"DAK{zip_val}  \x0a")
    body.append(f"DCF{inputs['dd_code']}\x0a")
    body.append(f"DCGUSA\x0aDDAF\x0a")
    body.append(f"DDB{inputs['rev_date']}\x0a")
    body.append(f"DDD1\x0a")
    
    if not options['hide_audit']: 
        body.append(f"DCJ{inputs['audit']}\x0a")
        
    body.append(f"DCU")

    subfile_str = "DL" + "".join(body) + "\x0d"
    subfile_bytes = subfile_str.encode('latin-1')
    len_dl = len(subfile_bytes)

    header_prefix = f"@\x0a\x1e\x0dANSI {iin}{aamva_ver}{jur_ver}{num_entries}"
    designator = f"DL0032{len_dl:04d}"
    
    return header_prefix.encode('latin-1') + designator.encode('latin-1') + b"\x0d" + subfile_bytes

# ==================== 3. 主界面布局 ====================

def main():
    st.set_page_config(page_title="PDF417 条码专家", layout="wide")
    st.markdown("<h2 style='text-align: center;'>PDF417 AAMVA 明文数据分析器</h2>", unsafe_allow_html=True)
    st.markdown("---")

    with st.sidebar:
        st.subheader("⚙️ 配置")
        target_state = st.selectbox("选择州", list(JURISDICTION_MAP.keys()), index=9)
        st.markdown("---")
        hide_h = st.checkbox("隐藏身高 (DAU)", False)
        hide_a = st.checkbox("隐藏审计码 (DCJ)", False)
        options = {'hide_height': hide_h, 'hide_audit': hide_a}
        col_count = st.slider("条码列数", 9, 20, 13)

    # 输入表单 (为了演示，直接使用上一轮的数据)
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            ln = st.text_input("姓 (DCS)", "SOLOMON")
            fn = st.text_input("名 (DAC)", "DANIEL")
            mn = st.text_input("中间名", "NONE")
            dl = st.text_input("证件号 (DAQ)", "WDL0ALXD2K1B")
            sex = st.selectbox("性别", ["1", "2"])
        with col2:
            dob = st.text_input("生日", "08081998")
            iss = st.text_input("签发日", "06062024")
            exp = st.text_input("过期日", "08082030")
            rev = st.text_input("版面日期", "11122019")
            dd_code = st.text_input("鉴别码 (DCF)", "WDL0ALXD2K1BA020424988483")
        
        addr = st.text_input("地址", "29810 224TH AVE SE")
        city, zip_c = st.columns(2)
        city_v = city.text_input("城市", "KENT")
        zip_v = zip_c.text_input("邮编", "98010")

    if st.button("🚀 生成条码并输出明文", type="primary", use_container_width=True):
        inputs = {
            'state': target_state, 'last_name': ln, 'first_name': fn, 'middle_name': mn,
            'dl_number': dl, 'dob': dob, 'iss_date': iss, 'exp_date': exp,
            'rev_date': rev, 'sex': sex, 'address': addr, 'city': city_v,
            'zip': zip_v, 'height': '072', 'eyes': 'BLU', 'class': 'NONE',
            'dd_code': dd_code, 'audit': 'A020424988483'
        }
        
        raw_data = build_aamva_stream(inputs, options)
        
        st.markdown("---")
        # 核心输出区
        res_col, plain_col = st.columns([1, 1])
        
        with res_col:
            st.subheader("📊 条码预览")
            codes = encode(raw_data, columns=col_count, security_level=5)
            img = render_image(codes, scale=3)
            st.image(img)

        with plain_col:
            st.subheader("📄 明文数据 (Plain Text)")
            # 这里输出解码后的明文
            readable_text = get_readable_plain_text(raw_data)
            st.text_area("原始字符串流 (包含控制字符标识):", value=readable_text, height=300)
            
            st.subheader("🔢 十六进制 (HEX)")
            st.code(raw_data.hex().upper(), language="text")

if __name__ == "__main__":
    main()
