
import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import gspread
from gspread_dataframe import get_as_dataframe
from oauth2client.service_account import ServiceAccountCredentials
import os

# Initialize app
app = dash.Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
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
        img_tag = html.Img(src=f"/assets/{img_file}", height="45px", style={'borderRadius': '50%'})
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

# Home
home_layout = html.Div([
    html.H1("Welcome to AIS Portal", className="text-center my-4"),
    dbc.Row([
        dbc.Col(dcc.Link(dbc.Button("📊 Dashboard", color="primary", className="btn-lg w-100"), href="/dashboard"), width=6),
        dbc.Col(dcc.Link(dbc.Button("🛡️ Risk View", color="danger", className="btn-lg w-100"), href="/risks"), width=6),
    ], className="my-4 text-center", justify="center")
])

# Root app layout
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content")
])

# Routing callback
@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def display_page(pathname):
    if pathname == "/dashboard":
        return main_dashboard()
    elif pathname == "/risks":
        return risk_dashboard()

def risk_dashboard():
    # GSheet load
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open("Project_Planning_Workbook")
    df_risks = get_as_dataframe(sheet.worksheet("Risk_Register")).dropna(how="all")

    df_risks['Likelihood (1-5)'] = pd.to_numeric(df_risks['Likelihood (1-5)'], errors='coerce')
    df_risks['Impact (1-5)'] = pd.to_numeric(df_risks['Impact (1-5)'], errors='coerce')
    df_risks['Risk Score'] = pd.to_numeric(df_risks['Risk Score'], errors='coerce')
    df_risks = df_risks[df_risks['Status'].astype(str).str.lower().str.strip() == 'open']

    # --- New Summary Block (Top Left) ---
    score_counts = {
        "High": df_risks[(df_risks['Risk Score'] >= 10)].shape[0],
        "Medium": df_risks[(df_risks['Risk Score'] >= 5) & (df_risks['Risk Score'] < 10)].shape[0],
        "Low": df_risks[(df_risks['Risk Score'] >= 1) & (df_risks['Risk Score'] < 5)].shape[0],
    }

    summary_block = dbc.Card([
        dbc.CardHeader("Open Risks by Severity"),
        dbc.CardBody([
            html.Div([
                html.Div([
                    html.Span("🟥 High", style={"fontWeight": "bold", "color": "red", "marginRight": "10px"}),
                    html.Span(f"{score_counts['High']} risks")
                ], className="mb-2"),
                html.Div([
                    html.Span("🟧 Medium", style={"fontWeight": "bold", "color": "orange", "marginRight": "10px"}),
                    html.Span(f"{score_counts['Medium']} risks")
                ], className="mb-2"),
                html.Div([
                    html.Span("🟨 Low", style={"fontWeight": "bold", "color": "gold", "marginRight": "10px"}),
                    html.Span(f"{score_counts['Low']} risks")
                ])
            ])
        ], style={"minHeight": "300px"})
    ])

    # --- New Risk Matrix ---
    matrix_df = df_risks[['Risk ID', 'Likelihood (1-5)', 'Impact (1-5)', 'Risk Score']].dropna()
    matrix_cells = {}
    for _, row in matrix_df.iterrows():
        key = (int(row['Likelihood (1-5)']), int(row['Impact (1-5)']))
        matrix_cells.setdefault(key, []).append(str(row['Risk ID']))

    matrix_grid = []
    for impact in range(5, 0, -1):
        row = []
        for likelihood in range(1, 6):
            risk_ids = matrix_cells.get((likelihood, impact), [])
            score = impact * likelihood
            if score >= 10:
                color = "red"
            elif score >= 5:
                color = "orange"
            else:
                color = "yellow"
            cell_content = html.Div(", ".join(risk_ids), style={"fontSize": "0.75rem"})
            row.append(html.Td(cell_content, style={"backgroundColor": color, "border": "1px solid #ccc", "padding": "12px", "minWidth": "90px"}))
        matrix_grid.append(html.Tr(row))

    matrix_table = dbc.Card([
        dbc.CardHeader("Risk Matrix (Likelihood × Impact)"),
        dbc.CardBody([
            html.Table(matrix_grid, style={"width": "100%", "borderCollapse": "collapse"})
        ])
    ])

    # --- Risk Table (Bottom) ---
    table_columns = ["Risk ID", "Risk Description", "Likelihood (1-5)", "Impact (1-5)", "Risk Score", "Status"]
    risk_table = dash_table.DataTable(
        columns=[{"name": i, "id": i} for i in table_columns],
        data=df_risks[table_columns].to_dict('records'),
        style_table={"maxHeight": "300px", "overflowY": "auto"},
        style_cell={"textAlign": "left", "padding": "5px"},
        style_header={"backgroundColor": "rgb(230, 230, 230)", "fontWeight": "bold"}
    )

    return dbc.Container([
        html.H2("Risk Dashboard", className="text-center my-4"),
        dbc.Row([
            dbc.Col(summary_block, width=6),
            dbc.Col(matrix_table, width=6)
        ], className="mb-4"),
        dbc.Row([
            dbc.Col([
                html.H5("Open Risks Table", className="mb-3"),
                risk_table
            ])
        ])
    ], fluid=True)

