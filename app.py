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
    "DDK": "器官捐献标识", "DDL": "退伍军人标识" # 更新为 DDL
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

def build_aamva_stream(inputs, options):
    iin = JURISDICTION_MAP[inputs['state']]
    body = [
        f"DAQ{inputs['dl_number'].upper()}\x0a", f"DCS{inputs['last_name'].upper()}\x0a",
        f"DDEN\x0a", f"DAC{inputs['first_name'].upper()}\x0a", f"DDFN\x0a",
        f"DAD{inputs['middle_name'].upper()}\x0a", f"DDGN\x0a",
        f"DCA{inputs['class'].upper()}\x0a", f"DCB{inputs['rest'].upper()}\x0a",
        f"DCD{inputs['end'].upper()}\x0a", f"DBD{clean_date(inputs['iss_date'])}\x0a",
        f"DBB{clean_date(inputs['dob'])}\x0a", f"DBA{clean_date(inputs['exp_date'])}\x0a",
        f"DBC{inputs['sex']}\x0a"
    ]
    # 物理特征
    if not options['hide_height']: body.append(f"DAU{inputs['height']} in\x0a")
    if not options['hide_weight']: body.append(f"DAW{inputs['weight']}\x0a")
    if not options['hide_eyes']:   body.append(f"DAY{inputs['eyes'].upper()}\x0a")
    if not options['hide_hair']:   body.append(f"DAZ{inputs['hair'].upper()}\x0a")
    if not options['hide_race']:   body.append(f"DCL{inputs['race'].upper()}\x0a")
    if not options['hide_icn']:    body.append(f"DCH{inputs['icn'].upper()}\x0a")
    
    # 地址与核心信息
    body.append(f"DAG{inputs['address'].upper()}\x0a")
    body.append(f"DAI{inputs['city'].upper()}\x0a")
    body.append(f"DAJ{inputs['state']}\x0a")
    zip_val = clean_date(inputs['zip'])
    if len(zip_val) == 5: zip_val += "0000"
    body.append(f"DAK{zip_val}  \x0a")
    body.append(f"DCF{inputs['dd_code'].upper()}\x0a")
    body.append(f"DCGUSA\x0a")
    body.append(f"DDA{'F' if inputs['real_id'] else 'N'}\x0a")
    
    # DDB 修订日期
    body.append(f"DDB{clean_date(inputs['rev_date'])}\x0a")
    
    # --- 核心改动：挪到 DDB 后面 ---
    if inputs['donor']:   body.append(f"DDKY\x0a")
    if inputs['veteran']: body.append(f"DDLY\x0a") # 使用 DDL
    
    if not options['hide_audit']: body.append(f"DCJ{inputs['audit'].upper()}\x0a")
    
    # 已删除 DCU
    
    subfile_str = "DL" + "".join(body) + "\x0d"
    subfile_bytes = subfile_str.encode('latin-1')
    header = f"@\x0a\x1e\x0dANSI {iin}090001".encode('latin-1')
    designator = f"DL0032{len(subfile_bytes):04d}".encode('latin-1')
    return header + designator + b"\x0d" + subfile_bytes

# ==================== 4. 主界面 ====================

