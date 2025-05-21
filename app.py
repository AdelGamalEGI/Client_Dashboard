import os
import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import gspread
from gspread_dataframe import get_as_dataframe
from oauth2client.service_account import ServiceAccountCredentials
import traceback

# Initialize app
app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP]
)
server = app.server

# Photo map
photo_mapping = {
    "lavjit singh": "lavjit.jpg",
    "adel gamal": "adel.jpg",
    "don sunny": "don.jpg",
    "ganesh shinde": "ganesh.jpg",
    "samuel ezannaya": "samuel.jpg",
    "stefan stroobants": "stefan.jpg",
    "jaco roesch": "jaco.jpg",
    "gustav brand": "gustav.jpg",
    "seyed khali": "seyed.jpg"
}

def member_card(name, role):
    key = name.strip().lower()
    img_file = photo_mapping.get(key)
    if img_file:
        img_tag = html.Img(src=app.get_asset_url(img_file), height="45px", style={'borderRadius': '50%'})
    else:
        img_tag = html.Div("👤", style={'fontSize': '2rem'})
    return dbc.Card(
        dbc.Row([
            dbc.Col(img_tag, width='auto'),
            dbc.Col([
                html.Div(html.Strong(name)),
                html.Div(html.Small(role, className='text-muted'))
            ])
        ], align='center'),
        className='mb-2 p-2 shadow-sm'
    )

# Home layout
home_layout = html.Div([
    html.H1("Welcome to AIS Portal", className="text-center my-4"),
    dbc.Row([
        dbc.Col(dcc.Link(dbc.Button("📊 Dashboard", color="primary", className="btn-lg w-100"), href="/dashboard"), width=6),
        dbc.Col(dcc.Link(dbc.Button("🛡️ Risk View", color="danger", className="btn-lg w-100"), href="/risks"), width=6),
    ], className="my-4 text-center", justify="center")
])

# App layout
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content")
])

# Routing: single callback
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    if pathname == "/dashboard":
        return main_dashboard()
    elif pathname == "/risks":
        return risk_dashboard()
    return home_layout

# Risk Dashboard
def risk_dashboard():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open("Project_Planning_Workbook")

    df_risks = get_as_dataframe(sheet.worksheet("Risk_Register")).dropna(how="all")
    df_risks['Likelihood (1-5)'] = pd.to_numeric(df_risks['Likelihood (1-5)'], errors='coerce')
    df_risks['Impact (1-5)'] = pd.to_numeric(df_risks['Impact (1-5)'], errors='coerce')
    df_risks['Risk Score'] = df_risks['Likelihood (1-5)'] * df_risks['Impact (1-5)']
    df_risks = df_risks[df_risks['Status'].str.lower().str.strip() == 'open']

    score_counts = {
        "High": df_risks[df_risks['Risk Score'] >= 10].shape[0],
        "Medium": df_risks[(df_risks['Risk Score'] >= 5) & (df_risks['Risk Score'] < 10)].shape[0],
        "Low": df_risks[(df_risks['Risk Score'] < 5) & (df_risks['Risk Score'] >= 1)].shape[0]
    }

    summary_block = dbc.Card([
        dbc.CardHeader("Open Risks by Severity"),
        dbc.CardBody([
            html.Div([
                html.Div([html.Span("🟥 High", style={"fontWeight": "bold"}), html.Span(f" {score_counts['High']} risks")], className="mb-2"),
                html.Div([html.Span("🟧 Medium", style={"fontWeight": "bold"}), html.Span(f" {score_counts['Medium']} risks")], className="mb-2"),
                html.Div([html.Span("🟨 Low", style={"fontWeight": "bold"}), html.Span(f" {score_counts['Low']} risks")])
            ])
        ])
    ], className="mb-4")

    matrix_cells = {}
    for _, row in df_risks.iterrows():
        key = (int(row['Likelihood (1-5)']), int(row['Impact (1-5)']))
        matrix_cells.setdefault(key, []).append(str(row['Risk ID']))

    matrix_grid = []
    for impact in range(5, 0, -1):
        row_cells = []
        for likelihood in range(1, 6):
            ids = matrix_cells.get((likelihood, impact), [])
            score = impact * likelihood
            color = 'red' if score >= 10 else 'orange' if score >= 5 else 'yellow'
            row_cells.append(html.Td(html.Div(", ".join(ids), style={"fontSize": "0.75rem"}),
                                     style={"backgroundColor": color, "border": "1px solid #ccc", "padding": "12px"}))
        matrix_grid.append(html.Tr(row_cells))

    matrix_table = dbc.Card([
        dbc.CardHeader("Risk Matrix (Likelihood × Impact)"),
        dbc.CardBody(html.Table(matrix_grid, style={"width": "100%", "borderCollapse": "collapse"}))
    ], className="mb-4")

    cols = ["Risk ID", "Risk Description", "Likelihood (1-5)", "Impact (1-5)", "Risk Score", "Status"]
    risk_table = dash_table.DataTable(
        columns=[{"name": c, "id": c} for c in cols],
        data=df_risks[cols].to_dict('records'),
        style_table={"maxHeight": "300px", "overflowY": "auto"},
        style_cell={"textAlign": "left", "padding": "5px"},
        style_header={"backgroundColor": "#E6E6E6", "fontWeight": "bold"}
    )

    return dbc.Container([
        html.H2("Risk Dashboard", className="text-center my-4"),
        dbc.Row([dbc.Col(summary_block, width=6), dbc.Col(matrix_table, width=6)]),
        dbc.Row(dbc.Col([html.H5("Open Risks Table", className="mb-2"), risk_table]))
    ], fluid=True)

