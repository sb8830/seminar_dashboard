# 📊 Invesmate Seminar Analytics Dashboard

A production-grade Streamlit dashboard for offline seminar performance analysis.  
Traces every seminar attendee → conversion → lead intelligence across 3 data files.

---

## 🚀 Deploy on Streamlit Community Cloud

1. **Fork or push this repo to GitHub**
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → select your repo → set `app.py` as the main file
4. Click **Deploy** — done!

---

## 📁 Project Structure

```
seminar_dashboard/
├── app.py                  # Main Streamlit application
├── requirements.txt        # Python dependencies
├── .streamlit/
│   └── config.toml         # Dark theme configuration
└── README.md
```

---

## 🔐 Login Credentials

| Username   | Password         |
|------------|-----------------|
| `admin`    | `admin123`       |
| `invesmate`| `invesmate@2024` |

---

## 📂 File Upload

After login, upload all **3 files** on the upload page:

| File | Description |
|------|-------------|
| **Seminar Updated Sheet** | `.xlsx` or `.csv` — attendance, seminar date, location, trainer |
| **Conversion List** | `.xlsx` — orders, payment_received, total_gst, total_due |
| **Leads Report** | `.xlsx` — webinar/non-webinar, lead source, campaign, owner |

The app **auto-detects column names** flexibly — no renaming needed.

---

## 📊 Dashboard Pages

### 1. Overview
- 15 KPI cards (attendees, conversions, revenue, dues, webinar/non-webinar splits)
- Conversion trends by seminar date
- Attendees & conversions by location
- Session split, lead type split, revenue by location
- Trainer performance table

### 2. Course Analysis
- Course-wise student count (horizontal bar)
- Course share pie (by student count)
- Course-wise revenue
- Paid vs Due stacked by course
- Full course summary table with share %, avg paid

### 3. Combo Cross-Sell
- "Power Of Trading & Investing Combo → Other Course Buyers" analysis
- Cross-sell rate, additional revenue
- Top additional courses bought after combo
- Student-level combo cross-sell table

### 4. Lead Intelligence
- Lead KPIs (matched, webinar, non-webinar, attempted, unattempted)
- Lead source distribution
- Lead status breakdown
- State-wise leads
- Lead owner performance
- Campaign performance table
- Full lead intelligence table with search

### 5. Student Journey
- Complete per-student view: Seminar → Order → Lead data
- Searchable, sortable full-width table

### 6. Data Tables
- Attendee Master Table (with CSV download)
- Converted Students Table (with CSV download)
- Location Summary Table (with CSV download)

---

## 🔧 Master Filters (20 filters, all interconnected)

All filters live in the sidebar and affect every page:

- Seminar Date (single + range)
- Location / Place
- Session
- Trainer
- Converted Status
- Primary Course
- Additional Course
- Due Status (Due=0 / Has Due)
- Paid Amount Range (slider)
- Lead Type (Webinar / Non-Webinar)
- Lead Source
- Campaign Name
- Lead Status
- Stage Name
- Lead Owner
- State
- Attempted / Unattempted

---

## 💡 Business Logic

- **Attendee-first**: Only seminar attendees are the base population
- **Post-seminar conversion only**: Orders before seminar date are excluded
- **Preferred course**: "Power Of Trading & Investing Combo Course" is the primary course if present
- **Paid Amount** = `payment_received + total_gst` (NOT total_amount)
- **Due = 0** means `total_due <= 0`
- **Mobile matching**: Cleaned to last 10 digits across all 3 files

---

## 🛠️ Local Development

```bash
git clone https://github.com/YOUR_USERNAME/seminar_dashboard
cd seminar_dashboard
pip install -r requirements.txt
streamlit run app.py
```

---

## 📦 Dependencies

```
streamlit>=1.32.0
pandas>=2.0.0
plotly>=5.18.0
openpyxl>=3.1.0
xlrd>=2.0.1
```
