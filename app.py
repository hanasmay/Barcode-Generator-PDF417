# -*- coding: utf-8 -*-
import streamlit as st
import io
import re
import pandas as pd
from PIL import Image

# --- 核心库加载 ---
try:
    from pdf417 import encode, render_image
except ImportError:
    st.error("缺失依赖库！请运行: pip install pdf417 Pillow pandas streamlit")

# ==================== 1. 数据字典与配置 ====================
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
    "DAQ": "证件号码 (DL/ID Number)",
    "DCS": "姓 (Last Name)",
    "DAC": "名 (First Name)",
    "DAD": "中间名 (Middle Name)",
    "DBB": "出生日期 (Date of Birth)",
    "DBD": "签发日期 (Issue Date)",
    "DBA": "过期日期 (Expiry Date)",
    "DBC": "性别 (Sex)",
    "DAU": "身高 (Height)",
    "DAW": "体重 (Weight)",
    "DAY": "眼睛颜色 (Eye Color)",
    "DAZ": "头发颜色 (Hair Color)",
    "DAG": "街道地址 (Address)",
    "DAI": "城市 (City)",
    "DAJ": "州代码 (State)",
    "DAK": "邮政编码 (Zip)",
    "DCF": "鉴别码 (Discriminator)",
    "DCG": "国家 (Country)",
    "DDA": "REAL ID 状态",
    "DCJ": "审计码 (Audit)",
    "DDB": "版面修订日期 (Revision Date)",
    "DCA": "准驾等级 (Class)"
}

# ==================== 2. 核心辅助函数 ====================

def clean_date(date_str):
    """自动清理日期中的非数字字符"""
    return re.sub(r'[^0-9]', '', date_str)

def format_hex_dump(raw_bytes):
    """将字节流格式化为: HEX | ASCII 视图"""
    lines = []
    for i in range(0, len(raw_bytes), 16):
        chunk = raw_bytes[i:i+16]
        hex_part = chunk.hex().upper().ljust(32)
        ascii_part = "".join([chr(b) if 32 <= b <= 126 else "." for b in chunk])
        lines.append(f"{hex_part} | {ascii_part}")
    
    header = f"📦 数据长度: {len(raw_bytes)} 字节\n"
    divider = "-" * 55 + "\n"
    return header + divider + "\n".join(lines)

def parse_for_analysis(plain_text):
    """将明文流解析为表格数据"""
    parsed_data = []
    clean_text = plain_text.replace('\r', '')
    if "DL" in clean_text:
        data_part = clean_text.split("DL", 1)[1]
        lines = data_part.split('\x0a')
        for line in lines:
            if len(line) >= 3:
                tag = line[:3]
                val = line[3:].strip()
                desc = AAMVA_TAGS_MAP.get(tag, "其他标识符")
                parsed_data.append({"标识符 (Tag)": tag, "字段含义": desc, "解析内容": val})
    return parsed_data

def build_aamva_stream(inputs, options):
    """构建符合 AAMVA 09 标准的字节流"""
    iin = JURISDICTION_MAP[inputs['state']]
    
    # 构建内容列表
    body = [
        f"DAQ{inputs['dl_number'].upper()}\x0a",
        f"DCS{inputs['last_name'].upper()}\x0a",
        f"DAC{inputs['first_name'].upper()}\x0a",
        f"DAD{inputs['middle_name'].upper()}\x0a",
        f"DCA{inputs['class'].upper()}\x0a",
        f"DBD{clean_date(inputs['iss_date'])}\x0a",
        f"DBB{clean_date(inputs['dob'])}\x0a",
        f"DBA{clean_date(inputs['exp_date'])}\x0a",
        f"DBC{inputs['sex']}\x0a"
    ]
    
    if not options['hide_height']: body.append(f"DAU{inputs['height']} in\x0a")
    if not options['hide_weight']: body.append(f"DAW{inputs['weight']}\x0a")
    if not options['hide_eyes']:   body.append(f"DAY{inputs['eyes'].upper()}\x0a")
    if not options['hide_hair']:   body.append(f"DAZ{inputs['hair'].upper()}\x0a")
    
    body.append(f"DAG{inputs['address'].upper()}\x0a")
    body.append(f"DAI{inputs['city'].upper()}\x0a")
    body.append(f"DAJ{inputs['state']}\x0a")
    
    zip_val = clean_date(inputs['zip'])
    if len(zip_val) == 5: zip_val += "0000"
    body.append(f"DAK{zip_val}  \x0a")
    
    body.append(f"DCF{inputs['dd_code'].upper()}\x0a")
    body.append(f"DCGUSA\x0a")
    body.append(f"DDA{'F' if inputs['real_id'] else 'N'}\x0a")
    body.append(f"DDB{clean_date(inputs['rev_date'])}\x0a")
    
    if not options['hide_audit']: body.append(f"DCJ{inputs['audit'].upper()}\x0a")
    body.append(f"DCU")

    # 子文件打包
    subfile_str = "DL" + "".join(body) + "\x0d"
    subfile_bytes = subfile_str.encode('latin-1')
    
    # 头部与设计器 (偏移量 32)
    header = f"@\x0a\x1e\x0dANSI {iin}090001".encode('latin-1')
    designator = f"DL0032{len(subfile_bytes):04d}".encode('latin-1')
    
    return header + designator + b"\x0d" + subfile_bytes

