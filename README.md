# Data Boat Display

A Streamlit dashboard for temperature, pressure, altitude, humidity, and GY-271 heading readings.

The sensors contribute different measurements:

- AHT module: temperature and humidity
- BMP module (BMP180/BMP280 or compatible): pressure and altitude
- GY-271 (HMC5883L or QMC5883L): compass heading

Each serial sample should be a JSON object on one line:

```text
{"temperature":21.8,"pressure":1012.4,"altitude":125.3,"humidity":47.2,"heading":315.0}
```

### How to run it on your own machine

Prerequisite: install `uv` if you don't already have it.

```
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

1. Sync the dependencies

   ```
   $ uv sync
   ```

2. Run the app

   ```
   $ uv run streamlit run streamlit_app.py
   ```
