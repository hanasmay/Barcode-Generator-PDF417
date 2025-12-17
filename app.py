# -*- coding: utf-8 -*-
import streamlit as st
import io
import re
import pandas as pd
from PIL import Image

# --- 1. 核心库加载 ---
try:
    from pdf417 import encode, render_image
except ImportError:
    st.error("缺失依赖库！请运行: pip install pdf417 Pillow pandas")

# ==================== 2. AAMVA 数据字典 ====================
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
    "DCA": "准驾等级 (Class)",
    "DCB": "限制码 (Restrictions)",
    "DCD": "背书码 (Endorsements)"
}

# ==================== 3. 核心工具逻辑 ====================

def clean_date(date_str):
    """自动将 05/05/2000 或 2000-05-05 转换为 05052000"""
    return re.sub(r'[^0-9]', '', date_str)

def parse_for_analysis(plain_text):
    """结构化解析明文流"""
    parsed_data = []
    # 按照 AAMVA 换行符拆分
    clean_text = plain_text.replace('\r', '')
    if "DL" in clean_text:
        # 只解析 DL 子文件内容
        data_part = clean_text.split("DL", 1)[1]
        lines = data_part.split('\x0a')
        for line in lines:
            if len(line) >= 3:
                tag = line[:3]
                val = line[3:].strip()
                desc = AAMVA_TAGS_MAP.get(tag, "其他标识符")
                parsed_data.append({"标识符": tag, "含义": desc, "内容": val})
    return parsed_data

def build_aamva_stream(inputs, options):
    """动态回填对齐算法 (锁死 09/00/01)"""
    iin = JURISDICTION_MAP[inputs['state']]
    aamva_ver, jur_ver, num_entries = "09", "00", "01"

    # 1. 构造 Body
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
    
    # 动态显示控制
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

    # 2. 测量与对齐 (Latin-1)
    subfile_str = "DL" + "".join(body) + "\x0d"
    subfile_bytes = subfile_str.encode('latin-1')
    len_dl = len(subfile_bytes)

    header = f"@\x0a\x1e\x0dANSI {iin}{aamva_ver}{jur_ver}{num_entries}"
    designator = f"DL0032{len_dl:04d}" # 固定偏移 32
    
    return header.encode('latin-1') + designator.encode('latin-1') + b"\x0d" + subfile_bytes

# ==================== 4. UI 布局 ====================

