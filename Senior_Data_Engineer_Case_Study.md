# Senior Data Engineer — Take-Home Case Study

**Time budget:** 3–4 hours (we mean it — we're evaluating judgment, not volume)
**Deliverable:** A short deck or doc (max 10 slides / 4 pages) + a working repo
**Follow-up:** 45-minute panel discussion where you walk us through your decisions

---

## The Scenario

You've just joined a mid-stage startup that operates **medical clinics across a large metro area**. The company has ~80 locations, is growing fast, and has never had a data engineer. Today, analysts query production databases directly, dashboards break every Monday, and nobody trusts the numbers because Finance, Ops, and the CEO all calculate them differently.

Leadership wants to understand **appointment utilization and no-show behavior** — how effectively each clinic fills its available capacity, and what drives patients to miss appointments. This sounds simple, but nobody agrees on the definitions. How do you measure a clinic's "no-show rate" when scheduling volume varies wildly by location? Should you account for lead time between scheduling and appointment date? Does an SMS reminder change the denominator or just the numerator? What does "high-risk" even mean when you have ten correlated patient attributes?

## The Dataset

You've been given `clinic_appointments.csv` — an extract from the scheduling system. ~110K appointments across 80+ clinic locations. Columns:

- `PatientId`, `AppointmentID`
- `ScheduledDay`, `AppointmentDay`
- `Age`, `Gender`
- `Clinic`
- `LowIncome`, `Hypertension`, `Diabetes`, `SubstanceUseDisorder`, `Disability`
- `SMSReminder`
- `NoShow` (Yes/No)

This CSV is your source system.

---

## Your Task

### 1. Explore and Profile the Data (30–45 min)

Pull the dataset and explore it. Document what you find — quality issues, gaps, oddities, implicit assumptions. Don't clean everything; tell us what you'd clean and what you'd leave, and why.

Things worth investigating (not an exhaustive list):
- What's the grain of this table? Is it what you'd expect?
- Are there patients with multiple appointments? What does that imply for modeling?
- What's going on with the date columns — are there records where the scheduled date is *after* the appointment date?
- Are age values realistic? What's the distribution?
- How many clinics are there, and does the volume distribution across them look reasonable?
- What does `Disability` actually encode? (Hint: look at the distinct values — it's not a boolean.)

### 2. Model It (60–90 min)

Design and implement a dimensional model (or whatever modeling approach you'd choose — defend it) that would support a **"Clinic Utilization & No-Show Dashboard."** The dashboard needs to answer:

- Which clinics have the highest no-show rates, and is that stable over time?
- Does the gap between scheduling and appointment date predict no-shows?
- Do SMS reminders correlate with lower no-show rates, or is that confounded?
- What does a "patient risk profile" look like across clinics?

Implement your model in **DuckDB, SQLite, or Postgres** — whatever you'd reach for. Include the DDL and the transformation SQL/Python that loads it. We should be able to run it.

### 3. Make Three Hard Calls (the actual test)

In your deliverable, explicitly document three decisions you made where reasonable engineers would disagree. For each one:

- What was the decision?
- What were the alternatives you considered?
- What did you choose and why?
- What would change your mind?

Examples of the kind of decisions we mean (don't limit yourself to these):
- How you handled patients who appear many times — is each appointment independent, or do you build a patient-level entity with slowly-changing attributes?
- Whether you computed "lead time" as a first-class dimension or a derived metric, and how you handled the rows where it's negative
- How you defined "clinic utilization" when you have no data on actual *capacity* — only completed and missed appointments
- Whether you chose star schema, OBT, or something else — and why
- How you handled the `Disability` column (it's not a boolean despite looking like one)
- Whether `SMSReminder` belongs in a fact or a dimension, and whether it's an attribute of the appointment or the patient

### 4. Write One Query You're Proud Of (15 min)

Write a single analytical query against your model that surfaces something non-obvious in the data. Annotate it briefly — what does it show and why would a clinic operator care?

### 5. Sketch the Production Version (30 min)

On one page (or 2 slides), sketch what this pipeline looks like if you were building it for real at a growing multi-clinic company. Not a polished architecture diagram — a rough sketch that answers:

- Where does the data land, how does it move, what orchestrates it?
- How do you test that the numbers are right?
- What breaks first when a source schema changes upstream?
- How does an analyst know if today's data is stale?
- How do you handle the fact that Operations and Finance will inevitably want different definitions of "no-show rate"?

We don't care what tools you name-drop. We care that your choices hang together and that you can explain the tradeoffs.

---

## What We're Evaluating

| | Matters a lot | Doesn't matter |
|---|---|---|
| **Judgment** | Why you made the calls you made | Whether you picked the "right" tool |
| **Communication** | Can you explain tradeoffs to a non-technical stakeholder? | Slide design |
| **Craft** | Is your SQL/Python clean and intentional? | Did you use every feature of dbt |
| **Pragmatism** | Did you scope appropriately for 3–4 hours? | Did you build a complete production system |
| **Curiosity** | Did you find something interesting in the data? | Did you build 15 dashboards |

## What to Submit

- A repo (GitHub, zip, whatever) with your code — we will run it
- A short doc or deck walking through your decisions
- Be ready to screen-share and walk us through it live

## A Note on AI Tools

You're welcome to use AI tools the same way you would on the job. But you'll be defending every decision in a live panel, and we'll ask you to modify things on the fly. The people who do well on this are the ones who actually explored the data and formed opinions — not the ones who generated the most polished output.
