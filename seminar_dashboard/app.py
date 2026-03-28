import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
import io
from datetime import datetime, date

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Invesmate Seminar Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* Hide default Streamlit header */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* KPI Cards */
.kpi-card {
    background: #131929;
    border: 1px solid #1e2d4a;
    border-radius: 14px;
    padding: 18px 20px;
    text-align: center;
    border-top: 3px solid var(--accent, #6366f1);
}
.kpi-label { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
.kpi-value { font-size: 28px; font-weight: 800; color: #e2e8f0; margin: 4px 0; letter-spacing: -1px; }
.kpi-sub   { font-size: 11px; color: #64748b; }

/* Section headers */
.section-header {
    font-size: 15px; font-weight: 700; color: #e2e8f0;
    border-left: 3px solid #6366f1; padding-left: 10px;
    margin: 4px 0 16px 0;
}

/* Badge */
.badge-green { background:#10b98120; color:#10b981; border-radius:5px; padding:2px 8px; font-size:11px; font-weight:600; }
.badge-red   { background:#ef444420; color:#ef4444; border-radius:5px; padding:2px 8px; font-size:11px; font-weight:600; }
.badge-blue  { background:#6366f120; color:#6366f1; border-radius:5px; padding:2px 8px; font-size:11px; font-weight:600; }
.badge-cyan  { background:#06b6d420; color:#06b6d4; border-radius:5px; padding:2px 8px; font-size:11px; font-weight:600; }

/* Login */
.login-box { max-width: 400px; margin: 80px auto; background: #131929; border: 1px solid #1e2d4a; border-radius: 20px; padding: 48px 40px; }
.login-logo { text-align: center; margin-bottom: 32px; }
.login-logo h1 { font-size: 22px; font-weight: 700; color: #e2e8f0; }
.login-logo p  { color: #64748b; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

COMBO_COURSE = "Power Of Trading & Investing Combo Course"
CHART_COLORS = [
    "#6366f1","#8b5cf6","#06b6d4","#10b981","#f59e0b",
    "#ef4444","#f97316","#ec4899","#14b8a6","#a855f7",
    "#3b82f6","#84cc16",
]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def clean_mobile(x):
    if pd.isna(x):
        return None
    s = re.sub(r"\D", "", str(x))
    return s[-10:] if len(s) >= 10 else None

def parse_date_series(series):
    for fmt in ["%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%b-%d-%Y"]:
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
    """Load xlsx/xls/csv from an UploadedFile object."""

    """
    Supports both CSV and Excel files from BytesIO or UploadedFile.
    Automatically detects type using filename or content fallback.
    """
    name = (filename or "").lower()

    try:
        # ✅ CSV handling
        if name.endswith(".csv"):
            return pd.read_csv(file_obj)

        # ✅ Excel handling
        elif name.endswith((".xlsx", ".xls")):
            return pd.read_excel(file_obj, sheet_name=0)

        # ✅ Fallback (auto-detect)
        else:
            try:
                return pd.read_excel(file_obj, sheet_name=0)
            except Exception:
                file_obj.seek(0)
                return pd.read_csv(file_obj)

    except Exception as e:
        file_obj.seek(0)
        raise ValueError(f"Error reading file ({filename}): {e}")

# ─────────────────────────────────────────────
# COLUMN DETECTION
# ─────────────────────────────────────────────
def detect_col(df, candidates, required=False):
    """Return the first matching column (case-insensitive, stripped)."""
    norm = {c.strip().lower(): c for c in df.columns}
    for cand in candidates:
        key = cand.strip().lower()
        if key in norm:
            return norm[key]
    if required:
        st.warning(f"⚠️ Could not find column matching: {candidates}. Some metrics may be missing.")
    return None

# ─────────────────────────────────────────────
# DATA PROCESSING
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def process_data(sem_bytes, conv_bytes, leads_bytes,
                 sem_name, conv_name, leads_name):
    """
    Process all three files and return a unified attendee-first DataFrame.
    Cache key uses file names + sizes (passed as strings).
    """
    # ── SEMINAR ──────────────────────────────
    sem = load_excel_or_csv(io.BytesIO(sem_bytes), sem_name)
    sem.columns = [str(c).strip() for c in sem.columns]

    c_mobile   = detect_col(sem, ["Mobile","Phone","mobile","phone","Contact"])
    c_name     = detect_col(sem, ["NAME","Name","Student Name","name"])
    c_place    = detect_col(sem, ["Place","Location","Venue","City","place"])
    c_trainer  = detect_col(sem, ["Trainer / Presenter","Trainer","Presenter","trainer"])
    c_semdate  = detect_col(sem, ["Seminar Date","Date","seminar_date","Event Date"])
    c_session  = detect_col(sem, ["Session","session","Batch","Time"])
    c_attended = detect_col(sem, ["Is Attended ?","Attended","is_attended","attended"])
    c_altmob   = detect_col(sem, ["Alternate Number","Alt Mobile","alternate_number"])

    sem["mobile_clean"] = sem[c_mobile].apply(clean_mobile) if c_mobile else None
    sem["seminar_date"] = parse_date_series(sem[c_semdate]) if c_semdate else pd.NaT
    sem["attended_flag"] = (
        sem[c_attended].astype(str).str.strip().str.upper().isin(["YES","TRUE","1","Y"])
        if c_attended else False
    )

    attendees = sem[sem["attended_flag"]].copy().reset_index(drop=True)

    # ── CONVERSION ───────────────────────────
    conv = load_excel_or_csv(io.BytesIO(conv_bytes), conv_name)
    conv.columns = [str(c).strip() for c in conv.columns]

    cc_mobile   = detect_col(conv, ["phone","Phone","mobile","Mobile","Contact"])
    cc_service  = detect_col(conv, ["service_name","Service Name","Course","course_name","ServiceName"])
    cc_orderdt  = detect_col(conv, ["order_date","Order Date","OrderDate","Date"])
    cc_payrec   = detect_col(conv, ["payment_received","Payment Received","PaymentReceived","amount_paid"])
    cc_gst      = detect_col(conv, ["total_gst","GST","gst","TotalGST"])
    cc_due      = detect_col(conv, ["total_due","Due","total_due_amount","TotalDue"])
    cc_trainer  = detect_col(conv, ["trainer","Trainer"])
    cc_salesrep = detect_col(conv, ["sales_rep_name","Sales Rep","SalesRep","sales_rep"])
    cc_mode     = detect_col(conv, ["payment_mode","Payment Mode","mode"])

    conv["mobile_clean"]      = conv[cc_mobile].apply(clean_mobile) if cc_mobile else None
    conv["order_date_clean"]  = pd.to_datetime(
        conv[cc_orderdt], errors="coerce", utc=True
    ).dt.tz_localize(None) if cc_orderdt else pd.NaT
    conv["payment_received"]  = safe_numeric(conv[cc_payrec])  if cc_payrec  else 0
    conv["total_gst"]         = safe_numeric(conv[cc_gst])     if cc_gst     else 0
    conv["total_due"]         = safe_numeric(conv[cc_due])     if cc_due     else 0
    conv["paid_amount"]       = conv["payment_received"] + conv["total_gst"]
    conv["service_name_clean"]= conv[cc_service].astype(str).str.strip() if cc_service else ""

    # ── LEADS ────────────────────────────────
    leads = load_excel_or_csv(io.BytesIO(leads_bytes), leads_name)
    leads.columns = [str(c).strip() for c in leads.columns]

    lc_mobile   = detect_col(leads, ["phone","Phone","mobile","Mobile"])
    lc_convfrom = detect_col(leads, ["converted_from","ConvertedFrom","lead_type","LeadType"])
    lc_source   = detect_col(leads, ["leadsource","lead_source","LeadSource","Source"])
    lc_campaign = detect_col(leads, ["campaign_name","Campaign","CampaignName"])
    lc_status   = detect_col(leads, ["leadstatus","lead_status","LeadStatus","Status"])
    lc_stage    = detect_col(leads, ["stage_name","StageName","Stage"])
    lc_owner    = detect_col(leads, ["leadownername","LeadOwner","lead_owner","Owner"])
    lc_state    = detect_col(leads, ["state","State","Province"])
    lc_attempted= detect_col(leads, ["Attempted/Unattempted","attempted","Attempted"])
    lc_service  = detect_col(leads, ["servicename","ServiceName","service_name"])
    lc_email    = detect_col(leads, ["email","Email"])
    lc_remarks  = detect_col(leads, ["remarks","Remarks","Notes"])
    lc_name     = detect_col(leads, ["name","Name","StudentName"])

    leads["mobile_clean"] = leads[lc_mobile].apply(clean_mobile) if lc_mobile else None
    lead_map = leads.drop_duplicates("mobile_clean").set_index("mobile_clean") if lc_mobile else pd.DataFrame()

    # ── MERGE ────────────────────────────────
    def get_lead(mob):
        if not mob or lead_map.empty or mob not in lead_map.index:
            return {}
        r = lead_map.loc[mob]
        def gs(col): return str(r[col]).strip() if col and col in r.index else ""
        wt = gs(lc_convfrom)
        if not wt:
            src = gs(lc_source)
            wt = "Webinar" if "WBN" in src.upper() else ("Non Webinar" if src else "")
        return {
            "webinar_type":   wt,
            "lead_source":    gs(lc_source),
            "campaign_name":  gs(lc_campaign),
            "lead_status":    gs(lc_status),
            "stage_name":     gs(lc_stage),
            "lead_owner":     gs(lc_owner),
            "state":          gs(lc_state),
            "attempted":      gs(lc_attempted),
            "service_name_lead": gs(lc_service),
            "email":          gs(lc_email),
            "remarks":        gs(lc_remarks),
            "lead_name":      gs(lc_name),
        }

    rows = []
    for _, row in attendees.iterrows():
        mob     = row["mobile_clean"]
        sem_dt  = row["seminar_date"]
        entry = {
            "name":         str(row.get(c_name, "")).strip() if c_name else "",
            "mobile":       mob or "",
            "place":        str(row.get(c_place, "")).strip() if c_place else "",
            "trainer":      str(row.get(c_trainer, "")).strip() if c_trainer else "",
            "seminar_date": sem_dt,
            "session":      str(row.get(c_session, "")).strip().upper() if c_session else "",
            "attended":     True,
            "primary_course": "",
            "primary_order_date": pd.NaT,
            "primary_paid": 0.0,
            "primary_due":  0.0,
            "additional_courses": [],
            "additional_paid": 0.0,
            "converted":    False,
            "trainer_conv": "",
            "sales_rep":    "",
        }

        if mob and pd.notna(sem_dt):
            valid = conv[
                (conv["mobile_clean"] == mob) &
                (conv["order_date_clean"] >= sem_dt)
            ].sort_values("order_date_clean")

            if len(valid) > 0:
                entry["converted"] = True
                combo = valid[valid["service_name_clean"].str.contains(
                    "Power Of Trading", na=False, case=False)]
                primary = combo.iloc[0] if len(combo) > 0 else valid.iloc[0]

                entry["primary_course"]     = primary["service_name_clean"]
                entry["primary_order_date"] = primary["order_date_clean"]
                entry["primary_paid"]       = float(primary["paid_amount"])
                entry["primary_due"]        = float(primary["total_due"])
                if cc_trainer:
                    entry["trainer_conv"] = str(primary.get(cc_trainer, "")).strip()
                if cc_salesrep:
                    entry["sales_rep"] = str(primary.get(cc_salesrep, "")).strip()

                others = valid[valid.index != primary.name]
                entry["additional_courses"] = list(others["service_name_clean"].dropna().unique())
                entry["additional_paid"]    = float(others["paid_amount"].sum())

        lead_info = get_lead(mob)
        entry.update(lead_info)
        rows.append(entry)

    df = pd.DataFrame(rows)

    # Post-processing
    for col in ["webinar_type","lead_source","campaign_name","lead_status",
                "stage_name","lead_owner","state","attempted",
                "service_name_lead","email","remarks","lead_name"]:
        if col not in df.columns:
            df[col] = ""

    df["seminar_date_str"] = df["seminar_date"].dt.strftime("%Y-%m-%d").fillna("")
    df["primary_order_date_str"] = df["primary_order_date"].dt.strftime("%Y-%m-%d").fillna("")
    df["due_zero"] = df["primary_due"] <= 0

    return df


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────
CREDENTIALS = {"admin": "admin123", "invesmate": "invesmate@2024"}

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


# ─────────────────────────────────────────────
# FILE UPLOAD PAGE
# ─────────────────────────────────────────────
def upload_page():
    st.markdown('<div class="section-header">📁 Upload Data Files</div>', unsafe_allow_html=True)
    st.markdown("Upload all three source files. The dashboard will auto-detect columns and build the full analysis.")

    c1, c2, c3 = st.columns(3)
    with c1:
        sem_file = st.file_uploader(
            "📋 Seminar Updated Sheet",
            type=["xlsx","xls","csv"],
            key="sem_file",
            help="Student attendance and seminar details"
        )
    with c2:
        conv_file = st.file_uploader(
            "💰 Conversion List",
            type=["xlsx","xls","csv"],
            key="conv_file",
            help="Orders, payment_received, GST, due amounts"
        )
    with c3:
        leads_file = st.file_uploader(
            "🎯 Leads Report",
            type=["xlsx","xls","csv"],
            key="leads_file",
            help="Webinar/Non-Webinar, lead source, campaign, owner etc."
        )

    if sem_file and conv_file and leads_file:
        if st.button("🚀 Build Dashboard", use_container_width=True, type="primary"):
            with st.spinner("Processing files and building analytics…"):
                try:
                    df = process_data(
                        sem_file.read(), conv_file.read(), leads_file.read(),
                        sem_file.name, conv_file.name, leads_file.name,
                    )
                    st.session_state["df"] = df
                    st.session_state["files_loaded"] = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Error processing files: {e}")
                    st.exception(e)
    else:
        missing = []
        if not sem_file:  missing.append("Seminar Sheet")
        if not conv_file: missing.append("Conversion List")
        if not leads_file: missing.append("Leads Report")
        st.info(f"Waiting for: {', '.join(missing)}")


# ─────────────────────────────────────────────
# MASTER FILTERS (sidebar)
# ─────────────────────────────────────────────
def render_filters(df):
    st.sidebar.markdown("## 🔧 Master Filters")
    st.sidebar.markdown("---")

    def opts(col, label="All"):
        vals = sorted(df[col].dropna().unique().tolist())
        vals = [v for v in vals if str(v).strip() not in ("","nan","NaT","None")]
        return [label] + vals

    # Date
    dates = sorted(df["seminar_date_str"].dropna().unique().tolist())
    dates = [d for d in dates if d]
    sel_date = st.sidebar.selectbox("📅 Seminar Date", ["All Dates"] + dates)

    date_min = df["seminar_date"].dropna().min().date() if df["seminar_date"].notna().any() else date.today()
    date_max = df["seminar_date"].dropna().max().date() if df["seminar_date"].notna().any() else date.today()
    date_range = st.sidebar.date_input("📅 Date Range", value=(date_min, date_max), min_value=date_min, max_value=date_max)

    st.sidebar.markdown("---")
    sel_place   = st.sidebar.selectbox("📍 Location / Place", opts("place"))
    sel_session = st.sidebar.selectbox("🌓 Session",          opts("session"))
    sel_trainer = st.sidebar.selectbox("👨‍🏫 Trainer",         opts("trainer"))

    st.sidebar.markdown("---")
    sel_conv    = st.sidebar.selectbox("✅ Converted Status", ["All","Converted","Not Converted"])
    sel_course  = st.sidebar.selectbox("📚 Primary Course",   opts("primary_course"))
    add_courses_all = sorted(set(c for row in df["additional_courses"] for c in row if c))
    sel_addcourse = st.sidebar.selectbox("➕ Additional Course", ["All"] + add_courses_all)
    sel_due     = st.sidebar.selectbox("💸 Due Status",        ["All","Due = 0","Has Due"])

    paid_max_val = int(df["primary_paid"].max()) if df["primary_paid"].max() > 0 else 100000
    paid_range = st.sidebar.slider("💰 Paid Amount (₹)", 0, paid_max_val, (0, paid_max_val), step=1000)

    st.sidebar.markdown("---")
    sel_leadtype = st.sidebar.selectbox("🌐 Lead Type",    opts("webinar_type"))
    sel_source   = st.sidebar.selectbox("📡 Lead Source",  opts("lead_source"))
    sel_campaign = st.sidebar.selectbox("📢 Campaign",     opts("campaign_name"))
    sel_lstatus  = st.sidebar.selectbox("📊 Lead Status",  opts("lead_status"))
    sel_stage    = st.sidebar.selectbox("🏷️ Stage Name",   opts("stage_name"))
    sel_owner    = st.sidebar.selectbox("👤 Lead Owner",   opts("lead_owner"))
    sel_state    = st.sidebar.selectbox("🗺️ State",        opts("state"))
    sel_attempt  = st.sidebar.selectbox("📞 Attempted",    opts("attempted"))

    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Reset Filters", use_container_width=True):
        st.rerun()

    # ── APPLY ──────────────────────────────
    fdf = df.copy()

    if sel_date != "All Dates":
        fdf = fdf[fdf["seminar_date_str"] == sel_date]
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        dr0 = pd.Timestamp(date_range[0])
        dr1 = pd.Timestamp(date_range[1])
        fdf = fdf[(fdf["seminar_date"] >= dr0) & (fdf["seminar_date"] <= dr1)]

    if sel_place   != "All":    fdf = fdf[fdf["place"]   == sel_place]
    if sel_session != "All":    fdf = fdf[fdf["session"] == sel_session]
    if sel_trainer != "All":    fdf = fdf[fdf["trainer"] == sel_trainer]
    if sel_conv == "Converted":     fdf = fdf[fdf["converted"]]
    if sel_conv == "Not Converted": fdf = fdf[~fdf["converted"]]
    if sel_course  != "All":    fdf = fdf[fdf["primary_course"] == sel_course]
    if sel_addcourse != "All":  fdf = fdf[fdf["additional_courses"].apply(lambda lst: sel_addcourse in lst)]
    if sel_due == "Due = 0":    fdf = fdf[fdf["primary_due"] <= 0]
    if sel_due == "Has Due":    fdf = fdf[fdf["primary_due"] > 0]
    fdf = fdf[(fdf["primary_paid"] >= paid_range[0]) & (fdf["primary_paid"] <= paid_range[1])]
    if sel_leadtype != "All":   fdf = fdf[fdf["webinar_type"] == sel_leadtype]
    if sel_source   != "All":   fdf = fdf[fdf["lead_source"]  == sel_source]
    if sel_campaign != "All":   fdf = fdf[fdf["campaign_name"] == sel_campaign]
    if sel_lstatus  != "All":   fdf = fdf[fdf["lead_status"]  == sel_lstatus]
    if sel_stage    != "All":   fdf = fdf[fdf["stage_name"]   == sel_stage]
    if sel_owner    != "All":   fdf = fdf[fdf["lead_owner"]   == sel_owner]
    if sel_state    != "All":   fdf = fdf[fdf["state"]        == sel_state]
    if sel_attempt  != "All":   fdf = fdf[fdf["attempted"]    == sel_attempt]

    return fdf


# ─────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────
def kpi_card(label, value, sub="", accent="#6366f1"):
    return f"""
    <div class="kpi-card" style="border-top-color:{accent}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-sub">{sub}</div>
    </div>"""

def render_kpis(fdf):
    conv    = fdf[fdf["converted"]]
    total   = len(fdf)
    n_conv  = len(conv)
    rate    = f"{(n_conv/total*100):.1f}%" if total else "0%"
    t_paid  = fdf["primary_paid"].sum()
    t_due   = fdf["primary_due"].sum()
    fp      = len(conv[conv["primary_due"] <= 0])
    hd      = len(conv[conv["primary_due"] > 0])
    uniq_c  = fdf["primary_course"].nunique()
    wbn     = len(fdf[fdf["webinar_type"] == "Webinar"])
    non_wbn = len(fdf[fdf["webinar_type"] == "Non Webinar"])
    add_rev = fdf["additional_paid"].sum()

    cols = st.columns(5)
    cards = [
        ("Total Attendees",    total,           "Filtered seminar attendees",  "#6366f1"),
        ("Converted",          n_conv,          "Post-seminar conversions",    "#10b981"),
        ("Conversion Rate",    rate,            "Attend → Purchase rate",      "#06b6d4"),
        ("Total Paid Amount",  fmt_inr(t_paid), "payment_received + GST",      "#f59e0b"),
        ("Total Due",          fmt_inr(t_due),  "Outstanding dues",            "#ef4444"),
    ]
    for i, (lbl, val, sub, clr) in enumerate(cards):
        cols[i].markdown(kpi_card(lbl, val, sub, clr), unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    cols2 = st.columns(5)
    cards2 = [
        ("Fully Paid",         fp,              "Due ≤ 0",                     "#10b981"),
        ("Has Due",            hd,              "Pending balance",             "#ef4444"),
        ("Unique Courses",     uniq_c,          "Distinct courses bought",     "#8b5cf6"),
        ("Webinar Leads",      wbn,             "From webinar source",         "#06b6d4"),
        ("Non-Webinar Leads",  non_wbn,         "Offline / walk-in",           "#f97316"),
    ]
    for i, (lbl, val, sub, clr) in enumerate(cards2):
        cols2[i].markdown(kpi_card(lbl, val, sub, clr), unsafe_allow_html=True)

    # Additional revenue row
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    cols3 = st.columns(5)
    cols3[0].markdown(kpi_card("Additional Revenue", fmt_inr(add_rev), "Cross-sell purchases", "#a855f7"), unsafe_allow_html=True)
    cols3[1].markdown(kpi_card("Avg Paid / Student", fmt_inr(t_paid/n_conv if n_conv else 0), "Per converted student", "#3b82f6"), unsafe_allow_html=True)
    cols3[2].markdown(kpi_card("Total Revenue", fmt_inr(t_paid + add_rev), "Primary + additional", "#f59e0b"), unsafe_allow_html=True)
    cols3[3].markdown(kpi_card("Attempted Leads", len(fdf[fdf["attempted"]=="Attempted"]), "Out of matched leads", "#10b981"), unsafe_allow_html=True)
    cols3[4].markdown(kpi_card("Unattempted Leads", len(fdf[fdf["attempted"]=="Unattempted"]), "Not yet contacted", "#ef4444"), unsafe_allow_html=True)


# ─────────────────────────────────────────────
# OVERVIEW CHARTS
# ─────────────────────────────────────────────
def render_overview(fdf):
    st.markdown('<div class="section-header">📅 Trends & Location Analysis</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        bydate = fdf.groupby("seminar_date_str").agg(
            Attendees=("attended","count"),
            Converted=("converted","sum")
        ).reset_index()
        fig = go.Figure()
        fig.add_bar(x=bydate["seminar_date_str"], y=bydate["Attendees"], name="Attendees",
                    marker_color="#6366f1", opacity=0.7)
        fig.add_bar(x=bydate["seminar_date_str"], y=bydate["Converted"], name="Converted",
                    marker_color="#10b981", opacity=0.9)
        fig.update_layout(
            title="Attendees & Conversions by Seminar Date",
            barmode="group", template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(t=50,b=30,l=20,r=20), height=320,
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        byloc = fdf.groupby("place").agg(
            Attendees=("attended","count"),
            Converted=("converted","sum"),
            Revenue=("primary_paid","sum")
        ).reset_index().sort_values("Attendees", ascending=False).head(12)
        fig2 = go.Figure()
        fig2.add_bar(x=byloc["place"], y=byloc["Attendees"], name="Attendees", marker_color="#6366f1", opacity=0.7)
        fig2.add_bar(x=byloc["place"], y=byloc["Converted"], name="Converted", marker_color="#10b981", opacity=0.9)
        fig2.update_layout(
            title="Attendees & Conversions by Location",
            barmode="group", template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(t=50,b=30,l=20,r=20), height=320,
        )
        st.plotly_chart(fig2, use_container_width=True)

    c3, c4, c5 = st.columns(3)

    with c3:
        sess = fdf.groupby("session").size().reset_index(name="Count")
        fig3 = px.pie(sess, names="session", values="Count", title="Session Split",
                      color_discrete_sequence=CHART_COLORS, hole=0.4)
        fig3.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                           margin=dict(t=50,b=10,l=10,r=10), height=280)
        st.plotly_chart(fig3, use_container_width=True)

    with c4:
        lt = fdf.groupby("webinar_type").size().reset_index(name="Count")
        lt = lt[lt["webinar_type"].str.strip() != ""]
        fig4 = px.pie(lt, names="webinar_type", values="Count", title="Webinar vs Non-Webinar",
                      color_discrete_sequence=CHART_COLORS, hole=0.4)
        fig4.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                           margin=dict(t=50,b=10,l=10,r=10), height=280)
        st.plotly_chart(fig4, use_container_width=True)

    with c5:
        rev_loc = fdf.groupby("place")["primary_paid"].sum().reset_index().sort_values("primary_paid", ascending=True).tail(10)
        fig5 = px.bar(rev_loc, x="primary_paid", y="place", orientation="h",
                      title="Revenue by Location (₹)", color_discrete_sequence=CHART_COLORS)
        fig5.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                           plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                           margin=dict(t=50,b=10,l=10,r=10), height=280)
        st.plotly_chart(fig5, use_container_width=True)

    # Trainer table
    st.markdown('<div class="section-header">👨‍🏫 Trainer Performance</div>', unsafe_allow_html=True)
    trainer_df = fdf.groupby("trainer").agg(
        Attendees=("attended","count"),
        Converted=("converted","sum"),
        Revenue=("primary_paid","sum"),
        AvgPaid=("primary_paid","mean"),
    ).reset_index()
    trainer_df["Conv Rate"] = (trainer_df["Converted"] / trainer_df["Attendees"] * 100).round(1).astype(str) + "%"
    trainer_df["Revenue"]   = trainer_df["Revenue"].apply(fmt_inr)
    trainer_df["AvgPaid"]   = trainer_df["AvgPaid"].apply(fmt_inr)
    trainer_df = trainer_df.sort_values("Attendees", ascending=False)
    trainer_df.columns = ["Trainer","Attendees","Converted","Revenue","Avg Paid","Conv Rate"]
    st.dataframe(trainer_df[["Trainer","Attendees","Converted","Conv Rate","Revenue","Avg Paid"]],
                 use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# COURSE ANALYSIS
# ─────────────────────────────────────────────
def render_courses(fdf):
    conv = fdf[fdf["converted"]].copy()
    if conv.empty:
        st.info("No converted students in current filter.")
        return

    byc = conv.groupby("primary_course").agg(
        Students=("attended","count"),
        Paid=("primary_paid","sum"),
        Due=("primary_due","sum"),
        Due0=("due_zero","sum"),
    ).reset_index().sort_values("Students", ascending=False)
    total = byc["Students"].sum()
    byc["Share %"] = (byc["Students"] / total * 100).round(1)
    byc["Avg Paid"] = (byc["Paid"] / byc["Students"]).round(0)

    c1, c2 = st.columns(2)

    with c1:
        fig = px.bar(byc.head(12), x="Students", y="primary_course", orientation="h",
                     title="Course-wise Student Count",
                     color="Students", color_continuous_scale=["#1e2d4a","#6366f1"])
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                          margin=dict(t=50,b=10,l=10,r=10), height=380,
                          yaxis_title="", xaxis_title="Students")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig2 = px.pie(byc.head(10), names="primary_course", values="Students",
                      title="Course Share by Student Count (Top 10)",
                      color_discrete_sequence=CHART_COLORS, hole=0.35)
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                           showlegend=False, margin=dict(t=50,b=10,l=10,r=10), height=380)
        st.plotly_chart(fig2, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        fig3 = px.bar(byc.head(12), x="Paid", y="primary_course", orientation="h",
                      title="Course-wise Revenue (₹ Paid Amount)",
                      color="Paid", color_continuous_scale=["#1e2d4a","#f59e0b"])
        fig3.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                           plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                           margin=dict(t=50,b=10,l=10,r=10), height=340,
                           yaxis_title="", xaxis_title="Paid Amount (₹)")
        st.plotly_chart(fig3, use_container_width=True)

    with c4:
        fig4 = px.bar(byc.head(10), x="primary_course", y=["Paid","Due"],
                      title="Paid vs Due by Course",
                      color_discrete_map={"Paid":"#10b981","Due":"#ef4444"},
                      barmode="stack")
        fig4.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                           plot_bgcolor="rgba(0,0,0,0)",
                           margin=dict(t=50,b=60,l=10,r=10), height=340,
                           xaxis_tickangle=-30, xaxis_title="")
        st.plotly_chart(fig4, use_container_width=True)

    st.markdown('<div class="section-header">📋 Course-wise Summary Table</div>', unsafe_allow_html=True)
    display = byc.copy()
    display["Paid"] = display["Paid"].apply(fmt_inr)
    display["Due"]  = display["Due"].apply(fmt_inr)
    display["Avg Paid"] = display["Avg Paid"].apply(fmt_inr)
    display.columns = ["Course","Students","Total Paid","Total Due","Due=0","Share %","Avg Paid"]
    st.dataframe(display[["Course","Students","Share %","Total Paid","Avg Paid","Total Due","Due=0"]],
                 use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# COMBO CROSS-SELL
# ─────────────────────────────────────────────
def render_combo(fdf):
    combo_buyers = fdf[fdf["primary_course"].str.contains("Power Of Trading", na=False, case=False)]
    with_other   = combo_buyers[combo_buyers["additional_courses"].apply(len) > 0]

    total_add_paid = with_other["additional_paid"].sum()
    cross_rate = f"{len(with_other)/len(combo_buyers)*100:.1f}%" if len(combo_buyers) else "0%"

    cols = st.columns(4)
    stats = [
        ("Combo Buyers",       len(combo_buyers), "#6366f1"),
        ("Also Bought More",   len(with_other),   "#10b981"),
        ("Cross-Sell Rate",    cross_rate,         "#06b6d4"),
        ("Additional Revenue", fmt_inr(total_add_paid), "#f59e0b"),
    ]
    for i, (lbl, val, clr) in enumerate(stats):
        cols[i].markdown(kpi_card(lbl, val, accent=clr), unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # Additional courses breakdown
    add_counts = {}
    add_rev    = {}
    for _, row in with_other.iterrows():
        for c in row["additional_courses"]:
            add_counts[c] = add_counts.get(c, 0) + 1
        for o in row.get("all_orders", []) if "all_orders" in row else []:
            pass

    # Simpler: explode additional_courses
    if len(with_other) > 0:
        exploded = with_other.explode("additional_courses")
        exploded = exploded[exploded["additional_courses"].notna() & (exploded["additional_courses"] != "")]
        if not exploded.empty:
            ac_counts = exploded.groupby("additional_courses").size().reset_index(name="Count").sort_values("Count", ascending=False).head(10)

            c1, c2 = st.columns(2)
            with c1:
                fig = px.bar(ac_counts, x="Count", y="additional_courses", orientation="h",
                             title="Top Additional Courses After Combo",
                             color_discrete_sequence=CHART_COLORS)
                fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                                  margin=dict(t=50,b=10,l=10,r=10), height=340, yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                fig2 = px.pie(ac_counts, names="additional_courses", values="Count",
                              title="Additional Course Distribution",
                              color_discrete_sequence=CHART_COLORS, hole=0.4)
                fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                                   showlegend=False, margin=dict(t=50,b=10,l=10,r=10), height=340)
                st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-header">👥 Combo Buyers — Student Level</div>', unsafe_allow_html=True)
    show = with_other[["name","mobile","place","seminar_date_str","primary_paid","additional_paid","additional_courses"]].copy()
    show["additional_courses"] = show["additional_courses"].apply(lambda x: ", ".join(x) if x else "—")
    show["primary_paid"]  = show["primary_paid"].apply(fmt_inr)
    show["additional_paid"] = show["additional_paid"].apply(fmt_inr)
    show.columns = ["Name","Mobile","Location","Seminar Date","Primary Paid","Add. Paid","Additional Courses"]
    st.dataframe(show, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# LEAD INTELLIGENCE
# ─────────────────────────────────────────────
def render_leads(fdf):
    # Lead KPIs
    cols = st.columns(5)
    lead_stats = [
        ("Leads Matched",  len(fdf[fdf["lead_source"] != ""]),          "#6366f1"),
        ("Webinar",        len(fdf[fdf["webinar_type"]=="Webinar"]),     "#06b6d4"),
        ("Non-Webinar",    len(fdf[fdf["webinar_type"]=="Non Webinar"]), "#8b5cf6"),
        ("Attempted",      len(fdf[fdf["attempted"]=="Attempted"]),      "#10b981"),
        ("Unattempted",    len(fdf[fdf["attempted"]=="Unattempted"]),    "#ef4444"),
    ]
    for i, (lbl, val, clr) in enumerate(lead_stats):
        cols[i].markdown(kpi_card(lbl, val, accent=clr), unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        src = fdf[fdf["lead_source"] != ""].groupby("lead_source").size().reset_index(name="Count").sort_values("Count", ascending=True).tail(12)
        fig = px.bar(src, x="Count", y="lead_source", orientation="h",
                     title="Lead Source Distribution", color_discrete_sequence=CHART_COLORS)
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                          margin=dict(t=50,b=10,l=10,r=10), height=340, yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        lst = fdf[fdf["lead_status"] != ""].groupby("lead_status").size().reset_index(name="Count")
        fig2 = px.pie(lst, names="lead_status", values="Count", title="Lead Status Breakdown",
                      color_discrete_sequence=CHART_COLORS, hole=0.4)
        fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                           showlegend=True, legend=dict(font=dict(size=10)),
                           margin=dict(t=50,b=10,l=10,r=10), height=340)
        st.plotly_chart(fig2, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        state_df = fdf[fdf["state"] != ""].groupby("state").size().reset_index(name="Count").sort_values("Count", ascending=True).tail(10)
        fig3 = px.bar(state_df, x="Count", y="state", orientation="h",
                      title="State-wise Lead Distribution", color_discrete_sequence=CHART_COLORS)
        fig3.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                           plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                           margin=dict(t=50,b=10,l=10,r=10), height=320, yaxis_title="")
        st.plotly_chart(fig3, use_container_width=True)

    with c4:
        owner_df = fdf[fdf["lead_owner"] != ""].groupby("lead_owner").agg(
            Count=("attended","count"), Converted=("converted","sum")
        ).reset_index().sort_values("Count", ascending=True).tail(10)
        fig4 = go.Figure()
        fig4.add_bar(x=owner_df["Count"],     y=owner_df["lead_owner"], name="Leads",     orientation="h", marker_color="#6366f1", opacity=0.7)
        fig4.add_bar(x=owner_df["Converted"], y=owner_df["lead_owner"], name="Converted", orientation="h", marker_color="#10b981", opacity=0.9)
        fig4.update_layout(title="Lead Owner Performance", barmode="overlay",
                           template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                           plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=50,b=10,l=10,r=10),
                           height=320, yaxis_title="")
        st.plotly_chart(fig4, use_container_width=True)

    # Campaign analysis
    st.markdown('<div class="section-header">📢 Campaign Performance</div>', unsafe_allow_html=True)
    camp = fdf[fdf["campaign_name"] != ""].groupby("campaign_name").agg(
        Leads=("attended","count"),
        Converted=("converted","sum"),
        Revenue=("primary_paid","sum"),
    ).reset_index()
    camp["Conv Rate"] = (camp["Converted"] / camp["Leads"] * 100).round(1).astype(str) + "%"
    camp["Revenue"]   = camp["Revenue"].apply(fmt_inr)
    camp = camp.sort_values("Leads", ascending=False)
    st.dataframe(camp[["campaign_name","Leads","Converted","Conv Rate","Revenue"]].rename(
        columns={"campaign_name":"Campaign"}
    ), use_container_width=True, hide_index=True)

    # Lead Intelligence Table
    st.markdown('<div class="section-header">📋 Lead Intelligence Table</div>', unsafe_allow_html=True)
    search = st.text_input("🔍 Search leads (name, mobile, location, source…)", key="lead_search")
    show = fdf[["name","mobile","place","seminar_date_str","converted","primary_course","primary_paid",
                "webinar_type","lead_source","lead_status","stage_name","lead_owner","state","attempted","email","remarks"]].copy()
    show["converted"]     = show["converted"].map({True:"✅ Yes", False:"❌ No"})
    show["primary_paid"]  = show["primary_paid"].apply(lambda x: fmt_inr(x) if x > 0 else "—")
    show.columns = ["Name","Mobile","Location","Seminar Date","Converted","Course","Paid",
                    "Lead Type","Source","Lead Status","Stage","Owner","State","Attempted","Email","Remarks"]
    if search:
        mask = show.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
        show = show[mask]
    st.caption(f"{len(show)} records")
    st.dataframe(show, use_container_width=True, hide_index=True, height=420)


# ─────────────────────────────────────────────
# STUDENT JOURNEY
# ─────────────────────────────────────────────
def render_journey(fdf):
    st.markdown('<div class="section-header">🗺️ Student Journey Table</div>', unsafe_allow_html=True)
    search = st.text_input("🔍 Search students…", key="journey_search")
    show = fdf[[
        "name","mobile","seminar_date_str","place","session","trainer","attended",
        "primary_course","primary_order_date_str","primary_paid","primary_due",
        "additional_courses","webinar_type","lead_source","lead_status","stage_name","lead_owner"
    ]].copy()
    show["attended"] = show["attended"].map({True:"✅"})
    show["primary_paid"] = show["primary_paid"].apply(lambda x: fmt_inr(x) if x > 0 else "—")
    show["primary_due"]  = show["primary_due"].apply(lambda x: fmt_inr(x) if x > 0 else "₹0")
    show["additional_courses"] = show["additional_courses"].apply(lambda x: " | ".join(x) if x else "—")
    show.columns = ["Name","Mobile","Seminar Date","Location","Session","Trainer","Attended",
                    "Primary Course","Order Date","Paid","Due","Additional Courses",
                    "Lead Type","Source","Lead Status","Stage","Owner"]
    if search:
        mask = show.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
        show = show[mask]
    st.caption(f"{len(show)} students")
    st.dataframe(show, use_container_width=True, hide_index=True, height=500)


# ─────────────────────────────────────────────
# DATA TABLES
# ─────────────────────────────────────────────
def render_tables(fdf):
    tab1, tab2, tab3 = st.tabs(["📋 Attendee Master", "✅ Converted Students", "📦 All Orders Summary"])

    with tab1:
        search = st.text_input("🔍 Search attendees…", key="att_search")
        show = fdf[["name","mobile","place","seminar_date_str","session","trainer",
                    "converted","primary_course","primary_paid","primary_due"]].copy()
        show["converted"]    = show["converted"].map({True:"✅ Yes", False:"❌ No"})
        show["primary_paid"] = show["primary_paid"].apply(lambda x: fmt_inr(x) if x > 0 else "—")
        show["primary_due"]  = show["primary_due"].apply(lambda x: fmt_inr(x) if x > 0 else "₹0")
        show.columns = ["Name","Mobile","Location","Seminar Date","Session","Trainer","Converted","Course","Paid","Due"]
        if search:
            mask = show.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
            show = show[mask]
        st.caption(f"{len(show)} attendees")
        st.dataframe(show, use_container_width=True, hide_index=True, height=400)
        csv = show.to_csv(index=False).encode()
        st.download_button("⬇️ Download CSV", csv, "attendees.csv", "text/csv")

    with tab2:
        conv = fdf[fdf["converted"]].copy()
        search2 = st.text_input("🔍 Search converted students…", key="conv_search")
        show2 = conv[["name","mobile","place","seminar_date_str","primary_course",
                       "primary_order_date_str","primary_paid","primary_due",
                       "additional_courses","webinar_type","lead_source"]].copy()
        show2["primary_paid"] = show2["primary_paid"].apply(fmt_inr)
        show2["primary_due"]  = show2["primary_due"].apply(lambda x: fmt_inr(x) if x > 0 else "₹0")
        show2["additional_courses"] = show2["additional_courses"].apply(lambda x: " | ".join(x) if x else "—")
        show2.columns = ["Name","Mobile","Location","Seminar Date","Course","Order Date","Paid","Due",
                          "Additional Courses","Lead Type","Source"]
        if search2:
            mask = show2.apply(lambda row: row.astype(str).str.contains(search2, case=False).any(), axis=1)
            show2 = show2[mask]
        st.caption(f"{len(show2)} converted students")
        st.dataframe(show2, use_container_width=True, hide_index=True, height=400)
        csv2 = show2.to_csv(index=False).encode()
        st.download_button("⬇️ Download CSV", csv2, "converted_students.csv", "text/csv")

    with tab3:
        summary = fdf.groupby("place").agg(
            Attendees=("attended","count"),
            Converted=("converted","sum"),
            Total_Paid=("primary_paid","sum"),
            Total_Due=("primary_due","sum"),
            Add_Revenue=("additional_paid","sum"),
        ).reset_index()
        summary["Conv Rate"] = (summary["Converted"] / summary["Attendees"] * 100).round(1).astype(str) + "%"
        summary["Total_Paid"] = summary["Total_Paid"].apply(fmt_inr)
        summary["Total_Due"]  = summary["Total_Due"].apply(fmt_inr)
        summary["Add_Revenue"] = summary["Add_Revenue"].apply(fmt_inr)
        summary.columns = ["Location","Attendees","Converted","Total Paid","Total Due","Add. Revenue","Conv Rate"]
        st.dataframe(summary, use_container_width=True, hide_index=True)
        csv3 = summary.to_csv(index=False).encode()
        st.download_button("⬇️ Download CSV", csv3, "location_summary.csv", "text/csv")


# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────
def main():
    # Session state defaults
    if "logged_in"    not in st.session_state: st.session_state["logged_in"]    = False
    if "files_loaded" not in st.session_state: st.session_state["files_loaded"] = False
    if "df"           not in st.session_state: st.session_state["df"]           = None

    # Login gate
    if not st.session_state["logged_in"]:
        login_page()
        return

    # File upload gate
    if not st.session_state["files_loaded"] or st.session_state["df"] is None:
        st.sidebar.markdown("### 📁 Data Files")
        if st.sidebar.button("🔄 Upload New Files"):
            st.session_state["files_loaded"] = False
            st.session_state["df"] = None
            st.rerun()
        upload_page()
        return

    df = st.session_state["df"]

    # Sidebar: allow re-upload
    st.sidebar.markdown("### 📁 Data")
    if st.sidebar.button("🔄 Upload New Files"):
        st.session_state["files_loaded"] = False
        st.session_state["df"] = None
        st.rerun()

    # Apply master filters
    fdf = render_filters(df)

    if fdf.empty:
        st.warning("⚠️ No data matches current filters. Please adjust your selections.")
        return

    # Navigation tabs
    tabs = st.tabs([
        "📊 Overview",
        "📚 Course Analysis",
        "🔗 Combo Cross-Sell",
        "🎯 Lead Intelligence",
        "🗺️ Student Journey",
        "📋 Data Tables",
    ])

    with tabs[0]:
        st.markdown('<div class="section-header">📊 Key Performance Indicators</div>', unsafe_allow_html=True)
        render_kpis(fdf)
        st.markdown("---")
        render_overview(fdf)

    with tabs[1]:
        render_courses(fdf)

    with tabs[2]:
        render_combo(fdf)

    with tabs[3]:
        render_leads(fdf)

    with tabs[4]:
        render_journey(fdf)

    with tabs[5]:
        render_tables(fdf)


if __name__ == "__main__":
    main()
