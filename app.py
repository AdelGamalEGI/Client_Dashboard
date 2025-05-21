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

# Helper to ensure string operations never fail
def ensure_str(series: pd.Series) -> pd.Series:
    return series.fillna('').astype(str)

# Initialize Google Sheets client once
SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
CREDS = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', SCOPES)
GS_CLIENT = gspread.authorize(CREDS)
SPREADSHEET = GS_CLIENT.open("Project_Planning_Workbook")

# Photo map for team member cards
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

# Routing callback (single)
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

# --- Risk Dashboard ---
def risk_dashboard():
    # Load and clean data
    raw = SPREADSHEET.worksheet("Risk_Register").get_all_values()
    df = pd.DataFrame(raw[1:], columns=raw[0])
    df['Status']     = ensure_str(df['Status']).str.lower().str.strip()
    df['Risk Level'] = ensure_str(df['Risk Level']).str.lower().str.strip()
    df['Likelihood (1-5)'] = pd.to_numeric(df['Likelihood (1-5)'], errors='coerce').fillna(0)
    df['Impact (1-5)']     = pd.to_numeric(df['Impact (1-5)'], errors='coerce').fillna(0)
    df['Risk Score']       = pd.to_numeric(df['Risk Score'], errors='coerce').fillna(0)
    df = df[df['Status'] == 'open']

    # Summary card
    counts = {
        'High':   df[df['Risk Level']=='high'].shape[0],
        'Medium': df[df['Risk Level']=='medium'].shape[0],
        'Low':    df[df['Risk Level']=='low'].shape[0]
    }
    summary = dbc.Card([
        dbc.CardHeader("Open Risks by Severity"),
        dbc.CardBody([
            html.Div([
                html.Div([html.Span("🟥 High", style={"fontWeight":"bold","color":"red","marginRight":"10px"}),
                          html.Span(f"{counts['High']} risks")], className="mb-2"),
                html.Div([html.Span("🟧 Medium", style={"fontWeight":"bold","color":"orange","marginRight":"10px"}),
                          html.Span(f"{counts['Medium']} risks")], className="mb-2"),
                html.Div([html.Span("🟨 Low", style={"fontWeight":"bold","color":"gold","marginRight":"10px"}),
                          html.Span(f"{counts['Low']} risks")])
            ])
        ])
    ], className="mb-4")

    # Fixed 5×5 risk matrix
    cells = {}
    for _, row in df.iterrows():
        key = (int(row['Likelihood (1-5)']), int(row['Impact (1-5)']))
        cells.setdefault(key, []).append(str(row['Risk ID']))
    matrix_rows = []
    for imp in range(5, 0, -1):
        tds = []
        for lik in range(1, 6):
            ids = cells.get((lik, imp), [])
            score = lik * imp
            color = 'red' if score >= 11 else 'orange' if score >= 6 else 'yellow'
            tds.append(html.Td(
                html.Div(", ".join(ids), style={"fontSize":"0.65rem","whiteSpace":"normal","wordWrap":"break-word"}),
                style={"backgroundColor":color, "border":"1px solid #ccc", "width":"80px", "height":"80px", "textAlign":"center", "verticalAlign":"middle"}
            ))
        matrix_rows.append(html.Tr(tds))
    matrix = dbc.Card([
        dbc.CardHeader("Risk Matrix (Likelihood × Impact)"),
        dbc.CardBody(html.Table(matrix_rows, style={"borderCollapse":"collapse"}))
    ], className="mb-4")

    # Detailed risk table
    columns = ["Risk ID","Risk Description","Likelihood (1-5)","Impact (1-5)","Risk Level","Status"]
    risk_table = dash_table.DataTable(
        columns=[{"name":col,"id":col} for col in columns],
        data=df[columns].to_dict('records'),
        style_table={"maxHeight":"300px","overflowY":"auto"},
        style_cell={"textAlign":"left","padding":"5px"},
        style_header={"backgroundColor":"#E6E6E6","fontWeight":"bold"}
    )

    return dbc.Container([
        html.H2("Risk Dashboard", className="text-center my-4"),
        dbc.Row([dbc.Col(summary, width=6), dbc.Col(matrix, width=6)], className="mb-4"),
        dbc.Row(dbc.Col([html.H5("Open Risks Table", className="mb-2"), risk_table]))
    ], fluid=True)

# --- Main Dashboard ---
def main_dashboard():
    return dbc.Container([
        html.H2('Client Dashboard', className='text-center my-4'),
        dcc.Interval(id='interval-refresh', interval=60*1000, n_intervals=0),
        dbc.Row([
            dbc.Col(html.Div(id='kpi-summary'), width=6),
            dbc.Col(dcc.Graph(id='workstream-progress-chart'), width=6)
        ], className='mb-4'),
        dbc.Row([
            dbc.Col(html.Div(id='tasks-table'), width=6),
            dbc.Col(html.Div(id='team-members'), width=6)
        ])
    ], fluid=True)

