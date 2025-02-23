"""Script to create Q-Value JSON file, initializing with zeros"""

import json
from pathlib import Path


# 定义 X, Y, 以及速度的范围
x_values = list(range(-40, 140, 10)) + list(range(140, 421, 70))
y_values = list(range(-300, 180, 10)) + list(range(180, 421, 60))
v_values = range(-10, 11)

# 生成 q 值字典，键格式为 "x_y_v"，初始值为 [0, 0]
qval = {f"{x}_{y}_{v}": [0, 0] for x in x_values for y in y_values for v in v_values}

data_dir = Path(__file__).resolve().parent.parent / "data"
data_dir.mkdir(parents=True, exist_ok=True)  # 确保 data 目录存在

with open(data_dir / "qvalues.json", "w") as fd:
    json.dump(qval, fd)
