import json
import math
import time
from datetime import datetime

import pandas as pd
import serial
import serial.tools.list_ports
import streamlit as st
import altair as alt


MAX_POINTS = 240
SERIAL_FIELDS = (
    "temperature",
    "pressure",
    "altitude",
    "humidity",
    "heading",
)

st.set_page_config(
    page_title="Data Boat Sensor Readings",
    page_icon="⚓",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
        --ocean-deep: #061d33;
        --ocean-blue: #0b3a55;
        --seafoam: #5fd5c1;
        --foam: #edfaff;
    }

    .stApp {
        background:
            radial-gradient(circle at 82% 12%, rgba(95, 213, 193, 0.16), transparent 24rem),
            linear-gradient(145deg, #061d33 0%, #083653 55%, #0a4d63 100%);
        color: var(--foam);
    }

    [data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, rgba(4, 29, 48, 0.98), rgba(8, 67, 82, 0.96));
        border-right: 1px solid rgba(137, 231, 218, 0.18);
    }

    [data-testid="stSidebar"] * {
        color: #edfaff;
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    h1, h2, h3 {
        color: #f3fdff !important;
        letter-spacing: 0.01em;
    }

    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(19, 101, 123, 0.72), rgba(9, 61, 82, 0.82));
        border: 1px solid rgba(137, 231, 218, 0.24);
        border-radius: 18px;
        box-shadow: 0 12px 32px rgba(2, 18, 34, 0.28);
        padding: 16px 18px;
    }

    [data-testid="stMetricLabel"] {
        color: #bdebe4 !important;
    }

    [data-testid="stMetricValue"] {
        color: #ffffff !important;
    }

    [data-testid="stExpander"] {
        background: rgba(8, 58, 78, 0.72);
        border: 1px solid rgba(137, 231, 218, 0.20);
        border-radius: 14px;
    }

    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary * {
        color: #edfaff !important;
    }

    .stAlert {
        background: rgba(9, 65, 84, 0.82) !important;
        border: 1px solid rgba(137, 231, 218, 0.22);
        border-radius: 14px;
        color: #edfaff !important;
    }

    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(137, 231, 218, 0.18);
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        box-sizing: border-box;
        width: 100%;
        max-width: 100%;
        overflow: hidden;
        border: 3px solid #111111;
        border-radius: 24px;
        padding: 14px;
        background: rgba(237, 250, 255, 0.82);
        box-shadow: 0 10px 24px rgba(2, 18, 34, 0.24);
    }

    [data-testid="stVegaLiteChart"] {
        border-radius: 12px;
        overflow: hidden;
    }

    [data-testid="stAppViewBlockContainer"] {
        padding-top: 2.2rem;
    }

    .data-boat-title {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        margin-bottom: 0.15rem;
        color: #f3fdff;
        font-size: 2.35rem;
        font-weight: 700;
    }

    .data-boat-title span {
        font-size: 2.1rem;
    }

    .data-boat-subtitle {
        color: #addfd9;
        margin: 0 0 1.2rem 0;
    }

    #MainMenu, footer {
        visibility: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def new_history():
    return pd.DataFrame(columns=["timestamp", *SERIAL_FIELDS])


def normalize_reading(reading):
    normalized = {"timestamp": datetime.now()}
    for field in SERIAL_FIELDS:
        value = reading.get(field)
        normalized[field] = float(value) if value is not None else None
    return normalized


def demo_reading():
    now = time.time()
    return normalize_reading(
        {
            "temperature": 21.5 + 1.2 * math.sin(now / 12),
            "pressure": 1013.25 + 1.8 * math.sin(now / 20),
            "altitude": 125 + 15 * math.sin(now / 20),
            "humidity": 48 + 5 * math.sin(now / 15),
            "heading": (now * 4) % 360,
        }
    )


def read_serial_line(port_name, baud_rate):
    connection = st.session_state.get("serial_connection")
    if connection is None or not connection.is_open:
        connection = serial.Serial(port_name, baud_rate, timeout=0.25)
        st.session_state.serial_connection = connection

    raw_line = connection.readline()
    if not raw_line:
        return None

    line = raw_line.decode("utf-8", errors="replace").strip()
    if not line:
        return None

    return normalize_reading(json.loads(line))


def append_reading(history, reading):
    row = pd.DataFrame([reading])
    return pd.concat([history, row], ignore_index=True).tail(MAX_POINTS)


