# Case study: building a data platform from zero

*Company details are anonymized. The code in this repository is a clean-room rebuild on synthetic data.*

## Context

A fast-growing healthcare and wellness organization ran its clinics on a single CRM. As it grew from a handful of clinics to two national brands, including an acquired franchise network, it still had no data platform. There was no warehouse, no shared definitions and no automated reporting.

## Before

Every report started as a CRM export. Someone downloaded the data, pasted it into Excel and calculated revenue, visits and memberships by hand. Each report computed its numbers slightly differently, so leadership regularly saw two versions of the same metric. Test accounts and duplicate customer records were counted as real. Reporting took days, broke whenever a new clinic opened, and could not keep up with an acquisition.

## What I built

- **Automated ingestion** from the CRM and the other core systems (accounting, marketing platforms) into a central data platform, replacing manual exports.
- **A layered data model:** raw data kept exactly as the source recorded it, a cleaning layer that fixes messy source data once, and a certified layer that all reporting must use.
- **A KPI Bible:** one written definition for every metric, with an owner and a certification tier, so "revenue" means the same thing in every report.
- **Data quality checks** that compare totals across layers, so certified revenue provably matches the source.
- **Standardized location scorecards and executive reporting**, which scaled from 5 clinics to 16, then absorbed a 42-location acquisition without rebuilding anything.
- **Automated distribution** of recurring reports, including franchisee-facing reporting.

## Outcome

- Manual Excel reporting replaced by 70+ automated recurring reports and scorecards across 58+ locations and two brands.
- One set of certified numbers for executives, the board and franchisees.
- A foundation ready for the next steps: a tool-independent cloud warehouse, and AI tools that answer questions only from certified data.

## What this repository shows

The same architecture at laptop scale: messy source, incremental ingestion, dbt transformation layers, a certified layer with tests, a KPI Bible that is validated on every run, and a dashboard that reads only certified data. It also documents two real bugs the tests caught during the build; see the README.

## Skills demonstrated

Data architecture, data engineering (Python, SQL, dbt), data modeling, data quality and certification, KPI governance, BI delivery, and building reporting that scales with acquisitions.
