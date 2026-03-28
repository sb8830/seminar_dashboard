import io
import re
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Invesmate Seminar Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# THEME
# ─────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}
.stApp {
    background:
      radial-gradient(circle at top right, rgba(99,102,241,.14), transparent 28%),
      radial-gradient(circle at top left, rgba(6,182,212,.10), transparent 24%),
      linear-gradient(180deg, #08101d 0%, #0b1220 100%);
}
.block-container {padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1500px;}
.kpi-card {
    background: linear-gradient(180deg, rgba(19,25,41,.96), rgba(12,18,32,.96));
    border: 1px solid rgba(99,102,241,.14);
    border-radius: 18px;
    padding: 18px 18px;
    text-align: left;
    border-top: 3px solid var(--accent, #6366f1);
    box-shadow: 0 14px 32px rgba(2,6,23,.25);
}
.kpi-label {
    font-size: 11px;
    color: #7f8aa3;
    text-transform: uppercase;
    letter-spacing: .08em;
    font-weight: 700;
}
.kpi-value {
    font-size: 30px;
    font-weight: 800;
    color: #edf2ff;
    margin: 6px 0 3px;
    letter-spacing: -.03em;
}
.kpi-sub {font-size: 11px; color: #94a3b8;}
.section-header {
    font-size: 16px;
    font-weight: 800;
    color: #eef2ff;
    border-left: 4px solid #6366f1;
    padding-left: 12px;
    margin: 6px 0 16px 0;
}
.hero {
    background: linear-gradient(135deg, rgba(99,102,241,.18), rgba(6,182,212,.12));
    border: 1px solid rgba(99,102,241,.22);
    border-radius: 20px;
    padding: 20px 24px;
    margin-bottom: 14px;
}
.hero-title {font-size: 28px; font-weight: 800; color: #e5e7eb; margin-bottom: 4px;}
.hero-sub {color: #94a3b8; font-size: 13px;}
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
[data-testid="stDateInputField"] {
    background: rgba(15,23,42,.88) !important;
    border: 1px solid rgba(148,163,184,.14) !important;
    border-radius: 12px !important;
}
label[data-testid="stWidgetLabel"] {
    color: #94a3b8 !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: .06em !important;
}
.stMultiSelect [data-baseweb="tag"] {
    background: rgba(99,102,241,.16) !important;
    border: 1px solid rgba(99,102,241,.25) !important;
    border-radius: 999px !important;
}
button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, #6366f1, #7c3aed) !important;
    border: none !important;
    border-radius: 12px !important;
    color: white !important;
    font-weight: 700 !important;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    border-bottom: 1px solid rgba(148,163,184,.12);
}
.stTabs [data-baseweb="tab"] {
    background: rgba(15,23,42,.55);
    border-radius: 12px 12px 0 0;
    color: #94a3b8;
    font-weight: 700;
    padding: .7rem 1rem;
}
.stTabs [aria-selected="true"] {
    color: #eef2ff !important;
    background: rgba(99,102,241,.15) !important;
    border-bottom: 2px solid #6366f1 !important;
}
[data-testid="stDataFrame"] {
    border: 1px solid rgba(148,163,184,.10);
    border-radius: 16px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

CHART_COLORS = [
    "#6366f1", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b",
    "#ef4444", "#f97316", "#ec4899", "#14b8a6", "#a855f7",
    "#3b82f6", "#84cc16",
]
PTI_MATCH = "Power Of Trading & Investing Combo Course"
CREDENTIALS = {"admin": "admin123", "invesmate": "invesmate@2024"}

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
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
    return pd.to_datetime(series, dayfirst=True, errors="coerce")

def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)

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
        raise ValueError(f"Error reading file ({filename}): {e}") from e

def detect_col(df, candidates, required=False):
    norm = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        key = cand.strip().lower()
        if key in norm:
            return norm[key]
    if required:
        st.warning(f"Missing column from candidates: {candidates}")
    return None

def normalize_status(raw):
    raw = str(raw).strip().lower()
    if raw in ["active", "success", "completed", "paid"]:
        return "Active"
    if raw in ["inactive", "cancelled", "canceled", "failed", "refund", "refunded"]:
        return "Inactive"
    return raw.title() if raw else ""

def kpi_card(label, value, sub="", accent="#6366f1"):
    return f"""
    <div class="kpi-card" style="border-top-color:{accent}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-sub">{sub}</div>
    </div>"""

def render_section_student_details(title, df, extra_cols=None, key_prefix="sec"):
    st.markdown(f'<div class="section-header">👥 {title} — Student Details</div>', unsafe_allow_html=True)
    if df is None or df.empty:
        st.info("No student records available for the current filters.")
        return

    base_cols = [
        "name", "mobile", "place", "seminar_date_str", "session", "trainer",
        "seat_book_amount", "converted", "primary_course", "primary_order_date_str",
        "primary_paid", "primary_due", "primary_status", "webinar_type", "lead_source",
        "lead_status", "stage_name", "lead_owner"
    ]
    cols = [c for c in base_cols if c in df.columns]
    if extra_cols:
        for c in extra_cols:
            if c in df.columns and c not in cols:
                cols.append(c)

    show = df[cols].copy()
    if "converted" in show.columns:
        show["converted"] = show["converted"].map({True: "✅ Yes", False: "❌ No"})
    for c in ["seat_book_amount", "primary_paid"]:
        if c in show.columns:
            show[c] = show[c].apply(lambda x: fmt_inr(x) if pd.notna(x) and float(x) > 0 else "—")
    if "primary_due" in show.columns:
        show["primary_due"] = show["primary_due"].apply(lambda x: fmt_inr(x) if pd.notna(x) and float(x) > 0 else "₹0")
    if "additional_courses" in show.columns:
        show["additional_courses"] = show["additional_courses"].apply(lambda x: " | ".join(x) if isinstance(x, list) and x else "—")

    rename_map = {
        "name": "Name", "mobile": "Mobile", "place": "Location", "seminar_date_str": "Seminar Date",
        "session": "Session", "trainer": "Trainer", "seat_book_amount": "Seat Book Amt",
        "converted": "Converted", "primary_course": "Primary Course", "primary_order_date_str": "Order Date",
        "primary_paid": "Paid", "primary_due": "Due", "primary_status": "Status",
        "webinar_type": "Lead Type", "lead_source": "Lead Source", "lead_status": "Lead Status",
        "stage_name": "Stage", "lead_owner": "Owner", "additional_courses": "Additional Courses",
        "email": "Email", "remarks": "Remarks"
    }
    show = show.rename(columns=rename_map)

    search = st.text_input(f"Search in {title} student details", key=f"{key_prefix}_search")
    if search:
        mask = show.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
        show = show[mask]

    st.caption(f"{len(show)} students")
    st.dataframe(show, use_container_width=True, hide_index=True, height=380)
    st.download_button(
        f"⬇️ Download {title} Students CSV",
        show.to_csv(index=False).encode(),
        f"{key_prefix}_students.csv",
        "text/csv",
        key=f"{key_prefix}_dl"
    )

# ─────────────────────────────────────────────
# DATA PROCESSING
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def process_data(sem_bytes, conv_bytes, leads_bytes, sem_name, conv_name, leads_name):
    sem = load_excel_or_csv(io.BytesIO(sem_bytes), sem_name)
    sem.columns = [str(c).strip() for c in sem.columns]

    c_mobile = detect_col(sem, ["Mobile", "Phone", "mobile", "phone", "Contact"])
    c_altmob = detect_col(sem, ["Alternate Number", "Alt Mobile", "alternate_number", "Alternate Mobile", "Alternative Mobile"])
    c_name = detect_col(sem, ["NAME", "Name", "Student Name", "name"])
    c_place = detect_col(sem, ["Place", "Location", "Venue", "City", "place"])
    c_trainer = detect_col(sem, ["Trainer / Presenter", "Trainer", "Presenter", "trainer"])
    c_semdate = detect_col(sem, ["Seminar Date", "Date", "seminar_date", "Event Date"])
    c_session = detect_col(sem, ["Session", "session", "Batch", "Time"])
    c_attended = detect_col(sem, ["Is Attended ?", "Attended", "is_attended", "attended"])
    c_amount = detect_col(sem, ["Amount Paid", "amount paid", "Seat Book Amount", "Seat Amount", "Seminar Amount", "Amount"])

    sem["mobile_clean"] = sem[c_mobile].apply(clean_mobile) if c_mobile else None
    sem["alt_mobile_clean"] = sem[c_altmob].apply(clean_mobile) if c_altmob else None
    sem["seminar_date"] = parse_date_series(sem[c_semdate]) if c_semdate else pd.NaT
    sem["seat_book_amount"] = safe_numeric(sem[c_amount]) if c_amount else 0
    sem["attended_flag"] = sem[c_attended].astype(str).str.strip().str.upper().isin(["YES", "TRUE", "1", "Y"]) if c_attended else False

    attendees = sem[
        (
            sem["attended_flag"] |
            (sem["seat_book_amount"] > 0)
        ) & (
            sem["mobile_clean"].notna() |
            sem["alt_mobile_clean"].notna()
        )
    ].copy().reset_index(drop=True)

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
    conv["payment_received"] = safe_numeric(conv[cc_payrec]) if cc_payrec else 0
    conv["total_gst"] = safe_numeric(conv[cc_gst]) if cc_gst else 0
    conv["total_due"] = safe_numeric(conv[cc_due]) if cc_due else 0
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

    def get_lead(possible_mobiles):
        blank = {
            "webinar_type": "", "lead_source": "", "campaign_name": "", "lead_status": "",
            "stage_name": "", "lead_owner": "", "state": "", "attempted": "",
            "service_name_lead": "", "email": "", "remarks": "", "lead_name": ""
        }
        if lead_map.empty:
            return blank

        for mob in possible_mobiles:
            if mob and mob in lead_map.index:
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
                break
        return blank

    rows, order_rows = [], []

    for _, row in attendees.iterrows():
        mob = row.get("mobile_clean")
        alt_mob = row.get("alt_mobile_clean")
        possible_mobiles = [m for m in [mob, alt_mob] if m]
        sem_dt = row["seminar_date"]

        entry = {
            "name": str(row.get(c_name, "")).strip() if c_name else "",
            "mobile": mob or alt_mob or "",
            "primary_mobile": mob or "",
            "alternate_mobile": alt_mob or "",
            "place": str(row.get(c_place, "")).strip() if c_place else "",
            "trainer": str(row.get(c_trainer, "")).strip() if c_trainer else "",
            "seminar_date": sem_dt,
            "session": str(row.get(c_session, "")).strip().upper() if c_session else "",
            "attended": bool(row.get("attended_flag", False)),
            "seat_book_amount": float(row.get("seat_book_amount", 0) or 0),
            "seat_booked": bool(float(row.get("seat_book_amount", 0) or 0) > 0),
            "primary_course": "",
            "primary_order_date": pd.NaT,
            "primary_paid": 0.0,
            "primary_due": 0.0,
            "primary_gst": 0.0,
            "primary_mode": "",
            "primary_status": "",
            "additional_courses": [],
            "additional_paid": 0.0,
            "converted": False,
            "trainer_conv": "",
            "sales_rep": "",
        }

        all_mobile_orders = conv[conv["mobile_clean"].isin(possible_mobiles)].sort_values("order_date_clean") if possible_mobiles else pd.DataFrame()
        valid = all_mobile_orders[all_mobile_orders["order_date_clean"] >= sem_dt].sort_values("order_date_clean") if (not all_mobile_orders.empty and pd.notna(sem_dt)) else pd.DataFrame()

        status_source = valid if not valid.empty else all_mobile_orders
        if not status_source.empty:
            entry["primary_status"] = normalize_status(status_source.iloc[-1]["status_clean"])

        if not valid.empty:
            entry["converted"] = True
            pti = valid[valid["service_name_clean"].str.contains(PTI_MATCH, na=False, case=False)]
            primary = pti.iloc[0] if not pti.empty else valid.iloc[0]

            entry["primary_course"] = primary["service_name_clean"]
            entry["primary_order_date"] = primary["order_date_clean"]
            entry["primary_paid"] = float(primary["paid_amount"])
            entry["primary_due"] = float(primary["total_due"])
            entry["primary_gst"] = float(primary["total_gst"])
            entry["primary_mode"] = str(primary["payment_mode_clean"]).strip()
            entry["trainer_conv"] = str(primary["trainer_clean"]).strip()
            entry["sales_rep"] = str(primary["sales_rep_clean"]).strip()

            others = valid[valid.index != primary.name]
            entry["additional_courses"] = list(others["service_name_clean"].dropna().astype(str).str.strip().unique())
            entry["additional_paid"] = float(others["paid_amount"].sum())

            for _, o in valid.iterrows():
                order_rows.append({
                    "name": entry["name"],
                    "mobile": entry["mobile"],
                    "place": entry["place"],
                    "seminar_date": sem_dt,
                    "seminar_date_str": sem_dt.strftime("%Y-%m-%d") if pd.notna(sem_dt) else "",
                    "course": str(o["service_name_clean"]).strip(),
                    "order_date": o["order_date_clean"],
                    "order_date_str": o["order_date_clean"].strftime("%Y-%m-%d") if pd.notna(o["order_date_clean"]) else "",
                    "paid_amount": float(o["paid_amount"]),
                    "total_due": float(o["total_due"]),
                    "total_gst": float(o["total_gst"]),
                    "payment_mode": str(o["payment_mode_clean"]).strip(),
                    "status": normalize_status(o["status_clean"]),
                    "sales_rep": str(o["sales_rep_clean"]).strip(),
                    "trainer_conv": str(o["trainer_clean"]).strip(),
                    "is_primary": bool(o.name == primary.name),
                    "order_id": str(o["order_id_clean"]).strip(),
                })

        entry.update(get_lead(possible_mobiles))
        rows.append(entry)

    df = pd.DataFrame(rows)
    orders_df = pd.DataFrame(order_rows)

    if df.empty:
        df = pd.DataFrame(columns=[
            "name", "mobile", "primary_mobile", "alternate_mobile", "place", "trainer", "seminar_date", "session", "attended",
            "seat_book_amount", "seat_booked", "primary_course", "primary_order_date",
            "primary_paid", "primary_due", "primary_gst", "primary_mode", "primary_status",
            "additional_courses", "additional_paid", "converted", "trainer_conv",
            "sales_rep", "webinar_type", "lead_source", "campaign_name", "lead_status",
            "stage_name", "lead_owner", "state", "attempted", "service_name_lead",
            "email", "remarks", "lead_name"
        ])

    for col in ["webinar_type", "lead_source", "campaign_name", "lead_status", "stage_name", "lead_owner",
                "state", "attempted", "service_name_lead", "email", "remarks", "lead_name"]:
        if col not in df.columns:
            df[col] = ""

    df["seminar_date_str"] = pd.to_datetime(df["seminar_date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    df["primary_order_date_str"] = pd.to_datetime(df["primary_order_date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    df["due_zero"] = safe_numeric(df["primary_due"]) <= 0

    if not orders_df.empty:
        lead_meta = df[["mobile", "webinar_type", "lead_source", "campaign_name",
                        "lead_status", "stage_name", "lead_owner", "state", "attempted"]].drop_duplicates("mobile")
        orders_df = orders_df.merge(lead_meta, on="mobile", how="left")
        orders_df["due_zero"] = safe_numeric(orders_df["total_due"]) <= 0

    return df, orders_df

# ─────────────────────────────────────────────
# LOGIN / UPLOAD
# ─────────────────────────────────────────────
def login_page():
    st.markdown("""
    <div style="text-align:center;margin-top:60px;margin-bottom:30px">
      <div style="font-size:48px">📊</div>
      <h1 style="font-size:26px;font-weight:800;color:#e2e8f0;margin:8px 0">Invesmate Analytics</h1>
      <p style="color:#64748b;font-size:14px">Seminar Performance Dashboard</p>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Sign In →", use_container_width=True)
            if submitted:
                if CREDENTIALS.get(username) == password:
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("Invalid credentials. Try admin / admin123")

def upload_page():
    st.markdown('<div class="section-header">📁 Upload Data Files</div>', unsafe_allow_html=True)
    st.markdown("Upload all three source files. The dashboard will auto-detect columns and build the full analysis.")
    c1, c2, c3 = st.columns(3)
    with c1:
        sem_file = st.file_uploader("📋 Seminar Updated Sheet", type=["xlsx", "xls", "csv"], key="sem_file")
    with c2:
        conv_file = st.file_uploader("💰 Conversion List", type=["xlsx", "xls", "csv"], key="conv_file")
    with c3:
        leads_file = st.file_uploader("🎯 Leads Report", type=["xlsx", "xls", "csv"], key="leads_file")

    if sem_file and conv_file and leads_file:
        if st.button("🚀 Build Dashboard", use_container_width=True, type="primary"):
            with st.spinner("Processing files and building analytics…"):
                df, orders_df = process_data(
                    sem_file.read(), conv_file.read(), leads_file.read(),
                    sem_file.name, conv_file.name, leads_file.name,
                )
                st.session_state["df"] = df
                st.session_state["orders_df"] = orders_df
                st.session_state["files_loaded"] = True
                st.rerun()
    else:
        missing = []
        if not sem_file: missing.append("Seminar Sheet")
        if not conv_file: missing.append("Conversion List")
        if not leads_file: missing.append("Leads Report")
        st.info(f"Waiting for: {', '.join(missing)}")

# ─────────────────────────────────────────────
# FILTERS
# ─────────────────────────────────────────────
def render_filters_top(df):
    st.markdown('<div class="section-header">🔧 Filters</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    dates = ["All"] + sorted([d for d in df["seminar_date_str"].dropna().unique().tolist() if d])
    sel_date = col1.selectbox("Seminar Date", dates)
    sel_place = col2.multiselect("Location", sorted(df["place"].dropna().astype(str).unique()))
    sel_session = col3.multiselect("Session", sorted(df["session"].dropna().astype(str).unique()))
    sel_trainer = col4.multiselect("Trainer", sorted(df["trainer"].dropna().astype(str).unique()))

    col5, col6, col7, col8 = st.columns(4)
    sel_conv = col5.selectbox("Converted", ["All", "Yes", "No"])
    sel_course = col6.multiselect("Primary Course", sorted(df["primary_course"].dropna().astype(str).unique()))
    sel_due = col7.selectbox("Due Filter", ["All", "Due = 0", "Has Due"])
    sel_lead = col8.multiselect("Lead Source", sorted(df["lead_source"].dropna().astype(str).unique()))

    col9, col10, col11, col12 = st.columns(4)
    max_paid = int(df["primary_paid"].max()) if df["primary_paid"].max() > 0 else 100000
    paid_range = col9.slider("Paid Amount (₹)", 0, max_paid, (0, max_paid))
    sel_webinar = col10.multiselect("Lead Type", sorted(df["webinar_type"].dropna().astype(str).unique()))
    sel_campaign = col11.multiselect("Campaign", sorted(df["campaign_name"].dropna().astype(str).unique()))
    sel_stage = col12.multiselect("Stage", sorted(df["stage_name"].dropna().astype(str).unique()))

    col13, col14, col15, col16 = st.columns(4)
    sel_owner = col13.multiselect("Lead Owner", sorted(df["lead_owner"].dropna().astype(str).unique()))
    sel_state = col14.multiselect("State", sorted(df["state"].dropna().astype(str).unique()))
    sel_attempt = col15.multiselect("Attempted", sorted(df["attempted"].dropna().astype(str).unique()))
    sel_seat = col16.selectbox("Seat Booked", ["All", "Seat Booked", "No Seat Booked"])

    col17, col18, col19 = st.columns(3)
    sel_status = col17.selectbox("Status", ["All", "Active", "Inactive"])
    sel_primary_status = col18.selectbox("Primary Status", ["All", "Seat Booked", "Partially Converted", "Converted"])
    reset = col19.button("Reset Filters", use_container_width=True)

    if reset:
        st.rerun()

    fdf = df.copy()
    if sel_date != "All":
        fdf = fdf[fdf["seminar_date_str"] == sel_date]
    if sel_place:
        fdf = fdf[fdf["place"].isin(sel_place)]
    if sel_session:
        fdf = fdf[fdf["session"].isin(sel_session)]
    if sel_trainer:
        fdf = fdf[fdf["trainer"].isin(sel_trainer)]
    if sel_conv == "Yes":
        fdf = fdf[fdf["converted"]]
    elif sel_conv == "No":
        fdf = fdf[~fdf["converted"]]
    if sel_course:
        fdf = fdf[fdf["primary_course"].isin(sel_course)]
    if sel_due == "Due = 0":
        fdf = fdf[fdf["primary_due"] <= 0]
    elif sel_due == "Has Due":
        fdf = fdf[fdf["primary_due"] > 0]
    fdf = fdf[(fdf["primary_paid"] >= paid_range[0]) & (fdf["primary_paid"] <= paid_range[1])]
    if sel_lead:
        fdf = fdf[fdf["lead_source"].isin(sel_lead)]
    if sel_webinar:
        fdf = fdf[fdf["webinar_type"].isin(sel_webinar)]
    if sel_campaign:
        fdf = fdf[fdf["campaign_name"].isin(sel_campaign)]
    if sel_stage:
        fdf = fdf[fdf["stage_name"].isin(sel_stage)]
    if sel_owner:
        fdf = fdf[fdf["lead_owner"].isin(sel_owner)]
    if sel_state:
        fdf = fdf[fdf["state"].isin(sel_state)]
    if sel_attempt:
        fdf = fdf[fdf["attempted"].isin(sel_attempt)]
    if sel_seat == "Seat Booked":
        fdf = fdf[fdf["seat_book_amount"] > 0]
    elif sel_seat == "No Seat Booked":
        fdf = fdf[fdf["seat_book_amount"] <= 0]
    if sel_status == "Active":
        fdf = fdf[fdf["primary_status"] == "Active"]
    elif sel_status == "Inactive":
        fdf = fdf[fdf["primary_status"] == "Inactive"]
    if sel_primary_status == "Seat Booked":
        fdf = fdf[(fdf["seat_book_amount"] > 0) & (~fdf["converted"])]
    elif sel_primary_status == "Partially Converted":
        fdf = fdf[(fdf["seat_book_amount"] > 0) & (fdf["converted"]) & (fdf["primary_due"] > 0)]
    elif sel_primary_status == "Converted":
        fdf = fdf[fdf["converted"]]
    return fdf

def filter_orders_by_attendees(orders_df, fdf):
    if orders_df is None or orders_df.empty or fdf.empty:
        return pd.DataFrame() if orders_df is None else orders_df.iloc[0:0].copy()
    keep = set(fdf["mobile"].dropna().astype(str))
    return orders_df[orders_df["mobile"].astype(str).isin(keep)].copy()



# ─────────────────────────────────────────────
# RENDERERS
# ─────────────────────────────────────────────
def render_kpis(fdf):
    conv = fdf[fdf["converted"]]
    total = len(fdf)
    n_conv = len(conv)
    rate = f"{(n_conv/total*100):.1f}%" if total else "0%"
    t_paid = conv["primary_paid"].sum()
    t_due = conv["primary_due"].sum()
    fp = len(conv[conv["primary_due"] <= 0])
    hd = len(conv[conv["primary_due"] > 0])
    uniq_c = fdf["primary_course"].replace("", pd.NA).dropna().nunique()
    wbn = len(fdf[fdf["webinar_type"] == "Webinar"])
    non_wbn = len(fdf[fdf["webinar_type"] == "Non Webinar"])
    add_rev = fdf["additional_paid"].sum()
    seat_book_count = len(fdf[fdf["seat_book_amount"] > 0]) if "seat_book_amount" in fdf.columns else 0
    seat_book_amount = fdf["seat_book_amount"].sum() if "seat_book_amount" in fdf.columns else 0

    cols = st.columns(5)
    cards = [
        ("Total Attendees", total, "Filtered seminar attendees", "#6366f1"),
        ("Converted", n_conv, "Post-seminar conversions", "#10b981"),
        ("Conversion Rate", rate, "Attend → Purchase rate", "#06b6d4"),
        ("Total Paid Amount", fmt_inr(t_paid), "Excl. GST", "#f59e0b"),
        ("Total Due", fmt_inr(t_due), "Outstanding dues", "#ef4444"),
    ]
    for i, (lbl, val, sub, clr) in enumerate(cards):
        cols[i].markdown(kpi_card(lbl, val, sub, clr), unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    seat_cols = st.columns(2)
    seat_cols[0].markdown(kpi_card("Seminar Seat Booked Count", seat_book_count, "From seminar updated file", "#22c55e"), unsafe_allow_html=True)
    seat_cols[1].markdown(kpi_card("Seminar Seat Booked Amount", fmt_inr(seat_book_amount), "Seat amount collected", "#14b8a6"), unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    cols2 = st.columns(5)
    cards2 = [
        ("Fully Paid", fp, "Due ≤ 0", "#10b981"),
        ("Has Due", hd, "Pending balance", "#ef4444"),
        ("Unique Courses", uniq_c, "Distinct courses bought", "#8b5cf6"),
        ("Webinar Leads", wbn, "From webinar source", "#06b6d4"),
        ("Non-Webinar Leads", non_wbn, "Offline / walk-in", "#f97316"),
    ]
    for i, (lbl, val, sub, clr) in enumerate(cards2):
        cols2[i].markdown(kpi_card(lbl, val, sub, clr), unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    cols3 = st.columns(5)
    cols3[0].markdown(kpi_card("Additional Revenue", fmt_inr(add_rev), "Cross-sell purchases", "#a855f7"), unsafe_allow_html=True)
    cols3[1].markdown(kpi_card("Avg Paid / Student", fmt_inr(t_paid/n_conv if n_conv else 0), "Per converted student", "#3b82f6"), unsafe_allow_html=True)
    cols3[2].markdown(kpi_card("Total Revenue", fmt_inr(t_paid + add_rev), "Primary + additional", "#f59e0b"), unsafe_allow_html=True)
    cols3[3].markdown(kpi_card("Attempted Leads", len(fdf[fdf["attempted"] == "Attempted"]), "Out of matched leads", "#10b981"), unsafe_allow_html=True)
    cols3[4].markdown(kpi_card("Unattempted Leads", len(fdf[fdf["attempted"] == "Unattempted"]), "Not yet contacted", "#ef4444"), unsafe_allow_html=True)

def render_overview(fdf):
    st.markdown('<div class="section-header">📅 Trends & Location Analysis</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    bydate = fdf.groupby("seminar_date_str").agg(Attendees=("attended", "count"), Converted=("converted", "sum")).reset_index()
    with c1:
        fig = go.Figure()
        fig.add_bar(x=bydate["seminar_date_str"], y=bydate["Attendees"], name="Attendees", marker_color="#6366f1", opacity=0.7)
        fig.add_bar(x=bydate["seminar_date_str"], y=bydate["Converted"], name="Converted", marker_color="#10b981", opacity=0.9)
        fig.update_layout(title="Attendees & Conversions by Seminar Date", barmode="group", template="plotly_dark",
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=50, b=30, l=20, r=20), height=320)
        st.plotly_chart(fig, use_container_width=True)
    byloc = fdf.groupby("place").agg(Attendees=("attended", "count"), Converted=("converted", "sum"), Revenue=("primary_paid", "sum")).reset_index().sort_values("Attendees", ascending=False).head(12)
    with c2:
        fig2 = go.Figure()
        fig2.add_bar(x=byloc["place"], y=byloc["Attendees"], name="Attendees", marker_color="#6366f1", opacity=0.7)
        fig2.add_bar(x=byloc["place"], y=byloc["Converted"], name="Converted", marker_color="#10b981", opacity=0.9)
        fig2.update_layout(title="Attendees & Conversions by Location", barmode="group", template="plotly_dark",
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=50, b=30, l=20, r=20), height=320)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-header">🎟️ Seminar Seat Booked Analysis</div>', unsafe_allow_html=True)
    sb1, sb2 = st.columns(2)
    seat_loc = fdf.groupby("place").agg(
        SeatBookedStudents=("seat_book_amount", lambda s: (pd.to_numeric(s, errors="coerce").fillna(0) > 0).sum()),
        SeatBookedAmount=("seat_book_amount", "sum"),
    ).reset_index().sort_values("SeatBookedAmount", ascending=False).head(12)
    with sb1:
        fig_sb1 = px.bar(seat_loc.sort_values("SeatBookedStudents", ascending=True), x="SeatBookedStudents", y="place", orientation="h",
                         title="Seminar Seat Booked Count by Location")
        fig_sb1.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=320, yaxis_title="")
        st.plotly_chart(fig_sb1, use_container_width=True)
    with sb2:
        fig_sb2 = px.bar(seat_loc.sort_values("SeatBookedAmount", ascending=True), x="SeatBookedAmount", y="place", orientation="h",
                         title="Seminar Seat Booked Amount by Location")
        fig_sb2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=320, yaxis_title="")
        st.plotly_chart(fig_sb2, use_container_width=True)

def render_courses(fdf):
    conv = fdf[fdf["converted"]].copy()
    if conv.empty:
        st.info("No converted students in current filter.")
        return
    byc = conv.groupby("primary_course").agg(Students=("attended", "count"), Paid=("primary_paid", "sum"), Due=("primary_due", "sum")).reset_index().sort_values("Students", ascending=False)
    total = byc["Students"].sum()
    byc["Share %"] = (byc["Students"] / total * 100).round(1)
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(byc.head(12), x="Students", y="primary_course", orientation="h", title="Course-wise Student Count")
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=380, yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig2 = px.pie(byc.head(10), names="primary_course", values="Students", title="Course Share by Student Count", hole=0.35, color_discrete_sequence=CHART_COLORS)
        fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", height=380)
        st.plotly_chart(fig2, use_container_width=True)

def render_combo(fdf, orders_df):
    pti_df = fdf[fdf["primary_course"].astype(str).str.contains(PTI_MATCH, na=False, case=False)]
    with_other = pti_df[pti_df["additional_courses"].apply(lambda x: len(x) if isinstance(x, list) else 0) > 0]
    cols = st.columns(4)
    stats = [
        ("PTI Buyers", len(pti_df), "#6366f1"),
        ("Also Bought More", len(with_other), "#10b981"),
        ("Cross-Sell Rate", f"{len(with_other)/len(pti_df)*100:.1f}%" if len(pti_df) else "0%", "#06b6d4"),
        ("Additional Revenue", fmt_inr(with_other["additional_paid"].sum()), "#f59e0b"),
    ]
    for i, (lbl, val, clr) in enumerate(stats):
        cols[i].markdown(kpi_card(lbl, val, accent=clr), unsafe_allow_html=True)
    if with_other.empty:
        st.info("No PTI buyers with later purchases in the current filter.")

def render_leads(fdf):
    show = fdf[["name", "mobile", "place", "seminar_date_str", "converted", "primary_course", "primary_paid",
                "webinar_type", "lead_source", "lead_status", "stage_name", "lead_owner", "state",
                "attempted", "email", "remarks"]].copy()
    show["converted"] = show["converted"].map({True: "✅ Yes", False: "❌ No"})
    show["primary_paid"] = show["primary_paid"].apply(lambda x: fmt_inr(x) if x > 0 else "—")
    show.columns = ["Name", "Mobile", "Location", "Seminar Date", "Converted", "Course", "Paid", "Lead Type", "Source", "Lead Status", "Stage", "Owner", "State", "Attempted", "Email", "Remarks"]
    st.dataframe(show, use_container_width=True, hide_index=True, height=420)

def render_journey(fdf):
    show = fdf[["name", "mobile", "seminar_date_str", "place", "session", "trainer", "attended",
                "seat_book_amount", "primary_course", "primary_order_date_str", "primary_paid", "primary_due",
                "additional_courses", "webinar_type", "lead_source", "lead_status", "stage_name", "lead_owner"]].copy()
    show["attended"] = show["attended"].map({True: "✅", False: "—"})
    show["seat_book_amount"] = show["seat_book_amount"].apply(lambda x: fmt_inr(x) if x > 0 else "—")
    show["primary_paid"] = show["primary_paid"].apply(lambda x: fmt_inr(x) if x > 0 else "—")
    show["primary_due"] = show["primary_due"].apply(lambda x: fmt_inr(x) if x > 0 else "₹0")
    show["additional_courses"] = show["additional_courses"].apply(lambda x: " | ".join(x) if isinstance(x, list) and x else "—")
    show.columns = ["Name", "Mobile", "Seminar Date", "Location", "Session", "Trainer", "Attended", "Seat Book Amt", "Primary Course", "Order Date", "Paid", "Due", "Additional Courses", "Lead Type", "Source", "Lead Status", "Stage", "Owner"]
    st.dataframe(show, use_container_width=True, hide_index=True, height=500)

def render_tables(fdf, orders_df):
    tab1, tab2, tab3 = st.tabs(["📋 Attendee Master", "✅ Converted Students", "📦 All Orders Summary"])
    with tab1:
        show = fdf[["name", "mobile", "place", "seminar_date_str", "session", "trainer", "seat_book_amount", "converted", "primary_course", "primary_paid", "primary_due", "primary_status"]].copy()
        show["seat_book_amount"] = show["seat_book_amount"].apply(lambda x: fmt_inr(x) if x > 0 else "—")
        show["converted"] = show["converted"].map({True: "✅ Yes", False: "❌ No"})
        show["primary_paid"] = show["primary_paid"].apply(lambda x: fmt_inr(x) if x > 0 else "—")
        show["primary_due"] = show["primary_due"].apply(lambda x: fmt_inr(x) if x > 0 else "₹0")
        show.columns = ["Name", "Mobile", "Location", "Seminar Date", "Session", "Trainer", "Seat Book Amt", "Converted", "Course", "Paid", "Due", "Status"]
        st.dataframe(show, use_container_width=True, hide_index=True, height=400)
    with tab2:
        conv = fdf[fdf["converted"]].copy()
        show2 = conv[["name", "mobile", "place", "seminar_date_str", "primary_course", "primary_order_date_str", "primary_paid", "primary_due", "additional_courses", "webinar_type", "lead_source", "primary_status"]].copy()
        show2["primary_paid"] = show2["primary_paid"].apply(fmt_inr)
        show2["primary_due"] = show2["primary_due"].apply(lambda x: fmt_inr(x) if x > 0 else "₹0")
        show2["additional_courses"] = show2["additional_courses"].apply(lambda x: " | ".join(x) if isinstance(x, list) and x else "—")
        show2.columns = ["Name", "Mobile", "Location", "Seminar Date", "Course", "Order Date", "Paid", "Due", "Additional Courses", "Lead Type", "Source", "Status"]
        st.dataframe(show2, use_container_width=True, hide_index=True, height=400)
    with tab3:
        if orders_df is None or orders_df.empty:
            st.info("No order records available.")
        else:
            summary = orders_df.groupby("place").agg(Students=("mobile", "nunique"), Orders=("course", "count"), Total_Paid=("paid_amount", "sum"), Total_Due=("total_due", "sum")).reset_index()
            summary["Total_Paid"] = summary["Total_Paid"].apply(fmt_inr)
            summary["Total_Due"] = summary["Total_Due"].apply(fmt_inr)
            summary.columns = ["Location", "Students", "Orders", "Total Paid", "Total Due"]
            st.dataframe(summary, use_container_width=True, hide_index=True)
# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "files_loaded" not in st.session_state:
        st.session_state["files_loaded"] = False
    if "df" not in st.session_state:
        st.session_state["df"] = None
    if "orders_df" not in st.session_state:
        st.session_state["orders_df"] = None

    if not st.session_state["logged_in"]:
        login_page()
        return

    st.markdown("""
    <div class="hero">
      <div class="hero-title">Invesmate Seminar Analytics</div>
      <div class="hero-sub">Attendee-first tracking: offline seminar → post-seminar conversion → lead intelligence</div>
    </div>
    """, unsafe_allow_html=True)

    toolbar = st.columns([1, 1, 5])
    if toolbar[0].button("Upload / reload data", use_container_width=True):
        st.session_state["files_loaded"] = False
        st.session_state["df"] = None
        st.session_state["orders_df"] = None
        st.rerun()
    if toolbar[1].button("Logout", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["files_loaded"] = False
        st.session_state["df"] = None
        st.session_state["orders_df"] = None
        st.rerun()

    if not st.session_state["files_loaded"] or st.session_state["df"] is None:
        upload_page()
        return

    df = st.session_state["df"]
    orders_df = st.session_state["orders_df"]

    fdf = render_filters_top(df)
    filtered_orders = filter_orders_by_attendees(orders_df, fdf)

    if fdf.empty:
        st.warning("No data matches current filters.")
        return

    st.markdown('<div class="section-header">👥 Filtered Students Details</div>', unsafe_allow_html=True)
    render_section_student_details("Filtered Students", fdf, extra_cols=["additional_courses", "email", "remarks"], key_prefix="filteredtop")

    tabs = st.tabs([
        "📊 Overview",
        "📚 Course Analysis",
        "🔗 PTI Cross-Sell",
        "🎯 Lead Intelligence",
        "🗺️ Student Journey",
        "📋 Data Tables",
    ])

    with tabs[0]:
        st.markdown('<div class="section-header">📊 Key Performance Indicators</div>', unsafe_allow_html=True)
        render_kpis(fdf)
        st.markdown("---")
        render_overview(fdf)
        st.markdown("---")
        render_section_student_details("Overview", fdf, key_prefix="overview")

    with tabs[1]:
        render_courses(fdf)
        st.markdown("---")
        render_section_student_details("Course Analysis", fdf[fdf["converted"]], extra_cols=["additional_courses"], key_prefix="course")

    with tabs[2]:
        render_combo(fdf, filtered_orders)
        st.markdown("---")
        pti_df = fdf[fdf["primary_course"].astype(str).str.contains(PTI_MATCH, na=False, case=False)].copy()
        render_section_student_details("PTI Cross-Sell", pti_df, extra_cols=["additional_courses"], key_prefix="pti")

    with tabs[3]:
        render_leads(fdf)
        st.markdown("---")
        lead_df = fdf[(fdf["lead_source"].astype(str).str.strip() != "") | (fdf["webinar_type"].astype(str).str.strip() != "")].copy()
        render_section_student_details("Lead Intelligence", lead_df, extra_cols=["email", "remarks"], key_prefix="leadsec")

    with tabs[4]:
        render_journey(fdf)
        st.markdown("---")
        render_section_student_details("Student Journey", fdf, extra_cols=["additional_courses"], key_prefix="journeysec")

    with tabs[5]:
        render_tables(fdf, filtered_orders)

if __name__ == "__main__":
    main()
