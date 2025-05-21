import os
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc

# Import your two standalone dashboards
from mian_dashboard_working import main_dashboard, refresh_dashboard as main_refresh
from risk_dashboard_working import risk_dashboard

# Initialize Dash
app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP]
)
server = app.server

# Home layout
home_layout = dbc.Container([
    html.H1("Welcome to AIS Portal", className="text-center my-4"),
    dbc.Row([
        dbc.Col(
            dcc.Link(
                dbc.Button("📊 Dashboard", color="primary", className="btn-lg w-100"),
                href="/dashboard"
            ),
            width=3
        ),
        dbc.Col(
            dcc.Link(
                dbc.Button("🛡️ Risk View", color="danger", className="btn-lg w-100"),
                href="/risks"
            ),
            width=3
        ),
    ], justify="center", className="my-5 g-4"),
    html.P(
        "Select an option above to view the AIS Dashboard or Risk View.",
        className="text-center text-muted"
    )
], fluid=True)

# App layout
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content")
])

# Routing callback
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

# Re-bind existing refresh callback
app.callback(
    Output('kpi-summary', 'children'),
    Output('workstream-progress-chart', 'figure'),
    Output('tasks-table', 'children'),
    Output('team-members', 'children'),
    Input('interval-refresh', 'n_intervals')
)(main_refresh)

# Run server on Render-compatible host & port
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