# Main Dashboard
def main_dashboard():
    return dbc.Container([
        html.H2('Client Dashboard', className='text-center my-4'),
        dcc.Interval(id='interval-refresh', interval=60*1000, n_intervals=0),
        dbc.Row([
            dbc.Col(html.Div(id='kpi-summary'), width=6),
            dbc.Col(dcc.Graph(id='workstream-progress-chart'), width=6),
        ], className='mb-4'),
        dbc.Row([
            dbc.Col(html.Div(id='tasks-table'), width=6),
            dbc.Col(html.Div(id='team-members'), width=6),
        ])
    ], fluid=True)

# Refresh callback with error handling
@app.callback(
    [Output('kpi-summary','children'),
     Output('workstream-progress-chart','figure'),
     Output('tasks-table','children'),
     Output('team-members','children')],
    Input('interval-refresh','n_intervals')
)
def refresh_dashboard(n):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        sheet = client.open("Project_Planning_Workbook")

        df_ws = get_as_dataframe(sheet.worksheet("Workstreams")).dropna(how='all')
        df_issues = get_as_dataframe(sheet.worksheet("Issue_Tracker")).dropna(how='all')
        df_risks = get_as_dataframe(sheet.worksheet("Risk_Register")).dropna(how='all')
        df_refs = get_as_dataframe(sheet.worksheet("References")).dropna(how='all')

        # KPIs
        tasks_month = df_ws.shape[0]
        open_issues = df_issues[df_issues['Status'].str.lower().str.strip()=='open'].shape[0]
        open_risks = df_risks[df_risks['Status'].str.lower().str.strip()=='open'].shape[0]

        kpi = dbc.Card([
            dbc.CardHeader("KPI Summary"),
            dbc.CardBody(dbc.Row([
                dbc.Col(html.Div([html.H2(tasks_month), html.P("Tasks This Month")])),
                dbc.Col(html.Div([html.H2(open_risks), html.P("Open Risks")])),
                dbc.Col(html.Div([html.H2(open_issues), html.P("Open Issues")]))
            ]))
        ], className="shadow-sm mb-4")

        # Placeholder empty figure
        fig = go.Figure()
        fig.update_layout(height=300)

        # Tasks table
        if 'Task Name' in df_ws.columns:
            table_df = df_ws[['Task Name', 'Actual % Complete']]
        elif 'Activity Name' in df_ws.columns:
            table_df = df_ws[['Activity Name', 'Actual % Complete']]
        else:
            table_df = df_ws
        table = dbc.Table.from_dataframe(table_df, striped=True, bordered=True, hover=True)

        # Team members
        assigned = df_ws.get('Assigned To', pd.Series()).dropna().astype(str).str.split(',').explode().str.strip().str.lower()
        df_refs['name_lower'] = df_refs.get('Person Name', pd.Series()).astype(str).str.strip().str.lower()
        active = df_refs[df_refs['name_lower'].isin(assigned)]
        members = [member_card(r['Person Name'], r.get('Role','')) for _, r in active.iterrows()]

        return kpi, fig, table, members

    except Exception as e:
        err_text = traceback.format_exc()
        error_card = dbc.Card([
            dbc.CardHeader("Error Loading Dashboard"),
            dbc.CardBody(html.Pre(err_text, style={'whiteSpace': 'pre-wrap', 'overflowX': 'auto'}), className='text-danger')
        ], color="light", outline=True)
        return error_card, go.Figure(), html.Pre(err_text), []

# Run server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
