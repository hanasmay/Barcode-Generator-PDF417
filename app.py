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
    "W": "W = 白人", "BK": "BK = 非裔", "AI": "AI = 原住民", 
    "AP": "AP = 亚裔", "H": "H = 西班牙裔", "O": "O = 其他", "U": "U = 未知"
}

AAMVA_TAGS_MAP = {
    "DAQ": "证件号码", "DCS": "姓", "DAC": "名", "DAD": "中间名",
    "DBB": "出生日期", "DBD": "签发日期", "DBA": "过期日期", "DBC": "性别",
    "DAU": "身高", "DAW": "体重", "DAY": "眼睛颜色", "DAZ": "头发颜色",
    "DAG": "街道地址", "DAH": "详细地址", "DAI": "城市", "DAJ": "州代码", 
    "DAK": "邮政编码", "DCF": "鉴别码", "DDA": "REAL ID 状态", "DCJ": "审计码", 
    "DDB": "修订日期", "DCA": "类型", "DCB": "限制", "DCD": "背书", 
    "DCK": "ICN", "DCL": "种族"
}

# ==================== 3. 核心工具 ====================

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

def build_aamva_stream(inputs, options):
    iin = JURISDICTION_MAP[inputs['state']]
    body = []
    
    # 基本信息
    body.append(f"DAQ{inputs['dl_number'].upper()}\x0a")
    body.append(f"DCS{inputs['last_name'].upper()}\x0a")
    body.append(f"DDEN\x0a")
    body.append(f"DAC{inputs['first_name'].upper()}\x0a")
    body.append(f"DDFN\x0a")
    body.append(f"DAD{inputs['middle_name'].upper()}\x0a")
    body.append(f"DDGN\x0a")
    
    # 要求的录入逻辑顺序 (DDA -> DCA -> DCB -> DCD)
    body.append(f"DDA{'F' if inputs['real_id'] else 'N'}\x0a")
    body.append(f"DCA{inputs['class'].upper()}\x0a")
    body.append(f"DCB{inputs['rest'].upper()}\x0a")
    body.append(f"DCD{inputs['end'].upper()}\x0a")
    
    # 日期组 (DBB -> DBA -> DBD)
    body.append(f"DBB{clean_date(inputs['dob'])}\x0a")
    body.append(f"DBA{clean_date(inputs['exp_date'])}\x0a")
    body.append(f"DBD{clean_date(inputs['iss_date'])}\x0a")
    
    # 地址信息
    body.append(f"DAG{inputs['address'].upper()}\x0a")
    if not options['hide_dah']: body.append(f"DAH{inputs['dah'].upper()}\x0a")
    body.append(f"DAI{inputs['city'].upper()}\x0a")
    body.append(f"DAJ{inputs['state'].upper()}\x0a")
    
    zip_raw = re.sub(r'[^0-9]', '', inputs['zip'])
    zip_final = zip_raw + "0000" if len(zip_raw) == 5 else zip_raw
    body.append(f"DAK{zip_final}  \x0a")

    # 管理字段
    body.append(f"DCF{inputs['dd_code'].upper()}\x0a")
    if not options['hide_icn']: body.append(f"DCK{inputs['icn'].upper()}\x0a")
    if not options['hide_audit']: body.append(f"DCJ{inputs['audit'].upper()}\x0a")

    # 身体特征
    body.append(f"DBC{inputs['sex']}\x0a")
    if not options['hide_height']: body.append(f"DAU{inputs['height']} IN\x0a")
    if not options['hide_weight']: body.append(f"DAW{inputs['weight']}\x0a")
    if not options['hide_eyes']:   body.append(f"DAY{inputs['eyes'].upper()}\x0a")
    if not options['hide_hair']:   body.append(f"DAZ{inputs['hair'].upper()}\x0a")
    if not options['hide_race']:   body.append(f"DCL{inputs['race'].upper()}\x0a")
    
    body.append(f"DDB{clean_date(inputs['rev_date'])}\x0a")
    
    sub_data = "DL" + "".join(body)
    subfile_bytes = sub_data.encode('latin-1')
    header = f"@\x0a\x1e\x0dANSI {iin}090001".encode('latin-1')
    designator = f"DL0032{len(subfile_bytes):04d}".encode('latin-1')
    return header + designator + b"\x0d" + subfile_bytes

# ==================== 4. 主界面 ====================

