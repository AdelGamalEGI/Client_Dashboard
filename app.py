import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Minimal Dashboard View for Debug
dashboard_layout = html.Div([
    html.H2("Main Dashboard Loaded", className="my-3 text-success"),
    html.P("This is the dashboard layout. If you see this, routing works.")
])

# Minimal Risk View for Debug
risk_view_layout = html.Div([
    html.H2("Risk View Loaded", className="my-3 text-danger"),
    html.P("This is the risk view layout. Routing also works here."),
    dcc.Link("← Back to Dashboard", href="/", className="btn btn-secondary")
])

# App Layout with Location for Routing
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content")
])

@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    print("DEBUG: Current pathname is", pathname)
    if pathname == "/risks":
        return risk_view_layout
    else:
        return dashboard_layout

if __name__ == "__main__":
    app.run_server(debug=True)
