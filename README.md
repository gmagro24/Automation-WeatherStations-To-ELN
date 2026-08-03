# WeatherStations Automated Updating

Automated environmental data ingestion platform for importing WeatherLink and LI-COR environmental monitoring data into Labguru datasets.

---

# Overview

This project provides automated integrations between:

- Davis WeatherLink API
- LI-COR Environmental Monitoring Exports
- Labguru Datasets

The goal is to create a centralized repository of environmental data within Labguru that can be linked to experiments, trials, and research records.

---

# Project Structure

```text
WeatherStations_Automated_Updating/

│
├── client/
│   ├── __init__.py
│   ├── labguru_client.py
│   └── labguru_config.py
│
├── weatherLink/
│   ├── weatherlink_to_labguru.py
│   └── test_weatherlink.py
│
├── licor/
│   ├── licor_to_labguru.py
│   ├── test_licor_pipeline.py
│   └── sample_data/
│
├── config.py
├── requirements.txt
├── README.md
├── .env.example
└── .gitignore
```
# Architecture
 
## WeatherLink
 
WeatherLink datasets are generated directly from the WeatherLink API.
 
```text
WeatherLink API
↓
Station Discovery
↓
Sensor Discovery
↓
Dataset Creation
↓
Labguru
```
### Sync Schedule
Every 15 minutes 
---
## LI-COR
LI-COR datasets are generated directly from the LI-COR Cloud API.
```text
LI-COR Cloud API
↓
Device Discovery
↓
Measurement Discovery
↓
Dataset Creation
↓
Labguru
```
Current discovered devices:
```text
Campus Bioassay Lab
Farm Basement GH
Aedes control 2479
culex control 2479
Hobo Water 3
```
### Sync Schedule
Every week

---

# Environment Variables

Create a `.env` file.

Example:

```env
WEATHERLINK_API_KEY=
WEATHERLINK_API_SECRET=

LABGURU_BASE_URL=
LABGURU_TOKEN=
LABGURU_AUTH_MODE=bearer

LABGURU_WEATHERLINK_PARENT_FOLDER_ID=
LABGURU_LICOR_PARENT_FOLDER_ID=

LICOR_DATA_FOLDER=licor/sample_data

DRY_RUN=true
AUTO_ADD_COLUMNS=true
```

---

# Installation

Create virtual environment:

```powershell
python -m venv .venv
```

Activate:

```powershell
.venv\Scripts\activate
```

Install packages:

```powershell
pip install -r requirements.txt
```

---

# Requirements

```text
requests>=2.32.0
python-dotenv>=1.0.1
pymongo>=4.10.0
pydantic>=2.11.0
pandas>=2.2.0
openpyxl>=3.1.0

```

Install:

```powershell
pip install -r requirements.txt
```

---

# Testing

## LI-COR Parser Test

```powershell
python licor\test_licor_pipeline.py
```

Expected:

```text
Rows: XXX
Columns: XXX
SUCCESS
```

---

## WeatherLink Discovery

```powershell
python weatherLink\weatherlink_to_labguru.py
```

with:

```env
DRY_RUN=true
```

Expected:

```text
Discovered stations
Discovered sensors
Dataset creation preview
```

without modifying Labguru.

---

# Labguru Workflow

Recommended Labguru Structure:

```text
Weather Data
│
├── WeatherLink
│   ├── Farm 2 - Vantage Pro2 Plus
│   ├── Winter Haven FL - Barometer
│   └── ...
│
└── LI-COR
    ├── Campus Bioassay Lab - LI6800
    ├── Farm Basement GH - LI6800
    └── ...
```

---

# Development Workflow

1. Develop and test locally
2. Run parser validation tests
3. Run WeatherLink discovery tests
4. Validate Labguru API connection
5. Test dataset creation
6. Enable automated syncing

---

# GitHub Deployment

Environment variables should be stored in:

```text
GitHub Secrets
```

Never commit:

```text
.env
```

to source control.

Only commit:

```text
.env.example
```

---

# Safety Notes

The following files should never be committed:

```text
.env
credentials.json
tokens.txt
```

Always verify:

```powershell
git status
```

before pushing changes.

---
Markdown
# Current Status

## WeatherLink

Completed:
- API authentication
- Station discovery
- Sensor discovery
- Dynamic schema creation
- Automatic dataset generation
- GitHub workflow integration

Status:
```text
Awaiting Labguru credential validation
```
---
## LI-COR
Completed:
- API authentication
- Device discovery
- Sensor discovery
- Dynamic schema creation
- Automatic dataset generation
- GitHub workflow integration

Status:

```text
Awaiting Labguru credential validation
```

Historical data endpoint validation remains under investigation.
Current implementation automatically uploads latest sensor values for all discovered devices.

# Author

Clarke Synergy / Environmental Data Integration Project