# Run

    return home_layout

# --------------------- Main Dashboard ---------------------
def main_dashboard():
    return dbc.Container([
        html.H2('Client Dashboard', className='text-center my-4'),
        dcc.Interval(id='interval-refresh', interval=60*1000, n_intervals=0),
        dbc.Row([
            dbc.Col(html.Div(dbc.Card(id='kpi-summary', className='shadow-sm'), style={"height": "300px", "overflowY": "auto"}), width=6),
            dbc.Col(dbc.Card([dbc.CardHeader('Workstream Progress'), dbc.CardBody([dcc.Graph(id='workstream-progress-chart')])], className="shadow-sm"), width=6),
        ], className='mb-4'),
        dbc.Row([
            dbc.Col(dbc.Card([dbc.CardHeader('Tasks This Month'), dbc.CardBody([html.Div(dbc.Table(id='tasks-table'), style={"maxHeight": "300px", "overflowY": "auto"})])], className="shadow-sm"), width=6),
            dbc.Col(dbc.Card([dbc.CardHeader('Active Team Members'), dbc.CardBody(html.Div(id='team-members', style={"maxHeight": "300px", "overflowY": "auto"}))], className="shadow-sm"), width=6),
        ])
    ], fluid=True)

@app.callback(
    Output('kpi-summary', 'children'),
    Output('workstream-progress-chart', 'figure'),
    Output('tasks-table', 'children'),
    Output('team-members', 'children'),
    Input('interval-refresh', 'n_intervals')
)
def refresh_dashboard(n):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open("Project_Planning_Workbook")
    df_workstreams = get_as_dataframe(spreadsheet.worksheet("Workstreams")).dropna(how='all')
    df_issues = get_as_dataframe(spreadsheet.worksheet("Issue_Tracker")).dropna(how='all')
    df_risks = get_as_dataframe(spreadsheet.worksheet("Risk_Register")).dropna(how='all')
    df_team = get_as_dataframe(spreadsheet.worksheet("References")).dropna(how='all')

    df_workstreams['Start Date'] = pd.to_datetime(df_workstreams['Start Date'], errors='coerce')
    df_workstreams['End Date'] = pd.to_datetime(df_workstreams['End Date'], errors='coerce')
    df_workstreams['Actual % Complete'] = pd.to_numeric(df_workstreams['Actual % Complete'], errors='coerce')
    df_workstreams['Duration (Effort Days)'] = pd.to_numeric(df_workstreams['Duration (Effort Days)'], errors='coerce').fillna(0)

    today = pd.Timestamp.today()
    start_month = today.replace(day=1)
    end_month = start_month + pd.offsets.MonthEnd(1)

    def compute_planned_percent(row):
        if pd.isna(row['Start Date']) or pd.isna(row['End Date']):
            return 0
        duration = (row['End Date'] - row['Start Date']).days
        elapsed = (today - row['Start Date']).days
        return max(0, min(1, elapsed / duration)) * row['Duration (Effort Days)'] if duration > 0 else 0

    df_workstreams['Planned Weighted'] = df_workstreams.apply(compute_planned_percent, axis=1)
    df_workstreams['Actual Weighted'] = df_workstreams['Actual % Complete'] * df_workstreams['Duration (Effort Days)']

    ws_summary = df_workstreams.groupby('Workstream').agg({
        'Duration (Effort Days)': 'sum',
        'Planned Weighted': 'sum',
        'Actual Weighted': 'sum'
    }).reset_index()
    ws_summary['Planned %'] = (ws_summary['Planned Weighted'] / ws_summary['Duration (Effort Days)']).fillna(0) * 100
    ws_summary['Actual %'] = (ws_summary['Actual Weighted'] / ws_summary['Duration (Effort Days)']).fillna(0)

    tasks_this_month = df_workstreams[(df_workstreams['Start Date'] <= end_month) & (df_workstreams['End Date'] >= start_month)]
    num_tasks = tasks_this_month.shape[0]
    num_open_issues = df_issues[df_issues['Status'].astype(str).str.lower().str.strip() == 'open'].shape[0]
    open_risks = df_risks[df_risks['Status'].astype(str).str.lower().str.strip() == 'open']
    num_open_risks = open_risks.shape[0]

    if 'High' in open_risks['Risk Score'].values:
        risk_color = 'danger'
    elif 'Medium' in open_risks['Risk Score'].values:
        risk_color = 'warning'
    else:
        risk_color = 'warning' if num_open_risks > 0 else 'secondary'

    kpi_card = [
        dbc.CardHeader("KPI Summary"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col(html.Div([
                    html.H2(f"{num_tasks}", className="text-primary mb-0", style={"fontWeight": "bold", "fontSize": "2rem", "textAlign": "center"}),
                    html.P("Tasks This Month", className="text-muted", style={"textAlign": "center"})
                ])),
                dbc.Col(html.Div([
                    html.H2([dcc.Link(dbc.Badge(f"{num_open_risks}", color=risk_color, className="px-3 py-2", pill=True), href="/risks", style={"textDecoration": "none"})],
                            className="mb-0", style={"textAlign": "center"}),
                    html.P("Open Risks", className="text-muted", style={"textAlign": "center"})
                ])),
                dbc.Col(html.Div([
                    html.H2(f"{num_open_issues}", className="text-primary mb-0", style={"fontWeight": "bold", "fontSize": "2rem", "textAlign": "center"}),
                    html.P("Open Issues", className="text-muted", style={"textAlign": "center"})
                ])),
            ], justify="center")
        ], style={"maxHeight": "300px", "overflowY": "auto"})
    ]

    fig = go.Figure()
    for _, row in ws_summary.iterrows():
        delta = abs(row['Planned %'] - row['Actual %'])
        color = 'green' if delta <= 15 else 'orange' if delta <= 30 else 'red'
        fig.add_trace(go.Bar(name='Planned', x=[row['Planned %']], y=[row['Workstream']], orientation='h', marker_color='blue'))
        fig.add_trace(go.Bar(name='Actual', x=[row['Actual %']], y=[row['Workstream']], orientation='h', marker_color=color))
    fig.update_layout(barmode='overlay', title='Workstream Progress', height=300)

    table = dbc.Table.from_dataframe(tasks_this_month[['Task Name', 'Actual % Complete']], striped=True, bordered=True, hover=True)
    assigned_people = tasks_this_month['Assigned To'].dropna().astype(str).str.split(',').explode().str.strip().str.lower()
    df_team['Person Name Lower'] = df_team['Person Name'].astype(str).str.strip().str.lower()
    active_members = df_team[df_team['Person Name Lower'].isin(assigned_people.unique())]
    team_cards = [member_card(row['Person Name'], row['Role']) for _, row in active_members.iterrows()]
    return kpi_card, fig, table, team_cards

# Risk dashboard preserved (already updated)

# Run
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
