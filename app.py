# -*- coding: utf-8 -*-
"""
AAMVA PDF417 50-State DL Generator (FINAL ULTIMATE FIX - REAL LENGTH MATCH)
功能：生成符合 AAMVA 格式但包含用户特定修改 (DL03) 的条码。
特点：锁定 IIN，强制 DL03，通过“二次计算法”确保声明长度与实际长度百分之百匹配。
"""
import streamlit as st
from PIL import Image
import io 
import math
import pandas as pd

# --- 引入外部库 ---
try:
    from pdf417 import encode, render_image
except ImportError:
    st.warning("警告：PDF417 编码库未安装。")
    def encode(*args, **kwargs): return []
    def render_image(*args, **kwargs): return Image.new('RGB', (100, 100))

# ==================== 0. 配置与 51 州 IIN 映射 (完全保留用户版本) ====================
JURISDICTION_MAP = {
    "AL": {"name": "Alabama - 阿拉巴马州", "iin": "636033", "jver": "01", "race": "W", "country": "USA", "abbr": "AL"},
    "AK": {"name": "Alaska - 阿拉斯加州", "iin": "636059", "jver": "00", "race": "W", "country": "USA", "abbr": "AK"},
    "AZ": {"name": "Arizona - 亚利桑那州", "iin": "636026", "jver": "01", "race": "W", "country": "USA", "abbr": "AZ"},
    "AR": {"name": "Arkansas - 阿肯色州", "iin": "636021", "jver": "01", "race": "W", "country": "USA", "abbr": "AR"},
    "CA": {"name": "California - 加利福尼亚州", "iin": "636014", "jver": "00", "race": "W", "country": "USA", "abbr": "CA"},
    "CO": {"name": "Colorado - 科罗拉多州", "iin": "636020", "jver": "01", "race": "CLW", "country": "USA", "abbr": "CO"}, 
    "CT": {"name": "Connecticut - 康涅狄格州", "iin": "636006", "jver": "01", "race": "W", "country": "USA", "abbr": "CT"},
    "DE": {"name": "Delaware - 特拉华州", "iin": "636011", "jver": "01", "race": "W", "country": "USA", "abbr": "DE"},
    "DC": {"name": "District of Columbia - 华盛顿特区", "iin": "636043", "jver": "01", "race": "W", "country": "USA", "abbr": "DC"},
    "FL": {"name": "Florida - 佛罗里达州", "iin": "636010", "jver": "01", "race": "W", "country": "USA", "abbr": "FL"},
    "GA": {"name": "Georgia - 佐治亚州", "iin": "636055", "jver": "01", "race": "W", "country": "USA", "abbr": "GA"},
    "HI": {"name": "Hawaii - 夏威夷州", "iin": "636047", "jver": "01", "race": "W", "country": "USA", "abbr": "HI"},
    "ID": {"name": "Idaho - 爱达荷州", "iin": "636050", "jver": "01", "race": "W", "country": "USA", "abbr": "ID"},
    "IL": {"name": "Illinois - 伊利诺伊州", "iin": "636035", "jver": "01", "race": "W", "country": "USA", "abbr": "IL"},
    "IN": {"name": "Indiana - 印第安纳州", "iin": "636037", "jver": "01", "race": "W", "country": "USA", "abbr": "IN"},
    "IA": {"name": "Iowa - 爱荷华州", "iin": "636018", "jver": "01", "race": "W", "country": "USA", "abbr": "IA"},
    "KS": {"name": "Kansas - 堪萨斯州", "iin": "636022", "jver": "01", "race": "W", "country": "USA", "abbr": "KS"},
    "KY": {"name": "Kentucky - 肯塔基州", "iin": "636046", "jver": "01", "race": "W", "country": "USA", "abbr": "KY"},
    "LA": {"name": "Louisiana - 路易斯安那州", "iin": "636007", "jver": "01", "race": "W", "country": "USA", "abbr": "LA"},
    "ME": {"name": "Maine - 缅因州", "iin": "636041", "jver": "01", "race": "W", "country": "USA", "abbr": "ME"},
    "MD": {"name": "Maryland - 马里兰州", "iin": "636003", "jver": "01", "race": "W", "country": "USA", "abbr": "MD"},
    "MA": {"name": "Massachusetts - 马萨诸塞州", "iin": "636002", "jver": "01", "race": "W", "country": "USA", "abbr": "MA"},
    "MI": {"name": "Michigan - 密歇根州", "iin": "636032", "jver": "01", "race": "W", "country": "USA", "abbr": "MI"},
    "MN": {"name": "Minnesota - 明尼苏达州", "iin": "636038", "jver": "01", "race": "W", "country": "USA", "abbr": "MN"},
    "MS": {"name": "Mississippi - 密西西比州", "iin": "636051", "jver": "01", "race": "W", "country": "USA", "abbr": "MS"},
    "MO": {"name": "Missouri - 密苏里州", "iin": "636030", "jver": "01", "race": "W", "country": "USA", "abbr": "MO"},
    "MT": {"name": "Montana - 蒙大拿州", "iin": "636008", "jver": "01", "race": "W", "country": "USA", "abbr": "MT"},
    "NE": {"name": "Nebraska - 内布拉斯加州", "iin": "636054", "jver": "01", "race": "W", "country": "USA", "abbr": "NE"},
    "NV": {"name": "Nevada - 内华达州", "iin": "636049", "jver": "01", "race": "W", "country": "USA", "abbr": "NV"},
    "NH": {"name": "New Hampshire - 新罕布什尔州", "iin": "636039", "jver": "01", "race": "W", "country": "USA", "abbr": "NH"},
    "NJ": {"name": "New Jersey - 新泽西州", "iin": "636036", "jver": "01", "race": "W", "country": "USA", "abbr": "NJ"},
    "NM": {"name": "New Mexico - 新墨西哥州", "iin": "636009", "jver": "01", "race": "W", "country": "USA", "abbr": "NM"},
    "NY": {"name": "New York - 纽约州", "iin": "636001", "jver": "01", "race": "W", "country": "USA", "abbr": "NY"},
    "NC": {"name": "North Carolina - 北卡罗来纳州", "iin": "636004", "jver": "01", "race": "W", "country": "USA", "abbr": "NC"}, 
    "ND": {"name": "North Dakota - 北达科他州", "iin": "636034", "jver": "01", "race": "W", "country": "USA", "abbr": "ND"}, 
    "OH": {"name": "Ohio - 俄亥俄州", "iin": "636023", "jver": "01", "race": "W", "country": "USA", "abbr": "OH"},
    "OK": {"name": "Oklahoma - 俄克拉荷马州", "iin": "636058", "jver": "01", "race": "W", "country": "USA", "abbr": "OK"},
    "OR": {"name": "Oregon - 俄勒冈州", "iin": "636029", "jver": "01", "race": "W", "country": "USA", "abbr": "OR"},
    "PA": {"name": "Pennsylvania - 宾夕法尼亚州", "iin": "636025", "jver": "01", "race": "W", "country": "USA", "abbr": "PA"},
    "RI": {"name": "Rhode Island - 罗德岛州", "iin": "636052", "jver": "01", "race": "W", "country": "USA", "abbr": "RI"},
    "SC": {"name": "South Carolina - 南卡罗来纳州", "iin": "636005", "jver": "01", "race": "W", "country": "USA", "abbr": "SC"},
    "SD": {"name": "South Dakota - 南达科他州", "iin": "636042", "jver": "01", "race": "W", "country": "USA", "abbr": "SD"},
    "TN": {"name": "Tennessee - 田纳西州", "iin": "636053", "jver": "01", "race": "W", "country": "USA", "abbr": "TN"},
    "TX": {"name": "Texas - 德克萨斯州", "iin": "636015", "jver": "01", "race": "W", "country": "USA", "abbr": "TX"}, 
    "UT": {"name": "Utah - 犹他州", "iin": "636040", "jver": "01", "race": "W", "country": "USA", "abbr": "UT"},
    "VT": {"name": "Vermont - 佛蒙特州", "iin": "636024", "jver": "01", "race": "W", "country": "USA", "abbr": "VT"},
    "VA": {"name": "Virginia - 弗吉尼亚州", "iin": "636000", "jver": "01", "race": "W", "country": "USA", "abbr": "VA"},
    "WA": {"name": "Washington - 华盛顿州", "iin": "636045", "jver": "00", "race": "W", "country": "USA", "abbr": "WA"}, 
    "WV": {"name": "West Virginia - 西弗吉尼亚州", "iin": "636061", "jver": "01", "race": "W", "country": "USA", "abbr": "WV"},
    "WI": {"name": "Wisconsin - 威斯康星州", "iin": "636031", "jver": "01", "race": "W", "country": "USA", "abbr": "WI"},
    "WY": {"name": "Wyoming - 怀俄明州", "iin": "636060", "jver": "01", "race": "W", "country": "USA", "abbr": "WY"},
    "GU": {"name": "Guam - 关岛", "iin": "636019", "jver": "01", "race": "W", "country": "USA", "abbr": "GU"},
    "PR": {"name": "Puerto Rico - 波多黎各", "iin": "604431", "jver": "01", "race": "W", "country": "USA", "abbr": "PR"},
    "VI": {"name": "Virgin Islands - 维尔京群岛", "iin": "636062", "jver": "01", "race": "W", "country": "USA", "abbr": "VI"},
    "AS": {"name": "American Samoa - 美属萨摩亚", "iin": "604427", "jver": "01", "race": "W", "country": "USA", "abbr": "AS"},
    "MP": {"name": "Norther Marianna Islands - 北马里亚纳群岛", "iin": "604430", "jver": "01", "race": "W", "country": "USA", "abbr": "MP"},
}

