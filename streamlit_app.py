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
col_old  = st.selectbox("คอลัมน์ Source (ฝ่ายเดิม)", df.columns)
col_new  = st.selectbox("คอลัมน์ Target (ฝ่ายใหม่)", df.columns)
col_name = st.selectbox("คอลัมน์ชื่อบุคคล (ใช้ในโหมดแสดงชื่อ)", ["—ไม่ใช้—"] + list(df.columns))
col_val  = st.selectbox("คอลัมน์ Value (จำนวน)", ["—ไม่ใช้—"] + list(df.columns))

mode = st.radio("โหมดแสดงผล", ["ซ่อนชื่อ (ระดับฝ่าย)", "แสดงชื่อบุคคล"], horizontal=True)

# ========== Filter (with Select All) ==========
c1, c2 = st.columns(2)

with c1:
    all_old = sorted(df[col_old].dropna().unique())
    sel_all_old = st.checkbox("เลือกทั้งหมด (ฝ่ายเดิม)", value=True, key="sel_all_old")
    sel_old = st.multiselect(
        "เลือกฝ่ายเดิม",
        all_old,
        default=all_old if sel_all_old else [],
        key="old_multi"
    )

with c2:
    all_new = sorted(df[col_new].dropna().unique())
    sel_all_new = st.checkbox("เลือกทั้งหมด (ฝ่ายใหม่)", value=True, key="sel_all_new")
    sel_new = st.multiselect(
        "เลือกฝ่ายใหม่",
        all_new,
        default=all_new if sel_all_new else [],
        key="new_multi"
    )

# ถ้า checkbox ติ๊กทั้งหมด แต่ user ไปลบค่าออกหมดใน multiselect ให้กันพังด้วย fallback
if sel_all_old and len(sel_old) == 0:
    sel_old = all_old
if sel_all_new and len(sel_new) == 0:
    sel_new = all_new

# กรองข้อมูล
df = df[df[col_old].isin(sel_old) & df[col_new].isin(sel_new)]
if df.empty:
    st.warning("ไม่มีข้อมูลหลังจากกรอง")
    st.stop()

# ========== Build Sankey ==========
if mode == "ซ่อนชื่อ (ระดับฝ่าย)":
    if col_val != "—ไม่ใช้—":
        # บังคับ value เป็นตัวเลขถ้าเลือกคอลัมน์ Value
        try:
            df[col_val] = pd.to_numeric(df[col_val], errors="coerce")
            flows = df.dropna(subset=[col_val]).groupby([col_old, col_new])[col_val].sum().reset_index(name="count")
        except Exception:
            st.error("คอลัมน์ Value ต้องเป็นประเภทตัวเลข หรือเลือก '—ไม่ใช้—' เพื่อให้นับจำนวนแทน")
            st.stop()
    else:
        flows = df.groupby([col_old, col_new]).size().reset_index(name="count")

    if flows.empty:
        st.warning("ไม่มีข้อมูลสำหรับวาด Sankey")
        st.stop()

    # กำหนด node
    all_nodes = pd.Index(flows[col_old].tolist() + flows[col_new].tolist()).unique()
    node_idx  = {name: i for i, name in enumerate(all_nodes)}
    sources   = [node_idx[s] for s in flows[col_old]]
    targets   = [node_idx[t] for t in flows[col_new]]
    values    = flows["count"].astype(float).tolist()

    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=30, thickness=25,
            label=all_nodes.tolist(),
            line=dict(color="black", width=1.0)  # ไม่มี node.font!
        ),
        link=dict(source=sources, target=targets, value=values)
    )])

else:
    # โหมดแสดงชื่อบุคคล (ค่าลิงก์=1)
    if col_name == "—ไม่ใช้—":
        st.error("กรุณาเลือกคอลัมน์ชื่อบุคคลเพื่อใช้โหมดนี้")
        st.stop()

    d = df.dropna(subset=[col_name]).copy()
    if d.empty:
        st.warning("ไม่มีข้อมูลชื่อบุคคลในคอลัมน์ที่เลือก")
        st.stop()

    d["left_label"] = d[col_old] + " : " + d[col_name]
    sources_lbl = d["left_label"]
    targets_lbl = d[col_new]
    values      = [1] * len(d)

    all_nodes = pd.Index(pd.concat([sources_lbl, targets_lbl]).unique())
    node_idx  = {name: i for i, name in enumerate(all_nodes)}
    source_ids = [node_idx[s] for s in sources_lbl]
    target_ids = [node_idx[t] for t in targets_lbl]

    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=30, thickness=25,
            label=all_nodes.tolist(),
            line=dict(color="black", width=1.0)
        ),
        link=dict(source=source_ids, target=target_ids, value=values)
    )])

# ฟอนต์ใหญ่ ชัดทั้งกราฟ + tooltip ใหญ่ขึ้น
fig.update_layout(
    title="Sankey Diagram",
    font=dict(color="black", size=18, family="Tahoma"),
    paper_bgcolor="white",
    plot_bgcolor="white",
    margin=dict(l=20, r=20, t=60, b=20),
    hoverlabel=dict(font_size=16, font_family="Tahoma")
)

st.plotly_chart(fig, use_container_width=True)

# ดาวน์โหลด HTML
html = fig.to_html(include_plotlyjs="cdn", full_html=True)
st.download_button("💾 ดาวน์โหลด Sankey เป็น HTML", data=html, file_name="sankey.html", mime="text/html")
