# Updated version of mian_dashboard_working.py with two-layer Gantt bars and status legend

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
                html.Div(
                    "▫️ Not Started • 🟧 In Progress • 🟩 Completed • 🟥 Overdue", 
                    className="text-muted text-center mt-2"
                )
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
    ], fluid=True)

# Helper to read data from Google Sheets
def fetch_data():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
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

    # Preprocess milestone dates and progress
    df_milestones['Start Date'] = pd.to_datetime(df_milestones['Start Date'], errors='coerce')
    df_milestones['End Date']   = pd.to_datetime(df_milestones['End Date'], errors='coerce')
    df_milestones['Overall Progress'] = (
        pd.to_numeric(df_milestones['Overall Progress'], errors='coerce').fillna(0)
    )
    today = pd.Timestamp.today()

    # Build bars: background and overlay
    bars = []
    for _, r in df_milestones.iterrows():
        start = r['Start Date']
        end = r['End Date']
        prog = r['Overall Progress']
        mid = r['Milestone ID']
        name = r['Milestone Name']

        # Base bar: always lightgray
        bars.append({
            'Milestone Name': name,
            'Start': start,
            'End': end,
            'Category': 'Background',
            'Milestone ID': mid,
            'Progress': prog
        })

        # Determine overlay end date
        overlay_end = min(today, end)
        if overlay_end > start:
            # Determine status for overlay color
            if today < end:
                # Before end date
                if prog > 0:
                    status = 'In Progress'
                else:
                    status = 'Not Started'
            else:
                # On or after end date
                if prog < 1:
                    status = 'Overdue'
                else:
                    status = 'Completed'

            bars.append({
                'Milestone Name': name,
                'Start': start,
                'End': overlay_end,
                'Category': status,
                'Milestone ID': mid,
                'Progress': prog
            })

    df_combined = pd.DataFrame(bars)

    # Color mapping for categories
    color_map = {
        'Background': 'lightgray',
        'Not Started': 'lightgray',
        'In Progress': 'orange',
        'Overdue': 'red',
        'Completed': 'green'
    }

    # Create Gantt chart
    fig = px.timeline(
        df_combined,
        x_start='Start', x_end='End',
        y='Milestone Name', color='Category',
        color_discrete_map=color_map,
        hover_data={'Milestone ID': True, 'Progress': ':.0%'},
        custom_data=['Milestone ID']
    )
    # Hide background category from legend
    for trace in fig.data:
        if trace.name == 'Background':
            trace.showlegend = False

    fig.update_yaxes(autorange='reversed')
    fig.update_layout(
        title='Milestone Gantt Chart with Progress Coloring',
        xaxis_title='Timeline', xaxis_tickformat='%b %Y',
        height=500, showlegend=True, legend_title_text='Milestone Status'
    )
    # Add "Today" line
    fig.add_shape(
        type='line', x0=today, x1=today, y0=0, y1=1,
        xref='x', yref='paper', line=dict(dash='dot', color='black')
    )
    fig.add_annotation(
        x=today, y=1.02, text='Today', showarrow=False,
        xref='x', yref='paper'
    )

    # Determine active team members
    df_activities['Progress'] = pd.to_numeric(df_activities['Progress'], errors='coerce').fillna(0)
    active = df_activities[df_activities['Progress'] < 1]
    assigned_people = (
        active['Assigned To']
        .dropna()
        .astype(str)
        .str.split(',')
        .explode()
        .str.strip()
        .str.lower()
    )
    df_references['Person Name Lower'] = df_references['Person Name'].astype(str).str.lower()
    active_members = df_references[df_references['Person Name Lower'].isin(assigned_people.unique())]
    cards = [member_card(row['Person Name'], row['Role']) for _, row in active_members.iterrows()]

    return fig, cards

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
        milestone_id = clickData['points'][0]['customdata'][0]
        _, df_activities, _ = fetch_data()
        df = df_activities[df_activities['Mielstone ID'] == milestone_id]
        data = df.to_dict('records')
        columns = [{"name": i, "id": i} for i in df.columns]
        return True, f"Activities for {milestone_id}", data, columns
    return False, dash.no_update, dash.no_update, dash.no_update

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
