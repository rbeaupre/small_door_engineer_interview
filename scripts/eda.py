"""
Task 1 — Exploratory Data Analysis: clinic_appointments.csv
Outputs:
  - Descriptive stats printed to terminal
  - Data quality flags printed to terminal
  - Charts saved to ../charts/
"""

import os
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.dirname(SCRIPT_DIR)
CSV_PATH   = os.path.join(ROOT_DIR, "case_study", "clinic_appointments.csv")
CHARTS_DIR = os.path.join(ROOT_DIR, "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

sns.set_theme(style="whitegrid", palette="muted")
DIVIDER = "─" * 72

def section(title: str) -> None:
    print(f"\n{DIVIDER}\n  {title}\n{DIVIDER}")

def flag(msg: str) -> None:
    print(f"  [FLAG] {msg}")

def info(msg: str) -> None:
    print(f"  {msg}")

def save(fig: plt.Figure, name: str) -> None:
    path = os.path.join(CHARTS_DIR, name)
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"  [CHART] saved → charts/{name}")


# ── Load ──────────────────────────────────────────────────────────────────────
section("Loading data")
df = pd.read_csv(CSV_PATH)
info(f"Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")
info(f"Columns: {list(df.columns)}")

# Parse dates
df["ScheduledDay"]    = pd.to_datetime(df["ScheduledDay"],    utc=True)
df["AppointmentDay"]  = pd.to_datetime(df["AppointmentDay"], utc=True)

# Derived: lead-time in calendar days
df["lead_time_days"] = (df["AppointmentDay"] - df["ScheduledDay"]).dt.total_seconds() / 86400
df["lead_time_days"] = df["lead_time_days"].round(2)

# Boolean target
df["no_show"] = df["NoShow"].map({"Yes": True, "No": False})


# ── 1. GRAIN & UNIQUENESS ─────────────────────────────────────────────────────
section("1 · Grain & Uniqueness")

appt_unique   = df["AppointmentID"].nunique()
total_rows    = len(df)
dup_appt      = total_rows - appt_unique
patient_count = df["PatientId"].nunique()

info(f"Total rows:          {total_rows:,}")
info(f"Unique AppointmentID:{appt_unique:,}")
info(f"Unique PatientId:    {patient_count:,}")

if dup_appt:
    flag(f"{dup_appt:,} duplicate AppointmentIDs — grain is NOT appointment-level!")
else:
    info("AppointmentID is unique — grain confirmed as one row per appointment.")

appts_per_patient = df.groupby("PatientId")["AppointmentID"].count()
info(f"\nAppointments per patient:")
info(str(appts_per_patient.describe().round(2)))

repeat_patients = (appts_per_patient > 1).sum()
max_appts       = appts_per_patient.max()
info(f"\nPatients with >1 appointment: {repeat_patients:,}  ({repeat_patients/patient_count*100:.1f}% of patients)")
info(f"Max appointments for a single patient: {max_appts}")

if repeat_patients / patient_count > 0.3:
    flag(">30% of patients appear multiple times — patient is NOT an independent unit of analysis. "
         "Any per-patient aggregate must account for repeated measures.")

# Chart: appointments per patient (capped histogram)
fig, ax = plt.subplots(figsize=(8, 4))
cap = 20
capped = appts_per_patient.clip(upper=cap)
ax.hist(capped, bins=range(1, cap + 2), edgecolor="white", align="left")
ax.set_xlabel("Appointments per patient (capped at 20)")
ax.set_ylabel("Number of patients")
ax.set_title("Distribution of appointments per patient")
save(fig, "01_appts_per_patient.png")


# ── 2. DATE QUALITY ───────────────────────────────────────────────────────────
section("2 · Date Quality")

neg_lead      = df[df["lead_time_days"] < 0]
same_day      = df[df["lead_time_days"].between(0, 1, inclusive="left")]
far_future    = df[df["lead_time_days"] > 180]

