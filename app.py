import os
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc

# Import full Dash app from your new milestone-based dashboard
from mian_dashboard_working import app as milestone_app
from risk_dashboard_working import risk_dashboard
from issue_dashboard import issue_dashboard, register_issue_callbacks

server = milestone_app.server  # Use the server object from the imported app

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

# Wrap the imported app layout with routing
milestone_app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content")
])

# Page routing
@milestone_app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    if pathname == "/dashboard":
        return milestone_app.layout  # dashboard layout is already set in the main file
    elif pathname == "/risks":
        return risk_dashboard()
    elif pathname == "/issues":
        return issue_dashboard()
    else:
        return home_layout

# Register issue tracker callbacks
register_issue_callbacks(milestone_app)

# Run server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    milestone_app.run(host="0.0.0.0", port=port, debug=True)
