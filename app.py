# -*- coding: utf-8 -*-
import streamlit as st
import io
import re
import math
import pandas as pd
from PIL import Image

# --- 1. 核心库加载 ---
try:
    from pdf417 import encode, render_image
except ImportError:
    st.error("缺失依赖库！请运行: pip install pdf417 Pillow pandas streamlit")

# ==================== 2. 数据映射 ====================
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

RACE_OPTIONS = {
    "W":  "W = 白人 (欧洲、北非或中东)",
    "BK": "BK = 非裔 (非洲黑人)",
    "AI": "AI = 阿拉斯加原住民或美洲印第安人",
    "AP": "AP = 亚裔或太平洋岛民",
    "H":  "H = 西班牙裔",
    "O":  "O = 非西班牙裔",
    "U":  "U = 未知"
}

AAMVA_TAGS_MAP = {
    "DAQ": "证件号码", "DCS": "姓", "DAC": "名", "DAD": "中间名",
    "DBB": "出生日期", "DBD": "签发日期", "DBA": "过期日期", "DBC": "性别",
    "DAU": "身高", "DAW": "体重", "DAY": "眼睛颜色", "DAZ": "头发颜色",
    "DAG": "街道地址", "DAH": "详细地址(Line 2)", "DAI": "城市", "DAJ": "州代码", 
    "DAK": "邮政编码", "DCF": "鉴别码", "DDA": "REAL ID 状态", "DCJ": "审计码", 
    "DDB": "修订日期", "DCA": "类型", "DCB": "限制", "DCD": "背书", 
    "DCK": "ICN", "DCL": "种族", "DDK": "器官捐献标识", "DDL": "退伍军人标识"
}

# ==================== 3. 核心辅助函数 ====================

def clean_date(date_str):
    return re.sub(r'[^0-9]', '', date_str)

def format_hex_inspector(raw_bytes):
    lines = []
    for i in range(0, len(raw_bytes), 16):
        chunk = raw_bytes[i:i+16]
        offset = f"{i:04X}"
        hex_content = " ".join([f"{b:02X}" for b in chunk]).ljust(47)
        ascii_preview = "".join([chr(b) if 32 <= b <= 126 else "." for b in chunk])
        lines.append(f"{offset}  {hex_content}  |{ascii_preview}|")
    return "\n".join(lines)

def reverse_pdf417_params(data_len, ecc_level=5):
    ecc_map = {0:2, 1:4, 2:8, 3:16, 4:32, 5:64, 6:128, 7:256, 8:512}
    ecc_codewords = ecc_map.get(ecc_level, 64)
    data_codewords = math.ceil(data_len / 1.5) 
    total_codewords = data_codewords + ecc_codewords + 1
    results = []
    for cols in range(9, 21):
        rows = math.ceil(total_codewords / cols)
        if 3 <= rows <= 90:
            rec = "✅ 推荐" if cols == 17 else ""
            results.append({"列数": cols, "行数": rows, "总码词": total_codewords, "备注": rec})
    return pd.DataFrame(results)

