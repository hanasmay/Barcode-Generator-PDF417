# -*- coding: utf-8 -*-
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

# ==================== 1. 核心逻辑：真值回填 ====================

def build_complete_stream(inputs, options):
    iin = JURISDICTION_MAP[inputs['state']]['iin']
    
    # 构建子文件内容
    fields = [
        f"DAQ{inputs['dl_number']}\x0a",
        f"DCS{inputs['last_name']}\x0a",
        f"DDEN{inputs['first_name']}\x0a",
        f"DAC{inputs['middle_name']}\x0a",
        "DDFN\x0aDAD\x0aDDGN\x0a",
        f"DCA{inputs['class_code']}\x0a",
        f"DBD{inputs['iss_date']}\x0a",
        f"DBB{inputs['dob']}\x0a",
        f"DBA{inputs['exp_date']}\x0a",
        f"DBC{inputs['sex']}\x0a"
    ]
    
    # 动态身体特征
    if not options['hide_height']: fields.append(f"DAU{int(inputs['height']):03d}IN\x0a")
    if not options['hide_eyes']: fields.append(f"DAY{inputs['eyes']}\x0a")
    if not options['hide_hair']: fields.append(f"DAZ{inputs['hair']}\x0a")
    if not options['hide_weight']: fields.append(f"DAW{inputs['weight']}\x0a")
    if not options['hide_race']: fields.append(f"DCL{inputs['race']}\x0a")
    
    # 地址与标识
    fields.append(f"DAG{inputs['address']}\x0a")
    if not options['hide_apt'] and inputs['apt']: fields.append(f"DAH{inputs['apt']}\x0a")
    fields.append(f"DAI{inputs['city']}\x0a")
    fields.append(f"DAJ{inputs['state']}\x0a")
    fields.append(f"DAK{inputs['zip']}0000\x0a")
    fields.append(f"DCF{inputs['dd_code']}\x0a")
    fields.append("DCGUSA\x0aDDAF\x0a")
    fields.append(f"DDB{inputs['rev_date']}\x0a")
    if not options['hide_audit']: fields.append(f"DCJ{inputs['audit']}\x0a")

    # 合并 Subfile 并移除最后一个多余的换行，添加结束符 \x0d
    subfile_content = "".join(fields).strip() + "\x0d"
    full_body = "DL" + subfile_content
    len_dl = len(full_body.encode('latin-1'))

    # 固定长度：Prefix(17) + CF(10) + Des(10) = 37
    header_prefix = ("@\x0a\x1e\x0dANSI " + iin + "1").encode('latin-1')
    total_len = 37 + len_dl
    
    # 构造头部
    control_field = f"DL03{total_len:05d}1"
    designator = f"DL{37:04d}{len_dl:04d}"
    
    return header_prefix + control_field.encode('latin-1') + designator.encode('latin-1') + full_body.encode('latin-1')

# ==================== 2. UI 界面 ====================

st.set_page_config(page_title="AAMVA Pro Generator", layout="wide")

def main():
    st.title("💳 AAMVA PDF417 50-州 生成专家 (完整版)")
    
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
        columns = st.slider("条码列数", 10, 20, 15)

    c1, c2, c3 = st.columns(3)
    with c1:
        state = st.selectbox("州", list(JURISDICTION_MAP.keys()), index=43)
        last_name = st.text_input("姓", "GOODING")
        first_name = st.text_input("名", "LACEY")
        middle_name = st.text_input("中间名", "LYNN")
    with c2:
        dl_num = st.text_input("证件号", "171625540")
        dob = st.text_input("生日 (MMDDYYYY)", "09231990")
        iss = st.text_input("签发日", "04202021")
        exp = st.text_input("到期日", "09232026")
    with c3:
        address = st.text_input("地址", "8444 KALAMATH ST")
        city = st.text_input("城市", "FEDERAL HEIGHTS")
        zip_code = st.text_input("邮编", "80260")
        audit = st.text_input("审计码", "CDOR123456")

    if st.button("🚀 生成条码"):
        inputs = {
            'state': state, 'last_name': last_name, 'first_name': first_name,
            'middle_name': middle_name, 'dl_number': dl_num, 'dob': dob,
            'iss_date': iss, 'exp_date': exp, 'address': address, 'city': city,
            'zip': zip_code, 'sex': '2', 'height': '069', 'weight': '140',
            'eyes': 'BLU', 'hair': 'BRO', 'race': 'W', 'apt': 'APT B',
            'dd_code': '6358522', 'rev_date': '10302015', 'audit': audit, 'class_code': 'C'
        }
        
        final_data = build_complete_stream(inputs, options)
        
        # 校验
        actual = len(final_data)
        claimed = int(final_data[21:26].decode('latin-1'))
        if actual == claimed:
            st.success(f"✅ 校验通过：{actual} 字节完全匹配")
        else:
            st.error(f"❌ 长度不一致：实际 {actual} vs 声明 {claimed}")

        # 显示
        img = render_image(encode(final_data, columns=columns), scale=3)
        st.image(img, caption="PDF417 Barcode")
        st.code(final_data.hex().upper())

if __name__ == "__main__":
    main()
