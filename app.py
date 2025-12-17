# -*- coding: utf-8 -*-
import streamlit as st
import io
from datetime import datetime
from PIL import Image

# --- 依赖库加载 ---
try:
    from pdf417 import encode, render_image
except ImportError:
    st.error("缺失依赖库！请在 requirements.txt 中添加 pdf417")

# ==================== 1. AAMVA 50 州 IIN 数据库 ====================
# 包含 IIN 映射，部分州根据规范做了版本微调
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

# ==================== 2. 核心计算逻辑：回填对齐算法 ====================

def build_aamva_stream(inputs, options):
    """
    核心对齐逻辑：
    1. 锁定版本参数：AAMVA 09, JUR 00, Entries 01 (WA标准)
    2. 构建 Subfile 字节流并测量物理长度
    3. 动态回填 Offset 和 Total Length
    """
    iin = JURISDICTION_MAP[inputs['state']]
    
    # 锁定版本控制 (基于您的要求)
    aamva_ver = "09"
    jur_ver = "00"
    num_entries = "01"

    # 自动计算 18/21 岁日期
    try:
        dob_dt = datetime.strptime(inputs['dob'], "%m%d%Y")
        ddh = dob_dt.replace(year=dob_dt.year + 18).strftime("%m%d%Y")
        ddj = dob_dt.replace(year=dob_dt.year + 21).strftime("%m%d%Y")
    except:
        ddh, ddj = "00000000", "00000000"

    # --- 构建子文件主体 ---
    body = []
    # 依照 AAMVA D20 常见排序
    body.append(f"DAQ{inputs['dl_number']}\x0a")
    body.append(f"DCS{inputs['last_name']}\x0a")
    body.append(f"DDEN{inputs['first_name']}\x0a")
    body.append(f"DAC{inputs['middle_name']}\x0a")
    body.append(f"DDFN\x0aDAD\x0aDDGN\x0a")
    body.append(f"DCA{inputs['class']}\x0a")
    body.append(f"DBD{inputs['iss_date']}\x0a")
    body.append(f"DBB{inputs['dob']}\x0a")
    body.append(f"DBA{inputs['exp_date']}\x0a")
    body.append(f"DBC{inputs['sex']}\x0a")
    
    if not options['hide_height']: body.append(f"DAU{inputs['height']} in\x0a")
    if not options['hide_eyes']: body.append(f"DAY{inputs['eyes']}\x0a")
    if not options['hide_hair']: body.append(f"DAZ{inputs['hair']}\x0a")
    if not options['hide_weight']: body.append(f"DAW{inputs['weight']}\x0a")
    if not options['hide_race']: body.append(f"DCL{inputs['race']}\x0a")
    
    body.append(f"DAG{inputs['address']}\x0a")
    if not options['hide_apt']: body.append(f"DAH{inputs['apt']}\x0a")
    
    body.append(f"DAI{inputs['city']}\x0a")
    body.append(f"DAJ{inputs['state']}\x0a")
    
    # 邮编处理
    zip_val = inputs['zip'].replace("-", "")
    if len(zip_val) == 5: zip_val += "0000"
    body.append(f"DAK{zip_val}  \x0a") # AAMVA DAK 常见带两个空格填充
    
    body.append(f"DCF{inputs['dd_code']}\x0a")
    body.append(f"DCGUSA\x0a")
    body.append(f"DDAF\x0a")
    body.append(f"DDB{inputs['rev_date']}\x0a")
    body.append(f"DDD1\x0a") # 驾照指示符
    
    if not options['hide_audit']: body.append(f"DCJ{inputs['audit']}\x0a")
    
    body.append(f"DDH{ddh}\x0a")
    body.append(f"DDJ{ddj}\x0a")
    body.append(f"DCU")

    # 封装并测量 (Latin-1 编码确保字节数准确)
    subfile_str = "DL" + "".join(body) + "\x0d"
    subfile_bytes = subfile_str.encode('latin-1')
    len_dl = len(subfile_bytes)

    # --- 计算头部结构 ---
    # Header Prefix (@\x0a\x1e\x0dANSI 6位IIN + 2位Ver + 2位JVer + 2位Num) = 21 bytes
    # Designator (DL + 4位偏移 + 4位长度) = 10 bytes
    # Control Field (DL03 + 5位总长 + 1位文件数) = 9 bytes
    # 分隔符 \x0d = 1 byte
    
    prefix_len, cf_len, des_len, sep_len = 21, 9, 10, 1
    total_len = prefix_len + cf_len + des_len + sep_len + len_dl
    
    header_prefix = f"@\x0a\x1e\x0dANSI {iin}{aamva_ver}{jur_ver}{num_entries}"
    control_field = f"DL03{total_len:05d}1"
    offset_dl = prefix_len + cf_len + des_len + sep_len
    designator = f"DL{offset_dl:04d}{len_dl:04d}"
    
    return header_prefix.encode('latin-1') + \
           control_field.encode('latin-1') + \
           designator.encode('latin-1') + \
           b"\x0d" + \
           subfile_bytes

