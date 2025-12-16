# -*- coding: utf-8 -*-
"""
AAMVA PDF417 Generator (FINAL ULTIMATE VERSION - 100% LENGTH MATCH)
功能：生成符合 AAMVA 规范的 50 州条码，强制 DL03 结构。
核心：锁定 IIN 映射，通过“二次回填”技术确保声明长度与实际字节数完全一致。
"""
import streamlit as st
from PIL import Image
import io

# --- 引入 PDF417 库 ---
try:
    from pdf417 import encode, render_image
except ImportError:
    st.warning("请在终端运行: pip install pdf417")

# ==================== 0. 配置与 IIN 锁定 (锁定用户指定版本) ====================
JURISDICTION_MAP = {
    "AL": {"iin": "636033", "abbr": "AL"}, "AK": {"iin": "636059", "abbr": "AK"},
    "AZ": {"iin": "636026", "abbr": "AZ"}, "AR": {"iin": "636021", "abbr": "AR"},
    "CA": {"iin": "636014", "abbr": "CA"}, "CO": {"iin": "636020", "abbr": "CO"}, 
    "CT": {"iin": "636006", "abbr": "CT"}, "DE": {"iin": "636011", "abbr": "DE"},
    "DC": {"iin": "636043", "abbr": "DC"}, "FL": {"iin": "636010", "abbr": "FL"},
    "GA": {"iin": "636055", "abbr": "GA"}, "HI": {"iin": "636047", "abbr": "HI"},
    "ID": {"iin": "636050", "abbr": "ID"}, "IL": {"iin": "636035", "abbr": "IL"},
    "IN": {"iin": "636037", "abbr": "IN"}, "IA": {"iin": "636018", "abbr": "IA"},
    "KS": {"iin": "636022", "abbr": "KS"}, "KY": {"iin": "636046", "abbr": "KY"},
    "LA": {"iin": "636007", "abbr": "LA"}, "ME": {"iin": "636041", "abbr": "ME"},
    "MD": {"iin": "636003", "abbr": "MD"}, "MA": {"iin": "636002", "abbr": "MA"},
    "MI": {"iin": "636032", "abbr": "MI"}, "MN": {"iin": "636038", "abbr": "MN"},
    "MS": {"iin": "636051", "abbr": "MS"}, "MO": {"iin": "636030", "abbr": "MO"},
    "MT": {"iin": "636008", "abbr": "MT"}, "NE": {"iin": "636054", "abbr": "NE"},
    "NV": {"iin": "636049", "abbr": "NV"}, "NH": {"iin": "636039", "abbr": "NH"},
    "NJ": {"iin": "636036", "abbr": "NJ"}, "NM": {"iin": "636009", "abbr": "NM"},
    "NY": {"iin": "636001", "abbr": "NY"}, "NC": {"iin": "636004", "abbr": "NC"}, 
    "ND": {"iin": "636034", "abbr": "ND"}, "OH": {"iin": "636023", "abbr": "OH"},
    "OK": {"iin": "636058", "abbr": "OK"}, "OR": {"iin": "636029", "abbr": "OR"},
    "PA": {"iin": "636025", "abbr": "PA"}, "RI": {"iin": "636052", "abbr": "RI"},
    "SC": {"iin": "636005", "abbr": "SC"}, "SD": {"iin": "636042", "abbr": "SD"},
    "TN": {"iin": "636053", "abbr": "TN"}, "TX": {"iin": "636015", "abbr": "TX"}, 
    "UT": {"iin": "636040", "abbr": "UT"}, "VT": {"iin": "636024", "abbr": "VT"},
    "VA": {"iin": "636000", "abbr": "VA"}, "WA": {"iin": "636045", "abbr": "WA"}, 
    "WV": {"iin": "636061", "abbr": "WV"}, "WI": {"iin": "636031", "abbr": "WI"},
    "WY": {"iin": "636060", "abbr": "WY"},
}

# ==================== 1. 核心逻辑：动态真值回填 ====================

