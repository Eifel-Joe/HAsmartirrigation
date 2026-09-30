---
layout: default
title: Usage: Troubleshooting
---
# Troubleshooting

> Main page: [Usage](usage.md)<br/>
> Previous: [Automations](usage-automations.md)<br/>

In order to troubleshoot this integration or get help, it's important to check two sources:
- the diagnostic file / storage file. You can either generate a diagnostic file or get the `irrigation_plus.storage` file from the `configuration/.storage` folder. To download a diagnostics file, in Home Assistant, go to Settings >Devices&Services > Integrations >Irrigation Plus, or use this [link](https://my.home-assistant.io/redirect/integration/?domain=irrigation_plus). Click the 'three vertical dots' menu and select 'download diagnostics'.

## Reading the diagnostic / storage file
The diagnostic / storage file is in a JSON format and lists your configuration settings, your zones, sensor groups and modules.
It also lists the weather data collected. The weather data is stored in the metric system, so might not match up with what you see in the UI.
Here's a list of units:

- Dewpoint, Temperature: degrees Celsius (C)
- Evapotranspiration, Total Precipitation: millimeters (mm)
- Humidity: Percentage (%)
- Pressure: converted to absolute if provided as relative pressure and stored in hPa
- Solar radiation: megajoule per day per square meter (MJ/day/m2)
- Windspeed: meter per second (m/s)

The reason we're using these units is consistency but also because the most-used module (PyETO) requires the data to be provided in these units (at least, that's what the limited documentation and code seem to imply).
For those interested, [here's the function that does this most of the conversion in code (with the exception of the absolute to relative conversion for pressure)](https://github.com/JustChr/HAsmartirrigation/blob/7c206809ac35a686a16eb8b3b209d030a28463f7/custom_components/irrigation_plus/helpers.py#L115): 

## Docker or Core: the container's time zone {#container-timezone}

The integration records the time of each weather reading, and of each zone's last
calculation, on the clock you set in Home Assistant under **Settings → System →
General**. The time zone of the container Home Assistant runs in (on a Core install, the
machine's) does not change the calculation.

Earlier releases recorded those times on the container's clock. If you ran Home Assistant
in Docker, or as a Core install in a virtual environment, and the container's time zone
differed from Home Assistant's, the intra-day live estimate drifted away from the figure
the nightly calculation arrives at, and on installs that use solar radiation the
radiation figures were off as well. Home Assistant OS and Supervised keep the two in
step, so this could not happen there.

**When you update from such a release,** the times already recorded are converted once,
the first time Home Assistant starts with the new release: each is read in the
container's time zone as it is at that moment and moved onto Home Assistant's clock. If
the two zones already agree, nothing moves. So leave the container's time zone (its `TZ`;
on a Core install, the machine's) as it is until Home Assistant has started once with the
new release, and change it afterwards if you want to. If you change it in the same step,
the first calculation afterwards covers a period that is too long or too short by the
difference between the two zones, and the figures settle within a calculation or two.

Changing the time zone in Home Assistant itself has the same effect: the times already
recorded carry no zone of their own, so the stored readings, which reach back up to a
week, are read off by the difference until they have been replaced.

> Main page: [Usage](usage.md)<br/>
> Previous: [Automations](usage-automations.md)<br/>