def build_aamva_stream(inputs, options):
    iin = JURISDICTION_MAP[inputs['state']]
    body = []
    
    # 按照 AAMVA 标准子文件内字段物理顺序
    body.append(f"DAQ{inputs['dl_number'].upper()}\x0a")
    body.append(f"DCS{inputs['last_name'].upper()}\x0a")
    body.append(f"DDEN\x0a")
    body.append(f"DAC{inputs['first_name'].upper()}\x0a")
    body.append(f"DDFN\x0a")
    body.append(f"DAD{inputs['middle_name'].upper()}\x0a")
    body.append(f"DDGN\x0a")
    body.append(f"DCA{inputs['class'].upper()}\x0a")
    body.append(f"DCB{inputs['rest'].upper()}\x0a")
    body.append(f"DCD{inputs['end'].upper()}\x0a")
    body.append(f"DBD{clean_date(inputs['iss_date'])}\x0a")
    body.append(f"DBB{clean_date(inputs['dob'])}\x0a")
    body.append(f"DBA{clean_date(inputs['exp_date'])}\x0a")
    body.append(f"DBC{inputs['sex']}\x0a")
    
    if not options['hide_height']: body.append(f"DAU{inputs['height']} IN\x0a")
    if not options['hide_eyes']:   body.append(f"DAY{inputs['eyes'].upper()}\x0a")
    
    body.append(f"DAG{inputs['address'].upper()}\x0a")
    if not options['hide_dah']:   body.append(f"DAH{inputs['dah'].upper()}\x0a")
    body.append(f"DAI{inputs['city'].upper()}\x0a")
    body.append(f"DAJ{inputs['state'].upper()}\x0a")
    
    zip_raw = re.sub(r'[^0-9]', '', inputs['zip'])
    zip_final = zip_raw + "0000" if len(zip_raw) == 5 else zip_raw
    body.append(f"DAK{zip_final}  \x0a")
    
    body.append(f"DCF{inputs['dd_code'].upper()}\x0a")
    body.append(f"DCGUSA\x0a")
    
    if not options['hide_weight']: body.append(f"DAW{inputs['weight']}\x0a")
    if not options['hide_hair']:   body.append(f"DAZ{inputs['hair'].upper()}\x0a")
    if not options['hide_race']:   body.append(f"DCL{inputs['race'].upper()}\x0a")
    
    if not options['hide_icn']:    body.append(f"DCK{inputs['icn'].upper()}\x0a")
    body.append(f"DDA{'F' if inputs['real_id'] else 'N'}\x0a")
    body.append(f"DDB{clean_date(inputs['rev_date'])}\x0a")
    
    if inputs['veteran']: body.append(f"DDL1\x0a")
    if inputs['donor']:   body.append(f"DDK1\x0a")
    if not options['hide_audit']: body.append(f"DCJ{inputs['audit'].upper()}\x0a")
    
    sub_data = "DL" + "".join(body)
    subfile_bytes = sub_data.encode('latin-1')
    header = f"@\x0a\x1e\x0dANSI {iin}090001".encode('latin-1')
    designator = f"DL0032{len(subfile_bytes):04d}".encode('latin-1')
    return header + designator + b"\x0d" + subfile_bytes

# ==================== 4. 主界面布局 ====================

