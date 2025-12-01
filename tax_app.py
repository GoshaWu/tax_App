import streamlit as st

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="工资条个税审计工具",
    page_icon="🧾",
    layout="centered",  # 居中布局适合单据展示
    initial_sidebar_state="collapsed"
)


# --- 2. 核心计算逻辑 (累计预扣法) ---
def calculate_details(month, gross, social_total, special, slip_tax):
    threshold = 5000.0

    # A. 累计计算
    cum_gross = gross * month
    cum_social = social_total * month
    cum_threshold = threshold * month
    cum_special = special * month
    cum_deduction_total = cum_social + cum_threshold + cum_special
    cum_taxable = max(0, cum_gross - cum_deduction_total)

    # B. 税率判定 (2019版个税税率表)
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

    # C. 模拟已缴 (前 month-1 个月)
    # 注意：这里假设前几个月收入与本月完全一致，这是产生误差的主要原因之一
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


# --- 3. CSS 样式注入 (适配 Shared Streamlit) ---
# 强制表格区域为白底，确保在 Dark Mode 下也能像“纸质工资条”一样清晰
st.markdown("""
<style>
    /* 隐藏右上角菜单，让应用更像原生App */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* 结果卡片数值字体 */
    div[data-testid="stMetricValue"] {
        font-family: "Roboto Mono", Consolas, monospace;
        font-weight: 700;
    }

    /* 审计表格容器 */
    .table-container {
        background-color: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-top: 20px;
        border: 1px solid #e0e0e0;
    }

    /* 表格样式 */
    .audit-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
        color: #333; /* 强制黑色字体 */
    }

    .audit-table th {
        background-color: #f8f9fa;
        text-align: left;
        padding: 12px 8px;
        color: #555;
        font-weight: 600;
        border-bottom: 2px solid #ddd;
    }

    .audit-table td {
        padding: 12px 8px;
        border-bottom: 1px solid #f0f0f0;
        text-align: left; /* 核心需求：左对齐 */
        vertical-align: middle;
    }

    /* 辅助样式类 */
    .font-mono { font-family: "Roboto Mono", Consolas, monospace; font-weight: 600; }
    .text-red { color: #d32f2f; }
    .text-green { color: #2e7d32; }
    .text-note { color: #888; font-size: 12px; font-family: Consolas, monospace; }

    /* 高亮行 */
    .row-highlight { background-color: #e3f2fd; color: #0d47a1; font-weight: 600; }
    .row-final { background-color: #fff3e0; border-top: 2px solid #ffb74d; color: #e65100; font-weight: 700; }

    /* 智能提示框 */
    .smart-tip-box {
        padding: 15px;
        border-radius: 6px;
        margin-bottom: 20px;
        font-size: 14px;
        line-height: 1.5;
    }
    .tip-warn { background-color: #fff3e0; border-left: 5px solid #ff9800; color: #e65100; }
    .tip-info { background-color: #e3f2fd; border-left: 5px solid #2196f3; color: #0d47a1; }
    .tip-success { background-color: #e8f5e9; border-left: 5px solid #4caf50; color: #1b5e20; }

</style>
""", unsafe_allow_html=True)

# --- 4. 界面主逻辑 ---

st.title("🧾 工资条个税审计明细")
st.markdown("部署于 Shared Streamlit • 累计预扣法审计")

# 使用 Form 容器，防止每次输入都自动刷新，提升体验
with st.form("input_form"):
    st.subheader("1. 基础数据")
    c1, c2 = st.columns(2)
    with c1:
        month = st.number_input("当前月份", 1, 12, 11)
    with c2:
        gross_pay = st.number_input("应发合计 (税前)", min_value=0.0, step=100.0, format="%.2f",
                                    help="工资条中未扣除任何费用前的总金额")

    st.subheader("2. 个人扣缴明细")
    c3, c4 = st.columns(2)
    with c3:
        fund = st.number_input("① 住房公积金", 0.0, step=100.0, format="%.2f")
        unemploy = st.number_input("③ 失业保险", 0.0, step=10.0, format="%.2f")
    with c4:
        pension = st.number_input("② 养老保险", 0.0, step=100.0, format="%.2f")
        medical = st.number_input("④ 医疗保险", 0.0, step=10.0, format="%.2f")

    social_total = fund + pension + unemploy + medical
    # 在表单内显示合计不太方便实时更新，这里放到计算结果里显示，或者只用 caption
    st.caption(f"注：三险一金将自动合计计算")

    st.subheader("3. 校验数据")
    c5, c6 = st.columns(2)
    with c5:
        slip_tax = st.number_input("工资条显示的个税", 0.0, step=10.0, format="%.2f")
    with c6:
        special = st.number_input("专项附加扣除", 0.0, step=100.0, format="%.2f",
                                  help="子女教育、赡养老人等。不确定可填0。")

    submitted = st.form_submit_button("生成计算过程明细单", type="primary", use_container_width=True)