# ==================== 3. Streamlit 界面 ====================

def main():
    st.set_page_config(page_title="AAMVA Pro Generator", layout="wide")
    st.title("💳 AAMVA 终极解析生成器 (V2)")

    with st.sidebar:
        st.header("⚙️ 全局配置")
        state = st.selectbox("目标州", list(JURISDICTION_MAP.keys()), index=47) # 默认 WA
        st.markdown("---")
        st.subheader("🙈 动态字段显示")
        opts = {
            'hide_height': st.checkbox("隐藏身高 (DAU)"),
            'hide_weight': st.checkbox("隐藏体重 (DAW)"),
            'hide_eyes': st.checkbox("隐藏眼色 (DAY)"),
            'hide_hair': st.checkbox("隐藏发色 (DAZ)"),
            'hide_audit': st.checkbox("隐藏审计码 (DCJ)", True)
        }
        st.markdown("---")
        cols = st.slider("条码列数", 9, 20, 13)

    # 输入区
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("👤 基本信息")
        ln = st.text_input("姓 (DCS)", "SOLOMON")
        fn = st.text_input("名 (DAC)", "DANIEL")
        mn = st.text_input("中间名 (DAD)", "NONE")
        dl = st.text_input("证件号 (DAQ)", "WDL0ALXD2K1B")
        real_id = st.toggle("REAL ID (DDA)", True)
        sex = st.selectbox("性别", ["1", "2"], format_func=lambda x: "男 (1)" if x=="1" else "女 (2)")

    with c2:
        st.subheader("📅 日期与等级")
        dob = st.text_input("生日 (MM/DD/YYYY)", "08/08/1998")
        iss = st.text_input("签发日", "06/06/2024")
        exp = st.text_input("过期日", "08/08/2030")
        rev = st.text_input("修订日", "11/12/2019")
        cl = st.text_input("等级 (DCA)", "NONE")

    st.markdown("---")
    st.subheader("🏠 物理特征与地址")
    addr_c = st.columns(3)
    addr = addr_c[0].text_input("街道 (DAG)", "29810 224TH AVE SE")
    city = addr_c[1].text_input("城市 (DAI)", "KENT")
    zip_c = addr_c[2].text_input("邮编 (DAK)", "98010")

    phys_c = st.columns(4)
    h_v = phys_c[0].text_input("身高", "072") if not opts['hide_height'] else "072"
    w_v = phys_c[1].text_input("体重", "175") if not opts['hide_weight'] else "175"
    e_v = phys_c[2].text_input("眼睛", "BLU") if not opts['hide_eyes'] else "BLU"
    hr_v = phys_c[3].text_input("头发", "BRO") if not opts['hide_hair'] else "BRO"

    dcf = st.text_input("鉴别码 (DCF)", "WDL0ALXD2K1BA020424988483")
    audit = st.text_input("审计码 (DCJ)", "A020424988483") if not opts['hide_audit'] else ""

    if st.button("🚀 生成并深度解析", type="primary", use_container_width=True):
        inputs = {
            'state': state, 'last_name': ln, 'first_name': fn, 'middle_name': mn,
            'dl_number': dl, 'iss_date': iss, 'dob': dob, 'exp_date': exp,
            'rev_date': rev, 'sex': sex, 'address': addr, 'city': city,
            'zip': zip_c, 'height': h_v, 'weight': w_v, 'eyes': e_v, 
            'hair': hr_v, 'real_id': real_id, 'class': cl, 'dd_code': dcf, 'audit': audit
        }

        try:
            raw_data = build_aamva_stream(inputs, opts)
            
            # 展示区
            col_left, col_right = st.columns([1, 1.2])
            
            with col_left:
                st.subheader("📊 条码预览")
                codes = encode(raw_data, columns=cols, security_level=5)
                img = render_image(codes, scale=3)
                st.image(img)
                
                # 下载
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                st.download_button("💾 下载图片", buf.getvalue(), f"{state}_DL.png")

                # Hex Dump 视图
                st.subheader("📦 十六进制视图 (Hex Dump)")
                st.code(format_hex_dump(raw_data), language="text")

            with col_right:
                st.subheader("🔍 字段明文解析表")
                raw_text = raw_data.decode('latin-1')
                analysis = parse_for_analysis(raw_text)
                if analysis:
                    st.dataframe(pd.DataFrame(analysis), use_container_width=True, hide_index=True)
                
                with st.expander("查看原始明文流 (Raw)"):
                    st.text(raw_text)

        except Exception as e:
            st.error(f"发生错误: {e}")

if __name__ == "__main__":
    main()