def main():
    st.set_page_config(page_title="AAMVA 字段专家", layout="wide")
    st.markdown("<h2 style='text-align: center;'>📐 AAMVA 字段解析与 PDF417 助手</h2>", unsafe_allow_html=True)

    with st.sidebar:
        st.header("⚙️ 配置")
        state = st.selectbox("目标州", list(JURISDICTION_MAP.keys()), index=47)
        st.subheader("🙈 字段隐藏")
        hide_h = st.checkbox("隐藏身高 (DAU)")
        hide_w = st.checkbox("隐藏体重 (DAW)")
        hide_e = st.checkbox("隐藏眼色 (DAY)")
        hide_hair = st.checkbox("隐藏发色 (DAZ)")
        hide_icn = st.checkbox("隐藏 ICN (DCH)", False)
        hide_a = st.checkbox("隐藏审计码 (DCJ)", True)
        hide_race = st.checkbox("隐藏种族 (DCL)", True)
        opts = {'hide_height':hide_h,'hide_weight':hide_w,'hide_eyes':hide_e,'hide_hair':hide_hair,
                'hide_icn':hide_icn,'hide_audit':hide_a,'hide_race':hide_race}
        sel_cols = st.slider("列数", 9, 20, 15)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("👤 身份信息")
        ln = st.text_input("姓 (DCS)", "SOLOMON").upper()
        fn = st.text_input("名 (DAC)", "DANIEL").upper()
        mn = st.text_input("中间名 (DAD)", "NONE").upper()
        dob = st.text_input("生日 (MMDDYYYY)", "08/08/1998")
        iss = st.text_input("签发日", "06/06/2024")
        exp = st.text_input("过期日", "08/08/2030")
        rev = st.text_input("修订日", "11/12/2019")

    with c2:
        st.subheader("📝 证件信息")
        dl = st.text_input("证件号 (DAQ)", "WDL0ALXD2K1B").upper()
        real_id = st.toggle("符合 REAL ID 标准 (DDA)", True)
        dcf = st.text_input("鉴别码 (DCF)", "WDL0ALXD2K1BA020424988483").upper()
        icn = st.text_input("ICN (DCH)", "123456789012345").upper() if not opts['hide_icn'] else ""
        cls_val = st.text_input("类型 (DCA)", "D").upper()
        rest_val = st.text_input("限制 (DCB)", "NONE").upper()
        end_val = st.text_input("背书 (DCD)", "NONE").upper()
        audit_val = st.text_input("审计码 (DCJ)", "A020424988483").upper() if not opts['hide_audit'] else ""

    st.markdown("---")
    st.subheader("🏠 地址与特征")
    addr_row = st.columns(4)
    addr = addr_row[0].text_input("街道 (DAG)", "29810 224TH AVE SE").upper()
    city = addr_row[1].text_input("城市 (DAI)", "KENT").upper()
    zip_c = addr_row[2].text_input("邮编 (DAK)", "98010")
    sex = addr_row[3].selectbox("性别 (DBC)", ["1", "2", "9", "0"], 
                               format_func=lambda x: {"1":"男","2":"女","9":"其他","0":"未知"}[x])

    phys_c = st.columns(5)
    h_v, w_v, e_v, hr_v, r_v = "072", "175", "BLU", "BRO", "W"
    idx = 0
    if not opts['hide_height']: h_v = phys_c[idx%5].text_input("身高", h_v); idx+=1
    if not opts['hide_weight']: w_v = phys_c[idx%5].text_input("体重", w_v); idx+=1
    if not opts['hide_eyes']:   e_v = phys_c[idx%5].text_input("眼色", e_v); idx+=1
    if not opts['hide_hair']:   hr_v = phys_c[idx%5].text_input("发色", hr_v); idx+=1
    if not opts['hide_race']:   r_v = phys_c[idx%5].text_input("种族", r_v); idx+=1
    
    st.markdown("##### 特殊标识 (DDB 修订日期后写入)")
    sb1, sb2 = st.columns(2)
    donor_v = sb1.toggle("器官捐献者 (DDK)", False)
    vet_v = sb2.toggle("退伍军人 (DDL)", False) # 改为 DDL

    if st.button("🚀 生成并分析", type="primary", use_container_width=True):
        inputs = {'state':state,'last_name':ln,'first_name':fn,'middle_name':mn,'dl_number':dl,'icn':icn,'class':cls_val,'rest':rest_val,'end':end_val,'iss_date':iss,'dob':dob,'exp_date':exp,'rev_date':rev,'sex':sex,'address':addr,'city':city,'zip':zip_c,'height':h_v,'weight':w_v,'eyes':e_v,'hair':hr_v,'race':r_v,'donor':donor_v,'veteran':vet_v,'real_id':real_id,'dd_code':dcf,'audit':audit_val}
        
        try:
            raw_data = build_aamva_stream(inputs, opts)
            raw_text = raw_data.decode('latin-1')
            
            c_l, c_r = st.columns([1, 1.2])
            with c_l:
                st.subheader("📊 条码")
                codes = encode(raw_data, columns=sel_cols, security_level=5)
                st.image(render_image(codes, scale=3))
                with st.expander("Hex Dump"): st.code(format_hex_dump(raw_data))

            with c_r:
                st.subheader("🔍 解析")
                if "DL" in raw_text:
                    content = raw_text.split("DL", 1)[1]
                    match = re.search(r'[A-Z]{3}', content)
                    if match:
                        parsed = []
                        for line in content[match.start():].split('\x0a'):
                            if len(line) >= 3:
                                tag = line[:3]
                                if tag in AAMVA_TAGS_MAP:
                                    parsed.append({"标签": tag, "描述": AAMVA_TAGS_MAP[tag], "值": line[3:].strip()})
                        st.table(pd.DataFrame(parsed))
                with st.expander("原始数据流"): st.text(raw_text)
        except Exception as e:
            st.error(f"错误: {e}")

if __name__ == "__main__":
    main()
