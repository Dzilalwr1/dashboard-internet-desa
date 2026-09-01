# AGENTS.md

## Role

You are working as a software engineer and data analyst
for the Internet Desa Dashboard project.

Your responsibility is to help develop, debug, test, and
improve the dashboard without changing the project's
core analytical objectives.

---

## Project Objective

Build a web-based analytical dashboard where:

Input:
Excel file

Process:
Validation → Cleaning → Analysis → Visualization

Output:
Interactive web dashboard

The dashboard must be reusable when the Excel dataset
is updated monthly.

---

## Important Context

This project is the final project for a PKL.

The project is NOT primarily a CRUD application.

The main purpose is:

- data processing
- data analysis
- data visualization
- monitoring
- generating analytical insights

Do not introduce unnecessary CRUD functionality,
authentication, database systems, or unrelated features
unless explicitly requested.

---

## Dataset

The main dataset contains Internet Desa information.

The Excel file may contain multiple sheets.

The primary dashboard sheet is:

`data_dashboard`

The dataset is longitudinal.

One location can appear multiple times because the same
location is recorded across different months.

Example:

Desa A
- June 2025
- July 2025
- August 2025
- ...
- January 2026

Therefore:

RECORD ≠ LOCATION

Do not count every row as a unique village.

---

## Location Identity

A location should be identified using:

Kabupaten + Kecamatan + Desa

Do not use Desa alone as a unique identifier.

---

## Main Analysis

The dashboard should support:

1. Descriptive analysis
2. Comparative analysis
3. Temporal analysis
4. Spatial analysis
5. Location-priority analysis

---

## Analysis Rules

### Descriptive

Calculate:

- total records
- total unique locations
- total districts
- total ISPs
- evaluation distribution
- usage distribution

### Comparative

Compare:

- Kabupaten
- ISP

When comparing groups, prefer percentages/proportions
instead of raw counts when appropriate.

This prevents groups with more records from automatically
appearing worse.

### Temporal

Use:

- Tahun
- Bulan
- Bulan No

Always preserve chronological order.

Never sort months alphabetically.

### Spatial

Latitude and longitude should be treated as geographic
coordinates.

Invalid coordinates should not break the dashboard.

---

## Evaluation Categories

Use the original categories from the dataset.

Possible categories:

- SANGAT OPTIMAL
- OPTIMAL
- KURANG OPTIMAL
- TIDAK OPTIMAL
- TIDAK TERDETEKSI
- TIDAK AKTIF
- BELUM TERPASANG

Do not change the meaning of these categories.

Do not invent new evaluation categories unless explicitly
requested.

---

## Problematic Conditions

For monitoring purposes, the following categories can be
considered attention/problem conditions:

- TIDAK OPTIMAL
- KURANG OPTIMAL
- TIDAK TERDETEKSI
- TIDAK AKTIF
- BELUM TERPASANG

This classification is an analytical rule for the dashboard,
not a replacement for the official evaluation definition.

---

## Data Updating

The dashboard MUST NOT depend on a hardcoded filename.

Bad:

pd.read_excel("Internet Desa 2026.xlsx")

Preferred:

User uploads an Excel file
→ validate
→ clean
→ analyze
→ visualize

The dashboard should continue working when new monthly
data is added, provided the required structure remains
compatible.

---

## Dashboard Requirements

The dashboard should contain:

### Overview

- KPI
- evaluation distribution
- summary insights

### Regional Analysis

- Kabupaten comparison
- ISP comparison

### Temporal Analysis

- monthly trends
- evaluation changes

### Spatial Analysis

- Internet Desa map
- location information

### Detail Data

- filtered dataset
- detailed records

---

## Insight Requirements

Insights MUST be generated dynamically from the uploaded data.

Do not hardcode statements such as:

"Kutai Kartanegara has the highest number..."

Instead calculate the result first.

Example:

data
→ groupby Kabupaten
→ calculate proportion
→ find maximum
→ generate insight

Insights should remain correct when the Excel file changes.

---

## Code Architecture

Keep responsibilities separated.

`app.py`
- Streamlit UI
- page layout
- interaction

`utils/data_processing.py`
- Excel loading
- validation
- cleaning
- standardization

`utils/analysis.py`
- analytical calculations

`utils/insights.py`
- analytical interpretation
- dynamic insight generation

Avoid putting all logic directly inside `app.py`.

---

## Development Rules

Before modifying code:

1. Inspect the existing implementation.
2. Understand the data flow.
3. Reuse existing functions when possible.
4. Avoid unnecessary rewrites.
5. Keep analytical logic separate from UI logic.

After modifying code:

1. Run syntax checks.
2. Test with the actual dataset.
3. Check numerical results.
4. Check filters.
5. Check visualizations.
6. Check edge cases.

---

## Data Integrity

Never silently:

- delete records
- change evaluation categories
- alter location names
- fabricate missing values
- change analytical definitions

If cleaning changes the data significantly,
make the transformation explicit.

---

## Important Constraint

The dashboard is an analytical and monitoring tool.

Do not claim that an analytical result represents
an official government decision unless the dataset
or project specification explicitly establishes it.

---

## Current Development Priority

Priority order:

1. Correct data processing
2. Correct analytical calculations
3. Correct visualization
4. Dynamic insights
5. User interface
6. Performance optimization
7. Deployment

Do not prioritize visual styling over analytical correctness.

---

## Expected Agent Behavior

When a task is ambiguous:

- inspect the existing code first;
- inspect the dataset structure;
- explain assumptions;
- choose the simplest solution consistent with
  the project requirements.

When an analytical definition is unclear,
do not silently invent a methodology.

Ask for clarification or clearly mark the assumption.

---

## Definition of Done

A feature is considered complete when:

- it works with the current dataset;
- it works after uploading an updated dataset;
- calculations are correct;
- filters work;
- visualization matches the filtered data;
- no hardcoded dataset-specific values are required;
- code remains maintainable.