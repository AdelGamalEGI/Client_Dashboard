import dash
from dash import html, dcc
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
start_month = now.replace(day=1)
end_month = (start_month + pd.offsets.MonthEnd(1)).date()
tasks_month = df_workstreams[
    (df_workstreams['Planned Start Date'] <= end_month) &
    (df_workstreams['Planned End Date'] >= start_month)
][['Activity Code', 'Activity Name', 'Planned Start Date', 'Planned End Date']]

# Team members with hours logged
df_resources['Allocated/Used Hours'] = pd.to_numeric(df_resources['Allocated/Used Hours'], errors='coerce')
active_team = df_resources[df_resources['Allocated/Used Hours'] > 0][['Person Name', 'Role', 'Allocated/Used Hours']]

# Dash app setup
app = dash.Dash(__name__)
server = app.server
app.title = "Client Dashboard"

app.layout = html.Div([
    html.H1("Client-Facing Project Dashboard", style={'textAlign': 'center'}),

    html.Div([
        html.Div([
            html.H3("Workstream Progress"),
            dcc.Graph(figure=fig_progress)
        ], className="six columns"),

        html.Div([
            html.H3("Risk Overview"),
            dcc.Graph(figure=fig_risk)
        ], className="six columns")
    ], className="row"),

    html.Div([
        html.Div([
            html.H3("Tasks in Current Month"),
            dcc.Markdown("#### Activities"),
            html.Table([
                html.Tr([html.Th(col) for col in tasks_month.columns])
            ] + [
                html.Tr([html.Td(tasks_month.iloc[i][col]) for col in tasks_month.columns])
                for i in range(len(tasks_month))
            ])
        ], className="six columns"),

        html.Div([
            html.H3("Active Team Members"),
            html.Table([
                html.Tr([html.Th(col) for col in active_team.columns])
            ] + [
                html.Tr([html.Td(active_team.iloc[i][col]) for col in active_team.columns])
                for i in range(len(active_team))
            ])
        ], className="six columns")
    ], className="row")
])

if __name__ == '__main__':
    app.run_server(debug=True)