info(f"Negative lead-time (scheduled AFTER appointment): {len(neg_lead):,}")
info(f"Same-day appointments (lead_time < 1 day):        {len(same_day):,}")
info(f"Lead-time > 180 days:                             {len(far_future):,}")

if len(neg_lead):
    flag(f"{len(neg_lead):,} rows where ScheduledDay > AppointmentDay. "
         "Likely data-entry errors or timezone artifacts. "
         "Recommend: exclude from lead-time analysis; keep for no-show counts.")

info(f"\nLead-time (days) summary:")
info(str(df["lead_time_days"].describe().round(2)))

# Chart: lead-time distribution (exclude extreme negatives for readability)
plot_df = df[df["lead_time_days"].between(-5, 180)]
fig, ax = plt.subplots(figsize=(9, 4))
ax.hist(plot_df["lead_time_days"], bins=90, edgecolor="none")
ax.axvline(0, color="red", linestyle="--", linewidth=1, label="Same-day threshold")
ax.set_xlabel("Lead time (days): AppointmentDay − ScheduledDay")
ax.set_ylabel("Appointments")
ax.set_title("Lead-time distribution (−5 to 180 days shown)")
ax.legend()
save(fig, "02_lead_time_distribution.png")


# ── 3. AGE ────────────────────────────────────────────────────────────────────
section("3 · Age")

info(str(df["Age"].describe().round(2)))

neg_age  = (df["Age"] < 0).sum()
zero_age = (df["Age"] == 0).sum()
old_age  = (df["Age"] > 110).sum()

if neg_age:
    flag(f"{neg_age:,} rows with negative Age — impossible, needs investigation.")
if zero_age:
    flag(f"{zero_age:,} rows with Age == 0 — could be infants (valid) or sentinel value.")
if old_age:
    flag(f"{old_age:,} rows with Age > 110 — plausible outliers or data errors.")

# Chart: age distribution with flags
fig, ax = plt.subplots(figsize=(9, 4))
ax.hist(df["Age"].clip(-5, 120), bins=61, edgecolor="none")
ax.axvline(0,   color="red",    linestyle="--", linewidth=1, label="Age = 0")
ax.axvline(110, color="orange", linestyle="--", linewidth=1, label="Age = 110")
ax.set_xlabel("Age (years)")
ax.set_ylabel("Appointments")
ax.set_title("Age distribution")
ax.legend()
save(fig, "03_age_distribution.png")


# ── 4. GENDER ─────────────────────────────────────────────────────────────────
section("4 · Gender")

gender_counts = df["Gender"].value_counts()
info(str(gender_counts))

unexpected_genders = set(df["Gender"].unique()) - {"F", "M"}
if unexpected_genders:
    flag(f"Unexpected gender values: {unexpected_genders}")

# Chart
fig, ax = plt.subplots(figsize=(5, 4))
gender_counts.plot(kind="bar", ax=ax, edgecolor="white")
ax.set_xlabel("Gender")
ax.set_ylabel("Appointments")
ax.set_title("Appointments by gender")
ax.tick_params(axis="x", rotation=0)
save(fig, "04_gender_distribution.png")


# ── 5. CLINIC VOLUME ──────────────────────────────────────────────────────────
section("5 · Clinic Volume")

clinic_counts = df["Clinic"].value_counts()
n_clinics     = clinic_counts.shape[0]
info(f"Distinct clinics: {n_clinics}")
info(f"\nTop 10 by appointment volume:\n{clinic_counts.head(10).to_string()}")
info(f"\nBottom 10 by appointment volume:\n{clinic_counts.tail(10).to_string()}")

cv = clinic_counts.std() / clinic_counts.mean()
info(f"\nCoefficient of variation across clinics: {cv:.2f}")
if cv > 1.0:
    flag("High volume disparity across clinics (CV > 1.0). "
         "No-show rates must be volume-weighted or aggregated carefully.")