def main():
    st.set_page_config(page_title="AAMVA 终极解析生成器", layout="wide")
    st.markdown("<h2 style='text-align: center;'>AAMVA PDF417 50-州 终极对齐解析器</h2>", unsafe_allow_html=True)
    st.markdown("---")

    with st.sidebar:
        st.subheader("⚙️ 侧边栏配置")
        target_state = st.selectbox("目标州", list(JURISDICTION_MAP.keys()), index=47)
        st.info(f"IIN: {JURISDICTION_MAP[target_state]} | 模式: 09/00/01")
        
        st.markdown("---")
        st.subheader("🙈 字段可见性控制")
        options = {
            'hide_height': st.checkbox("隐藏身高 (DAU)", False),
            'hide_weight': st.checkbox("隐藏体重 (DAW)", False),
            'hide_eyes': st.checkbox("隐藏眼色 (DAY)", False),
            'hide_hair': st.checkbox("隐藏发色 (DAZ)", False),
            'hide_audit': st.checkbox("隐藏审计码 (DCJ)", True)
        }
        
        st.markdown("---")
        col_count = st.slider("条码列数", 9, 20, 13)

    # 主输入表单
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("👤 身份与基本信息")
        ln = st.text_input("姓 (Last Name)", "SOLOMON").upper()
        fn = st.text_input("名 (First Name)", "DANIEL").upper()
        mn = st.text_input("中间名 (Middle Name)", "NONE").upper()
        dl = st.text_input("证件号 (DAQ)", "WDL0ALXD2K1B").upper()
        real_id = st.toggle("符合 REAL ID 标准 (DDA)", value=True)
        sex = st.selectbox("性别 (DBC)", ["1", "2"], format_func=lambda x: "男 (1)" if x=="1" else "女 (2)")

    with c2:
        st.subheader("📅 日期 (支持 05/05/2000)")
        dob = st.text_input("生日", "08/08/1998")
        iss = st.text_input("签发日期", "06/06/2024")
        exp = st.text_input("过期日期", "08/08/2030")
        rev = st.text_input("版面修订日期", "11/12/2019")
        cl = st.text_input("准驾等级 (Class)", "NONE").upper()

    st.markdown("---")
    st.subheader("🏠 地址与物理特征")
    addr_cols = st.columns(3)
    addr = addr_cols[0].text_input("街道 (DAG)", "29810 224TH AVE SE").upper()
    city = addr_cols[1].text_input("城市 (DAI)", "KENT").upper()
    zip_c = addr_cols[2].text_input("邮编 (DAK)", "98010")

    phys_cols = st.columns(4)
    active_idx = 0
    h_v = "072"
    if not options['hide_height']: 
        h_v = phys_cols[active_idx % 4].text_input("身高 (in)", "072"); active_idx += 1
    w_v = "175"
    if not options['hide_weight']: 
        w_v = phys_cols[active_idx % 4].text_input("体重 (lb)", "175"); active_idx += 1
    e_v = "BLU"
    if not options['hide_eyes']: 
        e_v = phys_cols[active_idx % 4].text_input("眼色", "BLU").upper(); active_idx += 1
    hair_v = "BRO"
    if not options['hide_hair']: 
        hair_v = phys_cols[active_idx % 4].text_input("发色", "BRO").upper(); active_idx += 1

    st.markdown("---")
    dcf = st.text_input("鉴别码 (DCF)", "WDL0ALXD2K1BA020424988483").upper()
    audit = ""
    if not options['hide_audit']:
        audit = st.text_input("审计码 (DCJ)", "A020424988483").upper()

    if st.button("🚀 生成条码并执行结构化解析", type="primary", use_container_width=True):
        inputs = {
            'state': target_state, 'last_name': ln, 'first_name': fn, 'middle_name': mn,
            'dl_number': dl, 'iss_date': iss, 'dob': dob, 'exp_date': exp, 'rev_date': rev,
            'sex': sex, 'address': addr, 'city': city, 'zip': zip_c, 'height': h_v,
            'weight': w_v, 'eyes': e_v, 'hair': hair_v, 'real_id': real_id,
            'class': cl, 'dd_code': dcf, 'audit': audit
        }
        
        try:
            raw_data = build_aamva_stream(inputs, options)
            res_c, data_c = st.columns([1, 1.2])
            
            with res_c:
                st.subheader("📊 条码预览")
                codes = encode(raw_data, columns=col_count, security_level=5)
                img = render_image(codes, scale=3)
                st.image(img)
                buf = io.BytesIO(); img.save(buf, format="PNG")
                st.download_button("💾 下载图片", buf.getvalue(), f"{target_state}_DL.png", use_container_width=True)
                st.subheader("🔢 十六进制 (HEX)")
                st.code("\n".join([(raw_data.hex().upper())[i:i+32] for i in range(0, len(raw_data.hex()), 32)]), language="text")

            with data_c:
                st.subheader("🔍 字段结构化解析 (明文分析)")
                raw_text = raw_data.decode('latin-1')
                analysis_list = parse_for_analysis(raw_text)
                
                if analysis_list:
                    df = pd.DataFrame(analysis_list)
                    st.table(df) # 使用静态表格展示，更清晰
                
                with st.expander("查看原始明文流 (Raw Stream)"):
                    st.text(raw_text)

        except Exception as e:
            st.error(f"生成失败: {e}")

if __name__ == "__main__":
    main()