def close_connection():
    connection = st.session_state.pop("serial_connection", None)
    if connection is not None and connection.is_open:
        connection.close()


if "history" not in st.session_state:
    st.session_state.history = new_history()

st.title("Data Boat Sensor Readings")
st.caption("Temperature, pressure, altitude, humidity, and GY-271 heading")

with st.sidebar:
    st.header("Source")
    data_source = st.radio(
        "Input",
        ["Serial port", "Demo data"],
        index=1,
        help="BMP supplies pressure/altitude, AHT supplies temperature/humidity, and GY-271 supplies heading.",
    )

    baud_rate = 115200
    selected_port = None
    if data_source == "Serial port":
        ports = serial.tools.list_ports.comports()
        port_names = [port.device for port in ports]
        selected_port = st.selectbox(
            "USB serial port",
            port_names,
            index=0 if port_names else None,
            placeholder="No serial ports found",
        )
        baud_rate = st.number_input("Baud rate", min_value=1200, value=115200, step=100)

        if st.button("Disconnect"):
            close_connection()
            st.success("Serial connection closed.")
    else:
        if st.session_state.get("serial_connection") is not None:
            close_connection()

    refresh_seconds = st.slider("Refresh interval (seconds)", 0.5, 5.0, 1.0, 0.5)
    if st.button("Clear history"):
        st.session_state.history = new_history()

reading = None
error = None

if data_source == "Demo data":
    reading = demo_reading()
elif selected_port:
    try:
        reading = read_serial_line(selected_port, int(baud_rate))
    except (serial.SerialException, json.JSONDecodeError, ValueError, OSError) as exc:
        error = str(exc)
        close_connection()

if error:
    st.error(f"Could not read sensor data: {error}")
elif reading is not None:
    st.session_state.history = append_reading(st.session_state.history, reading)

history = st.session_state.history
latest = history.iloc[-1] if not history.empty else None

metric_columns = st.columns(5)
metric_specs = [
    ("temperature", "Temperature", "°C"),
    ("pressure", "Pressure", "hPa"),
    ("altitude", "Altitude", "m"),
    ("humidity", "Humidity", "%"),
    ("heading", "GY-271 heading", "°"),
]

for column, (field, label, unit) in zip(metric_columns, metric_specs):
    value = latest[field] if latest is not None and pd.notna(latest[field]) else None
    column.metric(label, f"{value:.2f} {unit}" if value is not None else "No data")

if not history.empty:
    chart_data = history.set_index("timestamp")
    chart_specs = [
        ("temperature", "Temperature (°C)", "temperature"),
        ("pressure", "Pressure (hPa)", "pressure"),
        ("altitude", "Altitude (m)", "altitude"),
        ("humidity", "Humidity (%)", "humidity"),
        ("heading", "GY-271 Heading (°)", "heading"),
    ]

    chart_columns = st.columns(2)
    for index, (field, label, column_name) in enumerate(chart_specs):
        with chart_columns[index % 2]:
            with st.container(border=True):
                st.subheader(label)
                plot_data = chart_data[[column_name]].dropna().reset_index()
                chart = (
                    alt.Chart(plot_data)
                    .mark_line(strokeWidth=3, color="#5fd5c1")
                    .encode(
                        x=alt.X(
                            "timestamp:T",
                            title=None,
                            axis=alt.Axis(
                                labelFontSize=12,
                                labelFontWeight="bold",
                                labelColor="#111111",
                                tickColor="#111111",
                                domainColor="#111111",
                                domainWidth=2,
                                gridColor="rgba(17, 17, 17, 0.12)",
                            ),
                        ),
                        y=alt.Y(
                            f"{column_name}:Q",
                            title=None,
                            axis=alt.Axis(
                                labelFontSize=12,
                                labelFontWeight="bold",
                                labelColor="#111111",
                                tickColor="#111111",
                                domainColor="#111111",
                                domainWidth=2,
                                gridColor="rgba(17, 17, 17, 0.12)",
                            ),
                        ),
                    )
                    .properties(
                        height=220,
                        padding={"left": 10, "right": 10, "top": 10, "bottom": 10},
                    )
                    .configure_view(stroke="#111111", strokeWidth=2)
                )
                st.altair_chart(chart, use_container_width=True)

    with st.expander("Latest readings"):
        st.dataframe(history.sort_values("timestamp", ascending=False), use_container_width=True)
else:
    st.info("Waiting for sensor data...")

time.sleep(refresh_seconds)
st.rerun()