def main():
    st.set_page_config(page_title="AAMVA 专家生成器", layout="wide")
    
    with st.sidebar:
        st.header("⚙️ 侧边栏配置")
        target_state = st.selectbox("目标州", list(JURISDICTION_MAP.keys()), index=0)
        sel_cols = st.slider("预览列数", 9, 20, 17)
        st.markdown("---")
        h_dah = st.checkbox("隐藏详细地址 (DAH)", True)
        h_h = st.checkbox("隐藏身高 (DAU)", False)
        h_w = st.checkbox("隐藏体重 (DAW)", False)
        h_e = st.checkbox("隐藏眼色 (DAY)", False)
        h_hair = st.checkbox("隐藏发色 (DAZ)", False)
        h_icn = st.checkbox("隐藏 ICN (DCK)", False)
        h_audit = st.checkbox("隐藏审计码 (DCJ)", True)
        h_race = st.checkbox("隐藏种族 (DCL)", True)
        opts = {'hide_dah': h_dah, 'hide_height': h_h, 'hide_weight': h_w, 'hide_eyes': h_e, 
                'hide_hair': h_hair, 'hide_race': h_race, 'hide_icn': h_icn, 'hide_audit': h_audit}

    # 1. 姓名与居住板块
    st.subheader("👤 个人姓名与居住信息")
    with st.container(border=True):
        n_cols = st.columns(3)
        # --- 修正姓名排列顺序：名 -> 中 -> 姓 ---
        fn = n_cols[0].text_input("名字 (DAC)", "CHARLES")
        mn = n_cols[1].text_input("中间名 (DAD)", "NONE")
        ln = n_cols[2].text_input("姓氏 (DCS)", "CORDOVA")
        
        a_cols = st.columns([2, 1, 1])
        addr = a_cols[0].text_input("街道地址 (DAG)", "3704 3RD PL NE")
        city = a_cols[1].text_input("城市 (DAI)", "CENTER POINT")
        zip_c = a_cols[2].text_input("邮政编码 (DAK)", "35215")
        dah_val = st.text_input("详细地址 (DAH)", "APT 101") if not h_dah else ""

    # 2. 证件信息板块
    st.subheader("📝 证件核心信息")
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        dl = c1.text_input("证件号 (DAQ)", "66004729")
        cl = c2.text_input("准驾等级 (DCA)", "D")
        real_id = c3.toggle("符合 REAL ID 标准 (DDA)", True)
        
        d_cols = st.columns(4)
        dob = d_cols[0].text_input("生日 (MMDDYYYY)", "03/04/1969")
        iss = d_cols[1].text_input("签发日", "11/05/2023")
        exp = d_cols[2].text_input("过期日", "11/05/2027")
        rev = d_cols[3].text_input("修订日 (DDB)", "04/26/2022")
        
        admin_cols = st.columns(2)
        icn_input = admin_cols[0].text_input("鉴别码 (DCF)", "NONE") if not h_icn else ""
        audit_input = admin_cols[1].text_input("审计码 (DCJ)", "A020424988483") if not h_audit else ""

        i_cols = st.columns(3)
        dcf = i_cols[0].text_input("ICN (DCK)", "66004729317182331201")
        rs = i_cols[1].text_input("限制代码 (DCB)", "NONE")
        ed = i_cols[2].text_input("背书代码 (DCD)", "NONE")

    # 3. 身体特征板块
    st.subheader("🏃 身体特征与代码")
    with st.container(border=True):
        phys_items = [("sex", "性别 (DBC)", ["1", "2", "9", "0"])]
        if not h_race: phys_items.append(("race", "种族代码 (DCL)", list(RACE_OPTIONS.keys())))
        if not h_h:    phys_items.append(("height", "身高", "070"))
        if not h_w:    phys_items.append(("weight", "体重", "181"))
        if not h_e:    phys_items.append(("eyes", "眼色", "BLU"))
        if not h_hair: phys_items.append(("hair", "发色", "BRO"))
        
        phys_vals = {}
        p_cols = st.columns(len(phys_items) if phys_items else 1)
        for i, item in enumerate(phys_items):
            key, label, default = item[0], item[1], item[2]
            if key == "sex":
                phys_vals["sex"] = p_cols[i].selectbox(label, default, format_func=lambda x: {"1":"男","2":"女","9":"其他","0":"未知"}[x])
            elif key == "race":
                phys_vals["race"] = p_cols[i].selectbox(label, default, index=0, format_func=lambda x: RACE_OPTIONS[x])
            else:
                phys_vals[key] = p_cols[i].text_input(label, default)
        
        st.markdown("---")
        b_cols = st.columns(2)
        vet = b_cols[0].toggle("退伍军人标识 (DDL)", False)
        don = b_cols[1].toggle("器官捐献标识 (DDK)", False)

    if st.button("🚀 生成并执行全面深度分析", type="primary", use_container_width=True):
        inputs = {
            'state': target_state, 'last_name': ln, 'first_name': fn, 'middle_name': mn,
            'dl_number': dl, 'iss_date': iss, 'dob': dob, 'exp_date': exp, 'rev_date': rev,
            'sex': phys_vals.get("sex", "1"), 'address': addr, 'dah': dah_val, 'city': city, 'zip': zip_c, 
            'height': phys_vals.get("height", "070"), 'weight': phys_vals.get("weight", "181"), 
            'eyes': phys_vals.get("eyes", "BLU"), 'hair': phys_vals.get("hair", "BRO"), 
            'race': phys_vals.get("race", "W"), 'icn': icn_input, 'audit': audit_input,
            'donor': don, 'veteran': vet, 'real_id': real_id, 'dd_code': dcf, 
            'class': cl, 'rest': rs, 'end': ed
        }
        
        try:
            raw_data = build_aamva_stream(inputs, opts)
            L = len(raw_data)
            l_col, r_col = st.columns([1.3, 1.4])
            
            with l_col:
                st.subheader("📊 PDF417 条码预览")
                codes = encode(raw_data, columns=sel_cols, security_level=5)
                st.image(render_image(codes, scale=3))
                st.markdown("---")
                st.subheader("📐 PDF417 参数逆向计算")
                st.table(reverse_pdf417_params(L))
                st.markdown("---")
                st.subheader("🛠️ 底层 HEX 查看器")
                st.code(format_hex_inspector(raw_data), language="text")

            with r_col:
                st.subheader("🔍 AAMVA 解析核对")
                raw_text = raw_data.decode('latin-1')
                if "DL" in raw_text:
                    content = raw_text.split("DL", 1)[1]
                    parsed = []
                    for line in content.split('\x0a'):
                        clean_line = line.strip()
                        if len(clean_line) >= 3:
                            tag = clean_line[:3]
                            if tag in AAMVA_TAGS_MAP:
                                parsed.append({"标签": tag, "描述": AAMVA_TAGS_MAP[tag], "内容": clean_line[3:]})
                    st.table(pd.DataFrame(parsed))
                st.markdown("---")
                st.subheader("📋 原始 HEX 字符串")
                st.code(raw_data.hex().upper(), language="text")
        except Exception as e:
            st.error(f"失败: {e}")

