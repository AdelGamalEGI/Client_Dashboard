import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime

# Load updated workbook
file_path = 'Project_ Planning_Workbook.xlsx'
df_workstreams = pd.read_excel(file_path, sheet_name='Workstreams')
df_risks = pd.read_excel(file_path, sheet_name='Risk_Register')
df_issues = pd.read_excel(file_path, sheet_name='Issue_Tracker')
df_team = pd.read_excel(file_path, sheet_name='References')

# Preprocess dates and percentages
df_workstreams['Start Date'] = pd.to_datetime(df_workstreams['Start Date'], errors='coerce')
df_workstreams['End Date'] = pd.to_datetime(df_workstreams['End Date'], errors='coerce')
df_workstreams['Actual % Complete'] = pd.to_numeric(df_workstreams['Actual % Complete'], errors='coerce')
df_workstreams['Duration (Effort Days)'] = pd.to_numeric(df_workstreams['Duration (Effort Days)'], errors='coerce').fillna(0)

# Define current month range
today = pd.Timestamp.today()
start_month = today.replace(day=1)
end_month = start_month + pd.offsets.MonthEnd(1)

# Weighted Planned % per workstream
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

# Section 1: KPI Summary
tasks_this_month = df_workstreams[
    (df_workstreams['Start Date'] <= end_month) & (df_workstreams['End Date'] >= start_month)
]
num_tasks = tasks_this_month.shape[0]

open_issues = df_issues[df_issues['Status'].astype(str).str.lower().str.strip() == 'open']
num_open_issues = open_issues.shape[0]

open_risks = df_risks[df_risks['Status'].astype(str).str.lower().str.strip() == 'open']
num_open_risks = open_risks.shape[0]

# Risk color
if 'High' in open_risks['Risk Score'].astype(str).values:
    risk_color = 'danger'
elif 'Medium' in open_risks['Risk Score'].astype(str).values:
    risk_color = 'warning'
else:
    risk_color = 'warning' if num_open_risks > 0 else 'secondary'

# Workstream Progress Chart
def progress_color(delta):
    if delta <= 15:
        return 'green'
    elif delta <= 30:
        return 'orange'
    return 'red'

ws_chart = go.Figure()
for _, row in ws_summary.iterrows():
    delta = abs(row['Planned %'] - row['Actual %'])
    ws_chart.add_trace(go.Bar(name='Planned', x=[row['Planned %']], y=[row['Workstream']], orientation='h', marker_color='blue'))
    ws_chart.add_trace(go.Bar(name='Actual', x=[row['Actual %']], y=[row['Workstream']], orientation='h', marker_color=progress_color(delta)))
ws_chart.update_layout(barmode='overlay', title='Workstream Progress', height=300)

# Section 3: Tasks This Month Table
task_table = dbc.Table.from_dataframe(tasks_this_month[['Task Name', 'Actual % Complete']], striped=True, bordered=True, hover=True)

# Section 4: Active Team Members (from "Assigned To")
if 'Assigned To' in df_workstreams.columns:
    assigned_people = df_workstreams['Assigned To'].dropna().astype(str).str.split(',').explode().str.strip().str.lower()
    active_names = assigned_people.unique()
else:
    active_names = []

df_team['Person Name Lower'] = df_team['Person Name'].astype(str).str.strip().str.lower()
active_members = df_team[df_team['Person Name Lower'].isin(active_names)]

# Photo Mapping (optional customization)
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

member_cards = [member_card(row['Person Name'], row['Role']) for _, row in active_members.iterrows()]

# KPI Card
kpi_card = dbc.Card([
    dbc.CardHeader("KPI Summary"),
    dbc.CardBody([
        dbc.Row([
            dbc.Col(html.Div([html.H2(f"{num_tasks}", className="text-primary text-center mb-0"),
                              html.P("Tasks This Month", className="text-muted text-center")])),
            dbc.Col(html.Div([html.H2([dbc.Badge(f"{num_open_risks}", color=risk_color, className="px-3 py-2", pill=True)],
                                      className="text-center mb-0"),
                              html.P("Open Risks", className="text-muted text-center")])),
            dbc.Col(html.Div([html.H2(f"{num_open_issues}", className="text-primary text-center mb-0"),
                              html.P("Open Issues", className="text-muted text-center")])),
        ], justify="center")
    ])
], className="p-3 shadow-sm")

# App Layout
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = dbc.Container([
    html.H2('Client Dashboard', className='text-center my-4'),

    dbc.Row([
        dbc.Col([kpi_card], width=6),
        dbc.Col(dbc.Card([dbc.CardHeader('Workstream Progress'), dbc.CardBody([dcc.Graph(figure=ws_chart)])], className="shadow-sm"), width=6),
    ], className='mb-4'),

    dbc.Row([
        dbc.Col(dbc.Card([dbc.CardHeader('Tasks This Month'), dbc.CardBody([task_table])], className="shadow-sm"), width=6),
        dbc.Col(dbc.Card([dbc.CardHeader('Active Team Members'), dbc.CardBody(member_cards)], className="shadow-sm"), width=6),
    ])
], fluid=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run_server(host='0.0.0.0', port=port)
