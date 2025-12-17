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
    "AI": "AI = Alaskan or American Indian",
    "AP": "AP = Asian or Pacific Islander",
    "BK": "BK = Black (African origins)",
    "W": "W = White (Europe, N. Africa, Middle East)",
    "H": "H = Hispanic Origin",
    "O": "O = Not of Hispanic Origin",
    "U": "U = Unknown"
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

# ==================== 3. 核心函数 ====================

def clean_date(date_str):
    return re.sub(r'[^0-9]', '', date_str)

def format_hex_dump(raw_bytes):
    lines = []
    for i in range(0, len(raw_bytes), 16):
        chunk = raw_bytes[i:i+16]
        hex_part = chunk.hex().upper().ljust(32)
        ascii_part = "".join([chr(b) if 32 <= b <= 126 else "." for b in chunk])
        lines.append(f"{hex_part} | {ascii_part}")
    return "\n".join(lines)

def build_aamva_stream(inputs, options):
    iin = JURISDICTION_MAP[inputs['state']]
    body = []
    
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
    body.append(f"DAJ \x0a")
    body.append(f"DAK{clean_date(inputs['zip'])}  \x0a")
    body.append(f"DCF{inputs['dd_code'].upper()}\x0a")
    body.append(f"DCGUSA\x0a")
    
    if not options['hide_weight']: body.append(f"DAW{inputs['weight']}\x0a")
    if not options['hide_hair']:   body.append(f"DAZ{inputs['hair'].upper()}\x0a")
    if not options['hide_race']:   body.append(f"DCL{inputs['race'].upper()}\x0a")
    if not options['hide_icn']:    body.append(f"DCK{inputs['icn'].upper()}\x0a")
    
    body.append(f"DDA{'F' if inputs['real_id'] else 'N'}\x0a")
    body.append(f"DDB{clean_date(inputs['rev_date'])}\x0a")
    
    if inputs['veteran']: body.append(f"DDLY\x0a")
    if inputs['donor']:   body.append(f"DDKY\x0a")
    if not options['hide_audit']: body.append(f"DCJ{inputs['audit'].upper()}\x0a")
    
    sub_data = "DL" + "".join(body)
    subfile_bytes = sub_data.encode('latin-1')
    header = f"@\x0a\x1e\x0dANSI {iin}090001".encode('latin-1')
    designator = f"DL0032{len(subfile_bytes):04d}".encode('latin-1')
    return header + designator + b"\x0d" + subfile_bytes

# ==================== 4. UI 界面 ====================