def main():
    st.set_page_config(page_title="AAMVA 对齐专家", layout="wide")
    
    with st.sidebar:
        st.header("⚙️ 侧边栏配置")
        target_state = st.selectbox("目标州", list(JURISDICTION_MAP.keys()), index=0)
        sel_cols = st.slider("预览列数", 9, 20, 17)
        st.markdown("---")
        # --- 重点：此处 DAH 默认设为 True ---
        h_dah = st.checkbox("隐藏详细地址 (DAH)", True) 
        h_icn = st.checkbox("隐藏 ICN (DCK)", False)
        h_audit = st.checkbox("隐藏审计码 (DCJ)", False)
        h_h = st.checkbox("隐藏身高 (DAU)", False)
        h_w = st.checkbox("隐藏体重 (DAW)", False)
        h_e = st.checkbox("隐藏眼色 (DAY)", False)
        h_hair = st.checkbox("隐藏发色 (DAZ)", False)
        h_race = st.checkbox("隐藏种族 (DCL)", False)
        opts = {'hide_dah': h_dah, 'hide_icn': h_icn, 'hide_audit': h_audit, 
                'hide_height': h_h, 'hide_weight': h_w, 'hide_eyes': h_e, 
                'hide_hair': h_hair, 'hide_race': h_race}

    st.subheader("👤 个人姓名与居住信息")
    with st.container(border=True):
        n_cols = st.columns(3)
        fn = n_cols[0].text_input("名字 (DAC)", "CHARLES")
        mn = n_cols[1].text_input("中间名 (DAD)", "NONE")
        ln = n_cols[2].text_input("姓氏 (DCS)", "CORDOVA")
        
        a_cols = st.columns([2, 1, 1])
        addr = a_cols[0].text_input("街道地址 (DAG)", "3704 3RD PL NE")
        city = a_cols[1].text_input("城市 (DAI)", "CENTER POINT")
        zip_c = a_cols[2].text_input("邮政编码 (DAK)", "35215")
        
        # 如果不隐藏，则显示 DAH
        dah_val = ""
        if not h_dah:
            dah_val = st.text_input("详细地址 (DAH)", "APT 101")

    st.subheader("📝 证件核心信息")
    with st.container(border=True):
        # 顺序：DAQ -> REAL ID -> DCA -> DCB -> DCD
        row1 = st.columns([2, 1, 1, 1, 1])
        dl = row1[0].text_input("证件号 (DAQ)", "66004729")
        real_id = row1[1].toggle("REAL ID", True)
        cl = row1[2].text_input("等级 (DCA)", "D")
        rs = row1[3].text_input("限制 (DCB)", "NONE")
        ed = row1[4].text_input("背书 (DCD)", "NONE")
        
        row2 = st.columns(4)
        dob = row2[0].text_input("生日 (MMDDYYYY)", "03/04/1969")
        exp = row2[1].text_input("过期日 (DBA)", "11/05/2027")
        iss = row2[2].text_input("签发日 (DBD)", "11/05/2023")
        rev = row2[3].text_input("修订日 (DDB)", "04/26/2022")
        
        row3 = st.columns([2, 2, 2])
        dcf = row3[0].text_input("鉴别码 (DCF)", "NONE")
        icn_val = row3[1].text_input("ICN (DCK)", "66004729317182331201") if not h_icn else ""
        audit_val = row3[2].text_input("审计码 (DCJ)", "A020424988483") if not h_audit else ""

    st.subheader("🏃 身体特征")
    with st.container(border=True):
        phys_active = [("sex", "性别 (DBC)", ["1", "2", "9"])]
        if not h_h: phys_active.append(("height", "身高 (DAU)", "070"))
        if not h_w: phys_active.append(("weight", "体重 (DAW)", "181"))
        if not h_e: phys_active.append(("eyes", "眼色 (DAY)", "BLU"))
        if not h_hair: phys_active.append(("hair", "发色 (DAZ)", "BRO"))
        if not h_race: phys_active.append(("race", "种族 (DCL)", list(RACE_OPTIONS.keys())))
        
        p_cols = st.columns(len(phys_active))
        phys_vals = {}
        for i, (key, label, default) in enumerate(phys_active):
            if key == "sex":
                phys_vals["sex"] = p_cols[i].selectbox(label, default, format_func=lambda x: {"1":"男","2":"女","9":"其他"}[x])
            elif key == "race":
                phys_vals["race"] = p_cols[i].selectbox(label, default, format_func=lambda x: RACE_OPTIONS[x])
            else:
                phys_vals[key] = p_cols[i].text_input(label, default)

    if st.button("🚀 生成条码并分析", type="primary", use_container_width=True):
        inputs = {
            'state': target_state, 'last_name': ln, 'first_name': fn, 'middle_name': mn,
            'dl_number': dl, 'iss_date': iss, 'dob': dob, 'exp_date': exp, 'rev_date': rev,
            'address': addr, 'dah': dah_val, 'city': city, 'zip': zip_c, 'real_id': real_id, 
            'dd_code': dcf, 'class': cl, 'rest': rs, 'end': ed, 
            'sex': phys_vals.get("sex", "1"), 'height': phys_vals.get("height", "070"), 
            'weight': phys_vals.get("weight", "181"), 'eyes': phys_vals.get("eyes", "BLU"), 
            'hair': phys_vals.get("hair", "BRO"), 'race': phys_vals.get("race", "W"), 
            'icn': icn_val, 'audit': audit_val
        }
        
        try:
            raw_bytes = build_aamva_stream(inputs, opts)
            st.image(render_image(encode(raw_bytes, columns=sel_cols, security_level=5), scale=3))
            st.code(format_hex_inspector(raw_bytes), language="text")
        except Exception as e:
            st.error(f"分析失败: {e}")

if __name__ == "__main__":
    main()