if __name__ == "__main__":
    main()# -*- coding: utf-8 -*-
import streamlit as st
import io
import re
import math
import pandas as pd
from PIL import Image

# --- 1. 核心库加载 ---
try:
    from pdf417 import encode, render_image
except ImportError:
    st.error("缺失依赖库！请运行: pip install pdf417 Pillow pandas streamlit")

# ==================== 2. 数据映射 ====================
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

RACE_OPTIONS = {
    "W":  "W = 白人 (欧洲、北非或中东)",
    "BK": "BK = 非裔 (非洲黑人)",
    "AI": "AI = 阿拉斯加原住民或美洲印第安人",
    "AP": "AP = 亚裔或太平洋岛民",
    "H":  "H = 西班牙裔",
    "O":  "O = 非西班牙裔",
    "U":  "U = 未知"
}

AAMVA_TAGS_MAP = {
    "DAQ": "证件号码", "DCS": "姓", "DAC": "名", "DAD": "中间名",
    "DBB": "出生日期", "DBD": "签发日期", "DBA": "过期日期", "DBC": "性别",
    "DAU": "身高", "DAW": "体重", "DAY": "眼睛颜色", "DAZ": "头发颜色",
    "DAG": "街道地址", "DAH": "详细地址(Line 2)", "DAI": "城市", "DAJ": "州代码", 
    "DAK": "邮政编码", "DCF": "鉴别码", "DDA": "REAL ID 状态", "DCJ": "审计码", 
    "DDB": "修订日期", "DCA": "类型", "DCB": "限制", "DCD": "背书", 
    "DCK": "ICN", "DCL": "种族", "DDK": "器官捐献标识", "DDL": "退伍军人标识"
}

# ==================== 3. 核心辅助函数 ====================

def clean_date(date_str):
    return re.sub(r'[^0-9]', '', date_str)

def format_hex_inspector(raw_bytes):
    lines = []
    for i in range(0, len(raw_bytes), 16):
        chunk = raw_bytes[i:i+16]
        offset = f"{i:04X}"
        hex_content = " ".join([f"{b:02X}" for b in chunk]).ljust(47)
        ascii_preview = "".join([chr(b) if 32 <= b <= 126 else "." for b in chunk])
        lines.append(f"{offset}  {hex_content}  |{ascii_preview}|")
    return "\n".join(lines)

def reverse_pdf417_params(data_len, ecc_level=5):
    ecc_map = {0:2, 1:4, 2:8, 3:16, 4:32, 5:64, 6:128, 7:256, 8:512}
    ecc_codewords = ecc_map.get(ecc_level, 64)
    data_codewords = math.ceil(data_len / 1.5) 
    total_codewords = data_codewords + ecc_codewords + 1
    results = []
    for cols in range(9, 21):
        rows = math.ceil(total_codewords / cols)
        if 3 <= rows <= 90:
            rec = "? 推荐" if cols == 17 else ""
            results.append({"列数": cols, "行数": rows, "总码词": total_codewords, "备注": rec})
    return pd.DataFrame(results)