# ==================== 3. Streamlit UI ====================

def main():
    st.set_page_config(page_title="AAMVA 50-State Pro", layout="wide", page_icon="💳")
    st.title("💳 AAMVA PDF417 50-州 终极生成器")

    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 动态控制")
        options = {
            'hide_height': st.checkbox("隐藏身高 (DAU)", False),
            'hide_weight': st.checkbox("隐藏体重 (DAW)", False),
            'hide_eyes': st.checkbox("隐藏眼睛 (DAY)", False),
            'hide_hair': st.checkbox("隐藏头发 (DAZ)", False),
            'hide_race': st.checkbox("隐藏民族 (DCL)", True),
            'hide_apt': st.checkbox("隐藏公寓号 (DAH)", True),
            'hide_audit': st.checkbox("隐藏审计码 (DCJ)", True),
        }
        st.markdown("---")
        target_state = st.selectbox("选择目标州", list(JURISDICTION_MAP.keys()), index=47) # 默认 WA
        cols = st.slider("条码列数", 11, 19, 13)
        st.info(f"当前模式: AAMVA 09 | JUR 00 | Entry 01")

    # 输入区域
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("👤 身份")
        ln = st.text_input("姓 (DCS)", "SOLOMON")
        fn = st.text_input("名 (DAC)", "DANIEL")
        mn = st.text_input("中间名", "NONE")
        dl = st.text_input("证件号 (DAQ)", "WDL0ALXD2K1B")
    with col2:
        st.subheader("📍 物理/地址")
        addr = st.text_input("街道 (DAG)", "29810 224TH AVE SE")
        city = st.text_input("城市 (DAI)", "KENT")
        zip_c = st.text_input("邮编 (DAK)", "98010")
        h = st.text_input("身高 (IN, 如 072)", "072")
        w = st.text_input("体重 (LB)", "175")
    with col3:
        st.subheader("📅 日期/代码")
        dob = st.text_input("生日 (MMDDYYYY)", "08081998")
        iss = st.text_input("签发日", "06062024")
        exp = st.text_input("过期日", "08082030")
        rev = st.text_input("版面日期", "11122019")
        dd = st.text_input("鉴别码 (DCF)", "WDL0ALXD2K1BA020424988483")

    st.markdown("---")

    if st.button("🚀 生成条码图像", type="primary"):
        inputs = {
            'state': target_state, 'last_name': ln, 'first_name': fn, 'middle_name': mn,
            'dl_number': dl, 'dob': dob, 'iss_date': iss, 'exp_date': exp,
            'rev_date': rev, 'sex': "1", 'address': addr, 'city': city,
            'zip': zip_c, 'height': h, 'weight': w, 'eyes': 'BLU', 'hair': 'BRO',
            'class': 'NONE', 'dd_code': dd, 'apt': 'APT 1', 'audit': 'A020424988483', 'race': 'W'
        }
        
        try:
            # 1. 生成字节流
            raw_data = build_aamva_stream(inputs, options)
            
            # 2. 校验长度 (21+9+10+1 = 41 字节头部固定开销)
            actual_len = len(raw_data)
            claimed_len = int(raw_data[21:26].decode('latin-1'))
            
            if actual_len == claimed_len:
                st.success(f"✅ 长度对齐成功：总长度 {actual_len} 字节")
            else:
                st.error(f"❌ 警告：实际 {actual_len} 字节 vs 声明 {claimed_len} 字节")

            # 3. 渲染
            codes = encode(raw_data, columns=cols, security_level=5)
            img = render_image(codes, scale=4, ratio=3, padding=10)
            
            # 4. 展示
            res_col, hex_col = st.columns([1, 1.2])
            with res_col:
                st.image(img, caption=f"{target_state} PDF417")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                st.download_button("💾 下载图片", buf.getvalue(), f"{target_state}_DL.png")
            with hex_col:
                st.subheader("📦 HEX 视图")
                hex_str = raw_data.hex().upper()
                st.code("\n".join([hex_str[i:i+32] for i in range(0, len(hex_str), 32)]))

        except Exception as e:
            st.error(f"发生错误: {e}")

if __name__ == "__main__":
    main()
