
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
    values = sheet.worksheet("Risk_Register").get_all_values()
    headers = values[0]
    rows = values[1:]
    df_risks = pd.DataFrame(rows, columns=headers)

    df_risks['Likelihood (1-5)'] = pd.to_numeric(df_risks['Likelihood (1-5)'], errors='coerce')
    df_risks['Impact (1-5)'] = pd.to_numeric(df_risks['Impact (1-5)'], errors='coerce')
    
    score_counts = {
        "High": df_risks[df_risks['Risk Level'].astype(str).str.strip().str.lower() == 'high'].shape[0],
        "Medium": df_risks[df_risks['Risk Level'].astype(str).str.strip().str.lower() == 'medium'].shape[0],
        "Low": df_risks[df_risks['Risk Level'].astype(str).str.strip().str.lower() == 'low'].shape[0],
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
        ])
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
            if score >= 11:
                color = "red"
            elif score >= 6:
                color = "orange"
            else:
                color = "yellow"
            cell_content = html.Div(", ".join(risk_ids), style={"fontSize": "0.75rem"})
            row.append(html.Td(cell_content, style={"backgroundColor": color, "border": "1px solid #ccc", "width": "80px", "height": "80px", "textAlign": "center", "verticalAlign": "middle", "fontSize": "0.65rem", "whiteSpace": "normal", "wordWrap": "break-word", "overflow": "hidden"}))
        matrix_grid.append(html.Tr(row))

    matrix_table = dbc.Card([
        dbc.CardHeader("Risk Matrix (Likelihood × Impact)"),
        dbc.CardBody([
            html.Table(matrix_grid, style={"width": "100%", "borderCollapse": "collapse"})
        ])
    ])

    # --- Risk Table (Bottom) ---
    table_columns = ["Risk ID", "Risk Description", "Likelihood (1-5)", "Impact (1-5)", "Risk Level", "Status"]
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
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