# Chart: clinic volume (sorted bar, top 30 for readability)
top30 = clinic_counts.head(30)
fig, ax = plt.subplots(figsize=(12, 5))
top30.plot(kind="bar", ax=ax, edgecolor="none")
ax.set_xlabel("Clinic")
ax.set_ylabel("Appointments")
ax.set_title("Appointment volume — top 30 clinics")
ax.tick_params(axis="x", rotation=45)
save(fig, "05a_clinic_volume_top30.png")

# Chart: histogram — how many clinics have N appointments
fig, ax = plt.subplots(figsize=(8, 4))
ax.hist(clinic_counts.values, bins=30, edgecolor="white")
ax.set_xlabel("Appointments per clinic")
ax.set_ylabel("Number of clinics")
ax.set_title("Distribution of appointment volume across clinics")
save(fig, "05b_clinics_by_appt_count.png")


# ── 6. NO-SHOW RATE ───────────────────────────────────────────────────────────
section("6 · No-Show Rate")

overall_ns = df["no_show"].mean()
info(f"Overall no-show rate: {overall_ns:.2%}")

ns_by_clinic = (
    df.groupby("Clinic")["no_show"]
    .agg(["mean", "count"])
    .rename(columns={"mean": "no_show_rate", "count": "appointments"})
    .sort_values("no_show_rate", ascending=False)
)
info(f"\nNo-show rate by clinic (top 10):\n{ns_by_clinic.head(10).round(3).to_string()}")
info(f"\nNo-show rate by clinic (bottom 10):\n{ns_by_clinic.tail(10).round(3).to_string()}")

# Chart: scatter — volume vs. no-show rate
fig, ax = plt.subplots(figsize=(9, 5))
ax.scatter(
    ns_by_clinic["appointments"],
    ns_by_clinic["no_show_rate"],
    alpha=0.7, edgecolors="none"
)
ax.set_xlabel("Total appointments")
ax.set_ylabel("No-show rate")
ax.set_title("Clinic volume vs. no-show rate")
ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
save(fig, "06a_clinic_volume_vs_noshowrate.png")

# Chart: no-show rate distribution across clinics
fig, ax = plt.subplots(figsize=(8, 4))
ax.hist(ns_by_clinic["no_show_rate"], bins=20, edgecolor="white")
ax.axvline(overall_ns, color="red", linestyle="--", label=f"Overall {overall_ns:.1%}")
ax.set_xlabel("No-show rate")
ax.set_ylabel("Number of clinics")
ax.set_title("Distribution of no-show rates across clinics")
ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
ax.legend()
save(fig, "06b_noshowrate_distribution_by_clinic.png")


# ── 7. DISABILITY COLUMN ──────────────────────────────────────────────────────
section("7 · Disability column (not a boolean)")

disability_counts = df["Disability"].value_counts().sort_index()
info(f"Distinct values:\n{disability_counts.to_string()}")

if disability_counts.index.max() > 1:
    flag("Disability contains values > 1 — this is an ordinal count, not a boolean flag. "
         "Treating it as binary will collapse meaningful severity distinctions.")


# ── 8. CONDITION FLAGS & CORRELATIONS ─────────────────────────────────────────
section("8 · Condition flags & no-show correlations")

condition_cols = ["LowIncome", "Hypertension", "Diabetes", "SubstanceUseDisorder",
                  "Disability", "SMSReminder"]

prev_table = (
    df[condition_cols + ["no_show"]]
    .assign(Disability_any=lambda d: (d["Disability"] > 0).astype(int))
    .drop(columns=["Disability"])
)

for col in condition_cols:
    if col == "Disability":
        rate_0 = df.loc[df["Disability"] == 0, "no_show"].mean()
        rate_1 = df.loc[df["Disability"] > 0,  "no_show"].mean()
        info(f"  {col:25s}  no-show if 0: {rate_0:.2%}  | if >0: {rate_1:.2%}")
    else:
        rate_0 = df.loc[df[col] == 0, "no_show"].mean()
        rate_1 = df.loc[df[col] == 1, "no_show"].mean()
        info(f"  {col:25s}  no-show if 0: {rate_0:.2%}  | if 1:  {rate_1:.2%}")

