
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from datetime import datetime

# Load Excel data
file_path = 'Project_Management_Template_Updated.xlsx'
df_workstreams = pd.read_excel(file_path, sheet_name='Workstreams')
df_risks = pd.read_excel(file_path, sheet_name='Risk_Register')
df_resources = pd.read_excel(file_path, sheet_name='Resources')

# Preprocess data
df_workstreams['Progress %'] = pd.to_numeric(df_workstreams['Progress %'], errors='coerce')
df_workstreams['Planned Start Date'] = pd.to_datetime(df_workstreams['Planned Start Date'], errors='coerce')
df_workstreams['Planned End Date'] = pd.to_datetime(df_workstreams['Planned End Date'], errors='coerce')

# Workstream progress chart
workstream_summary = df_workstreams.groupby('Work-stream')['Progress %'].mean().reset_index()
fig_progress = px.bar(workstream_summary, x='Work-stream', y='Progress %', text='Progress %')

# Risk overview chart
risk_summary = df_risks['Risk Score'].value_counts().reset_index()
risk_summary.columns = ['Risk Score', 'Count']
fig_risk = px.bar(risk_summary, x='Risk Score', y='Count')

# Tasks this month
now = datetime.now()
start_month = pd.Timestamp(now.replace(day=1))
end_month = pd.Timestamp(start_month + pd.offsets.MonthEnd(1))
tasks_month = df_workstreams[
    (df_workstreams['Planned Start Date'] <= end_month) &
    (df_workstreams['Planned End Date'] >= start_month)
][['Activity Code', 'Activity Name', 'Planned Start Date', 'Planned End Date']]

# Team members with hours logged
df_resources['Allocated/Used Hours'] = pd.to_numeric(df_resources['Allocated/Used Hours'], errors='coerce')
active_team = df_resources[df_resources['Allocated/Used Hours'] > 0][['Person Name', 'Role', 'Allocated/Used Hours']]

# Dash app setup
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.title = "Client Dashboard"

app.layout = dbc.Container([
    html.H1("Client-Facing Project Dashboard", className="my-4 text-center"),

    dbc.Row([
        dbc.Col([
            html.H4("Workstream Progress"),
            dcc.Graph(figure=fig_progress)
        ], width=6),

        dbc.Col([
            html.H4("Risk Overview"),
            dcc.Graph(figure=fig_risk)
        ], width=6)
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            html.H4("Tasks in Current Month"),
            dbc.Table.from_dataframe(tasks_month, striped=True, bordered=True, hover=True)
        ], width=6),

        dbc.Col([
            html.H4("Active Team Members"),
            dbc.Table.from_dataframe(active_team, striped=True, bordered=True, hover=True)
        ], width=6)
    ])
], fluid=True)

if __name__ == '__main__':
    app.run_server(debug=True)
