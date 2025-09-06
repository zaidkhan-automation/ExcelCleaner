
# premium_dashboard.py
import base64, io
from datetime import datetime
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, ctx, dash_table
import plotly.express as px

app = Dash(__name__)
server = app.server

# --- layout ---
app.layout = html.Div(
    [
        html.H1("Premium Data Dashboard", style={"textAlign": "center"}),
        dcc.Upload(
            id="upload-data",
            children=html.Div(["Drag & Drop or Select a CSV File"]),
            style={
                "width": "60%",
                "margin": "10px auto",
                "padding": "20px",
                "borderWidth": "2px",
                "borderStyle": "dashed",
                "textAlign": "center",
            },
            multiple=False,
        ),
        html.Div(id="status-message", style={"textAlign": "center", "color": "darkblue"}),
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Filter by Region:"),
                        dcc.Dropdown(id="region-filter", options=[], value=None, multi=False, placeholder="No region"),
                    ],
                    style={"width": "30%", "display": "inline-block", "verticalAlign": "top"},
                ),
                html.Div(
                    [
                        html.Label("Filter by Date:"),
                        dcc.DatePickerRange(
                            id="date-range",
                            start_date_placeholder_text="Start date",
                            end_date_placeholder_text="End date",
                        ),
                    ],
                    style={"width": "35%", "display": "inline-block", "marginLeft": "2rem"},
                ),
                html.Div(
                    [
                        html.Label("Chart Type:"),
                        dcc.Dropdown(id="chart-type", options=[{"label": "Bar", "value": "bar"}, {"label": "Line", "value": "line"}], value="bar"),
                    ],
                    style={"width": "25%", "display": "inline-block", "marginLeft": "2rem"},
                ),
            ],
            style={"width": "95%", "margin": "0 auto", "paddingTop": "10px"},
        ),
        dcc.Loading(dcc.Graph(id="main-graph"), type="circle"),
        html.Div(id="summary-stats", style={"width": "95%", "margin": "1rem auto"}),
        html.Button("Download Filtered Data", id="download-btn", n_clicks=0),
        dcc.Download(id="download-csv"),
        # hidden store for parsed dataframe (serialized)
        dcc.Store(id="df-store"),
    ],
    style={"fontFamily": "Arial, sans-serif"},
)


# --- helper to parse uploaded CSV ---
def parse_contents(contents, filename):
    if not contents:
        return None, "No file contents provided."

    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    try:
        # try to read CSV (utf-8 / latin-1 fallback)
        try:
            df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
        except UnicodeDecodeError:
            df = pd.read_csv(io.StringIO(decoded.decode("latin-1")))
    except Exception as e:
        return None, f"Error reading CSV: {e}"

    # normalize column names lower-case
    df.columns = [c.strip().lower() for c in df.columns]

    # required columns
    required = {"date", "region", "sales"}
    if not required.issubset(set(df.columns)):
        missing = required.difference(set(df.columns))
        return None, f"CSV missing required columns: {', '.join(missing)}"

    # convert date
    try:
        df["date"] = pd.to_datetime(df["date"])
    except Exception as e:
        return None, f"Could not parse 'date' column as datetime: {e}"

    # ensure sales numeric
    df["sales"] = pd.to_numeric(df["sales"], errors="coerce")
    if df["sales"].isna().all():
        return None, "All values in 'sales' are non-numeric."

    df = df.dropna(subset=["date", "region"])  # remove rows without critical data
    df = df.sort_values("date").reset_index(drop=True)
    return df, None


# --- single callback to update everything after upload or filter changes ---
@app.callback(
    Output("df-store", "data"),  # serialized dataframe (to keep state)
    Output("region-filter", "options"),
    Output("region-filter", "value"),
    Output("date-range", "start_date"),
    Output("date-range", "end_date"),
    Output("main-graph", "figure"),
    Output("summary-stats", "children"),
    Output("status-message", "children"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    Input("region-filter", "value"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
    Input("chart-type", "value"),
    prevent_initial_call=False,
)
def update_all(contents, filename, region_value, start_date, end_date, chart_type):
    # default empty outputs
    empty_fig = {
        "data": [],
        "layout": {"xaxis": {"visible": True}, "yaxis": {"visible": True}, "annotations": []},
    }
    empty_children = ""
    # No file uploaded yet: return defaults
    if not contents:
        return None, [], None, None, None, empty_fig, empty_children, "Upload a CSV with columns: date, region, sales."

    # parse uploaded file
    df, err = parse_contents(contents, filename)
    if err:
        return None, [], None, None, None, empty_fig, empty_children, f"Error: {err}"

    # prepare region options
    regions = sorted(df["region"].dropna().unique().tolist())
    region_options = [{"label": r, "value": r} for r in regions]

    # default region_value if not set or invalid
    if region_value not in regions:
        region_value = regions[0] if regions else None

    # determine date range defaults
    min_date = df["date"].min().date() if not df["date"].empty else None
    max_date = df["date"].max().date() if not df["date"].empty else None

    # apply filters
    filtered = df.copy()
    if region_value:
        filtered = filtered[filtered["region"] == region_value]
    try:
        if start_date:
            filtered = filtered[filtered["date"] >= pd.to_datetime(start_date)]
        if end_date:
            filtered = filtered[filtered["date"] <= pd.to_datetime(end_date)]
    except Exception:
        # if date parse fails, ignore date filtering
        pass

    # Prepare figure by grouping by date
    if filtered.empty:
        fig = {
            "data": [],
            "layout": {"title": "No data for selected filters", "xaxis": {"visible": True}, "yaxis": {"visible": True}},
        }
        summary = html.Div(["No data found for current filter selection."])
    else:
        agg = filtered.groupby(filtered["date"].dt.date)["sales"].sum().reset_index()
        agg.columns = ["date", "sales"]
        if chart_type == "line":
            fig = px.line(agg, x="date", y="sales", title=f"Sales for {region_value} (aggregated by date)")
        else:
            fig = px.bar(agg, x="date", y="sales", title=f"Sales for {region_value} (aggregated by date)")
        fig.update_layout(xaxis_title="Date", yaxis_title="Sales", template="plotly_white")

        # summary stats
        total = filtered["sales"].sum()
        avg = filtered["sales"].mean()
        rows = len(filtered)
        summary = html.Div(
            [
                html.P(f"Rows: {rows}"),
                html.P(f"Total Sales: {total:.2f}"),
                html.P(f"Average per row: {avg:.2f}"),
            ]
        )

    # store dataframe as JSON (ISO format for dates)
    store_json = filtered.to_json(date_format="iso", orient="split")

    status = f"Loaded '{filename}'. Regions found: {len(region_options)}. Showing region: {region_value}."
    return store_json, region_options, region_value, min_date, max_date, fig, summary, status


# --- download callback (separate, single output) ---
@app.callback(
    Output("download-csv", "data"),
    Input("download-btn", "n_clicks"),
    State("df-store", "data"),
    prevent_initial_call=True,
)
def download_filtered(n_clicks, json_data):
    if not json_data:
        return dcc.send_string("No data to download", filename="empty.txt")
    df = pd.read_json(json_data, orient="split")
    return dcc.send_data_frame(df.to_csv, "filtered_data.csv", index=False)


if __name__ == "__main__":
    app.run(debug=True, port=8050)