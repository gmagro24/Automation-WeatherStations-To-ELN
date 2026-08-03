# licor/test_licor_pipeline.py

from pathlib import Path

from licor_to_labguru import (
    LICOR_DATA_FOLDER,
    get_new_licor_files,
    load_licor_file,
    discover_columns,
    build_dataset_name,
    build_row,
    discover_locations
)

print("=" * 80)
print("LICOR CONFIGURATION")
print("=" * 80)

print("Data Folder:")
print(LICOR_DATA_FOLDER)

print("\nExists:")
print(LICOR_DATA_FOLDER.exists())

print("\n")

print("=" * 80)
print("FILE DISCOVERY")
print("=" * 80)

files = get_new_licor_files()

print(f"Found {len(files)} file(s)")

for file in files:
    print(file)

if not files:
    raise SystemExit(
        "No LI-COR files found."
    )

print("\n")

print("=" * 80)
print("LOAD FILE")
print("=" * 80)

test_file = files[0]

print("Using:")
print(test_file)

df = load_licor_file(test_file)

print("\nRows:")
print(len(df))

print("\nColumns:")
print(len(df.columns))

print("\n")

print("=" * 80)
print("COLUMN DISCOVERY")
print("=" * 80)

columns = discover_columns(df)

for column in columns:
    print(column)

print("\n")

print("=" * 80)
print("DATASET NAME")
print("=" * 80)

df = load_licor_file(test_file)

locations = discover_locations(df)

for location in locations:

    dataset_name = build_dataset_name(
        location
    )

    print(dataset_name)

print("Location:")
print(location)

dataset_name = build_dataset_name(location)

print("Dataset:")
print(dataset_name)

print("\n")

print("=" * 80)
print("FIRST ROW")
print("=" * 80)

sample_row = build_row(
    df.iloc[0]
)

for key, value in sample_row.items():
    print(
        f"{key}: {value}"
    )

print("\n")

print("=" * 80)
print("SUCCESS")
print("=" * 80)

print(
    "LI-COR parsing test completed successfully."
)

df = load_licor_file(test_file)

columns = discover_columns(df)

print("\nColumns that would be created:\n")

for c in columns:
    print(c)