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

# ==================== 2. AAMVA 数据配置 ====================
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

AAMVA_TAGS_MAP = {
    "DAQ": "证件号码", "DCS": "姓", "DAC": "名", "DAD": "中间名",
    "DBB": "出生日期", "DBD": "签发日期", "DBA": "过期日期", "DBC": "性别",
    "DAU": "身高", "DAW": "体重", "DAY": "眼睛颜色", "DAZ": "头发颜色",
    "DAG": "街道地址", "DAI": "城市", "DAJ": "州代码", "DAK": "邮政编码",
    "DCF": "鉴别码", "DDA": "REAL ID 状态", "DCJ": "审计码", "DDB": "修订日期",
    "DCA": "类型", "DCB": "限制", "DCD": "背书", "DCH": "ICN", "DCL": "种族",
    "DDK": "器官捐献标识", "DDL": "退伍军人标识", "DDEN": "名(空)", "DDFN": "姓(空)", "DDGN": "名(空)"
}

# ==================== 3. 辅助函数 ====================

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

def reverse_pdf417_params(data_len, ecc_level=5):
    ecc_map = {0:2, 1:4, 2:8, 3:16, 4:32, 5:64, 6:128, 7:256, 8:512}
    total_codewords = math.ceil(data_len / 1.85) + ecc_map.get(ecc_level, 64) + 1
    results = []
    for cols in range(9, 21):
        rows = math.ceil(total_codewords / cols)
        if 3 <= rows <= 90:
            status = "✅ 推荐" if 13 <= cols <= 17 and 14 <= rows <= 22 else ""
            results.append({"列数": cols, "行数": rows, "总码词": total_codewords, "建议": status})
    return pd.DataFrame(results)

def build_aamva_stream(inputs, options):
    iin = JURISDICTION_MAP[inputs['state']]
    body = [
        f"DL", # 子文件标识
        f"DAQ{inputs['dl_number'].upper()}\x0a", 
        f"DCS{inputs['last_name'].upper()}\x0a",
        f"DDEN\x0a", f"DAC{inputs['first_name'].upper()}\x0a", f"DDFN\x0a",
        f"DAD{inputs['middle_name'].upper()}\x0a", f"DDGN\x0a",
        f"DCA{inputs['class'].upper()}\x0a", f"DCB{inputs['rest'].upper()}\x0a",
        f"DCD{inputs['end'].upper()}\x0a", f"DBD{clean_date(inputs['iss_date'])}\x0a",
        f"DBB{clean_date(inputs['dob'])}\x0a", f"DBA{clean_date(inputs['exp_date'])}\x0a",
        f"DBC{inputs['sex']}\x0a"
    ]
    
    if not options['hide_height']: body.append(f"DAU{inputs['height']} IN\x0a")
    if not options['hide_eyes']:   body.append(f"DAY{inputs['eyes'].upper()}\x0a")
    
    body.append(f"DAG{inputs['address'].upper()}\x0a")
    body.append(f"DAI{inputs['city'].upper()}\x0a")
    body.append(f"DAJ \x0a") # 州占位
    
    zip_val = clean_date(inputs['zip'])
    body.append(f"DAK{zip_val}  \x0a")
    
    body.append(f"DCF{inputs['dd_code'].upper()}\x0a")
    body.append(f"DCGUSA\x0a")
    
    if not options['hide_weight']: body.append(f"DAW{inputs['weight']}\x0a")
    if not options['hide_hair']:   body.append(f"DAZ{inputs['hair'].upper()}\x0a")
    if not options['hide_race']:   body.append(f"DCL{inputs['race'].upper()}\x0a")
    if not options['hide_icn']:    body.append(f"DCK{inputs['icn'].upper()}\x0a")
    
    body.append(f"DDA{'F' if inputs['real_id'] else 'N'}\x0a")
    body.append(f"DDB  \x0a") # 修订日期占位
    
    if inputs['veteran']: body.append(f"DDLY\x0a")
    if inputs['donor']:   body.append(f"DDKY\x0a")
    
    if not options['hide_audit']: body.append(f"DCJ{inputs['audit'].upper()}\x0a")
    
    # 组合子文件
    sub_data = "".join(body)
    subfile_bytes = sub_data.encode('latin-1')
    
    # 头部 (Offset 32)
    header = f"@\x0a\x1e\x0dANSI {iin}090001".encode('latin-1')
    designator = f"DL0032{len(subfile_bytes):04d}".encode('latin-1')
    
    return header + designator + b"\x0d" + subfile_bytes

# ==================== 4. 主界面 ====================

