import datetime

import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets auth
SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
CREDS = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', SCOPES)
GS_CLIENT = gspread.authorize(CREDS)
SPREADSHEET = GS_CLIENT.open("Project_Planning_Workbook")
ISSUE_WS = SPREADSHEET.worksheet("Issue_Tracker")

# Layout for Issue Tracker page
def issue_dashboard():
    form = dbc.Card([
        dbc.CardHeader("Submit New Issue"),
        dbc.CardBody([
            # Issue Description
            html.Div([
                dbc.Label("Issue Description", html_for="issue-desc"),
                dbc.Textarea(id="issue-desc", placeholder="Describe the issue...", className="mb-3")
            ], className="mb-3"),
            # Severity
            html.Div([
                dbc.Label("Severity", html_for="issue-severity"),
                dcc.Dropdown(
                    id="issue-severity",
                    options=[
                        {"label": "High", "value": "High"},
                        {"label": "Medium", "value": "Medium"},
                        {"label": "Low", "value": "Low"}
                    ],
                    placeholder="Select severity",
                    className="mb-3"
                )
            ], className="mb-3"),
            # Reported By
            html.Div([
                dbc.Label("Reported By", html_for="issue-reported-by"),
                dbc.Input(id="issue-reported-by", placeholder="Your name...", type="text", className="mb-3")
            ], className="mb-3"),
            # Submit button
            dbc.Button("Submit Issue", id="submit-issue", color="primary")
        ])
    ], className="mb-4 shadow-sm")

    table = dbc.Card([
        dbc.CardHeader("Open Issues"),
        dbc.CardBody(
            dash_table.DataTable(
                id="issues-table",
                columns=[
                    {"name": c, "id": c}
                    for c in ["Issue ID", "Issue Description", "Severity", "Date Reported"]
                ],
                data=[],
                style_table={"overflowY": "auto", "maxHeight": "300px"},
                style_cell={"textAlign": "left", "padding": "5px"},
                style_header={"backgroundColor": "#E6E6E6", "fontWeight": "bold"}
            )
        )
    ], className="shadow-sm")

    return dbc.Container([
        html.H2("Issue Tracker", className="text-center my-4"),
        form,
        table
    ], fluid=True)

# Callback to handle submission & refresh table
def register_issue_callbacks(app: dash.Dash):
    @app.callback(
        Output("issues-table", "data"),
        Input("submit-issue", "n_clicks"),
        State("issue-desc", "value"),
        State("issue-severity", "value"),
        State("issue-reported-by", "value")
    )
    def update_issues_table(n_clicks, desc, sev, reporter):
        # Always reload sheet
        values = ISSUE_WS.get_all_values()
        headers = values[0]
        rows = values[1:]
        df = pd.DataFrame(rows, columns=headers)

        # On submission, append a new row
        if n_clicks:
            # Generate next Issue ID
            existing_ids = [r[0] for r in rows if r[0].startswith("ISSUE-")]
            nums = [int(i.split("-")[1]) for i in existing_ids if i.split("-")[1].isdigit()]
            next_num = max(nums) + 1 if nums else 1
            issue_id = f"ISSUE-{next_num:03d}"
            # Date reported
            date_reported = datetime.date.today().isoformat()
            # Build new row in sheet's column order
            new_row = []
            for col in headers:
                if col == "Issue ID": new_row.append(issue_id)
                elif col == "Issue Description": new_row.append(desc or "")
                elif col == "Severity": new_row.append(sev or "")
                elif col == "Reported By": new_row.append(reporter or "")
                elif col == "Date Reported": new_row.append(date_reported)
                elif col == "Status": new_row.append("Open")
                else: new_row.append("")
            ISSUE_WS.append_row(new_row, value_input_option="USER_ENTERED")
            # Reload df after append
            values = ISSUE_WS.get_all_values()
            df = pd.DataFrame(values[1:], columns=values[0])

        # Filter open issues and return required columns
        df['Status'] = df['Status'].astype(str).str.lower().str.strip()
        df_open = df[df['Status'] == 'open']
        return df_open[["Issue ID", "Issue Description", "Severity", "Date Reported"]].to_dict('records')
