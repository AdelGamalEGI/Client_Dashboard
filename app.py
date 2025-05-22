import os
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc

# Import your two standalone dashboards
from mian_dashboard_working import main_dashboard, refresh_dashboard as main_refresh
from risk_dashboard_working import risk_dashboard
from issue_dashboard      import issue_dashboard, register_issue_callbacks

# Initialize Dash
app    = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP]
)
server = app.server

# Home layout with navigation buttons
home_layout = dbc.Container([
    html.H1("Welcome to AIS Portal", className="text-center my-4"),
    dbc.Row([
        dbc.Col(
            dcc.Link(
                dbc.Button("📊 Dashboard", color="primary", className="btn-lg w-100"),
                href="/dashboard"
            ),
            width=4
        ),
        dbc.Col(
            dcc.Link(
                dbc.Button("🛡️ Risk View", color="danger", className="btn-lg w-100"),
                href="/risks"
            ),
            width=4
        ),
        dbc.Col(
            dcc.Link(
                dbc.Button("🐞 Issue Tracker", color="warning", className="btn-lg w-100"),
                href="/issues"
            ),
            width=4
        ),
    ], justify="center", className="my-4"),
    html.P(
        "Select an option above to navigate between views.",
        className="text-center text-muted"
    )
], fluid=True)

# App layout
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content")
])

# Page routing callback
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    if pathname == "/dashboard":
        return main_dashboard()
    elif pathname == "/risks":
        return risk_dashboard()
    elif pathname == "/issues":
        return issue_dashboard()
    else:
        return home_layout

# Re-bind the existing refresh callback from the main dashboard
app.callback(
    Output('kpi-summary', 'children'),
    Output('workstream-progress-chart', 'figure'),
    Output('tasks-table', 'children'),
    Output('team-members', 'children'),
    Input('interval-refresh', 'n_intervals')
)(main_refresh)

# Register the issue-tracker callbacks
register_issue_callbacks(app)

# Run server on Render-compatible host & port
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