def build_aamva_stream(inputs, options):
    iin = JURISDICTION_MAP[inputs['state']]
    body = []
    
    # 按照 AAMVA 标准子文件内字段物理顺序
    body.append(f"DAQ{inputs['dl_number'].upper()}\x0a")
    body.append(f"DCS{inputs['last_name'].upper()}\x0a")
    body.append(f"DDEN\x0a")
    body.append(f"DAC{inputs['first_name'].upper()}\x0a")
    body.append(f"DDFN\x0a")
    body.append(f"DAD{inputs['middle_name'].upper()}\x0a")
    body.append(f"DDGN\x0a")
    body.append(f"DCA{inputs['class'].upper()}\x0a")
    body.append(f"DCB{inputs['rest'].upper()}\x0a")
    body.append(f"DCD{inputs['end'].upper()}\x0a")
    body.append(f"DBD{clean_date(inputs['iss_date'])}\x0a")
    body.append(f"DBB{clean_date(inputs['dob'])}\x0a")
    body.append(f"DBA{clean_date(inputs['exp_date'])}\x0a")
    body.append(f"DBC{inputs['sex']}\x0a")
    
    if not options['hide_height']: body.append(f"DAU{inputs['height']} IN\x0a")
    if not options['hide_eyes']:   body.append(f"DAY{inputs['eyes'].upper()}\x0a")
    
    body.append(f"DAG{inputs['address'].upper()}\x0a")
    if not options['hide_dah']:   body.append(f"DAH{inputs['dah'].upper()}\x0a")
    body.append(f"DAI{inputs['city'].upper()}\x0a")
    body.append(f"DAJ{inputs['state'].upper()}\x0a")
    
    zip_raw = re.sub(r'[^0-9]', '', inputs['zip'])
    zip_final = zip_raw + "0000" if len(zip_raw) == 5 else zip_raw
    body.append(f"DAK{zip_final}  \x0a")
    
    body.append(f"DCF{inputs['dd_code'].upper()}\x0a")
    body.append(f"DCGUSA\x0a")
    
    if not options['hide_weight']: body.append(f"DAW{inputs['weight']}\x0a")
    if not options['hide_hair']:   body.append(f"DAZ{inputs['hair'].upper()}\x0a")
    if not options['hide_race']:   body.append(f"DCL{inputs['race'].upper()}\x0a")
    
    if not options['hide_icn']:    body.append(f"DCK{inputs['icn'].upper()}\x0a")
    body.append(f"DDA{'F' if inputs['real_id'] else 'N'}\x0a")
    body.append(f"DDB{clean_date(inputs['rev_date'])}\x0a")
    
    if inputs['veteran']: body.append(f"DDL1\x0a")
    if inputs['donor']:   body.append(f"DDK1\x0a")
    if not options['hide_audit']: body.append(f"DCJ{inputs['audit'].upper()}\x0a")
    
    sub_data = "DL" + "".join(body)
    subfile_bytes = sub_data.encode('latin-1')
    header = f"@\x0a\x1e\x0dANSI {iin}090001".encode('latin-1')
    designator = f"DL0032{len(subfile_bytes):04d}".encode('latin-1')
    return header + designator + b"\x0d" + subfile_bytes

# ==================== 4. 主界面布局 ====================