def build_aamva_final_stream(inputs):
    """
    通过两次构建来确保长度完美匹配。
    第一次：构建 Subfile 数据体并测量其实际长度。
    第二次：根据测量的长度回填声明值。
    """
    iin = JURISDICTION_MAP[inputs['state']]['iin']
    
    # --- 第一步：构造 Subfile 数据体 ---
    # 严格遵循 HEX 顺序：DAQ, DCS, DDEN, DAC...
    sub_body_str = (
        f"DAQ{inputs['dl_number']}\x0a"
        f"DCS{inputs['last_name']}\x0a"
        f"DDEN{inputs['first_name']}\x0a"
        f"DAC{inputs['middle_name']}\x0a"
        f"DDFN\x0aDAD\x0aDDGN\x0a"
        f"DCAC\x0a"
        f"DBD{inputs['iss_date']}\x0a"
        f"DBB{inputs['dob']}\x0a"
        f"DBA{inputs['exp_date']}\x0a"
        f"DBC2\x0a"
        f"DAU069IN\x0a"  # 锁定 DAU069IN 格式
        f"DAYBLU\x0a"
        f"DAG{inputs['address']}\x0a"
        f"DAIFEDERAL HEIGHTS\x0a"
        f"DAJ{inputs['state']}\x0a"
        f"DAK{inputs['zip']}00000\x0a"
        f"DCF6358522\x0a"
        f"DCGUSA\x0a"
        f"DDAF\x0a"
        f"DDB10302015\x0a"
        f"DAZBRO\x0a"
        f"DAW140"
    )
    
    # Subfile 必须以 'DL' 开头，并以 '\x0d' 结束
    subfile_full = "DL" + sub_body_str + "\x0d"
    subfile_bytes = subfile_full.encode('latin-1')
    len_dl = len(subfile_bytes)  # 这是真实的子文件字节数

    # --- 第二步：构造头部参数 ---
    # 基于您的 HEX 锁定前缀长度为 17：@\x0a\x1e\x0dANSI (8) + 空格(1) + IIN(6) + '1'(1) + '1'(1)
    # 注意：为了保持 17 字节，我们调整最后的版本标志
    header_prefix_str = "@\x0a\x1e\x0dANSI " + iin + "1"
    header_prefix_bytes = header_prefix_str.encode('latin-1')
    prefix_len = len(header_prefix_bytes) # 结果应为 17

    # Control Field: DL03 + 5位数字总长 + 1位文件数 = 10 字节
    cf_len = 10
    # Designator: DL + 4位偏移 + 4位长度 = 10 字节
    des_len = 10
    
    # --- 第三步：计算精确总长度并回填 ---
    total_data_len = prefix_len + cf_len + des_len + len_dl
    
    # 构造声明字符串
    control_field = f"DL03{total_data_len:05d}1"
    offset_val = prefix_len + cf_len + des_len
    designator = f"DL{offset_val:04d}{len_dl:04d}"
    
    # 拼接最终字节流
    final_data = (
        header_prefix_bytes + 
        control_field.encode('latin-1') + 
        designator.encode('latin-1') + 
        subfile_bytes
    )
    return final_data

# ==================== 2. Streamlit UI 界面 ====================

def main():
    st.set_page_config(page_title="AAMVA 长度完美适配版", layout="wide")
    st.title("💳 AAMVA PDF417 生成专家 (真值长度回填版)")
    st.info("此版本通过实时测量数据流长度并回填声明，彻底解决 264 vs 263 字节的不匹配警告。")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📋 基础信息")
        state = st.selectbox("选择目标州", list(JURISDICTION_MAP.keys()), index=43) # 默认 TX
        last_name = st.text_input("姓 (DCS)", "GOODING")
        first_name = st.text_input("名 (DDEN)", "LACEY")
        dl_number = st.text_input("驾照号 (DAQ)", "171625540")
        address = st.text_input("地址 (DAG)", "8444 KALAMATH ST")
    
    with col2:
        st.subheader("📅 日期与邮编")
        dob = st.text_input("生日 (DBB: MMDDYYYY)", "09231990")
        iss = st.text_input("签发日 (DBD: MMDDYYYY)", "04202021")
        exp = st.text_input("过期日 (DBA: MMDDYYYY)", "09232026")
        zip_code = st.text_input("邮编 (5位)", "80260")
        columns = st.slider("条码列数 (Columns)", 10, 20, 15)

    if st.button("🚀 生成条码并校验长度"):
        inputs = {
            'state': state, 'last_name': last_name, 'first_name': first_name,
            'middle_name': "LYNN", 'dl_number': dl_number, 'dob': dob,
            'iss_date': iss, 'exp_date': exp, 'zip': zip_code, 'address': address
        }
        
        # 执行动态生成
        final_stream = build_aamva_final_stream(inputs)
        
        # --- 校验结果展示 ---
        actual_size = len(final_stream)
        # 从流中提取 21 到 26 字节（即我们填入的声明长度数字）
        claimed_size_str = final_stream[21:26].decode('latin-1')
        claimed_size = int(claimed_size_str)
        
        if actual_size == claimed_size:
            st.success(f"✅ 完美匹配！实际长度: {actual_size} | 头部声明: {claimed_size}")
        else:
            st.error(f"❌ 警告: 实际 {actual_size} 字节 vs 声明 {claimed_size} 字节")

        # --- 生成图像 ---
        codes = encode(final_stream, columns=columns)
        img = render_image(codes, scale=3)
        
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="生成的 AAMVA PDF417 条码")
        
        # --- 十六进制展示 ---
        st.subheader("📦 原始 HEX 数据流")
        hex_data = final_stream.hex().upper()
        formatted_hex = "\n".join([hex_data[i:i+32] for i in range(0, len(hex_data), 32)])
        st.code(formatted_hex, language="text")

if __name__ == "__main__":
    main()
