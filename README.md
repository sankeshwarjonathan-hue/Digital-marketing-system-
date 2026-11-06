# DMMS Streamlit Interface

A simple data-entry interface for the DMMS database, built with Streamlit and
`mysql-connector-python`. It lets you add and view records for all six tables:
`users`, `client`, `campaigns`, `tasks`, `performance`, and `invoice`.

## Setup

1. Make sure your `dmms_db` database and its six tables already exist in MySQL
   (Phase 1/2 of your project).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   streamlit run app.py
   ```
4. In the sidebar, enter your MySQL host, port, user, password, and database
   name, then click **Connect**.

## How it works

- Each page (Users, Clients, Campaigns, Tasks, Performance, Invoices)
  has a form to insert a new row and a table showing existing rows.
- Foreign key fields (e.g. a campaign's client, a task's assignee) are shown
  as dropdowns populated live from the parent table — you can't create a
  child record until its parent exists, matching how the database itself
  enforces the relationships.
- Recommended order to enter data the first time: **Users → Clients →
  Campaigns → Tasks / Performance → Invoices** — this mirrors the foreign
  key dependency chain in the schema.

## Notes

- All inserts use parameterized queries (`%s` placeholders) to avoid SQL
  injection.
- If an insert fails (e.g. a duplicate `client_email`), MySQL's error message
  is shown directly in the app.
