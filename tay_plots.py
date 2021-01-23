import matplotlib.pyplot as plt
import numpy as np
import matplotlib.ticker as mticker


plt.style.use('seaborn-whitegrid')

fig = plt.figure()
ax = plt.axes()

plt.xlabel("Depth correction")
plt.ylabel("Milliseconds per step")

data_filename = 'plot_111'
plot_see_radii = [0, 1, 2]
plot_structures = [
    # 'CpuSimple',
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
    # elif radius == 2:
    #     style = '-.'
    else:
        style = ':'
    return color, style, '%s R:%g' % (label, pow(2, radius) * 50.0)


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
            n = float(tokens[1])
            y_vals = [n for _ in x_vals]
        else:
            y_vals = [float(n) for n in tokens[1:]]
        c, f, l = _format_and_label(label, radius)
        plt.plot(x_vals, y_vals, f, color=c, label=l)


plt.ylim([0, 100])
plt.gca().xaxis.set_major_locator(mticker.MultipleLocator(1))
plt.legend(bbox_to_anchor=(1, 1), loc="upper left");
plt.tight_layout()
plt.show()


fig.savefig('%s.png' % data_filename)