# --- 5. 计算结果展示 ---
if submitted:
    if gross_pay == 0:
        st.warning("⚠️ 请输入有效的应发合计金额")
    else:
        # 执行计算
        res = calculate_details(month, gross_pay, social_total, special, slip_tax)

        # --- A. 顶部核心指标 ---
        k1, k2, k3 = st.columns(3)
        k1.metric("工资条显示", f"¥ {slip_tax:,.2f}")
        k2.metric("系统计算", f"¥ {res['current_tax']:,.2f}")
        k3.metric("差额", f"¥ {res['diff']:+,.2f}", delta_color="inverse")

        # --- B. 智能差异分析 (针对您截图中的场景) ---
        diff = res['diff']
        estimated_special = 0
        if res['rate'] > 0:
            estimated_special = abs(diff) / res['rate']

        if abs(diff) < 1.0:
            st.markdown(
                '<div class="smart-tip-box tip-success"><strong>✅ 完美匹配：</strong> 您的工资条个税计算完全正确。</div>',
                unsafe_allow_html=True)

        elif diff > 10:
            # 系统算的高 (Diff > 0) -> 可能是少填了专项扣除
            st.markdown(f"""
            <div class="smart-tip-box tip-warn">
                <strong>💡 智能推断：您可能少填了专项附加扣除</strong><br>
                系统计算值 <strong>(¥{res['current_tax']:.2f})</strong> 高于工资条，这通常意味着您在税务系统有抵扣项未在此处输入。<br>
                👉 根据差额反推，您可能每月有约 <strong>¥ {estimated_special:,.0f}</strong> 的专项附加扣除（如子女教育、赡养老人）。
            </div>
            """, unsafe_allow_html=True)

        elif diff < -10:
            # 系统算的低 (Diff < 0) -> 这就是您截图中 -268.80 的情况
            st.markdown(f"""
            <div class="smart-tip-box tip-info">
                <strong>💡 智能推断：前期收入波动 或 奖金影响</strong><br>
                系统计算值 <strong>(¥{res['current_tax']:.2f})</strong> 低于工资条。这意味着您<strong>前 {month - 1} 个月的实际平均收入可能高于本月</strong>，或者之前发过奖金。<br>
                本工具默认假设您全年每月工资都与本月（¥{gross_pay:,.2f}）相同。由于您前期收入较高，累计税率档位可能提升得比模拟的更快，导致实际扣税更多。
            </div>
            """, unsafe_allow_html=True)


        # --- C. 详细审计表格 ---
        # 格式化助手：处理负数显示格式，将 ¥ -55 变为 - ¥ 55
        def fmt_money(val):
            sign = "-" if val < 0 else ""
            return f"{sign} ¥ {abs(val):,.2f}"


        # 构建数据行
        data_rows = [
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

        rows_html = ""
        for step, name, val, note, cls in data_rows:
            # 如果是负数且不是最终结果行，给文字加红色
            val_cls = "text-red" if (val < 0 and "row-final" not in cls) else "font-mono"
            if "row-final" in cls: val_cls = "font-mono"  # 最终行保持原有颜色

            rows_html += f"""
            <tr class="{cls}">
                <td style="text-align:center; color:#999;">{step}</td>
                <td>{name}</td>
                <td class="{val_cls} font-mono">{fmt_money(val)}</td>
                <td class="text-note">{note}</td>
            </tr>
            """

        st.markdown(f"""
        <div class="table-container">
            <h4 style="margin-top:0; margin-bottom:15px; color:#333;">📋 计算过程明细单</h4>
            <table class="audit-table">
                <thead>
                    <tr>
                        <th style="width:8%; text-align:center">步骤</th>
                        <th style="width:25%">项目名称</th>
                        <th style="width:25%">累计金额 (元)</th>
                        <th style="width:42%">计算过程 / 公式备注</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        """, unsafe_allow_html=True)