def main():
    st.set_page_config(page_title="AAMVA 物理参数助手", layout="wide")
    st.markdown("<h2 style='text-align: center;'>📐 AAMVA 字段全功能生成器</h2>", unsafe_allow_html=True)

    with st.sidebar:
        st.header("⚙️ 全局配置")
        state = st.selectbox("目标州", list(JURISDICTION_MAP.keys()), index=47)
        st.markdown("---")
        st.subheader("🙈 字段显示控制")
        h_h = st.checkbox("隐藏身高", False)
        h_w = st.checkbox("隐藏体重", False)
        h_e = st.checkbox("隐藏眼色", False)
        h_hair = st.checkbox("隐藏发色", False)
        h_race = st.checkbox("隐藏种族", False)
        h_icn = st.checkbox("隐藏 ICN", False)
        h_audit = st.checkbox("隐藏审计码", False)
        
        opts = {'hide_height':h_h, 'hide_weight':h_w, 'hide_eyes':h_e, 'hide_hair':h_hair, 
                'hide_race':h_race, 'hide_icn':h_icn, 'hide_audit':h_audit}
        st.markdown("---")
        sel_cols = st.slider("预览列数", 9, 20, 15)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("👤 身份与日期")
        ln = st.text_input("姓 (DCS)", "SOLOMON").upper()
        fn = st.text_input("名 (DAC)", "DANIEL").upper()
        mn = st.text_input("中 (DAD)", "NONE").upper()
        dob = st.text_input("生日 (MMDDYYYY)", "08/08/1998")
        iss = st.text_input("签发日", "06/06/2024")
        exp = st.text_input("过期日", "08/08/2030")

    with c2:
        st.subheader("📝 证件类型与代码")
        dl = st.text_input("证件号 (DAQ)", "WDL0ALXD2K1B").upper()
        real_id = st.toggle("REAL ID (DDA)", True)
        dcf = st.text_input("鉴别码 (DCF)", "WDL0ALXD2K1BA020424988483").upper()
        icn = st.text_input("ICN (DCK)", "123456789012345").upper()
        cl = st.text_input("类型 (DCA)", "D").upper()
        rs = st.text_input("限制 (DCB)", "NONE").upper()
        ed = st.text_input("背书 (DCD)", "NONE").upper()
        audit = st.text_input("审计码 (DCJ)", "A020424988483").upper()

    st.markdown("---")
    st.subheader("🏠 地址与物理特征")
    adr_row = st.columns(4)
    addr = adr_row[0].text_input("街道 (DAG)", "29810 224TH AVE SE").upper()
    city = adr_row[1].text_input("城市 (DAI)", "KENT").upper()
    zip_c = adr_row[2].text_input("邮编 (DAK)", "98010")
    sex = adr_row[3].selectbox("性别 (DBC)", ["1", "2", "9", "0"], format_func=lambda x: {"1":"男","2":"女","9":"其他","0":"未知"}[x])

    phys_row = st.columns(5)
    race = phys_row[0].text_input("种族 (DCL)", "W").upper()
    h_v = phys_row[1].text_input("身高", "072")
    w_v = phys_row[2].text_input("体重", "175")
    e_v = phys_row[3].text_input("眼色", "BLU").upper()
    hr_v = phys_row[4].text_input("发色", "BRO").upper()
    
    st.markdown("##### 特殊标识 (不选不输出)")
    sb1, sb2 = st.columns(2)
    vet = sb1.toggle("退伍军人 (DDL)", False)
    don = sb2.toggle("器官捐献 (DDK)", False)

    if st.button("🚀 生成条码并分析", type="primary", use_container_width=True):
        inputs = {'state':state, 'last_name':ln, 'first_name':fn, 'middle_name':mn, 'dl_number':dl, 'icn':icn,
                  'class':cl, 'rest':rs, 'end':ed, 'iss_date':iss, 'dob':dob, 'exp_date':exp, 'sex':sex,
                  'address':addr, 'city':city, 'zip':zip_c, 'height':h_v, 'weight':w_v, 'eyes':e_v, 
                  'hair':hr_v, 'race':race, 'donor':don, 'veteran':vet, 'real_id':real_id, 'dd_code':dcf, 'audit':audit}
        
        try:
            raw_data = build_aamva_stream(inputs, opts)
            raw_text = raw_data.decode('latin-1')
            L = len(raw_data)
            
            l_col, r_col = st.columns([1, 1.2])
            with l_col:
                st.subheader("📊 条码预览")
                codes = encode(raw_data, columns=sel_cols, security_level=5)
                st.image(render_image(codes, scale=3))
                st.success(f"**物理参数:** {sel_cols} 列 × {len(codes)} 行 | **数据长度:** `{L} bytes`")
                
                # --- 📐 参数逆向计算模块 (位置调整) ---
                st.subheader("📐 PDF417 参数逆向计算")
                st.dataframe(reverse_pdf417_params(L), use_container_width=True, hide_index=True)
                
                with st.expander("Hex Dump (十六进制)"): st.code(format_hex_dump(raw_data))

            with r_col:
                st.subheader("🔍 详细字段解析")
                if "DL" in raw_text:
                    content = raw_text.split("DL", 1)[1]
                    match = re.search(r'[A-Z]{3}', content)
                    if match:
                        parsed = []
                        for line in content[match.start():].split('\x0a'):
                            if len(line) >= 3:
                                tag = line[:3]
                                if tag in AAMVA_TAGS_MAP:
                                    parsed.append({"标签": tag, "字段描述": AAMVA_TAGS_MAP[tag], "值": line[3:].strip()})
                        st.table(pd.DataFrame(parsed))
                with st.expander("原始数据流"): st.text(raw_text)

        except Exception as e:
            st.error(f"错误: {e}")

if __name__ == "__main__":
    main()
