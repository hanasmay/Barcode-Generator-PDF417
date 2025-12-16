# -*- coding: utf-8 -*-
"""
AAMVA PDF417 Generator (FINAL ULTIMATE VERSION - 100% LENGTH MATCH)
功能：生成符合 AAMVA 逻辑的 PDF417 条码，强制 DL03 结构。
核心：通过二次编码确保声明长度与实际长度百分之百一致。
"""
import streamlit as st
from PIL import Image
import io

# --- 外部库处理 ---
try:
    from pdf417 import encode, render_image
except ImportError:
    st.warning("请安装库: pip install pdf417")

# ==================== 0. 配置与 IIN 锁定 (完全保留用户指定版本) ====================
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

# ==================== 1. 核心逻辑：动态长度修正 ====================

def build_aamva_stream(inputs):
    iin = JURISDICTION_MAP[inputs['state']]['iin']
    
    # 第一步：构造 Subfile 内容（不含长度信息的部分）
    subfile_body = (
        f"DAQ{inputs['dl_number']}\x0a"
        f"DCS{inputs['last_name']}\x0a"
        f"DDEN{inputs['first_name']}\x0a"
        f"DAC{inputs['middle_name']}\x0a"
        f"DDFN\x0aDAD\x0aDDGN\x0a"
        f"DCAC\x0a" # Class
        f"DBD{inputs['iss_date']}\x0a"
        f"DBB{inputs['dob']}\x0a"
        f"DBA{inputs['exp_date']}\x0a"
        f"DBC2\x0a" # Sex
        f"DAU069IN\x0a" # Height 锁定格式匹配 HEX
        f"DAYBLU\x0a" # Eyes
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
    
    # 真实计算 subfile body 的字节数
    # 注意：前面的 'DL' 标志和末尾的 '\x0d' 必须计入
    full_body = "DL" + subfile_body + "\x0d"
    len_dl = len(full_body.encode('latin-1')) # 比如 227

    # 固定前缀（基于您的 HEX: @\x0a\x1e\x0dANSI 6360431）
    header_prefix = ("@\x0a\x1e\x0dANSI " + iin + "1").encode('latin-1')
    prefix_len = len(header_prefix) # 应当是 17
    
    # 控制字段长度固定为 10 (DL03 + 5位数字 + 1位文件数)
    cf_len = 10
    # 标志符长度固定为 10 (DL + 4位偏移 + 4位长度)
    des_len = 10
    
    # 计算精确的总长度
    total_len = prefix_len + cf_len + des_len + len_dl # 17 + 10 + 10 + 226 = 263
    
    # 第二步：构造完整的头部，使用刚刚计算出的真实 total_len
    control_field = f"DL03{total_len:05d}1"
    offset_dl = prefix_len + cf_len + des_len
    designator = f"DL{offset_dl:04d}{len_dl:04d}"
    
    # 拼接最终字节流
    final_stream = (
        header_prefix + 
        control_field.encode('latin-1') + 
        designator.encode('latin-1') + 
        full_body.encode('latin-1')
    )
    return final_stream

# ==================== 2. Streamlit UI ====================

st.set_page_config(page_title="PDF417 长度校准器", layout="wide")

def main():
    st.title("💳 AAMVA 条码长度完美适配工具")
    
    col1, col2 = st.columns(2)
    with col1:
        state = st.selectbox("选择州 (用于获取IIN)", list(JURISDICTION_MAP.keys()), index=43) # 默认 TX
        last_name = st.text_input("Last Name", "GOODING")
        first_name = st.text_input("First Name", "LACEY")
        dl_number = st.text_input("DL Number", "171625540")
    with col2:
        dob = st.text_input("DOB (MMDDYYYY)", "09231990")
        iss = st.text_input("Issue Date", "04202021")
        exp = st.text_input("Expiry Date", "09232026")
        zip_code = st.text_input("Zip", "80260")

    if st.button("🚀 生成并校验长度"):
        inputs = {
            'state': state, 'last_name': last_name, 'first_name': first_name,
            'middle_name': "LYNN", 'dl_number': dl_number, 'dob': dob,
            'iss_date': iss, 'exp_date': exp, 'zip': zip_code,
            'address': '8444 KALAMATH ST', 'rev_date': '10302015'
        }
        
        raw_data = build_aamva_stream(inputs)
        
        # 实时长度检测
        actual_size = len(raw_data)
        # 从字节流中提取我们填入的声明长度（位置 21 到 26）
        claimed_size = int(raw_data[21:26].decode('latin-1'))
        
        if actual_size == claimed_size:
            st.success(f"✅ 校验通过！实际长度 ({actual_size}) 与 声明长度 ({claimed_size}) 完美匹配。")
        else:
            st.error(f"❌ 依然不匹配：实际 {actual_size} vs 声明 {claimed_size}")

        # 生成条码图
        codes = encode(raw_data, columns=15)
        image = render_image(codes, scale=3)
        st.image(image, caption="PDF417 条码")
        
        # 显示 HEX 以供对比
        st.subheader("生成的 HEX 数据流")
        hex_str = raw_data.hex().upper()
        formatted_hex = " ".join([hex_str[i:i+32] for i in range(0, len(hex_str), 32)])
        st.code(formatted_hex)

if __name__ == "__main__":
    main()