# Refresh callback with defensive cleaning
@app.callback(
    [Output('kpi-summary','children'), Output('workstream-progress-chart','figure'),
     Output('tasks-table','children'), Output('team-members','children')],
    Input('interval-refresh','n_intervals')
)
def refresh_dashboard(n):
    try:
        # Load sheets
        df_ws = get_as_dataframe(SPREADSHEET.worksheet("Workstreams")).dropna(how='all')
        df_issues = get_as_dataframe(SPREADSHEET.worksheet("Issue_Tracker")).dropna(how='all')
        df_refs = get_as_dataframe(SPREADSHEET.worksheet("References")).dropna(how='all')
        raw_r = SPREADSHEET.worksheet("Risk_Register").get_all_values()
        df_r = pd.DataFrame(raw_r[1:], columns=raw_r[0])

        # Clean text columns
        df_issues['Status']    = ensure_str(df_issues['Status']).str.lower().str.strip()
        df_r['Status']         = ensure_str(df_r['Status']).str.lower().str.strip()
        df_r['Risk Level']     = ensure_str(df_r['Risk Level']).str.lower().str.strip()

        # Coerce numeric columns
        df_ws['Actual % Complete']      = pd.to_numeric(df_ws['Actual % Complete'], errors='coerce').fillna(0)
        df_ws['Duration (Effort Days)'] = pd.to_numeric(df_ws['Duration (Effort Days)'], errors='coerce').fillna(0)
        df_r['Likelihood (1-5)']        = pd.to_numeric(df_r['Likelihood (1-5)'], errors='coerce').fillna(0)
        df_r['Impact (1-5)']            = pd.to_numeric(df_r['Impact (1-5)'], errors='coerce').fillna(0)

        # KPIs
        num_tasks  = df_ws.shape[0]
        num_issues = df_issues[df_issues['Status']=='open'].shape[0]
        num_risks  = df_r[df_r['Status']=='open'].shape[0]
        kpi = dbc.Card([
            dbc.CardHeader("KPI Summary"),
            dbc.CardBody(dbc.Row([
                dbc.Col(html.Div([html.H2(num_tasks),  html.P("Tasks This Month")])),
                dbc.Col(html.Div([html.H2(num_risks),  html.P("Open Risks")])),
                dbc.Col(html.Div([html.H2(num_issues), html.P("Open Issues")]))
            ]))
        ], className="shadow-sm mb-4")

        # Progress chart
        df_ws['Start Date'] = pd.to_datetime(df_ws['Start Date'], errors='coerce')
        df_ws['End Date']   = pd.to_datetime(df_ws['End Date'],   errors='coerce')
        today = pd.Timestamp.today()
        def calc_planned(r):
            if pd.isna(r['Start Date']) or pd.isna(r['End Date']):
                return 0
            dur = (r['End Date'] - r['Start Date']).days
            el  = (today - r['Start Date']).days
            return max(0, min(1, el/dur)) * r['Duration (Effort Days)'] if dur>0 else 0
        df_ws['Planned'] = df_ws.apply(calc_planned, axis=1)
        df_ws['ActualW'] = df_ws['Actual % Complete'] * df_ws['Duration (Effort Days)']
        summary = df_ws.groupby('Workstream').agg({'Duration (Effort Days)':'sum','Planned':'sum','ActualW':'sum'}).reset_index()
        summary['Planned%'] = summary['Planned']/summary['Duration (Effort Days)']*100
        summary['Actual%']  = summary['ActualW']/summary['Duration (Effort Days)']*100
        fig = go.Figure()
        for _, row in summary.iterrows():
            fig.add_trace(go.Bar(name='Planned',x=[row['Workstream']],y=[row['Planned%']]))
            fig.add_trace(go.Bar(name='Actual', x=[row['Workstream']],y=[row['Actual%']]))
        fig.update_layout(barmode='group', height=300)

        # Tasks table + team members
        table = dbc.Table.from_dataframe(df_ws[['Task Name','Actual % Complete']], striped=True, bordered=True, hover=True)
        assigned = df_ws['Assigned To'].dropna().str.split(',').explode().str.strip().str.lower()
        df_refs['lower'] = ensure_str(df_refs['Person Name']).str.lower().str.strip()
        members = [member_card(r['Person Name'], r['Role']) for _, r in df_refs[df_refs['lower'].isin(assigned)].iterrows()]

        return kpi, fig, table, members
    except Exception:
        tb = traceback.format_exc()
        err = dbc.Card([
            dbc.CardHeader("Error Loading Dashboard"),
            dbc.CardBody(html.Pre(tb), className='text-danger')
        ], color="light", outline=True)
        return err, go.Figure(), html.Pre(tb), []

# Run server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
