import streamlit as st

def calculate_tax(month, monthly_income, monthly_deduction, special_deduction):
    """
    核心算法：累计预扣法 (2019版个税)
    假设前提：前 month-1 个月的收入和扣除项与本月一致
    """
    threshold = 5000.0 # 基本减除费用
    
    # 1. 计算累计应纳税所得额
    cumulative_income = monthly_income * month
    cumulative_deduction = (monthly_deduction + threshold + special_deduction) * month
    cumulative_taxable_income = max(0, cumulative_income - cumulative_deduction)
    
    # 2. 定义税率表 (级数, 税率, 速算扣除数)
    brackets = [
        (36000, 0.03, 0),
        (144000, 0.10, 2520),
        (300000, 0.20, 16920),
        (420000, 0.25, 31920),
        (660000, 0.30, 52920),
        (960000, 0.35, 85920),
        (float('inf'), 0.45, 181920),
    ]
    
    rate = 0.03
    quick_deduction = 0
    for limit, r, q in brackets:
        if cumulative_taxable_income <= limit:
            rate = r
            quick_deduction = q
            break
            
    # 3. 计算本年累计应纳税额
    total_tax_year = (cumulative_taxable_income * rate) - quick_deduction
    
    # 4. 模拟前 (month-1) 个月的已缴税额 (反推本月应缴)
    if month > 1:
        prev_income = monthly_income * (month - 1)
        prev_deduc_total = (monthly_deduction + threshold + special_deduction) * (month - 1)
        prev_taxable = max(0, prev_income - prev_deduc_total)
        
        p_rate = 0.03
        p_quick = 0
        for limit, r, q in brackets:
            if prev_taxable <= limit:
                p_rate = r
                p_quick = q
                break
        prev_tax_paid = (prev_taxable * p_rate) - p_quick
    else:
        prev_tax_paid = 0
        
    current_month_tax = total_tax_year - prev_tax_paid
    
    return {
        "current_tax": current_month_tax,
        "cumulative_taxable": cumulative_taxable_income,
        "rate": rate,
        "year_total_tax": total_tax_year,
        "prev_paid": prev_tax_paid
    }

# --- Streamlit UI 界面 ---

st.set_page_config(page_title="工资条个税计算器", page_icon="🧮")

st.title("🧮 工资条个税校验工具")
st.markdown("本工具采用**累计预扣法**计算，只需手动输入工资条上的数据，即可快速验证个税是否准确。")

# 使用表单容器，让布局更紧凑
with st.container():
    st.subheader("1. 数据录入")
    
    col1, col2 = st.columns(2)

    with col1:
        month = st.number_input("当前月份", min_value=1, max_value=12, value=11, step=1)
        gross_pay = st.number_input("应发合计 (税前收入)", value=0.0, format="%.2f", help="工资条中金额最大的一项，未扣除任何费用前的总额")

        st.markdown("---")
        st.markdown("**👇 个人扣缴明细 (请按顺序填写)**")
        
        # 按您要求的顺序调整
        fund = st.number_input("1. 住房公积金", value=0.0, format="%.2f")
        pension = st.number_input("2. 养老保险", value=0.0, format="%.2f")
        unemploy = st.number_input("3. 失业保险", value=0.0, format="%.2f")
        medical = st.number_input("4. 医疗保险", value=0.0, format="%.2f")
        
        # 自动计算三险一金总和
        social_total = fund + pension + unemploy + medical
        st.info(f"🧾 个人社保公积金扣除合计: **¥{social_total:.2f}**")

    with col2:
        slip_tax = st.number_input("工资条显示的个税 (目标值)", value=0.0, format="%.2f", help="用于和系统计算结果进行比对")
        
        st.markdown("---")
        st.warning("👇 **关键项：专项附加扣除**")
        special_deduction = st.number_input(
            "专项附加扣除总额", 
            value=0.0, 
            step=100.0, 
            format="%.2f",
            help="包括子女教育、老人赡养、房贷利息、租金等。工资条通常不显示此项，但它直接决定税额。"
        )
        st.caption("💡 如果不确定具体金额，先填 0，计算后系统会尝试帮您反推。")

# 计算按钮
if st.button("开始计算与校验", type="primary", use_container_width=True):
    if gross_pay <= 0:
        st.error("请填写有效的应发合计金额")
    else:
        # 执行计算
        res = calculate_tax(month, gross_pay, social_total, special_deduction)
        
        sys_tax = res["current_tax"]
        diff = sys_tax - slip_tax
        
        st.divider()
        st.subheader("2. 校验结果")
        
        # 结果展示指标卡
        c1, c2, c3 = st.columns(3)
        c1.metric("工资条个税", f"¥ {slip_tax:.2f}")
        c2.metric("系统计算个税", f"¥ {sys_tax:.2f}")
        c3.metric("差额", f"¥ {diff:.2f}", delta_color="inverse")
        
        if abs(diff) < 1.0:
            st.success("✅ **校验通过！** 您的工资条个税计算完全正确。")
        else:
            st.error(f"⚠️ **存在差异**")
            
            # 智能分析差异原因
            st.markdown("#### 🕵️ 差异分析与建议")
            
            estimated_special = 0
            if res["rate"] > 0:
                estimated_special = diff / res["rate"]

            if special_deduction == 0 and diff > 0 and estimated_special > 500:
                st.info(f"""
                **推测原因：未录入专项附加扣除。**
                
                根据 **{diff:.2f}元** 的税额差异和您当前的税率 (**{res['rate']*100:.0f}%**)，
                您可能在个人所得税APP中申报了约 **¥{estimated_special:.0f}** 元的专项附加扣除（如子女教育、赡养老人等）。
                
                👉 请尝试在上方“专项附加扣除总额”中填入 **{estimated_special:.0f}**，然后重新计算。
                """)
            else:
                 st.markdown(f"""
                 **可能的原因：**
                 1. **收入波动**：本工具假设您前 {month-1} 个月的工资与本月完全一致。如果之前有奖金或缺勤，累计税率会有偏差。
                 2. **免税项**：检查应发合计中是否包含了通讯费、差旅费等免税补贴。
                 """)

        # 详细计算折叠面板
        with st.expander("查看详细计算过程 (累计预扣法)"):
            st.write(f"""
            | 项目 | 金额/说明 |
            | :--- | :--- |
            | **累计月份** | {month} 个月 |
            | **累计应发收入** | ¥{gross_pay * month:,.2f} |
            | **(-) 累计减除费用** | ¥{5000 * month:,.2f} |
            | **(-) 累计社保公积金** | ¥{social_total * month:,.2f} |
            | **(-) 累计专项附加扣除** | ¥{special_deduction * month:,.2f} |
            | **(=) 累计应纳税所得额** | **¥{res['cumulative_taxable']:,.2f}** |
            | **(×) 适用税率** | {res['rate']*100:.0f}% (速算扣除数 {2520 if res['rate']==0.1 else 0}) |
            | **(=) 累计应纳税额** | ¥{res['year_total_tax']:,.2f} |
            | **(-) 模拟已缴税额** | ¥{res['prev_paid']:,.2f} |
            | **(=) 本月实缴个税** | **¥{sys_tax:,.2f}** |
            """)