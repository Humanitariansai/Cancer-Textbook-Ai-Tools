import csv

input_file = "data/paragraph_image_map_14__20251027_234226.csv"

with open(input_file, "r") as f:
    reader = csv.DictReader(f)
    
    # Get column names
    print("Available columns in your CSV:")
    print("-" * 50)
    for i, col in enumerate(reader.fieldnames, 1):
        print(f"{i}. '{col}'")
    
    print("\n" + "=" * 50)
    print("First 3 rows of data:")
    print("=" * 50)
    
    # Reset to read data
    f.seek(0)
    reader = csv.DictReader(f)
    
    for i, row in enumerate(reader):
        if i >= 3:
            break
        print(f"\nRow {i+1}:")
        for key, value in row.items():
            # Truncate long values
            display_value = value[:100] + "..." if len(value) > 100 else value
            print(f"  {key}: {display_value}")