st.set_page_config(page_title="AAMVA PDF417 生成专家", page_icon="💳", layout="wide")

# ==================== 1. 辅助函数 ====================
def get_hex_dump_str(raw_bytes):
    output = []
    output.append(f"📦 数据长度: {len(raw_bytes)} 字节")
    output.append("-" * 50)
    hex_str = raw_bytes.hex().upper()
    for i in range(0, len(hex_str), 32):
        chunk = hex_str[i:i+32]
        ascii_chunk = "".join([chr(int(chunk[j:j+2], 16)) if 32 <= int(chunk[j:j+2], 16) <= 126 else "." for j in range(0, len(chunk), 2)])
        output.append(f"{chunk.ljust(32)} | {ascii_chunk}")
    return "\n".join(output)

def convert_height(h):
    if not h.isdigit(): return "000"
    return f"{int(h):03d}"

# ==================== 2. 核心生成逻辑 (二次计算法) ====================
def generate_aamva_final(inputs):
    config = JURISDICTION_MAP[inputs['jurisdiction_code']]
    iin = config['iin']
    
    # 构造数据体 (Subfile Body)
    sub_parts = [
        f"DAQ{inputs['dl_number']}\x0a",
        f"DCS{inputs['last_name']}\x0a",
        f"DDEN{inputs['first_name']}\x0a",
        f"DAC{inputs['middle_name']}\x0a",
        f"DDFN\x0aDAD\x0aDDGN\x0a",
        f"DCA{inputs['class_code']}\x0a",
        f"DBD{inputs['iss_date']}\x0a",
        f"DBB{inputs['dob']}\x0a",
        f"DBA{inputs['exp_date']}\x0a",
        f"DBC{inputs['sex']}\x0a",
        f"DAU{convert_height(inputs['height_input'])}IN\x0a",
        f"DAY{inputs['eyes']}\x0a",
        f"DAG{inputs['address']}\x0a",
        f"DAI{inputs['city']}\x0a",
        f"DAJ{inputs['jurisdiction_code']}\x0a",
        f"DAK{inputs['zip_input']}0000\x0a",
        f"DCF{inputs['dd_code']}\x0a",
        f"DCGUSA\x0a",
        f"DDAF\x0a",
        f"DDB{inputs['rev_date']}\x0a",
        f"DAZ{inputs['hair']}\x0a",
        f"DAW{inputs['weight']}"
    ]
    subfile_body = "DL" + "".join(sub_parts) + "\x0d"
    len_dl = len(subfile_body.encode('latin-1'))

    # 固定长度定义
    prefix = ("@\x0a\x1e\x0dANSI " + iin + "1").encode('latin-1')
    prefix_len = len(prefix) # 应当是 17
    cf_len = 10  # DL03 + 5位长度 + 1位文件数
    des_len = 10 # DL + 4位偏移 + 4位长度
    
    # 计算实际总长度并书写声明
    actual_total_len = prefix_len + cf_len + des_len + len_dl
    
    # 构造头部
    control_field = f"DL03{actual_total_len:05d}1"
    offset_dl = prefix_len + cf_len + des_len
    designator = f"DL{offset_dl:04d}{len_dl:04d}"
    
    full_data = prefix + control_field.encode('latin-1') + designator.encode('latin-1') + subfile_body.encode('latin-1')
    return full_data