if df.loc[df["SMSReminder"] == 1, "no_show"].mean() > df.loc[df["SMSReminder"] == 0, "no_show"].mean():
    flag("SMS reminders are associated with HIGHER no-show rates — counterintuitive. "
         "Likely a selection-bias artifact: reminders may be sent preferentially to "
         "high-risk / long lead-time patients.")

# Chart: no-show rate by binary condition flag
fig, ax = plt.subplots(figsize=(9, 5))
labels, rates_0, rates_1 = [], [], []
for col in condition_cols:
    labels.append(col)
    if col == "Disability":
        rates_0.append(df.loc[df["Disability"] == 0, "no_show"].mean())
        rates_1.append(df.loc[df["Disability"] > 0,  "no_show"].mean())
    else:
        rates_0.append(df.loc[df[col] == 0, "no_show"].mean())
        rates_1.append(df.loc[df[col] == 1, "no_show"].mean())

x = np.arange(len(labels))
w = 0.35
ax.bar(x - w/2, rates_0, w, label="Flag = 0", edgecolor="white")
ax.bar(x + w/2, rates_1, w, label="Flag = 1 (or > 0)", edgecolor="white")
ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=20, ha="right")
ax.set_ylabel("No-show rate")
ax.set_title("No-show rate by condition / flag")
ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
ax.legend()
save(fig, "07_noshowrate_by_flag.png")


# ── 9. LEAD-TIME vs. NO-SHOW ──────────────────────────────────────────────────
section("9 · Lead-time vs. no-show rate")

# Negative lead-time rows are excluded from this analysis (kept in no-show counts above).
# They are most likely same-day bookings recorded after a time-of-day cutoff that makes
# ScheduledDay appear to follow AppointmentDay due to timezone/truncation artifacts.
excluded = df[df["lead_time_days"] < 0]
info(f"Excluding {len(excluded):,} rows with negative lead-time from this section "
     f"({len(excluded)/len(df)*100:.1f}% of dataset). These are retained in all other analyses.")

valid_lead = df[df["lead_time_days"] >= 0].copy()
valid_lead["lead_bucket"] = pd.cut(
    valid_lead["lead_time_days"],
    bins=[-0.001, 0, 7, 14, 30, 60, 90, 180, 9999],
    labels=["Same-day", "1–7d", "8–14d", "15–30d", "31–60d", "61–90d", "91–180d", "180d+"]
)
lead_ns = (
    valid_lead.groupby("lead_bucket", observed=True)["no_show"]
    .agg(["mean", "count"])
    .rename(columns={"mean": "no_show_rate", "count": "appointments"})
)
info(str(lead_ns.round(3)))

fig, ax = plt.subplots(figsize=(9, 4))
ax.bar(lead_ns.index.astype(str), lead_ns["no_show_rate"], edgecolor="white")
ax.set_xlabel("Lead time bucket")
ax.set_ylabel("No-show rate")
ax.set_title("No-show rate by lead-time bucket")
ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
ax.tick_params(axis="x", rotation=20)
save(fig, "08_noshowrate_by_leadtime.png")


# ── SUMMARY ───────────────────────────────────────────────────────────────────
section("Summary of FLAGS")
print()
flags_summary = [
    ("Negative lead-time rows",        len(neg_lead)),
    ("Age == 0",                        zero_age),
    ("Age < 0",                         neg_age),
    ("Age > 110",                       old_age),
    ("Duplicate AppointmentIDs",        dup_appt),
    ("Disability values > 1",           int((df["Disability"] > 1).sum())),
]
for label, count in flags_summary:
    marker = "[FLAG]" if count else "[OK]  "
    print(f"  {marker}  {label}: {count:,}")

print(f"\n  Charts written to: {CHARTS_DIR}\n")
