
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime

# Load data
file_path = 'Project_Management_Template_Updated.xlsx'
df_workstreams = pd.read_excel(file_path, sheet_name='Workstreams')
df_risks = pd.read_excel(file_path, sheet_name='Risk_Register')
df_issues = pd.read_excel(file_path, sheet_name='Issue_Tracker')
df_resources = pd.read_excel(file_path, sheet_name='Resources')

# Preprocessing
df_workstreams['Planned Start Date'] = pd.to_datetime(df_workstreams['Planned Start Date'], errors='coerce')
df_workstreams['Planned End Date'] = pd.to_datetime(df_workstreams['Planned End Date'], errors='coerce')
df_workstreams['Progress %'] = pd.to_numeric(df_workstreams['Progress %'], errors='coerce')
df_resources['Allocated/Used Hours'] = pd.to_numeric(df_resources['Allocated/Used Hours'], errors='coerce')

# Calculate Planned % based on time elapsed
today = pd.Timestamp(datetime.today().date())
duration = (df_workstreams['Planned End Date'] - df_workstreams['Planned Start Date']).dt.days
elapsed = (today - df_workstreams['Planned Start Date']).dt.days
df_workstreams['Planned %'] = ((elapsed / duration) * 100).clip(lower=0, upper=100).fillna(0)

# Timeframe
start_month = pd.to_datetime(datetime.today().replace(day=1))
end_month = pd.to_datetime(start_month + pd.offsets.MonthEnd(1))

# KPI Summary
tasks_this_month = df_workstreams[(df_workstreams['Planned Start Date'] <= end_month) & (df_workstreams['Planned End Date'] >= start_month)]
num_tasks = tasks_this_month.shape[0]
open_issues = df_issues[df_issues['Status'].str.lower() == 'open']
num_open_issues = open_issues.shape[0]
open_risks = df_risks[df_risks['Status'].str.lower() == 'open']
num_open_risks = open_risks.shape[0]

# Risk color logic
if 'High' in open_risks['Risk Score'].values:
    risk_color = 'danger'
elif 'Medium' in open_risks['Risk Score'].values:
    risk_color = 'warning'
else:
    risk_color = 'warning' if num_open_risks > 0 else 'secondary'

# Workstream progress chart
def get_color(delta):
    if delta <= 15:
        return 'green'
    elif delta <= 30:
        return 'orange'
    return 'red'

ws_chart = go.Figure()
for _, row in df_workstreams.groupby('Work-stream').mean(numeric_only=True).reset_index().iterrows():
    delta = abs(row['Planned %'] - row['Progress %'])
    color = get_color(delta)
    ws_chart.add_trace(go.Bar(name='Planned', x=[row['Planned %']], y=[row['Work-stream']], orientation='h', marker_color='blue'))
    ws_chart.add_trace(go.Bar(name='Actual', x=[row['Progress %']], y=[row['Work-stream']], orientation='h', marker_color=color))
ws_chart.update_layout(barmode='overlay', title='Workstream Progress', height=300)

# Task table
task_table = dbc.Table.from_dataframe(tasks_this_month[['Activity Name', 'Progress %']], striped=True, bordered=True, hover=True)

# Active team members (assigned to tasks this month)
active_members = df_resources[df_resources['Allocated/Used Hours'] > 0][['Person Name', 'Role']].dropna()

def member_card(name, role):
    return dbc.Card(
        dbc.Row([
            dbc.Col(html.Div("👷", style={'fontSize': '2rem'}), width='auto'),
            dbc.Col([
                html.Div(html.Strong(name)),
                html.Div(html.Small(role, className='text-muted'))
            ])
        ], align='center'),
        className='mb-2 p-2 shadow-sm'
    )

member_cards = [member_card(row['Person Name'], row['Role']) for _, row in active_members.iterrows()]

# Layout
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = dbc.Container([
    html.H2('Client Dashboard', className='text-center my-4'),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader('KPI Summary'),
                dbc.CardBody([
                    html.Div(f'Tasks this month: {num_tasks}', className='text-primary mb-2'),
                    html.Div(f'Open Risks: {num_open_risks}', className=f'text-{risk_color} mb-2'),
                    html.Div(f'Open Issues: {num_open_issues}', className='text-primary')
                ])
            ])
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader('Workstream Progress'),
                dbc.CardBody([dcc.Graph(figure=ws_chart)])
            ])
        ], width=6)
    ], className='mb-4'),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader('Tasks This Month'),
                dbc.CardBody([task_table])
            ])
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader('Active Team Members'),
                dbc.CardBody(member_cards)
            ])
        ], width=6)
    ])
], fluid=True)

# Render-compatible port binding
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run_server(host='0.0.0.0', port=port)
