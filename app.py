
import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import gspread
from gspread_dataframe import get_as_dataframe
from oauth2client.service_account import ServiceAccountCredentials
import os

app = dash.Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# --- Layouts ---

home_layout = html.Div([
    html.H1("Welcome to AIS Portal", className="text-center my-4"),
    dbc.Row([
        dbc.Col(dcc.Link(dbc.Button("📊 Dashboard", color="primary", className="btn-lg w-100"), href="/dashboard"), width=6),
        dbc.Col(dcc.Link(dbc.Button("🛡️ Risk View", color="danger", className="btn-lg w-100"), href="/risks"), width=6),
    ], className="my-4 text-center", justify="center")
])

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content")
])

@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def display_page(pathname):
    if pathname == "/dashboard":
        return html.Div("DASHBOARD PLACEHOLDER")
    elif pathname == "/risks":
        return risk_dashboard()
    else:
        return home_layout

def risk_dashboard():
    # GSheet load
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open("Project_Planning_Workbook")
    df_risks = get_as_dataframe(sheet.worksheet("Risk_Register")).dropna(how="all")

    # Clean and prep
    df_risks['Likelihood (1-5)'] = pd.to_numeric(df_risks['Likelihood (1-5)'], errors='coerce')
    df_risks['Impact (1-5)'] = pd.to_numeric(df_risks['Impact (1-5)'], errors='coerce')
    df_risks = df_risks[df_risks['Status'].astype(str).str.lower().str.strip() == 'open']

    # --- Summary (Top Left): Count by Risk Category ---
    summary = df_risks.groupby('Risk Category')['Risk Score'].agg(['count']).reset_index()
    summary_chart = dbc.Card([
        dbc.CardHeader("Open Risks by Category"),
        dbc.CardBody([
            dcc.Graph(
                figure=go.Figure(
                    data=[go.Bar(x=summary['Risk Category'], y=summary['count'], marker_color='crimson')],
                    layout=go.Layout(height=300, margin=dict(l=30, r=30, t=40, b=30))
                )
            )
        ])
    ])

    # --- Matrix (Top Right) ---
    matrix = df_risks.groupby(['Likelihood (1-5)', 'Impact (1-5)']).size().reset_index(name='Count')
    heatmap = go.Figure(data=go.Heatmap(
        z=matrix['Count'],
        x=matrix['Likelihood (1-5)'],
        y=matrix['Impact (1-5)'],
        colorscale='YlOrRd'
    ))
    heatmap.update_layout(title="Risk Matrix (Likelihood × Impact)", height=300, margin=dict(l=40, r=20, t=40, b=20))

    matrix_chart = dbc.Card([
        dbc.CardHeader("Risk Matrix"),
        dbc.CardBody(dcc.Graph(figure=heatmap))
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

    # Combine Layout
    return dbc.Container([
        html.H2("Risk Dashboard", className="text-center my-4"),
        dbc.Row([
            dbc.Col(summary_chart, width=6),
            dbc.Col(matrix_chart, width=6)
        ], className="mb-4"),
        dbc.Row([
            dbc.Col([
                html.H5("Open Risks Table", className="mb-3"),
                risk_table
            ])
        ])
    ], fluid=True)

# Deployment config
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
