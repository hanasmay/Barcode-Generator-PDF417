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

# ==================== 2. AAMVA 数据映射 ====================
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

# --- 用于解析显示的标签字典 ---
TAG_DESCRIPTIONS = {
    "DAQ": "证件号码", "DCS": "姓", "DDEN": "名(空)", "DAC": "名", 
    "DDFN": "姓(空)", "DAD": "中间名", "DDGN": "名(空)", "DCA": "类型", 
    "DCB": "限制", "DCD": "背书", "DBD": "签发日期", "DBB": "生日", 
    "DBA": "过期日期", "DBC": "性别", "DAU": "身高", "DAY": "眼色", 
    "DAG": "街道", "DAI": "城市", "DAJ": "州(空)", "DAK": "邮编", 
    "DCF": "鉴别码", "DCG": "国家", "DAW": "体重", "DAZ": "发色", 
    "DCK": "ICN", "DDA": "REAL ID", "DDB": "修订日(空)", "DDL": "退伍军人", "DDK": "捐献者"
}

# ==================== 3. 辅助函数 ====================

def clean_date(date_str):
    return re.sub(r'[^0-9]', '', date_str)

def build_aamva_stream(inputs, options):
    iin = JURISDICTION_MAP[inputs['state']]
    
    # 按照要求的顺序构建 body
    body_parts = [
        f"DAQ{inputs['dl_number'].upper()}\x0a",
        f"DCS{inputs['last_name'].upper()}\x0a",
        f"DDEN\x0a",
        f"DAC{inputs['first_name'].upper()}\x0a",
        f"DDFN\x0a",
        f"DAD{inputs['middle_name'].upper()}\x0a",
        f"DDGN\x0a",
        f"DCA{inputs['class'].upper()}\x0a",
        f"DCB{inputs['rest'].upper()}\x0a",
        f"DCD{inputs['end'].upper()}\x0a",
        f"DBD{clean_date(inputs['iss_date'])}\x0a",
        f"DBB{clean_date(inputs['dob'])}\x0a",
        f"DBA{clean_date(inputs['exp_date'])}\x0a",
        f"DBC{inputs['sex']}\x0a"
    ]
    
    # 物理特征与地址
    body_parts.append(f"DAU{inputs['height']} IN\x0a")
    body_parts.append(f"DAY{inputs['eyes'].upper()}\x0a")
    body_parts.append(f"DAG{inputs['address'].upper()}\x0a")
    body_parts.append(f"DAI{inputs['city'].upper()}\x0a")
    body_parts.append(f"DAJ \x0a") # DAJ 后带空
    
    zip_val = clean_date(inputs['zip'])
    body_parts.append(f"DAK{zip_val}  \x0a")
    
    body_parts.append(f"DCF{inputs['dd_code'].upper()}\x0a")
    body_parts.append(f"DCGUSA\x0a")
    body_parts.append(f"DAW{inputs['weight']}\x0a")
    body_parts.append(f"DAZ{inputs['hair'].upper()}\x0a")
    
    # 证件控制码
    body_parts.append(f"DCK{inputs['icn'].upper()}\x0a")
    body_parts.append(f"DDA{'F' if inputs['real_id'] else 'N'}\x0a")
    
    # DDB 固定空输出
    body_parts.append(f"DDB  \x0a")
    
    # 只有选中时才输出 DDL 和 DDK
    if inputs['veteran']:
        body_parts.append(f"DDLY\x0a")
    if inputs['donor']:
        body_parts.append(f"DDKY\x0a")
    
    # 子文件打包逻辑 (偏移 32)
    subfile_str = "DL" + "".join(body_parts) + "\x0d"
    subfile_bytes = subfile_str.encode('latin-1')
    
    header = f"@\x0a\x1e\x0dANSI {iin}090001".encode('latin-1')
    designator = f"DL0032{len(subfile_bytes):04d}".encode('latin-1')
    
    return header + designator + b"\x0d" + subfile_bytes

# ==================== 4. 主界面布局 ====================

