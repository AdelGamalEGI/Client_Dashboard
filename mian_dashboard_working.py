# app.py: Self-contained Milestone Dashboard

import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import gspread
from gspread_dataframe import get_as_dataframe
from oauth2client.service_account import ServiceAccountCredentials
import os

# Initialize app
app = dash.Dash(__name__, suppress_callback_exceptions=True,
                external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Member photos mapping
PHOTO_MAPPING = {
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
    """Return a Bootstrap card with member photo and role."""
    key = name.strip().lower()
    img_file = PHOTO_MAPPING.get(key)
    if img_file:
        img = html.Img(src=f"/assets/{img_file}", height="45px",
                       style={'borderRadius': '50%'})
    else:
        img = html.Div("👤", style={'fontSize': '2rem'})
    return dbc.Card(
        dbc.Row([
            dbc.Col(img, width='auto'),
            dbc.Col([
                html.Div(html.Strong(name)),
                html.Div(html.Small(role, className='text-muted'))
            ])
        ], align='center'),
        className='mb-2 p-2 shadow-sm'
    )

# Layout definition
def milestone_dashboard_layout():
    return dbc.Container([
        html.H2("Milestone Dashboard", className="text-center my-4"),
        dcc.Interval(id='interval-refresh', interval=60 * 1000, n_intervals=0),
        dbc.Row([
            dbc.Col([
                dcc.Graph(id='milestone-gantt-chart'),
                html.Div(
                    "▫️ Not Started • 🟧 In Progress • 🟩 Completed • 🟥 Overdue (no progress past start date)",
                    className="text-muted text-center mt-2"
                )
            ], width=12)
        ]),
        html.Hr(),
        html.H4("Active Team Members", className="mt-4 mb-3"),
        dbc.Row(id='active-team-members'),
        # Modal for detailed activities
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="modal-title")),
            dbc.ModalBody(
                dash_table.DataTable(
                    id='activities-table',
                    style_table={"overflowX": "auto"},
                    page_size=10,
                )
            )
        ], id="activity-modal", size="xl", is_open=False)
    ])

# Set the app layout
app.layout = milestone_dashboard_layout()

# Main callback: update Gantt chart and member cards
def fetch_data():
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    book = client.open("Project_Planning_Workbook")
    df_m = get_as_dataframe(book.worksheet("Milestones")).dropna(how='all')
    df_a = get_as_dataframe(book.worksheet("Activities")).dropna(how='all')
    df_r = get_as_dataframe(book.worksheet("References")).dropna(how='all')
    return df_m, df_a, df_r

@app.callback(
    Output('milestone-gantt-chart', 'figure'),
    Output('active-team-members', 'children'),
    Input('interval-refresh', 'n_intervals')
)
def update_dashboard(n):
    # Load data
    df_milestones, df_activities, df_references = fetch_data()

    # Preprocess
    df_milestones['Start Date'] = pd.to_datetime(df_milestones['Start Date'], errors='coerce')
    df_milestones['End Date']   = pd.to_datetime(df_milestones['End Date'], errors='coerce')
    df_milestones['Overall Progress'] = (
        pd.to_numeric(df_milestones['Overall Progress'], errors='coerce').fillna(0)
    )
    today = pd.Timestamp.today()

    # Color logic
    def progress_color(row):
        if row['Overall Progress'] >= 1:
            return 'green'   # Completed
        if (today > row['Start Date']) and row['Overall Progress'] == 0:
            return 'red'     # Overdue
        if row['Overall Progress'] > 0:
            return 'orange'  # In progress
        return 'lightgray'  # Not started

    df_milestones['Color'] = df_milestones.apply(progress_color, axis=1)

    # Build bars
    bars = []
    for _, r in df_milestones.iterrows():
        # Full bar (gray or red)
        full_color = 'red' if (today > r['Start Date'] and r['Overall Progress'] == 0) else 'lightgray'
        bars.append({
            'Milestone Name': r['Milestone Name'],
            'Start': r['Start Date'],
            'End': r['End Date'],
            'Color': full_color,
            'Milestone ID': r['Milestone ID'],
            'Progress': r['Overall Progress']
        })
        # Progress overlay
        if r['Overall Progress'] > 0:
            end_prog = r['Start Date'] + (r['End Date'] - r['Start Date']) * r['Overall Progress']
            bars.append({
                'Milestone Name': r['Milestone Name'],
                'Start': r['Start Date'],
                'End': end_prog,
                'Color': r['Color'],
                'Milestone ID': r['Milestone ID'],
                'Progress': r['Overall Progress']
            })

    df_combined = pd.DataFrame(bars)

    # Plotly timeline
    fig = px.timeline(
        df_combined,
        x_start='Start', x_end='End',
        y='Milestone Name', color='Color',
        color_discrete_map={
            'lightgray': 'lightgray',
            'orange': 'orange',
            'green': 'green',
            'red': 'red'
        },
        hover_data={'Milestone ID': True, 'Progress': ':.0%'},
        custom_data=['Milestone ID']
    )
    fig.update_yaxes(autorange='reversed')
    fig.update_layout(
        title='Milestone Gantt Chart with Progress Coloring',
        xaxis_title='Timeline', xaxis_tickformat='%b %Y',
        xaxis=dict(showgrid=True), height=500, showlegend=False
    )
    # Today line
    fig.add_shape(
        type='line', x0=today, x1=today, y0=0, y1=1,
        xref='x', yref='paper', line=dict(dash='dot', color='black')
    )
    fig.add_annotation(
        x=today, y=1.02, text='Today', showarrow=False,
        xref='x', yref='paper'
    )

    # Active team members
    df_activities['Progress'] = pd.to_numeric(df_activities['Progress'], errors='coerce').fillna(0)
    active = df_activities[df_activities['Progress'] < 1]
    people = (
        active['Assigned To'].dropna()
              .astype(str).str.split(',')
              .explode().str.strip().str.lower()
    )
    df_references['Person Name Lower'] = (
        df_references['Person Name'].astype(str).str.lower()
    )
    members = df_references[df_references['Person Name Lower'].isin(people.unique())]
    cards = [member_card(r['Person Name'], r['Role']) for _, r in members.iterrows()]

    return fig, cards

# Modal callback
@app.callback(
    Output('activity-modal', 'is_open'),
    Output('modal-title', 'children'),
    Output('activities-table', 'data'),
    Output('activities-table', 'columns'),
    Input('milestone-gantt-chart', 'clickData'),
    State('activity-modal', 'is_open')
)
def show_activities(clickData, is_open):
    if clickData:
        mid = clickData['points'][0]['customdata'][0]
        df = fetch_data()[1]  # Activities sheet
        df = df[df['Mielstone ID'] == mid]
        data = df.to_dict('records')
        cols = [{'name': c, 'id': c} for c in df.columns]
        return True, f"Activities for {mid}", data, cols
    return False, dash.no_update, dash.no_update, dash.no_update

# Run server
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run(host='0.0.0.0', port=port, debug=True)
