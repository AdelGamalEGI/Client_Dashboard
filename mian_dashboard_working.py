# Updated version of the dashboard with enhanced readability for milestones

import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from gspread_dataframe import get_as_dataframe
from oauth2client.service_account import ServiceAccountCredentials
import os

# Initialize app
app = dash.Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Member photos mapping
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

def milestone_dashboard_layout():
    return dbc.Container([
        html.H2("Milestone Dashboard", className="text-center my-4"),
        dcc.Interval(id='interval-refresh', interval=60*1000, n_intervals=0),
        dbc.Row([
            dbc.Col([
                dcc.Graph(id='milestone-gantt-chart'),
                html.Div("""
                    🟩 Not Started • 🟧 In Progress • 🟥 Delayed
                """, className="text-muted text-center mt-2")
            ], width=12)
        ]),
        html.Hr(),
        html.H4("Active Team Members", className="mt-4 mb-3"),
        dbc.Row(id='active-team-members'),

        # Modal for Activities
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="modal-title")),
            dbc.ModalBody(dash_table.DataTable(id='activities-table', style_table={"overflowX": "auto"}))
        ], id="activity-modal", size="xl", is_open=False)
    ])

@app.callback(
    Output('milestone-gantt-chart', 'figure'),
    Output('active-team-members', 'children'),
    Input('interval-refresh', 'n_intervals')
)
def update_dashboard(n):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open("Project_Planning_Workbook")

    df_milestones = get_as_dataframe(sheet.worksheet("Milestones")).dropna(how='all')
    df_activities = get_as_dataframe(sheet.worksheet("Activities")).dropna(how='all')
    df_references = get_as_dataframe(sheet.worksheet("References")).dropna(how='all')

    df_milestones['Start Date'] = pd.to_datetime(df_milestones['Start Date'], errors='coerce')
    df_milestones['End Date'] = pd.to_datetime(df_milestones['End Date'], errors='coerce')
    df_milestones['Overall Progress'] = pd.to_numeric(df_milestones['Overall Progress'], errors='coerce').fillna(0)

    today = pd.Timestamp.today()

    def progress_color(row):
        if row['Start Date'] > today:
            return 'green'  # Not yet started
        elif row['Overall Progress'] >= 0.8:
            return 'green'
        elif row['Overall Progress'] >= 0.3:
            return 'orange'
        return 'red'

    df_milestones['Color'] = df_milestones.apply(progress_color, axis=1)

    full_bars = []
progress_bars = []
for _, row in df_milestones.iterrows():
    full_bars.append({
        "Milestone Name": row['Milestone Name'],
        "Start": row['Start Date'],
        "End": row['End Date'],
        "Type": "Full",
        "Color": "lightgray",
        "Milestone ID": row['Milestone ID'],
        "Progress": row['Overall Progress']
    })

    progress_duration = row['Start Date'] + (row['End Date'] - row['Start Date']) * row['Overall Progress']
    progress_bars.append({
        "Milestone Name": row['Milestone Name'],
        "Start": row['Start Date'],
        "End": progress_duration,
        "Type": "Progress",
        "Color": row['Color'],
        "Milestone ID": row['Milestone ID'],
        "Progress": row['Overall Progress']
    })

combined_df = pd.DataFrame(full_bars + progress_bars)
fig = px.timeline(
    combined_df,
    x_start="Start",
    x_end="End",
    y="Milestone Name",
    color="Color",
    color_discrete_map={"lightgray": "lightgray", "green": "green", "orange": "orange", "red": "red"},
    hover_data={"Milestone ID": True, "Progress": ":.0%"},
    custom_data=["Milestone ID"]
)
fig.update_yaxes(autorange='reversed')
    fig.update_layout(
        title="Milestone Gantt Chart with Progress Coloring",
        xaxis_title="Timeline",
        xaxis_tickformat="%b %Y",
        xaxis=dict(showgrid=True),
        height=500,
        showlegend=False
    )

    fig.add_shape(
        type="line",
        x0=today,
        x1=today,
        y0=0,
        y1=1,
        xref="x",
        yref="paper",
        line=dict(dash="dot", color="black")
    )
    fig.add_annotation(
        x=today,
        y=1.02,
        text="Today",
        showarrow=False,
        xref="x",
        yref="paper",
        font=dict(size=12, color="black")
    )

    df_activities['Progress'] = pd.to_numeric(df_activities['Progress'], errors='coerce').fillna(0)
    active = df_activities[df_activities['Progress'] < 1]
    assigned_people = active['Assigned To'].dropna().astype(str).str.split(',').explode().str.strip().str.lower()
    df_references['Person Name Lower'] = df_references['Person Name'].astype(str).str.lower()
    active_members = df_references[df_references['Person Name Lower'].isin(assigned_people.unique())]
    cards = [member_card(row['Person Name'], row['Role']) for _, row in active_members.iterrows()]

    return fig, cards

@app.callback(
    Output("activity-modal", "is_open"),
    Output("modal-title", "children"),
    Output("activities-table", "data"),
    Output("activities-table", "columns"),
    Input("milestone-gantt-chart", "clickData"),
    State("activity-modal", "is_open")
)
def show_activities(clickData, is_open):
    if clickData:
        milestone_id = clickData['points'][0]['customdata'][0]
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        df = get_as_dataframe(client.open("Project_Planning_Workbook").worksheet("Activities")).dropna(how='all')
        df = df[df['Mielstone ID'] == milestone_id]  # note typo in column name
        data = df.to_dict('records')
        columns = [{"name": i, "id": i} for i in df.columns]
        return True, f"Activities for {milestone_id}", data, columns
    return False, dash.no_update, dash.no_update, dash.no_update

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
