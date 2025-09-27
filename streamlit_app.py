import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Excel → Sankey", layout="wide")
st.title("📊 Sankey Diagram จาก Excel")

# ========== Upload ==========
uploaded = st.file_uploader("อัปโหลดไฟล์ Excel", type=["xlsx"])
if not uploaded:
    st.info("กรุณาอัปโหลดไฟล์ Excel (.xlsx)")
    st.stop()

xls = pd.ExcelFile(uploaded)
sheet = st.selectbox("เลือกชีต", xls.sheet_names)
df = pd.read_excel(xls, sheet_name=sheet)

if df.empty:
    st.error("ชีตนี้ไม่มีข้อมูล")
    st.stop()

# ========== เลือกคอลัมน์ ==========
st.subheader("🔧 ตั้งค่า")
col_old = st.selectbox("คอลัมน์ Source (ฝ่ายเดิม)", df.columns)
col_new = st.selectbox("คอลัมน์ Target (ฝ่ายใหม่)", df.columns)
col_name = st.selectbox("คอลัมน์ชื่อบุคคล", [None] + list(df.columns))
col_val = st.selectbox("คอลัมน์ Value (จำนวน)", [None] + list(df.columns))

mode = st.radio("โหมดแสดงผล", ["ซ่อนชื่อ (ระดับฝ่าย)", "แสดงชื่อบุคคล"], horizontal=True)

# ========== Filter ==========
c1, c2 = st.columns(2)
with c1:
    sel_old = st.multiselect("เลือกฝ่ายเดิม", sorted(df[col_old].dropna().unique()), default=sorted(df[col_old].dropna().unique()))
with c2:
    sel_new = st.multiselect("เลือกฝ่ายใหม่", sorted(df[col_new].dropna().unique()), default=sorted(df[col_new].dropna().unique()))

df = df[df[col_old].isin(sel_old) & df[col_new].isin(sel_new)]

if df.empty:
    st.warning("ไม่มีข้อมูลหลังจากกรอง")
    st.stop()

# ========== Prepare Data ==========
if mode == "ซ่อนชื่อ (ระดับฝ่าย)":
    if col_val and col_val != "None":
        flows = df.groupby([col_old, col_new])[col_val].sum().reset_index(name="count")
    else:
        flows = df.groupby([col_old, col_new]).size().reset_index(name="count")

    all_nodes = pd.Index(flows[col_old].tolist() + flows[col_new].tolist()).unique()
    node_idx = {name: i for i, name in enumerate(all_nodes)}

    sources = [node_idx[s] for s in flows[col_old]]
    targets = [node_idx[t] for t in flows[col_new]]
    values  = flows["count"].tolist()

    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=30, thickness=25,  # node ใหญ่ขึ้น
            label=all_nodes.tolist(),
            line=dict(color="black", width=1.0),
            font=dict(color="black", size=18, family="Tahoma")  # ฟอนต์ใหญ่ชัด
        ),
        link=dict(source=sources, target=targets, value=values)
    )])

else:  # โหมดแสดงชื่อบุคคล
    if not col_name or col_name == "None":
        st.error("กรุณาเลือกคอลัมน์ชื่อบุคคลเพื่อใช้โหมดนี้")
        st.stop()

    df = df.dropna(subset=[col_name])
    df["left_label"] = df[col_old] + " : " + df[col_name]

    sources_lbl = df["left_label"]
    targets_lbl = df[col_new]
    values      = [1] * len(df)

    all_nodes = pd.Index(pd.concat([sources_lbl, targets_lbl]).unique())
    node_idx  = {name: i for i, name in enumerate(all_nodes)}

    source_ids = [node_idx[s] for s in sources_lbl]
    target_ids = [node_idx[t] for t in targets_lbl]

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=30, thickness=25,  # node ใหญ่ขึ้น
            label=all_nodes.tolist(),
            line=dict(color="black", width=1.0),
            font=dict(color="black", size=18, family="Tahoma")  # ฟอนต์ใหญ่ชัด
        ),
        link=dict(source=source_ids, target=target_ids, value=values)
    )])

# ========== Show Chart ==========
st.plotly_chart(fig, use_container_width=True)

# ดาวน์โหลด HTML
html = fig.to_html(include_plotlyjs="cdn", full_html=True)
st.download_button("💾 ดาวน์โหลด Sankey เป็น HTML", data=html, file_name="sankey.html", mime="text/html")
