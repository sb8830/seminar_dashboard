import io
import re
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Invesmate Seminar Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
#MainMenu, footer, header {visibility:hidden;}
.stApp {background: linear-gradient(180deg, #0a0f1c 0%, #0d1322 100%);}
.block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 1500px;}
.hero {
    background: linear-gradient(135deg, rgba(99,102,241,.18), rgba(6,182,212,.12));
    border: 1px solid rgba(99,102,241,.22);
    border-radius: 20px;
    padding: 20px 24px;
    margin-bottom: 14px;
}
.hero-title {font-size: 28px; font-weight: 800; color: #e5e7eb; letter-spacing: -.02em; margin-bottom: 4px;}
.hero-sub {color: #94a3b8; font-size: 13px;}
.kpi-card {
    background: linear-gradient(180deg, #121a2c 0%, #0f1728 100%);
    border: 1px solid rgba(148,163,184,.14);
    border-radius: 18px;
    padding: 16px 18px;
    box-shadow: 0 10px 30px rgba(2,6,23,.22);
}
.kpi-label {color: #94a3b8; font-size: 11px; text-transform: uppercase; letter-spacing: .08em; font-weight: 700;}
.kpi-value {color: #f8fafc; font-size: 30px; font-weight: 800; margin: 5px 0 3px; letter-spacing: -.03em;}
.kpi-sub {color: #94a3b8; font-size: 11px;}
.section {margin-top: 12px; margin-bottom: 10px; color: #e2e8f0; font-size: 16px; font-weight: 800; border-left: 4px solid #6366f1; padding-left: 10px;}
.filter-shell {
    background: rgba(15,23,42,.72);
    border: 1px solid rgba(148,163,184,.14);
    border-radius: 18px;
    padding: 14px 16px 8px 16px;
    margin-bottom: 14px;
}
.filter-title {color: #e2e8f0; font-size: 14px; font-weight: 800; margin-bottom: 8px;}
</style>
""", unsafe_allow_html=True)

COMBO_COURSE = "Power Of Trading & Investing Combo Course"
CHART_COLORS = [
    "#6366f1", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b",
    "#ef4444", "#f97316", "#ec4899", "#14b8a6", "#a855f7",
    "#3b82f6", "#84cc16",
]
CREDENTIALS = {"admin": "admin123", "invesmate": "invesmate@2024"}

def clean_mobile(x):
    if pd.isna(x):
        return None
    s = re.sub(r"\D", "", str(x))
    return s[-10:] if len(s) >= 10 else None

def parse_date_series(series):
    for fmt in ["%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%b-%d-%Y", "%d %b %Y"]:
        try:
            return pd.to_datetime(series, format=fmt, errors="coerce")
        except Exception:
            pass
    return pd.to_datetime(series, errors="coerce", dayfirst=True)

def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce").fillna(0.0)

def fmt_inr(n):
    try:
        n = float(n)
        if n >= 1e7:
            return f"₹{n/1e7:.2f}Cr"
        if n >= 1e5:
            return f"₹{n/1e5:.2f}L"
        return f"₹{n:,.0f}"
    except Exception:
        return "₹0"

def detect_col(df, candidates):
    norm = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        key = cand.strip().lower()
        if key in norm:
            return norm[key]
    return None

def load_excel_or_csv(file_obj, filename=None):
    name = (filename or "").lower()
    try:
        if name.endswith(".csv"):
            try:
                return pd.read_csv(file_obj)
            except Exception:
                file_obj.seek(0)
                return pd.read_csv(file_obj, encoding="latin1")
        if name.endswith((".xlsx", ".xls")):
            return pd.read_excel(file_obj, sheet_name=0)
        try:
            return pd.read_excel(file_obj, sheet_name=0)
        except Exception:
            file_obj.seek(0)
            try:
                return pd.read_csv(file_obj)
            except Exception:
                file_obj.seek(0)
                return pd.read_csv(file_obj, encoding="latin1")
    except Exception as e:
        try:
            file_obj.seek(0)
        except Exception:
            pass
        raise ValueError(f"Could not read {filename or 'uploaded file'}: {e}") from e

def kpi_card(label, value, sub="", accent="#6366f1"):
    return f'''
    <div class="kpi-card" style="border-top:3px solid {accent}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-sub">{sub}</div>
    </div>'''

def safe_unique(series):
    vals = pd.Series(series).dropna().astype(str).str.strip()
    vals = vals[~vals.isin(["", "nan", "None", "NaT"])]
    return sorted(vals.unique().tolist())

def build_filter_row(df, columns, key_prefix):
    work = df.copy()
    cols = st.columns(len(columns))
    for i, col in enumerate(columns):
        vals = safe_unique(work[col]) if col in work.columns else []
        with cols[i]:
            if len(vals) <= 25:
                choice = st.multiselect(col, vals, key=f"{key_prefix}_{col}")
                if choice:
                    work = work[work[col].astype(str).isin(choice)]
            else:
                text = st.text_input(col, key=f"{key_prefix}_{col}")
                if text:
                    work = work[work[col].astype(str).str.contains(text, case=False, na=False)]
    return work

@st.cache_data(show_spinner=False)
def process_data(sem_bytes, conv_bytes, leads_bytes, sem_name, conv_name, leads_name):
    sem = load_excel_or_csv(io.BytesIO(sem_bytes), sem_name)
    sem.columns = [str(c).strip() for c in sem.columns]

    c_mobile = detect_col(sem, ["Mobile", "Phone", "mobile", "phone", "Contact"])
    c_name = detect_col(sem, ["NAME", "Name", "Student Name", "name"])
    c_place = detect_col(sem, ["Place", "Location", "Venue", "City", "place"])
    c_trainer = detect_col(sem, ["Trainer / Presenter", "Trainer", "Presenter", "trainer"])
    c_semdate = detect_col(sem, ["Seminar Date", "Date", "seminar_date", "Event Date"])
    c_session = detect_col(sem, ["Session", "session", "Batch", "Time"])
    c_attended = detect_col(sem, ["Is Attended ?", "Attended", "is_attended", "attended"])

    sem["mobile_clean"] = sem[c_mobile].apply(clean_mobile) if c_mobile else None
    sem["seminar_date"] = parse_date_series(sem[c_semdate]) if c_semdate else pd.NaT
    sem["attended_flag"] = sem[c_attended].astype(str).str.strip().str.upper().isin(["YES", "TRUE", "1", "Y"]) if c_attended else False
    attendees = sem[sem["attended_flag"]].copy().reset_index(drop=True)

    conv = load_excel_or_csv(io.BytesIO(conv_bytes), conv_name)
    conv.columns = [str(c).strip() for c in conv.columns]

    cc_mobile = detect_col(conv, ["phone", "Phone", "mobile", "Mobile", "Contact"])
    cc_service = detect_col(conv, ["service_name", "Service Name", "Course", "course_name", "ServiceName"])
    cc_orderdt = detect_col(conv, ["order_date", "Order Date", "OrderDate", "Date"])
    cc_payrec = detect_col(conv, ["payment_received", "Payment Received", "PaymentReceived", "amount_paid"])
    cc_gst = detect_col(conv, ["total_gst", "GST", "gst", "TotalGST"])
    cc_due = detect_col(conv, ["total_due", "Due", "total_due_amount", "TotalDue"])
    cc_trainer = detect_col(conv, ["trainer", "Trainer"])
    cc_salesrep = detect_col(conv, ["sales_rep_name", "Sales Rep", "SalesRep", "sales_rep"])
    cc_mode = detect_col(conv, ["payment_mode", "Payment Mode", "mode"])
    cc_status = detect_col(conv, ["status", "Status"])
    cc_orderid = detect_col(conv, ["orderID", "Order ID", "order_id", "OrderId"])

    conv["mobile_clean"] = conv[cc_mobile].apply(clean_mobile) if cc_mobile else None
    conv["order_date_clean"] = pd.to_datetime(conv[cc_orderdt], errors="coerce", utc=True).dt.tz_localize(None) if cc_orderdt else pd.NaT
    conv["payment_received"] = safe_numeric(conv[cc_payrec]) if cc_payrec else 0.0
    conv["total_gst"] = safe_numeric(conv[cc_gst]) if cc_gst else 0.0
    conv["total_due"] = safe_numeric(conv[cc_due]) if cc_due else 0.0
    conv["paid_amount"] = conv["payment_received"]
    conv["service_name_clean"] = conv[cc_service].astype(str).str.strip() if cc_service else ""
    conv["trainer_clean"] = conv[cc_trainer].astype(str).str.strip() if cc_trainer else ""
    conv["sales_rep_clean"] = conv[cc_salesrep].astype(str).str.strip() if cc_salesrep else ""
    conv["payment_mode_clean"] = conv[cc_mode].astype(str).str.strip() if cc_mode else ""
    conv["status_clean"] = conv[cc_status].astype(str).str.strip() if cc_status else ""
    conv["order_id_clean"] = conv[cc_orderid].astype(str).str.strip() if cc_orderid else ""

    leads = load_excel_or_csv(io.BytesIO(leads_bytes), leads_name)
    leads.columns = [str(c).strip() for c in leads.columns]

    lc_mobile = detect_col(leads, ["phone", "Phone", "mobile", "Mobile"])
    lc_convfrom = detect_col(leads, ["converted_from", "ConvertedFrom", "lead_type", "LeadType"])
    lc_source = detect_col(leads, ["leadsource", "lead_source", "LeadSource", "Source"])
    lc_campaign = detect_col(leads, ["campaign_name", "Campaign", "CampaignName"])
    lc_status = detect_col(leads, ["leadstatus", "lead_status", "LeadStatus", "Status"])
    lc_stage = detect_col(leads, ["stage_name", "StageName", "Stage"])
    lc_owner = detect_col(leads, ["leadownername", "LeadOwner", "lead_owner", "Owner"])
    lc_state = detect_col(leads, ["state", "State", "Province"])
    lc_attempted = detect_col(leads, ["Attempted/Unattempted", "attempted", "Attempted"])
    lc_service = detect_col(leads, ["servicename", "ServiceName", "service_name"])
    lc_email = detect_col(leads, ["email", "Email"])
    lc_remarks = detect_col(leads, ["remarks", "Remarks", "Notes"])
    lc_name = detect_col(leads, ["name", "Name", "StudentName"])

    leads["mobile_clean"] = leads[lc_mobile].apply(clean_mobile) if lc_mobile else None
    lead_map = leads.drop_duplicates("mobile_clean").set_index("mobile_clean") if lc_mobile else pd.DataFrame()

    def get_lead(mob):
        blank = {
            "webinar_type": "", "lead_source": "", "campaign_name": "", "lead_status": "",
            "stage_name": "", "lead_owner": "", "state": "", "attempted": "",
            "service_name_lead": "", "email": "", "remarks": "", "lead_name": ""
        }
        if not mob or lead_map.empty or mob not in lead_map.index:
            return blank
        r = lead_map.loc[mob]
        if isinstance(r, pd.DataFrame):
            r = r.iloc[0]
        def gs(col):
            return str(r[col]).strip() if col and col in r.index and pd.notna(r[col]) else ""
        wt = gs(lc_convfrom)
        if not wt:
            src = gs(lc_source)
            wt = "Webinar" if "WBN" in src.upper() else ("Non Webinar" if src else "")
        blank.update({
            "webinar_type": wt,
            "lead_source": gs(lc_source),
            "campaign_name": gs(lc_campaign),
            "lead_status": gs(lc_status),
            "stage_name": gs(lc_stage),
            "lead_owner": gs(lc_owner),
            "state": gs(lc_state),
            "attempted": gs(lc_attempted),
            "service_name_lead": gs(lc_service),
            "email": gs(lc_email),
            "remarks": gs(lc_remarks),
            "lead_name": gs(lc_name),
        })
        return blank

    attendee_rows, order_rows = [], []

    for _, row in attendees.iterrows():
        mob = row["mobile_clean"]
        sem_dt = row["seminar_date"]
        entry = {
            "name": str(row.get(c_name, "")).strip() if c_name else "",
            "mobile": mob or "",
            "place": str(row.get(c_place, "")).strip() if c_place else "",
            "trainer": str(row.get(c_trainer, "")).strip() if c_trainer else "",
            "seminar_date": sem_dt,
            "session": str(row.get(c_session, "")).strip().upper() if c_session else "",
            "attended": True,
            "primary_course": "",
            "primary_order_date": pd.NaT,
            "primary_paid": 0.0,
            "primary_due": 0.0,
            "primary_gst": 0.0,
            "primary_mode": "",
            "primary_status": "",
            "converted": False,
            "trainer_conv": "",
            "sales_rep": "",
            "additional_courses": [],
            "additional_paid": 0.0,
            "additional_orders": [],
        }

        valid = pd.DataFrame()
        if mob and pd.notna(sem_dt):
            valid = conv[(conv["mobile_clean"] == mob) & (conv["order_date_clean"] >= sem_dt)].sort_values("order_date_clean")

        if not valid.empty:
            entry["converted"] = True
            combo = valid[valid["service_name_clean"].str.contains("Power Of Trading", na=False, case=False)]
            primary = combo.iloc[0] if not combo.empty else valid.iloc[0]

            entry["primary_course"] = primary["service_name_clean"]
            entry["primary_order_date"] = primary["order_date_clean"]
            entry["primary_paid"] = float(primary["paid_amount"])
            entry["primary_due"] = float(primary["total_due"])
            entry["primary_gst"] = float(primary["total_gst"])
            entry["primary_mode"] = str(primary["payment_mode_clean"]).strip()
            entry["primary_status"] = str(primary["status_clean"]).strip()
            entry["trainer_conv"] = str(primary["trainer_clean"]).strip()
            entry["sales_rep"] = str(primary["sales_rep_clean"]).strip()

            others = valid[valid.index != primary.name].copy()
            entry["additional_courses"] = list(others["service_name_clean"].dropna().astype(str).str.strip().unique())
            entry["additional_paid"] = float(others["paid_amount"].sum())
            entry["additional_orders"] = others[["service_name_clean", "order_date_clean", "paid_amount", "total_due", "total_gst", "payment_mode_clean", "status_clean", "order_id_clean"]].rename(columns={
                "service_name_clean": "course",
                "order_date_clean": "order_date",
                "payment_mode_clean": "payment_mode",
                "status_clean": "status",
                "order_id_clean": "order_id",
            }).to_dict("records")

            for _, o in valid.iterrows():
                order_rows.append({
                    "mobile": mob or "",
                    "name": entry["name"],
                    "place": entry["place"],
                    "trainer": entry["trainer"],
                    "seminar_date": sem_dt,
                    "session": entry["session"],
                    "course": o["service_name_clean"],
                    "order_date": o["order_date_clean"],
                    "paid_amount": float(o["paid_amount"]),
                    "total_due": float(o["total_due"]),
                    "total_gst": float(o["total_gst"]),
                    "payment_mode": str(o["payment_mode_clean"]).strip(),
                    "status": str(o["status_clean"]).strip(),
                    "sales_rep": str(o["sales_rep_clean"]).strip(),
                    "trainer_conv": str(o["trainer_clean"]).strip(),
                    "is_primary": bool(o.name == primary.name),
                    "order_id": str(o["order_id_clean"]).strip(),
                })

        entry.update(get_lead(mob))
        attendee_rows.append(entry)

    attendees_df = pd.DataFrame(attendee_rows)
    orders_df = pd.DataFrame(order_rows)

    if not attendees_df.empty:
        attendees_df["seminar_date_str"] = pd.to_datetime(attendees_df["seminar_date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
        attendees_df["primary_order_date_str"] = pd.to_datetime(attendees_df["primary_order_date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
        attendees_df["due_zero"] = safe_numeric(attendees_df["primary_due"]) <= 0
        attendees_df["additional_course_count"] = attendees_df["additional_courses"].apply(lambda x: len(x) if isinstance(x, list) else 0)
    else:
        attendees_df = pd.DataFrame(columns=[
            "name", "mobile", "place", "trainer", "seminar_date", "session", "attended",
            "primary_course", "primary_order_date", "primary_paid", "primary_due", "primary_gst",
            "primary_mode", "primary_status", "converted", "trainer_conv", "sales_rep",
            "additional_courses", "additional_paid", "additional_orders", "webinar_type",
            "lead_source", "campaign_name", "lead_status", "stage_name", "lead_owner", "state",
            "attempted", "service_name_lead", "email", "remarks", "lead_name",
            "seminar_date_str", "primary_order_date_str", "due_zero", "additional_course_count",
        ])

    if not orders_df.empty:
        orders_df["seminar_date_str"] = pd.to_datetime(orders_df["seminar_date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
        orders_df["order_date_str"] = pd.to_datetime(orders_df["order_date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
        orders_df["due_zero"] = safe_numeric(orders_df["total_due"]) <= 0
        attendees_meta = attendees_df[["mobile", "webinar_type", "lead_source", "campaign_name", "lead_status", "stage_name", "lead_owner", "state", "attempted", "email", "remarks"]].drop_duplicates("mobile")
        orders_df = orders_df.merge(attendees_meta, on="mobile", how="left")

    return attendees_df, orders_df

def login_page():
    st.markdown('<div class="hero" style="max-width:460px;margin:90px auto 18px auto;"><div class="hero-title">Invesmate Analytics</div><div class="hero-sub">Seminar performance dashboard</div></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.1, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
            if submitted:
                if CREDENTIALS.get(username) == password:
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("Invalid credentials.")

def upload_page():
    st.markdown('<div class="hero"><div class="hero-title">Upload your 3 source files</div><div class="hero-sub">Seminar Updated Sheet → Conversion List → Leads Report</div></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        sem_file = st.file_uploader("📋 Seminar Updated Sheet", type=["xlsx", "xls", "csv"], key="sem_file")
    with c2:
        conv_file = st.file_uploader("💰 Conversion List", type=["xlsx", "xls", "csv"], key="conv_file")
    with c3:
        leads_file = st.file_uploader("🎯 Leads Report", type=["xlsx", "xls", "csv"], key="leads_file")
    if sem_file and conv_file and leads_file:
        if st.button("Build dashboard", use_container_width=True, type="primary"):
            with st.spinner("Processing files..."):
                attendees_df, orders_df = process_data(sem_file.read(), conv_file.read(), leads_file.read(), sem_file.name, conv_file.name, leads_file.name)
            st.session_state["attendees_df"] = attendees_df
            st.session_state["orders_df"] = orders_df
            st.session_state["files_loaded"] = True
            st.rerun()
    else:
        missing = []
        if not sem_file: missing.append("Seminar Sheet")
        if not conv_file: missing.append("Conversion List")
        if not leads_file: missing.append("Leads Report")
        st.info("Waiting for: " + ", ".join(missing))

def render_master_filters(df):
    st.markdown('<div class="filter-shell"><div class="filter-title">Unified master filters</div></div>', unsafe_allow_html=True)
    r1 = st.columns(4)
    dates = ["All Dates"] + safe_unique(df["seminar_date_str"])
    sel_date = r1[0].selectbox("Seminar date", dates, key="flt_date")
    date_min = df["seminar_date"].dropna().min().date() if df["seminar_date"].notna().any() else date.today()
    date_max = df["seminar_date"].dropna().max().date() if df["seminar_date"].notna().any() else date.today()
    sel_range = r1[1].date_input("Date range", value=(date_min, date_max), min_value=date_min, max_value=date_max, key="flt_range")
    sel_place = r1[2].multiselect("Location / Place", safe_unique(df["place"]), key="flt_place")
    sel_session = r1[3].multiselect("Session", safe_unique(df["session"]), key="flt_session")
    r2 = st.columns(4)
    sel_trainer = r2[0].multiselect("Trainer", safe_unique(df["trainer"]), key="flt_trainer")
    sel_conv = r2[1].selectbox("Converted status", ["All", "Converted", "Not Converted"], key="flt_conv")
    sel_course = r2[2].multiselect("Primary course", safe_unique(df["primary_course"]), key="flt_course")
    add_courses_all = sorted({c for lst in df["additional_courses"] for c in (lst if isinstance(lst, list) else []) if c})
    sel_additional = r2[3].multiselect("Additional course", add_courses_all, key="flt_additional")
    r3 = st.columns(4)
    sel_due = r3[0].selectbox("Due filter", ["All", "Due = 0", "Has Due"], key="flt_due")
    paid_max = int(df["primary_paid"].max()) if not df["primary_paid"].empty and df["primary_paid"].max() > 0 else 100000
    sel_paid = r3[1].slider("Paid amount (₹)", 0, paid_max, (0, paid_max), step=1000, key="flt_paid")
    sel_lead_type = r3[2].multiselect("Lead type", safe_unique(df["webinar_type"]), key="flt_leadtype")
    sel_source = r3[3].multiselect("Lead source", safe_unique(df["lead_source"]), key="flt_source")
    r4 = st.columns(4)
    sel_campaign = r4[0].multiselect("Campaign", safe_unique(df["campaign_name"]), key="flt_campaign")
    sel_status = r4[1].multiselect("Lead status", safe_unique(df["lead_status"]), key="flt_lstatus")
    sel_stage = r4[2].multiselect("Stage name", safe_unique(df["stage_name"]), key="flt_stage")
    sel_owner = r4[3].multiselect("Lead owner", safe_unique(df["lead_owner"]), key="flt_owner")
    r5 = st.columns(4)
    sel_state = r5[0].multiselect("State", safe_unique(df["state"]), key="flt_state")
    sel_attempt = r5[1].multiselect("Attempted", safe_unique(df["attempted"]), key="flt_attempt")
    reset = r5[3].button("Reset filters", use_container_width=True)
    if reset:
        for k in list(st.session_state.keys()):
            if k.startswith("flt_"):
                del st.session_state[k]
        st.rerun()
    fdf = df.copy()
    if sel_date != "All Dates":
        fdf = fdf[fdf["seminar_date_str"] == sel_date]
    if isinstance(sel_range, (tuple, list)) and len(sel_range) == 2:
        start_dt = pd.Timestamp(sel_range[0]); end_dt = pd.Timestamp(sel_range[1])
        fdf = fdf[(fdf["seminar_date"] >= start_dt) & (fdf["seminar_date"] <= end_dt)]
    if sel_place: fdf = fdf[fdf["place"].isin(sel_place)]
    if sel_session: fdf = fdf[fdf["session"].isin(sel_session)]
    if sel_trainer: fdf = fdf[fdf["trainer"].isin(sel_trainer)]
    if sel_conv == "Converted": fdf = fdf[fdf["converted"]]
    elif sel_conv == "Not Converted": fdf = fdf[~fdf["converted"]]
    if sel_course: fdf = fdf[fdf["primary_course"].isin(sel_course)]
    if sel_additional: fdf = fdf[fdf["additional_courses"].apply(lambda xs: any(x in xs for x in sel_additional) if isinstance(xs, list) else False)]
    if sel_due == "Due = 0": fdf = fdf[fdf["primary_due"] <= 0]
    elif sel_due == "Has Due": fdf = fdf[fdf["primary_due"] > 0]
    fdf = fdf[(fdf["primary_paid"] >= sel_paid[0]) & (fdf["primary_paid"] <= sel_paid[1])]
    if sel_lead_type: fdf = fdf[fdf["webinar_type"].isin(sel_lead_type)]
    if sel_source: fdf = fdf[fdf["lead_source"].isin(sel_source)]
    if sel_campaign: fdf = fdf[fdf["campaign_name"].isin(sel_campaign)]
    if sel_status: fdf = fdf[fdf["lead_status"].isin(sel_status)]
    if sel_stage: fdf = fdf[fdf["stage_name"].isin(sel_stage)]
    if sel_owner: fdf = fdf[fdf["lead_owner"].isin(sel_owner)]
    if sel_state: fdf = fdf[fdf["state"].isin(sel_state)]
    if sel_attempt: fdf = fdf[fdf["attempted"].isin(sel_attempt)]
    return fdf

def filter_orders_by_attendees(orders_df, attendees_df):
    if orders_df.empty or attendees_df.empty:
        return orders_df.iloc[0:0].copy()
    keep = attendees_df["mobile"].dropna().astype(str).unique().tolist()
    return orders_df[orders_df["mobile"].astype(str).isin(keep)].copy()

def render_kpis(fdf):
    conv = fdf[fdf["converted"]]
    total = len(fdf); n_conv = len(conv)
    rate = f"{(n_conv / total * 100):.1f}%" if total else "0%"
    t_paid = conv["primary_paid"].sum(); t_due = conv["primary_due"].sum()
    fully_paid = len(conv[conv["primary_due"] <= 0]); has_due = len(conv[conv["primary_due"] > 0])
    uniq_courses = conv["primary_course"].replace("", pd.NA).dropna().nunique()
    wbn = len(fdf[fdf["webinar_type"] == "Webinar"]); non_wbn = len(fdf[fdf["webinar_type"] == "Non Webinar"])
    row1 = st.columns(5)
    row1[0].markdown(kpi_card("Total attendees", total, "Filtered seminar attendees"), unsafe_allow_html=True)
    row1[1].markdown(kpi_card("Converted", n_conv, "Valid post-seminar conversions", "#10b981"), unsafe_allow_html=True)
    row1[2].markdown(kpi_card("Conversion rate", rate, "Attend → purchase", "#06b6d4"), unsafe_allow_html=True)
    row1[3].markdown(kpi_card("Paid amount", fmt_inr(t_paid), "Exclusive GST", "#f59e0b"), unsafe_allow_html=True)
    row1[4].markdown(kpi_card("Total due", fmt_inr(t_due), "Outstanding due", "#ef4444"), unsafe_allow_html=True)
    row2 = st.columns(5)
    row2[0].markdown(kpi_card("Fully paid", fully_paid, "Due ≤ 0", "#10b981"), unsafe_allow_html=True)
    row2[1].markdown(kpi_card("Has due", has_due, "Pending balance", "#ef4444"), unsafe_allow_html=True)
    row2[2].markdown(kpi_card("Unique courses", uniq_courses, "Primary courses", "#8b5cf6"), unsafe_allow_html=True)
    row2[3].markdown(kpi_card("Webinar leads", wbn, "Mapped from leads", "#06b6d4"), unsafe_allow_html=True)
    row2[4].markdown(kpi_card("Non-webinar leads", non_wbn, "Mapped from leads", "#f97316"), unsafe_allow_html=True)

def render_overview(fdf):
    st.markdown('<div class="section">Overview</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    bydate = fdf.groupby("seminar_date_str", dropna=False).agg(Attendees=("attended", "count"), Converted=("converted", "sum")).reset_index().sort_values("seminar_date_str")
    with c1:
        fig = go.Figure()
        fig.add_bar(x=bydate["seminar_date_str"], y=bydate["Attendees"], name="Attendees", marker_color="#6366f1", opacity=.72)
        fig.add_bar(x=bydate["seminar_date_str"], y=bydate["Converted"], name="Converted", marker_color="#10b981", opacity=.9)
        fig.update_layout(template="plotly_dark", title="Attendees & conversions by seminar date", barmode="group", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=320, margin=dict(t=45, l=10, r=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    byloc = fdf.groupby("place").agg(Attendees=("attended", "count"), Converted=("converted", "sum"), Paid=("primary_paid", "sum")).reset_index().sort_values("Attendees", ascending=False).head(12)
    with c2:
        fig = go.Figure()
        fig.add_bar(x=byloc["place"], y=byloc["Attendees"], name="Attendees", marker_color="#6366f1", opacity=.72)
        fig.add_bar(x=byloc["place"], y=byloc["Converted"], name="Converted", marker_color="#10b981", opacity=.9)
        fig.update_layout(template="plotly_dark", title="Location-wise attendees & conversions", barmode="group", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=320, margin=dict(t=45, l=10, r=10, b=30))
        st.plotly_chart(fig, use_container_width=True)

def render_course_analysis(fdf, orders_fdf):
    st.markdown('<div class="section">Course analysis</div>', unsafe_allow_html=True)
    conv = fdf[fdf["converted"]].copy()
    if conv.empty:
        st.info("No converted students in current filters.")
        return
    byc = conv.groupby("primary_course").agg(Students=("mobile", "nunique"), Paid=("primary_paid", "sum"), Due=("primary_due", "sum"), Due0=("due_zero", "sum")).reset_index().sort_values("Students", ascending=False)
    total_students = byc["Students"].sum()
    byc["Share %"] = (byc["Students"] / total_students * 100).round(1)
    byc["Avg Paid"] = (byc["Paid"] / byc["Students"]).round(0)
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(byc.head(12), x="Students", y="primary_course", orientation="h", color="Students", color_continuous_scale=["#1e2d4a", "#6366f1"], title="Course-wise student count")
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=380, margin=dict(t=45, l=10, r=10, b=10), yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.pie(byc.head(10), names="primary_course", values="Students", hole=.38, color_discrete_sequence=CHART_COLORS, title="Course share for selected seminar")
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", height=380, margin=dict(t=45, l=10, r=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

def render_combo_analysis(fdf, orders_fdf):
    st.markdown('<div class="section">Power Of Trading & Investing Combo → other course buyers</div>', unsafe_allow_html=True)
    combo_buyers = fdf[fdf["primary_course"].str.contains("Power Of Trading", na=False, case=False)].copy()
    with_other = combo_buyers[combo_buyers["additional_course_count"] > 0].copy()
    cross_rate = f"{(len(with_other) / len(combo_buyers) * 100):.1f}%" if len(combo_buyers) else "0%"
    stats = st.columns(4)
    stats[0].markdown(kpi_card("Combo buyers", len(combo_buyers)), unsafe_allow_html=True)
    stats[1].markdown(kpi_card("Bought other courses", len(with_other), accent="#10b981"), unsafe_allow_html=True)
    stats[2].markdown(kpi_card("Cross-sell rate", cross_rate, accent="#06b6d4"), unsafe_allow_html=True)
    stats[3].markdown(kpi_card("Additional paid", fmt_inr(with_other["additional_paid"].sum()), "Exclusive GST", "#f59e0b"), unsafe_allow_html=True)

def render_lead_intelligence(fdf):
    st.markdown('<div class="section">Lead intelligence</div>', unsafe_allow_html=True)
    show = fdf[["name", "mobile", "place", "seminar_date_str", "converted", "primary_course", "primary_paid", "webinar_type", "lead_source", "campaign_name", "lead_status", "stage_name", "lead_owner", "state", "attempted", "service_name_lead", "lead_name", "email", "remarks"]].copy()
    show["converted"] = show["converted"].map({True: "Yes", False: "No"})
    show["primary_paid"] = show["primary_paid"].apply(lambda x: fmt_inr(x) if x > 0 else "—")
    show.columns = ["Name", "Mobile", "Location", "Seminar Date", "Converted", "Primary Course", "Paid", "Lead Type", "Lead Source", "Campaign", "Lead Status", "Stage", "Owner", "State", "Attempted", "Lead Service", "Lead Name", "Email", "Remarks"]
    filtered = build_filter_row(show, list(show.columns), "leadtbl")
    st.dataframe(filtered, use_container_width=True, hide_index=True, height=450)

def render_student_journey(fdf):
    st.markdown('<div class="section">Student journey</div>', unsafe_allow_html=True)
    show = fdf[["name", "mobile", "seminar_date_str", "place", "session", "trainer", "attended", "primary_course", "primary_order_date_str", "primary_paid", "primary_due", "additional_courses", "webinar_type", "lead_source", "lead_status", "stage_name", "lead_owner"]].copy()
    show["attended"] = show["attended"].map({True: "Yes"})
    show["primary_paid"] = show["primary_paid"].apply(lambda x: fmt_inr(x) if x > 0 else "—")
    show["primary_due"] = show["primary_due"].apply(lambda x: fmt_inr(x) if x > 0 else "₹0")
    show["additional_courses"] = show["additional_courses"].apply(lambda x: " | ".join(x) if isinstance(x, list) and x else "—")
    show.columns = ["Name", "Mobile", "Seminar Date", "Location", "Session", "Trainer", "Attended", "Primary Course", "Order Date", "Paid", "Due", "Additional Courses", "Lead Type", "Lead Source", "Lead Status", "Stage", "Owner"]
    st.dataframe(show, use_container_width=True, hide_index=True, height=500)

def render_data_tables(fdf, orders_fdf):
    st.markdown('<div class="section">Data tables</div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Attendee master", "Orders"])
    with tab1:
        st.dataframe(fdf, use_container_width=True, hide_index=True, height=420)
    with tab2:
        st.dataframe(orders_fdf, use_container_width=True, hide_index=True, height=420)

def main():
    if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
    if "files_loaded" not in st.session_state: st.session_state["files_loaded"] = False
    if "attendees_df" not in st.session_state: st.session_state["attendees_df"] = None
    if "orders_df" not in st.session_state: st.session_state["orders_df"] = None
    if not st.session_state["logged_in"]:
        login_page(); return
    st.markdown('<div class="hero"><div class="hero-title">Invesmate Seminar Analytics</div><div class="hero-sub">Attendee-first tracking: offline seminar → post-seminar conversion → lead intelligence</div></div>', unsafe_allow_html=True)
    toolbar = st.columns([1, 1, 5])
    if toolbar[0].button("Upload / reload data", use_container_width=True):
        st.session_state["files_loaded"] = False; st.session_state["attendees_df"] = None; st.session_state["orders_df"] = None; st.rerun()
    if toolbar[1].button("Logout", use_container_width=True):
        st.session_state["logged_in"] = False; st.session_state["files_loaded"] = False; st.session_state["attendees_df"] = None; st.session_state["orders_df"] = None; st.rerun()
    if not st.session_state["files_loaded"] or st.session_state["attendees_df"] is None:
        upload_page(); return
    df = st.session_state["attendees_df"]
    orders_df = st.session_state["orders_df"] if st.session_state["orders_df"] is not None else pd.DataFrame()
    fdf = render_master_filters(df)
    orders_fdf = filter_orders_by_attendees(orders_df, fdf)
    if fdf.empty:
        st.warning("No data matches current filters."); return
    tabs = st.tabs(["Overview", "Course Analysis", "Combo Cross-Sell", "Lead Intelligence", "Student Journey", "Data Tables"])
    with tabs[0]:
        render_kpis(fdf); st.markdown("---"); render_overview(fdf)
    with tabs[1]:
        render_course_analysis(fdf, orders_fdf)
    with tabs[2]:
        render_combo_analysis(fdf, orders_fdf)
    with tabs[3]:
        render_lead_intelligence(fdf)
    with tabs[4]:
        render_student_journey(fdf)
    with tabs[5]:
        render_data_tables(fdf, orders_fdf)

if __name__ == "__main__":
    main()
