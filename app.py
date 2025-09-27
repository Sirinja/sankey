import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Sankey Rotation", layout="wide")

st.title("📊 Sankey Diagram - การโยกย้ายบุคลากร")

uploaded = st.file_uploader("อัปโหลดไฟล์ Excel", type=["xlsx"])
if uploaded:
    sheet_name = "ตารางรายละเอียด"
    data = pd.read_excel(uploaded, sheet_name=sheet_name, header=2)

    COL_OLD  = "ส่วนงานเดิม"
    COL_NAME = "คำนำหน้า ชื่อ - สกุล"
    COL_NEW  = [c for c in data.columns if str(c).startswith("ส่วนงานใหม่")][0]

    df = data[[COL_OLD, COL_NEW, COL_NAME]].dropna(subset=[COL_OLD, COL_NEW])

    # ตัวกรองหลายฝ่าย
    sel_old = st.multiselect("เลือกฝ่ายเดิม", sorted(df[COL_OLD].unique()), default=sorted(df[COL_OLD].unique()))
    sel_new = st.multiselect("เลือกฝ่ายใหม่", sorted(df[COL_NEW].unique()), default=sorted(df[COL_NEW].unique()))

    df = df[df[COL_OLD].isin(sel_old) & df[COL_NEW].isin(sel_new)]

    mode = st.radio("โหมดแสดงผล", ["ซ่อนชื่อ (ระดับฝ่าย)", "แสดงชื่อบุคคล"])

    if mode == "ซ่อนชื่อ (ระดับฝ่าย)":
        flows = (
            df.groupby([COL_OLD, COL_NEW], as_index=False)
              .size()
              .rename(columns={"size": "count"})
        )

        left_order = list(flows.groupby(COL_OLD)["count"].sum().sort_values(ascending=False).index)
        right_order = list(flows.groupby(COL_NEW)["count"].sum().sort_values(ascending=False).index)

        left_index = {name: i for i, name in enumerate(left_order)}
        right_index = {name: i + len(left_order) for i, name in enumerate(right_order)}
        labels = left_order + right_order

        sources = [left_index[o] for o in flows[COL_OLD]]
        targets = [right_index[n] for n in flows[COL_NEW]]
        values  = flows["count"].tolist()

        fig = go.Figure(data=[go.Sankey(
            node=dict(label=labels, pad=18, thickness=18),
            link=dict(source=sources, target=targets, value=values)
        )])

    else:  # แสดงชื่อบุคคล
        df["left_label"] = df[COL_OLD] + " : " + df[COL_NAME]
        sources = df["left_label"]
        targets = df[COL_NEW]
        values  = [1] * len(df)

        all_nodes = pd.Index(pd.concat([sources, targets]).unique())
        node_idx  = {name: i for i, name in enumerate(all_nodes)}

        source_ids = [node_idx[s] for s in sources]
        target_ids = [node_idx[t] for t in targets]

        fig = go.Figure(data=[go.Sankey(
            node=dict(label=all_nodes.tolist(), pad=18, thickness=18),
            link=dict(source=source_ids, target=target_ids, value=values)
        )])

    st.plotly_chart(fig, use_container_width=True)
