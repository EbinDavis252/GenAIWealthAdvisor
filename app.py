import streamlit as st
import plotly.express as px
import pandas as pd
import requests
from fpdf import FPDF
from io import BytesIO

# ---------------------- 1.  API / Secrets -----------------------
api_key   = st.secrets["openrouter_api_key"]
model_name = st.secrets["openrouter_model"]
api_base   = "https://openrouter.ai/api/v1"
headers    = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type":  "application/json"
}

# ---------------------- 2.  UI Helpers --------------------------
def login_section() -> None:
    st.sidebar.subheader("🔐 Simulated Login")
    email = st.sidebar.text_input("Enter your email")
    if st.sidebar.button("Login"):
        st.session_state["user"] = {"email": email}
        st.success(f"✅ Logged in as {email}")

def get_portfolio_allocation(risk: str) -> dict:
    return {
        "Low":    {"Equity": 30, "Debt": 60, "Gold": 10},
        "Medium": {"Equity": 50, "Debt": 40, "Gold": 10},
        "High":   {"Equity": 70, "Debt": 20, "Gold": 10},
    }[risk]

def explain_portfolio(allocation: dict, age: int, risk: str, goal: str) -> str:
    prompt = (
        f"Act like a professional financial advisor. "
        f"Explain this portfolio allocation for a {age}-year-old with {risk} risk tolerance. "
        f"Goal: {goal}. "
        f"Allocation: Equity {allocation['Equity']}%, "
        f"Debt {allocation['Debt']}%, Gold {allocation['Gold']}%."
    )
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are a helpful financial advisor."},
            {"role": "user",   "content": prompt}
        ]
    }
    try:
        resp = requests.post(f"{api_base}/chat/completions",
                             headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"🔌 LLM error: {e}")
        return "Sorry, I couldn’t fetch the explanation right now."

# ---------------------- 3.  PDF Generator -----------------------
def generate_pdf_bytes(name: str, age: int, income: int, risk: str,
                       goal: str, allocation: dict, explanation: str,
                       mip_info: dict | None = None) -> BytesIO:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Wealth Advisor Report", ln=True, align="C")
    pdf.set_font("Arial", size=12)

    # Profile Info
    pdf.ln(6)
    pdf.multi_cell(0, 8, f"Name: {name}    Age: {age}    Monthly Income: ₹{income:,}")
    pdf.multi_cell(0, 8, f"Risk Tolerance: {risk}    Goal: {goal}")

    # Allocation
    pdf.ln(4)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Portfolio Allocation:", ln=True)
    pdf.set_font("Arial", size=12)
    for asset, pct in allocation.items():
        pdf.cell(0, 8, f"- {asset}: {pct}%", ln=True)

    # Explanation
    pdf.ln(4)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Advisor’s Explanation:", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 8, explanation)

    # Monthly Investment Plan
    if mip_info:
        pdf.ln(4)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Monthly Investment Plan:", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 8, (
            f"Target Corpus: ₹{mip_info['future_value']:,}\n"
            f"Invest ₹{mip_info['monthly']:,} per month "
            f"for {mip_info['years']} years at "
            f"{mip_info['rate']}% expected return."
        ))

    # ✅ Fixed: Output PDF as bytes
    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    return BytesIO(pdf_bytes)

# ---------------------- 4.  Streamlit App -----------------------
st.set_page_config(page_title="GenAI Wealth Advisor", page_icon="💼")
st.title("💼 GenAI-Based Wealth Advisor Chatbot")

# Login
login_section()
if "user" not in st.session_state:
    st.stop()

# Profile inputs
st.subheader("👤 Profile Details")
age           = st.slider("Age", 18, 70, 30)
income        = st.number_input("Monthly Income (₹)", value=50_000, step=1_000)
risk_tolerance = st.selectbox("Risk Tolerance", ["Low", "Medium", "High"])
goal          = st.text_input("Primary Goal (e.g., retirement, house)")

# ----------------------------------------------------------------
# ▶ Generate Portfolio Button
# ----------------------------------------------------------------
if st.button("🔍 Generate Portfolio"):
    allocation = get_portfolio_allocation(risk_tolerance)

    # Donut Chart
    fig = px.pie(
        names=list(allocation.keys()),
        values=list(allocation.values()),
        title="Your Investment Allocation",
        hole=0.4,
        color_discrete_sequence=px.colors.sequential.RdBu
    )
    st.plotly_chart(fig, use_container_width=True)

    # LLM Explanation
    explanation = explain_portfolio(allocation, age, risk_tolerance, goal)
    st.markdown("### 📘 Advisor's Explanation")
    st.write(explanation)

    # ---------------- Monthly Investment Plan -------------------
    st.subheader("📈 Monthly Investment Plan")
    rate   = st.slider("Expected Annual Return (%)", 6.0, 15.0, 12.0)
    years  = st.slider("Investment Duration (Years)", 1, 40, 10)
    months = years * 12
    monthly_rate = rate / 100 / 12

    target_corpus = st.number_input("Target Corpus (₹)", value=4_500_000, step=50_000)
    monthly = target_corpus * monthly_rate / ((1 + monthly_rate)**months - 1)
    monthly = int(round(monthly, 0))
    st.success(
        f"To reach ₹{target_corpus:,} in {years} years at {rate}% return, "
        f"invest **₹{monthly:,}/month**."
    )

    mip_info = {
        "monthly":     monthly,
        "years":       years,
        "rate":        rate,
        "future_value": target_corpus
    }

    # ---------------- CAGR Table -----------------------
    st.subheader("📉 CAGR Estimates")
    cagr_data = {
        "Asset":        ["Equity", "Debt", "Gold"],
        "1 Year (%)":   [22.5, 6.2, 12.1],
        "3 Year (%)":   [18.3, 5.9, 11.4],
        "5 Year (%)":   [14.7, 6.0, 10.6]
    }
    df_cagr = pd.DataFrame(cagr_data)
    st.dataframe(df_cagr, use_container_width=True)

    avg_5yr = round(df_cagr["5 Year (%)"].mean(), 2)
    st.info(f"📊 Average 5-Year CAGR across assets: **{avg_5yr}%**")

    # ---------------- PDF Generation ---------------------------
    st.markdown("---")
    if st.button("📄 Generate PDF Report"):
        pdf_bytes = generate_pdf_bytes(
            name="User",
            age=age,
            income=income,
            risk=risk_tolerance,
            goal=goal,
            allocation=allocation,
            explanation=explanation,
            mip_info=mip_info
        )
        st.download_button(
            "📥 Download PDF",
            data=pdf_bytes,
            file_name="Wealth_Report.pdf",
            mime="application/pdf"
        )

    # ---------------- Feedback -------------------------
    st.subheader("⭐ Rate Your Experience")
    rating = st.selectbox(
        "How would you rate this output?",
        ["Select", "Excellent", "Good", "Average", "Poor"]
    )
    if rating != "Select":
        st.success("🎉 Thank you for your feedback! You may restart the app now.")
        if st.button("🔄 Restart"):
            st.session_state.clear()
            st.experimental_rerun()
