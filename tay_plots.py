import matplotlib.ticker as mticker
import matplotlib.pyplot as plt
import numpy as np

plt.style.use('seaborn-whitegrid')


value_index = 0
# value_label = "Milliseconds per step"
# value_label = "Narrow/broad phase ratio (%)"
value_label = "Mean relative deviation (%)"
data_filename = 'plot_uniform_telemetry'
plot_see_radii = [
    0,
    1,
    2,
]
plot_structures = [
    'CpuSimple',
    'CpuTree',
    'CpuGrid',
    # 'GpuSimple (direct)',
    # 'GpuSimple (indirect)',
]

def _format_and_label(label, radius):
    if label == 'CpuSimple':
        color = '#444444'
    elif label == 'CpuTree':
        color = '#00aa00'
    elif label == 'CpuGrid':
        color = '#55ff22'
    elif label == 'GpuSimple (direct)':
        color = '#ff9933'
    else:
        color = '#ee0000'
    if radius == 0:
        style = '-'
    elif radius == 1:
        style = '--'
    else:
        style = ':'
    # style = '-'
    return color, style, '%s R:%g' % (label, pow(2, radius) * 50.0)

fig = plt.figure(figsize=(8, 3.5))
ax = plt.axes()

plt.xlabel("Depth correction")
plt.ylabel(value_label)

def _number_from_token(token, index):
    bits = token.split('|')
    if index >= len(bits):
        return float(bits[0])
    else:
        return float(bits[index])

with open('../tay/benchmark/%s' % data_filename, 'r') as file:
    text = file.read()
    lines = text.splitlines()

    depth_corrections = lines[0].split(' ')
    min_depth_correction = int(depth_corrections[0])
    max_depth_correction = int(depth_corrections[1])

    x_vals = range(min_depth_correction, max_depth_correction)

    for line in lines[1:]:
        if line.startswith('--'):
            continue
        label, rest = line.split('::')
        if label not in plot_structures:
            continue
        tokens = rest.split(' ')
        radius = int(tokens[0])
        if radius not in plot_see_radii:
            continue
        if len(tokens) == 2:
            n = _number_from_token(tokens[1], value_index)
            y_vals = [n for _ in x_vals]
        else:
            y_vals = [_number_from_token(n, value_index) for n in tokens[1:]]
        c, f, l = _format_and_label(label, radius)
        plt.plot(x_vals, y_vals, f, color=c, label=l)

# plt.ylim([0, 100])

plt.gca().xaxis.set_major_locator(mticker.MultipleLocator(1))
plt.legend(bbox_to_anchor=(1, 1), loc="upper left");
plt.tight_layout()
plt.show()

fig.savefig('%s.png' % data_filename)