# ==================== 3. UI 界面 ====================
def main():
    st.title("💳 AAMVA PDF417 生成专家 (真值长度版)")
    
    # 侧边栏设置
    with st.sidebar:
        st.header("⚙️ 条码设置")
        selected_columns = st.selectbox("条码列数 (Columns)", [10, 13, 15, 17, 20], index=2)
        
    # 州选择
    jurisdictions = {v['name'] + f" ({k})": k for k, v in JURISDICTION_MAP.items()}
    state_label = st.selectbox("选择州", sorted(jurisdictions.keys()))
    jurisdiction_code = jurisdictions[state_label]

    # 输入表单
    col1, col2 = st.columns(2)
    with col1:
        last_name = st.text_input("姓 (DCS)", "GOODING")
        first_name = st.text_input("名 (DDEN)", "LACEY")
        middle_name = st.text_input("中间名 (DAC)", "LYNN")
        dl_number = st.text_input("驾照号 (DAQ)", "171625540")
    with col2:
        dob = st.text_input("生日 (DBB: MMDDYYYY)", "09231990")
        iss_date = st.text_input("签发日 (DBD: MMDDYYYY)", "04202021")
        exp_date = st.text_input("过期日 (DBA: MMDDYYYY)", "09232026")
        rev_date = st.text_input("版本日 (DDB: MMDDYYYY)", "10302015")

    # 其他信息
    with st.expander("更多身体与地址信息"):
        c1, c2, c3 = st.columns(3)
        sex = c1.selectbox("性别", ["1", "2"], index=1)
        height = c2.text_input("身高(英寸)", "069")
        weight = c3.text_input("体重(磅)", "140")
        address = st.text_input("地址", "8444 KALAMATH ST")
        city = st.text_input("城市", "FEDERAL HEIGHTS")
        zip_code = st.text_input("邮编(5位)", "80260")
        eyes = st.text_input("眼睛颜色", "BLU")
        hair = st.text_input("头发颜色", "BRO")
        dd_code = st.text_input("识别码 (DCF)", "6358522")

    if st.button("🚀 生成并校验条码"):
        inputs = {
            'jurisdiction_code': jurisdiction_code, 'last_name': last_name, 'first_name': first_name,
            'middle_name': middle_name, 'dl_number': dl_number, 'dob': dob, 'iss_date': iss_date,
            'exp_date': exp_date, 'rev_date': rev_date, 'sex': sex, 'height_input': height,
            'weight': weight, 'address': address, 'city': city, 'zip_input': zip_code,
            'eyes': eyes, 'hair': hair, 'dd_code': dd_code, 'class_code': 'C'
        }
        
        raw_data = generate_aamva_final(inputs)
        
        # 校验逻辑
        claimed_len_str = raw_data[21:26].decode('latin-1')
        actual_len = len(raw_data)
        
        if int(claimed_len_str) == actual_len:
            st.success(f"✅ 完美匹配！实际长度与声明长度均为: {actual_len} 字节")
        else:
            st.error(f"❌ 仍不匹配: 声明 {claimed_len_str} vs 实际 {actual_len}")

        # 生成条码图
        codes = encode(raw_data, columns=selected_columns)
        image = render_image(codes, scale=3)
        st.image(image, caption="生成的 PDF417 条码")
        
        st.subheader("数据详情 (HEX)")
        st.code(get_hex_dump_str(raw_data))

if __name__ == "__main__":
    main()