def main():
    st.set_page_config(page_title="PDF417 AAMVA Generator", layout="wide")
    st.title("💳 AAMVA PDF417 字段专家生成器")

    with st.sidebar:
        st.header("配置")
        target_state = st.selectbox("州", list(JURISDICTION_MAP.keys()), index=47)
        cols_slider = st.slider("列数", 9, 20, 15)

    # 左右分栏录入
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("👤 个人身份")
        ln = st.text_input("姓 (DCS)", "SOLOMON")
        fn = st.text_input("名 (DAC)", "DANIEL")
        mn = st.text_input("中 (DAD)", "NONE")
        dob = st.text_input("生日 (MMDDYYYY)", "08/08/1998")
        sex = st.selectbox("性别 (DBC)", ["1", "2", "9", "0"])
        st.markdown("---")
        st.subheader("📏 物理特征")
        h = st.text_input("身高 (DAU - 仅数字)", "072")
        w = st.text_input("体重 (DAW - 仅数字)", "175")
        ey = st.text_input("眼色 (DAY)", "BLU")
        hr = st.text_input("发色 (DAZ)", "BRO")

    with c2:
        st.subheader("🆔 证件与代码")
        dl = st.text_input("证件号 (DAQ)", "WDL0ALXD2K1B")
        icn = st.text_input("ICN (DCK)", "123456789012345")
        dcf = st.text_input("鉴别码 (DCF)", "WDL0ALXD2K1BA020424988483")
        real_id_toggle = st.toggle("REAL ID (DDA)", True)
        st.markdown("---")
        st.subheader("📜 驾驶权限")
        cl = st.text_input("类型 (DCA)", "D")
        rs = st.text_input("限制 (DCB)", "NONE")
        ed = st.text_input("背书 (DCD)", "NONE")
        st.markdown("---")
        iss = st.text_input("签发日", "06/06/2024")
        exp = st.text_input("过期日", "08/08/2030")

    st.markdown("---")
    addr_c = st.columns(3)
    adr = addr_c[0].text_input("地址 (DAG)", "29810 224TH AVE SE")
    cty = addr_c[1].text_input("城市 (DAI)", "KENT")
    zp = addr_c[2].text_input("邮编 (DAK)", "98010")

    st.markdown("##### 特殊标识 (DDB 之后)")
    b1, b2 = st.columns(2)
    vet = b1.toggle("退伍军人 (DDL)", False)
    don = b2.toggle("器官捐献 (DDK)", False)

    if st.button("🚀 执行生成并深度分析", type="primary", use_container_width=True):
        inputs = {
            'state': target_state, 'last_name': ln, 'first_name': fn, 'middle_name': mn,
            'dl_number': dl, 'iss_date': iss, 'dob': dob, 'exp_date': exp, 'sex': sex,
            'height': h, 'weight': w, 'eyes': ey, 'hair': hr, 'address': adr, 'city': cty,
            'zip': zp, 'icn': icn, 'real_id': real_id_toggle, 'class': cl, 'rest': rs, 
            'end': ed, 'dd_code': dcf, 'veteran': vet, 'donor': don
        }
        
        try:
            raw_data = build_aamva_stream(inputs, None)
            raw_text = raw_data.decode('latin-1')
            
            l_col, r_col = st.columns([1, 1.2])
            with l_col:
                st.subheader("📊 条码预览")
                codes = encode(raw_data, columns=cols_slider, security_level=5)
                st.image(render_image(codes, scale=3))
                st.code(raw_data.hex().upper(), language="text")

            with r_col:
                st.subheader("🔍 数据顺序核对")
                if "DL" in raw_text:
                    content = raw_text.split("DL", 1)[1]
                    # 解析逻辑优化：逐行显示
                    parsed = []
                    for line in content.split('\x0a'):
                        if len(line) >= 3:
                            tag = line[:3]
                            desc = TAG_DESCRIPTIONS.get(tag, "自定义标识")
                            parsed.append({"标签": tag, "字段描述": desc, "内容": line[3:].strip()})
                    st.table(pd.DataFrame(parsed))
                    
                with st.expander("查看原始流 (Raw Stream)"):
                    st.text(raw_text)

        except Exception as e:
            st.error(f"失败: {e}")

if __name__ == "__main__":
    main()
