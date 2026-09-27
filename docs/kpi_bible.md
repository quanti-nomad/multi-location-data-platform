# KPI Bible

*Generated from `kpis/kpi_bible.yml` on every pipeline run. Do not edit by hand.*

Every KPI below is validated against the certified warehouse: its source model is certified, and its column is documented and present.

| KPI | Definition | Formula | Tier | Source |
| --- | --- | --- | --- | --- |
| **Net Revenue** | Settled sales and refunds for real customers, excluding voided payments and test accounts. | `sum(fct_payments.amount_cents) / 100` | board | `kpi_location_monthly.net_revenue` |
| **Membership Revenue** | Net revenue from recurring membership charges. | `sum(amount_cents) where revenue_stream = 'membership'` | board | `kpi_location_monthly.membership_revenue` |
| **Service Revenue** | Net revenue from individual services, including refunds of those services. | `sum(amount_cents) where revenue_stream = 'service'` | executive | `kpi_location_monthly.service_revenue` |
| **Active Members** | Memberships active at any point in the month, including those that start or end in it. | `count(fct_membership_months rows)` | board | `kpi_location_monthly.active_members` |
| **New Members** | Memberships whose start date falls in the month. | `count where is_new` | executive | `kpi_location_monthly.new_members` |
| **Member Churn Rate** | Memberships ending in the month divided by memberships active at the start of the month. | `churned_members / (active_members - new_members)` | board | `kpi_location_monthly.member_churn_rate` |
| **Completed Visits** | Appointments with a completed status for real customers. | `count(fct_appointments) where status = 'completed'` | executive | `kpi_location_monthly.completed_visits` |
| **No-Show Rate** | No-show appointments divided by all scheduled appointments in the month. | `no_shows / appointments_scheduled` | operational | `kpi_location_monthly.no_show_rate` |
| **Revenue per Visit** | Service revenue divided by completed visits. Membership revenue is excluded. | `service_revenue / completed_visits` | operational | `kpi_location_monthly.revenue_per_visit` |
| **Lead Conversion Rate** | Leads created in the month that became real customers, divided by all leads created in the month. | `converted_leads / leads` | executive | `kpi_location_monthly.lead_conversion_rate` |
