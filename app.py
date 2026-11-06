"""
Tables (in required insertion order, respecting foreign keys):
    1. users        (no dependencies)
    2. client       (depends on users.user_id -> account_manager_id)
    3. campaigns    (depends on client.client_id)
    4. tasks        (depends on campaigns.campaign_id, users.user_id)
    5. performance  (depends on campaigns.campaign_id)
    6. invoice      (depends on client.client_id)
"""
from pathlib import Path
import streamlit as st
from datetime import date, datetime
from db import get_connection, run_query, fetch_options
st.set_page_config(page_title="DMMS", layout="wide")
_css = Path(__file__).parent / "style.css"
if _css.exists():
    st.markdown(f"<style>{_css.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# Sidebar: connection settings + navigation
st.sidebar.title("DMMS")
with st.sidebar.expander("Database connection", expanded="db_config" not in st.session_state):
    host = st.text_input("Host", value="localhost")
    port = st.number_input("Port", value=3306, step=1)
    user = st.text_input("MySQL user", value="root")
    password = st.text_input("Password", type="password")
    database = st.text_input("Database", value="dmms_db")
    if st.button("Connect"):
        st.session_state["db_config"] = {
            "host": host, "port": int(port), "user": user,
            "password": password, "database": database,
        }
        test_conn = get_connection()
        if test_conn:
            st.success("Connected successfully.")
            test_conn.close()

connected = "db_config" in st.session_state

page = st.sidebar.radio(
    "Go to",
    ["Dashboard", "Users", "Clients", "Campaigns", "Tasks", "Performance", "Invoices"],
)

if not connected:
    st.warning("Enter your MySQL connection details in the sidebar and click **Connect** to begin.")
    st.stop()

# Dashboard
if page == "Dashboard":
    st.title("DMMS Dashboard")
    st.caption("Digital Marketing Management System — overview")

    counts = {}
    for label, table in [
        ("Users", "users"), ("Clients", "client"), ("Campaigns", "campaigns"),
        ("Tasks", "tasks"), ("Performance records", "performance"), ("Invoices", "invoice"),
    ]:
        rows = run_query(f"SELECT COUNT(*) AS cnt FROM {table}", fetch=True)
        counts[label] = rows[0]["cnt"] if rows else 0

    cols = st.columns(6)
    for col, (label, value) in zip(cols, counts.items()):
        col.metric(label, value)

    st.divider()
    st.subheader("Active campaigns")
    active = run_query(
        """
        SELECT c.campaign_id, c.campaign_name, cl.company_name, c.platform,
               c.budget, c.status
        FROM campaigns c
        JOIN client cl ON cl.client_id = c.client_id
        WHERE c.status = 'ACTIVE'
        """,
        fetch=True,
    )
    if active:
        st.dataframe(active, use_container_width=True)
    else:
        st.info("No active campaigns yet.")


# Users
elif page == "Users":
    st.title("Users")
    st.caption("Staff accounts. No dependencies — insert these first.")

    with st.form("add_user"):
        st.subheader("Add a new user")
        c1, c2 = st.columns(2)
        user_name = c1.text_input("User name*")
        phone_number = c2.text_input("Phone number")
        email = c1.text_input("Email*")
        role = c2.selectbox("Role*", ["ADMIN", "MANAGER"])
        submitted = st.form_submit_button("Save user")

        if submitted:
            if not user_name or not email:
                st.error("User name and email are required.")
            else:
                new_id = run_query(
                    """INSERT INTO users (user_name, phone_number, email, role)
                       VALUES (%s, %s, %s, %s)""",
                    (user_name, phone_number or None, email, role),
                )
                if new_id:
                    st.success(f"User '{user_name}' saved with user_id = {new_id}.")

    st.divider()
    st.subheader("All users")
    rows = run_query("SELECT * FROM users ORDER BY user_id", fetch=True)
    st.dataframe(rows or [], use_container_width=True)


# Clients
elif page == "Clients":
    st.title("Clients")
    st.caption("Depends on Users (account_manager_id). Add users first.")

    manager_options = fetch_options(
        "SELECT user_id, user_name FROM users", "user_id", "user_name"
    )

    with st.form("add_client"):
        st.subheader("Add a new client")
        c1, c2 = st.columns(2)
        company_name = c1.text_input("Company name*")
        client_email = c2.text_input("Client email*")
        client_industry = c1.text_input("Industry")
        client_phone = c2.text_input("Phone")

        if manager_options:
            manager_label = st.selectbox("Account manager*", list(manager_options.keys()))
        else:
            manager_label = None
            st.warning("No users exist yet — add a user before creating a client.")

        submitted = st.form_submit_button("Save client")

        if submitted:
            if not company_name or not client_email or not manager_label:
                st.error("Company name, email, and account manager are required.")
            else:
                new_id = run_query(
                    """INSERT INTO client
                       (company_name, client_email, client_industry, client_phone, account_manager_id)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (company_name, client_email, client_industry or None,
                     client_phone or None, manager_options[manager_label]),
                )
                if new_id:
                    st.success(f"Client '{company_name}' saved with client_id = {new_id}.")

    st.divider()
    st.subheader("All clients")
    rows = run_query(
        """SELECT cl.*, u.user_name AS account_manager
           FROM client cl JOIN users u ON u.user_id = cl.account_manager_id
           ORDER BY cl.client_id""",
        fetch=True,
    )
    st.dataframe(rows or [], use_container_width=True)

# Campaigns
elif page == "Campaigns":
    st.title("Campaigns")
    st.caption("Depends on Clients. Add a client first.")

    client_options = fetch_options(
        "SELECT client_id, company_name FROM client", "client_id", "company_name"
    )

    with st.form("add_campaign"):
        st.subheader("Add a new campaign")

        if client_options:
            client_label = st.selectbox("Client*", list(client_options.keys()))
        else:
            client_label = None
            st.warning("No clients exist yet — add a client before creating a campaign.")

        c1, c2 = st.columns(2)
        campaign_name = c1.text_input("Campaign name*")
        platform = c2.text_input("Platform*", placeholder="e.g. Instagram, Google Ads")
        budget = c1.number_input("Budget", min_value=0.0, step=100.0, format="%.2f")
        status = c2.selectbox("Status", ["PLANNING", "ACTIVE", "COMPLETED", "PAUSED"])
        start_date = c1.date_input("Start date*", value=date.today())
        has_end_date = c2.checkbox("Set an end date?")
        end_date = c2.date_input("End date", value=date.today()) if has_end_date else None

        submitted = st.form_submit_button("Save campaign")

        if submitted:
            if not client_label or not campaign_name or not platform:
                st.error("Client, campaign name, and platform are required.")
            else:
                new_id = run_query(
                    """INSERT INTO campaigns
                       (client_id, campaign_name, budget, start_date, end_date, status, platform)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (client_options[client_label], campaign_name, budget,
                     datetime.combine(start_date, datetime.min.time()),
                     datetime.combine(end_date, datetime.min.time()) if end_date else None,
                     status, platform),
                )
                if new_id:
                    st.success(f"Campaign '{campaign_name}' saved with campaign_id = {new_id}.")

    st.divider()
    st.subheader("All campaigns")
    rows = run_query(
        """SELECT c.*, cl.company_name
           FROM campaigns c JOIN client cl ON cl.client_id = c.client_id
           ORDER BY c.campaign_id""",
        fetch=True,
    )
    st.dataframe(rows or [], use_container_width=True)


# Tasks
elif page == "Tasks":
    st.title("Tasks")
    st.caption("Depends on Campaigns and Users. Add both first.")

    campaign_options = fetch_options(
        "SELECT campaign_id, campaign_name FROM campaigns", "campaign_id", "campaign_name"
    )
    user_options = fetch_options(
        "SELECT user_id, user_name FROM users", "user_id", "user_name"
    )

    with st.form("add_task"):
        st.subheader("Add a new task")

        if campaign_options and user_options:
            campaign_label = st.selectbox("Campaign*", list(campaign_options.keys()))
            assignee_label = st.selectbox("Assigned to*", list(user_options.keys()))
        else:
            campaign_label = assignee_label = None
            st.warning("Need at least one campaign and one user before creating a task.")

        title = st.text_input("Task title*")
        c1, c2 = st.columns(2)
        status = c1.selectbox("Status", ["TODO", "IN_PROGRESS", "DONE"])
        due_date = c2.date_input("Due date", value=date.today())

        submitted = st.form_submit_button("Save task")

        if submitted:
            if not campaign_label or not assignee_label or not title:
                st.error("Campaign, assignee, and title are required.")
            else:
                new_id = run_query(
                    """INSERT INTO tasks (campaign_id, title, status, due_date, assigned_to)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (campaign_options[campaign_label], title, status, due_date,
                     user_options[assignee_label]),
                )
                if new_id:
                    st.success(f"Task '{title}' saved with task_id = {new_id}.")

    st.divider()
    st.subheader("All tasks")
    rows = run_query(
        """SELECT t.*, c.campaign_name, u.user_name AS assignee
           FROM tasks t
           JOIN campaigns c ON c.campaign_id = t.campaign_id
           JOIN users u ON u.user_id = t.assigned_to
           ORDER BY t.task_id""",
        fetch=True,
    )
    st.dataframe(rows or [], use_container_width=True)

# Performance
elif page == "Performance":
    st.title("Performance")
    st.caption("Depends on Campaigns. Add a campaign first.")

    campaign_options = fetch_options(
        "SELECT campaign_id, campaign_name FROM campaigns", "campaign_id", "campaign_name"
    )

    with st.form("add_performance"):
        st.subheader("Log a performance record")

        if campaign_options:
            campaign_label = st.selectbox("Campaign*", list(campaign_options.keys()))
        else:
            campaign_label = None
            st.warning("No campaigns exist yet — add a campaign before logging performance.")

        record_date = st.date_input("Record date*", value=date.today())
        c1, c2, c3, c4 = st.columns(4)
        impressions = c1.number_input("Impressions", min_value=0, step=1)
        clicks = c2.number_input("Clicks", min_value=0, step=1)
        conversions = c3.number_input("Conversions", min_value=0, step=1)
        spend = c4.number_input("Spend", min_value=0.0, step=10.0, format="%.2f")

        submitted = st.form_submit_button("Save record")

        if submitted:
            if not campaign_label:
                st.error("Campaign is required.")
            else:
                new_id = run_query(
                    """INSERT INTO performance
                       (campaign_id, record_date, impressions, clicks, conversions, spend)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (campaign_options[campaign_label], record_date,
                     impressions, clicks, conversions, spend),
                )
                if new_id:
                    st.success(f"Performance record saved with performance_id = {new_id}.")

    st.divider()
    st.subheader("All performance records")
    rows = run_query(
        """SELECT p.*, c.campaign_name
           FROM performance p JOIN campaigns c ON c.campaign_id = p.campaign_id
           ORDER BY p.performance_id""",
        fetch=True,
    )
    st.dataframe(rows or [], use_container_width=True)


# Invoices
elif page == "Invoices":
    st.title("Invoices")
    st.caption("Depends on Clients. Add a client first.")

    client_options = fetch_options(
        "SELECT client_id, company_name FROM client", "client_id", "company_name"
    )

    with st.form("add_invoice"):
        st.subheader("Create a new invoice")

        if client_options:
            client_label = st.selectbox("Client*", list(client_options.keys()))
        else:
            client_label = None
            st.warning("No clients exist yet — add a client before creating an invoice.")

        c1, c2, c3 = st.columns(3)
        amount = c1.number_input("Amount*", min_value=0.0, step=100.0, format="%.2f")
        issue_date = c2.date_input("Issue date*", value=date.today())
        due_date = c3.date_input("Due date*", value=date.today())
        status = st.selectbox("Status", ["DRAFT", "SENT", "PAID", "OVERDUE"])

        submitted = st.form_submit_button("Save invoice")

        if submitted:
            if not client_label or amount <= 0:
                st.error("Client and a positive amount are required.")
            else:
                new_id = run_query(
                    """INSERT INTO invoice (client_id, amount, issue_date, due_date, status)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (client_options[client_label], amount, issue_date, due_date, status),
                )
                if new_id:
                    st.success(f"Invoice saved with invoice_id = {new_id}.")

    st.divider()
    st.subheader("All invoices")
    rows = run_query(
        """SELECT i.*, cl.company_name
           FROM invoice i JOIN client cl ON cl.client_id = i.client_id
           ORDER BY i.invoice_id""",
        fetch=True,
    )
    st.dataframe(rows or [], use_container_width=True)