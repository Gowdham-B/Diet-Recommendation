import json

with open('Review_1.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i, cell in enumerate(nb['cells']):
    print(f"=== Cell {i} ({cell['cell_type']}) ===")
    print("".join(cell['source']))
    print()