def main():
    st.set_page_config(page_title="AAMVA 专家版", layout="wide")
    
    with st.sidebar:
        st.header("⚙️ 隐藏选项")
        h_dah = st.checkbox("隐藏详细地址 (DAH)", True)
        h_h = st.checkbox("隐藏身高 (DAU)", False)
        h_w = st.checkbox("隐藏体重 (DAW)", False)
        h_e = st.checkbox("隐藏眼色 (DAY)", False)
        h_hair = st.checkbox("隐藏发色 (DAZ)", False)
        h_race = st.checkbox("隐藏种族 (DCL)", False) # 改为默认显示以便测试下拉菜单
        h_icn = st.checkbox("隐藏 ICN (DCK)", False)
        h_audit = st.checkbox("隐藏审计码 (DCJ)", True)
        
        target_state = st.selectbox("目标州", list(JURISDICTION_MAP.keys()), index=47)
        sel_cols = st.slider("预览列数", 9, 20, 15)
        opts = {'hide_dah': h_dah, 'hide_height': h_h, 'hide_weight': h_w, 'hide_eyes': h_e, 
                'hide_hair': h_hair, 'hide_race': h_race, 'hide_icn': h_icn, 'hide_audit': h_audit}

    # --- 第一板块：姓名与居住信息 ---
    st.subheader("👤 个人姓名与居住信息")
    with st.container(border=True):
        name_cols = st.columns(3)
        ln = name_cols[0].text_input("姓 (DCS)", "SOLOMON")
        fn = name_cols[1].text_input("名 (DAC)", "DANIEL")
        mn = name_cols[2].text_input("中 (DAD)", "NONE")
        
        addr_cols = st.columns([2, 1, 1])
        addr = addr_cols[0].text_input("街道 (DAG)", "29810 224TH AVE SE")
        city = addr_cols[1].text_input("城市 (DAI)", "KENT")
        zip_c = addr_cols[2].text_input("邮编 (DAK)", "98010")
        
        if not h_dah:
            dah_val = st.text_input("详细地址/第二行 (DAH)", "")
        else:
            dah_val = ""

    # --- 第二板块：证件信息 ---
    st.subheader("📝 证件信息")
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        dl = c1.text_input("证件号 (DAQ)", "WDL0ALXD2K1B")
        cl = c2.text_input("准驾类型 (DCA)", "D")
        real_id = c3.toggle("REAL ID (DDA)", True)
        
        date_cols = st.columns(4)
        dob = date_cols[0].text_input("生日 (DBB)", "08081998")
        iss = date_cols[1].text_input("签发日 (DBD)", "06062024")
        exp = date_cols[2].text_input("过期日 (DBA)", "08082030")
        rev = date_cols[3].text_input("修订日 (DDB)", "11122019")
        
        info_cols = st.columns(3)
        dcf = info_cols[0].text_input("鉴别码 (DCF)", "WDL0ALXD2K1BA020424988483")
        rs = info_cols[1].text_input("限制 (DCB)", "NONE")
        ed = info_cols[2].text_input("背书 (DCD)", "NONE")
        
        extra_cols = st.columns(2)
        icn_val = extra_cols[0].text_input("ICN (DCK)", "123456789012345") if not h_icn else ""
        audit_val = extra_cols[1].text_input("审计码 (DCJ)", "A020424988483") if not h_audit else ""

    # --- 第三板块：身体特征与特殊标识 ---
    st.subheader("🏃 身体特征与特殊标识")
    with st.container(border=True):
        phys_items = []
        phys_items.append(("sex", "性别 (DBC)", ["1", "2", "9", "0"]))
        
        if not h_race: phys_items.append(("race", "种族 (DCL)", list(RACE_OPTIONS.keys())))
        if not h_h:    phys_items.append(("height", "身高", "072"))
        if not h_w:    phys_items.append(("weight", "体重", "175"))
        if not h_e:    phys_items.append(("eyes", "眼色", "BLU"))
        if not h_hair: phys_items.append(("hair", "发色", "BRO"))
        
        phys_vals = {}
        p_cols = st.columns(len(phys_items))
        
        for i, item in enumerate(phys_items):
            key, label = item[0], item[1]
            if key == "sex":
                phys_vals["sex"] = p_cols[i].selectbox(label, item[2], format_func=lambda x: {"1":"男","2":"女","9":"其他","0":"未知"}[x])
            elif key == "race":
                phys_vals["race"] = p_cols[i].selectbox(label, item[2], format_func=lambda x: RACE_OPTIONS[x], help="选择对应的种族代码")
            else:
                phys_vals[key] = p_cols[i].text_input(label, item[2])
        
        st.markdown("---")
        sb1, sb2 = st.columns(2)
        vet = sb1.toggle("退伍军人 (DDL)", False)
        don = sb2.toggle("器官捐献 (DDK)", False)

    if st.button("🚀 生成并深度核对分析", type="primary", use_container_width=True):
        inputs = {
            'state': target_state, 'last_name': ln, 'first_name': fn, 'middle_name': mn,
            'dl_number': dl, 'iss_date': iss, 'dob': dob, 'exp_date': exp, 'rev_date': rev,
            'sex': phys_vals["sex"], 'address': addr, 'dah': dah_val, 'city': city, 'zip': zip_c, 
            'height': phys_vals.get("height", "072"), 'weight': phys_vals.get("weight", "175"), 
            'eyes': phys_vals.get("eyes", "BLU"), 'hair': phys_vals.get("hair", "BRO"), 
            'race': phys_vals.get("race", "W"), 'donor': don, 'veteran': vet, 
            'real_id': real_id, 'dd_code': dcf, 'icn': icn_val, 'audit': audit_val,
            'class': cl, 'rest': rs, 'end': ed
        }
        
        try:
            raw_data = build_aamva_stream(inputs, opts)
            L = len(raw_data)
            l_col, r_col = st.columns([1, 1.2])
            with l_col:
                st.subheader("📊 条码预览")
                codes = encode(raw_data, columns=sel_cols, security_level=5)
                st.image(render_image(codes, scale=3))
                st.info(f"长度: {L} bytes | 规格: {sel_cols}列 × {len(codes)}行")
                with st.expander("Hex Dump"): st.code(format_hex_dump(raw_data))

            with r_col:
                st.subheader("🔍 解析核对")
                raw_text = raw_data.decode('latin-1')
                if "DL" in raw_text:
                    content = raw_text.split("DL", 1)[1]
                    parsed = []
                    for line in content.split('\x0a'):
                        clean_line = line.strip()
                        if len(clean_line) >= 3:
                            tag = clean_line[:3]
                            if tag in AAMVA_TAGS_MAP:
                                parsed.append({"标签": tag, "描述": AAMVA_TAGS_MAP[tag], "值": clean_line[3:]})
                    st.table(pd.DataFrame(parsed))
        except Exception as e:
            st.error(f"逻辑错误: {e}")

if __name__ == "__main__":
    main()
