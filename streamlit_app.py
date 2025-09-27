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
    sel_old = st.multiselect("เลือกฝ่ายเดิม", all_old, default=all_old if sel_all_old else [], key="old_multi")
with c2:
    all_new = sorted(df[col_new].dropna().unique())
    sel_all_new = st.checkbox("เลือกทั้งหมด (ฝ่ายใหม่)", value=True, key="sel_all_new")
    sel_new = st.multiselect("เลือกฝ่ายใหม่", all_new, default=all_new if sel_all_new else [], key="new_multi")

if sel_all_old and len(sel_old) == 0: sel_old = all_old
if sel_all_new and len(sel_new) == 0: sel_new = all_new

df = df[df[col_old].isin(sel_old) & df[col_new].isin(sel_new)]
if df.empty:
    st.warning("ไม่มีข้อมูลหลังจากกรอง")
    st.stop()

# helper: build sankey
def build_sankey(labels, sources, targets, values):
    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=30, thickness=25,
            label=labels,
            line=dict(color="black", width=1.0)
        ),
        link=dict(source=sources, target=targets, value=values)
    )])
    fig.update_layout(
        title="Sankey Diagram",
        font=dict(color="black", size=18, family="Tahoma"),
        paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(l=20, r=20, t=60, b=20),
        hoverlabel=dict(font_size=16, font_family="Tahoma")
    )
    return fig

# ========== Build Sankey ==========
if mode == "ซ่อนชื่อ (ระดับฝ่าย)":
    # รวมจำนวน (ใช้ col_val ถ้ากำหนด, ไม่งั้นนับจำนวน)
    if col_val != "—ไม่ใช้—":
        try:
            df[col_val] = pd.to_numeric(df[col_val], errors="coerce")
            flows = df.dropna(subset=[col_val]).groupby([col_old, col_new])[col_val].sum().reset_index(name="count")
        except Exception:
            st.error("คอลัมน์ Value ต้องเป็นตัวเลข หรือเลือก '—ไม่ใช้—' เพื่อให้นับจำนวนแทน")
            st.stop()
    else:
        flows = df.groupby([col_old, col_new]).size().reset_index(name="count")

    if flows.empty:
        st.warning("ไม่มีข้อมูลสำหรับวาด Sankey")
        st.stop()

    # totals per side
    left_totals = flows.groupby(col_old)["count"].sum().sort_values(ascending=False)
    right_totals = flows.groupby(col_new)["count"].sum().sort_values(ascending=False)

    left_order  = list(left_totals.index)
    right_order = list(right_totals.index)

    # labels with totals shown
    left_labels  = [f"{n} ({int(left_totals[n])})" for n in left_order]
    right_labels = [f"{n} ({int(right_totals[n])})" for n in right_order]
    labels = left_labels + right_labels

    # index maps
    left_index  = {name: i for i, name in enumerate(left_order)}
    right_index = {name: i + len(left_order) for i, name in enumerate(right_order)}

    sources = [left_index[s] for s in flows[col_old]]
    targets = [right_index[t] for t in flows[col_new]]
    values  = flows["count"].astype(float).tolist()

    fig = build_sankey(labels, sources, targets, values)
    st.plotly_chart(fig, use_container_width=True)

    # Top flows table
    st.subheader("🔢 Top flows")
    topk = st.slider("จำนวนแถวที่แสดง", 5, 50, 20, 5)
    st.dataframe(
        flows.sort_values("count", ascending=False).head(topk).rename(
            columns={col_old: "ฝ่ายเดิม", col_new: "ฝ่ายใหม่", "count": "จำนวน"}
        ),
        use_container_width=True
    )

else:
    # โหมดแสดงชื่อบุคคล: ลิงก์ value=1 แต่โชว์ยอดรวมบน “ฝ่ายใหม่”
    if col_name == "—ไม่ใช้—":
        st.error("กรุณาเลือกคอลัมน์ชื่อบุคคลเพื่อใช้โหมดนี้")
        st.stop()

    d = df.dropna(subset=[col_name]).copy()
    if d.empty:
        st.warning("ไม่มีข้อมูลชื่อบุคคลในคอลัมน์ที่เลือก")
        st.stop()

    d["left_label"] = d[col_old] + " : " + d[col_name]

    # totals for right side (ฝ่ายใหม่)
    right_totals = d.groupby(col_new).size().sort_values(ascending=False)
    right_order  = list(right_totals.index)
    right_labels = [f"{n} ({int(right_totals[n])})" for n in right_order]

    # left nodes are individuals (ไม่ใส่วงเล็บจำนวนเพื่อไม่ให้รก)
    left_order  = list(pd.Index(d["left_label"]).unique())
    left_labels = left_order

    labels = left_labels + right_labels
    left_index  = {name: i for i, name in enumerate(left_order)}
    right_index = {name: i + len(left_order) for i, name in enumerate(right_order)}

    sources = [left_index[s] for s in d["left_label"]]
    targets = [right_index[t] for t in d[col_new]]
    values  = [1.0] * len(d)

    fig = build_sankey(labels, sources, targets, values)
    st.plotly_chart(fig, use_container_width=True)

    # Top flows (รายชื่อ → ฝ่ายใหม่)
    st.subheader("🔢 Top flows")
    topk = st.slider("จำนวนแถวที่แสดง", 5, 50, 20, 5, key="topk_names")
    flows_names = (
        d.groupby(["left_label", col_new]).size().reset_index(name="count")
          .sort_values("count", ascending=False)
    )
    st.dataframe(
        flows_names.head(topk).rename(columns={"left_label": "ชื่อ (ฝ่ายเดิม)", col_new: "ฝ่ายใหม่", "count": "จำนวน"}),
        use_container_width=True
    )

# ดาวน์โหลด HTML
html = fig.to_html(include_plotlyjs="cdn", full_html=True)
st.download_button("💾 ดาวน์โหลด Sankey เป็น HTML", data=html, file_name="sankey.html", mime="text/html")
