import streamlit as st

# --- 配置页面 ---
st.set_page_config(page_title="工资条个税审计工具", page_icon="💰", layout="centered")

# --- 注入 CSS 样式 (复刻 HTML 版本的精美外观) ---
st.markdown("""
<style>
    /* 全局字体 */
    .main { font-family: "Segoe UI", sans-serif; }

    /* 结果卡片样式 */
    div[data-testid="stMetricValue"] { font-family: Consolas, monospace; }

    /* 自定义审计表格样式 */
    .audit-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 15px;
        margin-top: 20px;
        border: 1px solid #e1e4e8;
    }
    .audit-table th {
        background-color: #f1f3f5;
        text-align: left; /* 表头左对齐 */
        padding: 12px;
        color: #666;
        font-weight: bold;
        border-bottom: 2px solid #ddd;
    }
    .audit-table td {
        padding: 10px 12px;
        border-bottom: 1px solid #eee;
        text-align: left; /* 核心需求：左对齐 */
        vertical-align: middle;
    }

    /* 字体与颜色 */
    .font-mono { font-family: Consolas, Monaco, monospace; font-weight: 600; color: #333; }
    .text-red { color: #c0392b; }
    .text-note { color: #888; font-size: 13px; font-family: Consolas, monospace; }

    /* 高亮行 */
    .row-highlight { background-color: #f0f9ff; color: #0066cc; font-weight: bold; }
    .row-final { background-color: #fff8e6; border-top: 2px solid #ffe58f; color: #856404; font-weight: bold; }

    /* 智能提示框 */
    .smart-tip {
        background-color: #fffbe6;
        border: 1px solid #ffe58f;
        padding: 15px;
        border-radius: 5px;
        color: #856404;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)


# --- 核心计算逻辑 ---
def calculate_details(month, gross, social_total, special, slip_tax):
    threshold = 5000.0

    # 1. 累计计算
    cum_gross = gross * month
    cum_social = social_total * month
    cum_threshold = threshold * month
    cum_special = special * month
    cum_deduction_total = cum_social + cum_threshold + cum_special
    cum_taxable = max(0, cum_gross - cum_deduction_total)

    # 2. 税率判定
    brackets = [
        (36000, 0.03, 0), (144000, 0.10, 2520), (300000, 0.20, 16920),
        (420000, 0.25, 31920), (660000, 0.30, 52920), (960000, 0.35, 85920),
        (float('inf'), 0.45, 181920),
    ]

    rate = 0.03
    quick = 0
    for limit, r, q in brackets:
        if cum_taxable <= limit:
            rate = r
            quick = q
            break

    cum_tax_payable = (cum_taxable * rate) - quick

    # 3. 模拟已缴 (前 month-1 个月)
    prev_paid = 0
    if month > 1:
        prev_gross = gross * (month - 1)
        prev_deduc = (social_total + threshold + special) * (month - 1)
        prev_taxable = max(0, prev_gross - prev_deduc)

        p_rate = 0.03
        p_quick = 0
        for limit, r, q in brackets:
            if prev_taxable <= limit:
                p_rate = r
                p_quick = q
                break
        prev_paid = (prev_taxable * p_rate) - p_quick

    current_tax = cum_tax_payable - prev_paid
    diff = current_tax - slip_tax

    return {
        "cum_gross": cum_gross,
        "cum_threshold": cum_threshold,
        "cum_social": cum_social,
        "cum_special": cum_special,
        "cum_taxable": cum_taxable,
        "rate": rate,
        "quick": quick,
        "cum_tax_payable": cum_tax_payable,
        "prev_paid": prev_paid,
        "current_tax": current_tax,
        "diff": diff
    }


# --- 界面布局 ---

st.title("💰 工资条个税审计工具")
st.markdown("数据透明 • 计算合规 • 结果精确 (Python Pro版)")

with st.container():
    st.subheader("1. 基础数据")
    c1, c2 = st.columns(2)
    with c1:
        month = st.number_input("当前月份", 1, 12, 11)
    with c2:
        # 需求：placeholder 改为 "例如 8000" (Streamlit placeholder 仅在空时显示，这里用 help 或 label 提示)
        gross_pay = st.number_input("应发合计 (税前)", min_value=0.0, step=100.0, format="%.2f", help="例如 8000")

    st.subheader("2. 个人扣缴明细 (按顺序填写)")
    # 需求：严格顺序 1.公积金 2.养老 3.失业 4.医疗
    c3, c4 = st.columns(2)
    with c3:
        fund = st.number_input("① 住房公积金", 0.0, step=10.0, format="%.2f")
    with c4:
        pension = st.number_input("② 养老保险", 0.0, step=10.0, format="%.2f")

    c5, c6 = st.columns(2)
    with c5:
        unemploy = st.number_input("③ 失业保险", 0.0, step=10.0, format="%.2f")
    with c6:
        medical = st.number_input("④ 医疗保险", 0.0, step=10.0, format="%.2f")

    social_total = fund + pension + unemploy + medical
    st.caption(f"🧾 三险一金合计: **¥ {social_total:,.2f}**")

    st.subheader("3. 校验与调节")
    c7, c8 = st.columns(2)
    with c7:
        slip_tax = st.number_input("工资条显示的个税", 0.0, step=10.0, format="%.2f")
    with c8:
        st.markdown("**★ 专项附加扣除 (关键)**")
        special = st.number_input("专项附加扣除", 0.0, step=100.0, format="%.2f", label_visibility="collapsed",
                                  help="如果不确定，先填0，系统会自动反推")

# --- 计算按钮与结果 ---
if st.button("生成计算过程明细单", type="primary", use_container_width=True):
    if gross_pay == 0:
        st.error("请填写应发合计")
    else:
        # 执行计算
        res = calculate_details(month, gross_pay, social_total, special, slip_tax)

        st.divider()

        # 1. 顶部 KPI 卡片
        k1, k2, k3 = st.columns(3)
        k1.metric("工资条显示", f"¥ {slip_tax:,.2f}")
        k2.metric("系统计算", f"¥ {res['current_tax']:,.2f}")
        k3.metric("差额", f"¥ {res['diff']:+,.2f}", delta_color="inverse")

        # 2. 智能提示 (Smart Tip)
        estimated = 0
        if res['rate'] > 0:
            estimated = res['diff'] / res['rate']

        if special == 0 and res['diff'] > 10 and estimated > 500:
            st.markdown(f"""
            <div class="smart-tip">
                <strong>💡 智能推断：</strong><br>
                系统算出税额偏高。根据 <strong>{res['diff']:.2f}元</strong> 的差额，您可能少填了约 
                <strong>¥ {estimated:,.0f}</strong> 的专项附加扣除（如子女教育、赡养老人）。
            </div>
            """, unsafe_allow_html=True)


        # 3. 详细审计表格 (HTML渲染，确保左对齐和样式)
        # 格式化助手
        def fmt(n):
            return f"¥ {n:,.2f}"


        rows_html = ""
        data = [
            ("1", "累计应发工资", res['cum_gross'], f"月薪 {gross_pay:,.2f} × {month}个月", ""),
            ("2", "(-) 累计基本减除", -res['cum_threshold'], f"5000 × {month}个月", "text-red"),
            ("3", "(-) 累计社保公积金", -res['cum_social'], f"个人月缴 {social_total:,.2f} × {month}个月", "text-red"),
            ("4", "(-) 累计专项附加", -res['cum_special'], f"申报额 {special:,.2f} × {month}个月", "text-red"),
            ("5", "(=) 累计应纳税所得额", res['cum_taxable'], "累计收入 - 上述扣除项", "row-highlight"),
            ("6", "累计应纳税额", res['cum_tax_payable'],
             f"累计基数 × {res['rate'] * 100:.0f}% - 速算扣除数{res['quick']}", "row-highlight"),
            ("7", "(-) 模拟已缴税额", -res['prev_paid'], f"前 {month - 1} 个月估算已缴", "text-red"),
            ("8", "(=) 本月应补(退)税", res['current_tax'], "累计应纳 - 已缴", "row-final"),
        ]

        for step, name, val, note, cls in data:
            val_style = "color:#c0392b" if (val < 0 and "row-final" not in cls) else ""
            rows_html += f"""
            <tr class="{cls}">
                <td style="text-align:center">{step}</td>
                <td>{name}</td>
                <td class="font-mono" style="{val_style}">{fmt(val)}</td>
                <td class="text-note">{note}</td>
            </tr>
            """

        st.markdown(f"""
        <h4>📊 计算过程明细单</h4>
        <table class="audit-table">
            <thead>
                <tr>
                    <th style="width:8%; text-align:center">步骤</th>
                    <th style="width:25%">项目名称</th>
                    <th style="width:25%">累计金额 (元)</th> <th style="width:42%">计算过程 / 公式备注</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """, unsafe_allow_html=True)