def main():
    st.set_page_config(page_title="AAMVA 专家生成器", layout="wide")
    
    with st.sidebar:
        st.header("?? 侧边栏配置")
        target_state = st.selectbox("目标州", list(JURISDICTION_MAP.keys()), index=0)
        sel_cols = st.slider("预览列数", 9, 20, 17)
        st.markdown("---")
        h_dah = st.checkbox("隐藏详细地址 (DAH)", True)
        h_h = st.checkbox("隐藏身高 (DAU)", False)
        h_w = st.checkbox("隐藏体重 (DAW)", False)
        h_e = st.checkbox("隐藏眼色 (DAY)", False)
        h_hair = st.checkbox("隐藏发色 (DAZ)", False)
        h_icn = st.checkbox("隐藏 ICN (DCK)", False)
        h_audit = st.checkbox("隐藏审计码 (DCJ)", True)
        h_race = st.checkbox("隐藏种族 (DCL)", True)
        opts = {'hide_dah': h_dah, 'hide_height': h_h, 'hide_weight': h_w, 'hide_eyes': h_e, 
                'hide_hair': h_hair, 'hide_race': h_race, 'hide_icn': h_icn, 'hide_audit': h_audit}

    # 1. 姓名与居住板块
    st.subheader("?? 个人姓名与居住信息")
    with st.container(border=True):
        n_cols = st.columns(3)
        # --- 修正姓名排列顺序：名 -> 中 -> 姓 ---
        fn = n_cols[0].text_input("名字 (DAC)", "CHARLES")
        mn = n_cols[1].text_input("中间名 (DAD)", "NONE")
        ln = n_cols[2].text_input("姓氏 (DCS)", "CORDOVA")
        
        a_cols = st.columns([2, 1, 1])
        addr = a_cols[0].text_input("街道地址 (DAG)", "3704 3RD PL NE")
        city = a_cols[1].text_input("城市 (DAI)", "CENTER POINT")
        zip_c = a_cols[2].text_input("邮政编码 (DAK)", "35215")
        dah_val = st.text_input("详细地址 (DAH)", "APT 101") if not h_dah else ""

    # 2. 证件信息板块
    st.subheader("?? 证件核心信息")
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        dl = c1.text_input("证件号 (DAQ)", "66004729")
        cl = c2.text_input("准驾等级 (DCA)", "D")
        real_id = c3.toggle("符合 REAL ID 标准 (DDA)", True)
        
        d_cols = st.columns(4)
        dob = d_cols[0].text_input("生日 (MMDDYYYY)", "03/04/1969")
        iss = d_cols[1].text_input("签发日", "11/05/2023")
        exp = d_cols[2].text_input("过期日", "11/05/2027")
        rev = d_cols[3].text_input("修订日 (DDB)", "04/26/2022")
        
        admin_cols = st.columns(2)
        icn_input = admin_cols[0].text_input("ICN (DCK)", "66004729317182331201") if not h_icn else ""
        audit_input = admin_cols[1].text_input("审计码 (DCJ)", "A020424988483") if not h_audit else ""

        i_cols = st.columns(3)
        dcf = i_cols[0].text_input("鉴别码 (DCF)", "NONE")
        rs = i_cols[1].text_input("限制代码 (DCB)", "NONE")
        ed = i_cols[2].text_input("背书代码 (DCD)", "NONE")

    # 3. 身体特征板块
    st.subheader("?? 身体特征与代码")
    with st.container(border=True):
        phys_items = [("sex", "性别 (DBC)", ["1", "2", "9", "0"])]
        if not h_race: phys_items.append(("race", "种族代码 (DCL)", list(RACE_OPTIONS.keys())))
        if not h_h:    phys_items.append(("height", "身高", "070"))
        if not h_w:    phys_items.append(("weight", "体重", "181"))
        if not h_e:    phys_items.append(("eyes", "眼色", "BLU"))
        if not h_hair: phys_items.append(("hair", "发色", "BRO"))
        
        phys_vals = {}
        p_cols = st.columns(len(phys_items) if phys_items else 1)
        for i, item in enumerate(phys_items):
            key, label, default = item[0], item[1], item[2]
            if key == "sex":
                phys_vals["sex"] = p_cols[i].selectbox(label, default, format_func=lambda x: {"1":"男","2":"女","9":"其他","0":"未知"}[x])
            elif key == "race":
                phys_vals["race"] = p_cols[i].selectbox(label, default, index=0, format_func=lambda x: RACE_OPTIONS[x])
            else:
                phys_vals[key] = p_cols[i].text_input(label, default)
        
        st.markdown("---")
        b_cols = st.columns(2)
        vet = b_cols[0].toggle("退伍军人标识 (DDL)", False)
        don = b_cols[1].toggle("器官捐献标识 (DDK)", False)

    if st.button("?? 生成并执行全面深度分析", type="primary", use_container_width=True):
        inputs = {
            'state': target_state, 'last_name': ln, 'first_name': fn, 'middle_name': mn,
            'dl_number': dl, 'iss_date': iss, 'dob': dob, 'exp_date': exp, 'rev_date': rev,
            'sex': phys_vals.get("sex", "1"), 'address': addr, 'dah': dah_val, 'city': city, 'zip': zip_c, 
            'height': phys_vals.get("height", "070"), 'weight': phys_vals.get("weight", "181"), 
            'eyes': phys_vals.get("eyes", "BLU"), 'hair': phys_vals.get("hair", "BRO"), 
            'race': phys_vals.get("race", "W"), 'icn': icn_input, 'audit': audit_input,
            'donor': don, 'veteran': vet, 'real_id': real_id, 'dd_code': dcf, 
            'class': cl, 'rest': rs, 'end': ed
        }
        
        try:
            raw_data = build_aamva_stream(inputs, opts)
            L = len(raw_data)
            l_col, r_col = st.columns([1.3, 1.4])
            
            with l_col:
                st.subheader("?? PDF417 条码预览")
                codes = encode(raw_data, columns=sel_cols, security_level=5)
                st.image(render_image(codes, scale=3))
                st.markdown("---")
                st.subheader("?? PDF417 参数逆向计算")
                st.table(reverse_pdf417_params(L))
                st.markdown("---")
                st.subheader("??? 底层 HEX 查看器")
                st.code(format_hex_inspector(raw_data), language="text")

            with r_col:
                st.subheader("?? AAMVA 解析核对")
                raw_text = raw_data.decode('latin-1')
                if "DL" in raw_text:
                    content = raw_text.split("DL", 1)[1]
                    parsed = []
                    for line in content.split('\x0a'):
                        clean_line = line.strip()
                        if len(clean_line) >= 3:
                            tag = clean_line[:3]
                            if tag in AAMVA_TAGS_MAP:
                                parsed.append({"标签": tag, "描述": AAMVA_TAGS_MAP[tag], "内容": clean_line[3:]})
                    st.table(pd.DataFrame(parsed))
                st.markdown("---")
                st.subheader("?? 原始 HEX 字符串")
                st.code(raw_data.hex().upper(), language="text")
        except Exception as e:
            st.error(f"失败: {e}")

if __name__ == "__main__":
    main()
