import matplotlib.ticker as mticker
import matplotlib.pyplot as plt
import numpy as np

plt.style.use('seaborn-whitegrid')


def _format_and_label(label, radius, all_lines):
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
    if all_lines:
        style = '-'
    else:
        if radius == 0:
            style = '-'
        elif radius == 1:
            style = '--'
        else:
            style = ':'
    return color, style, '%s R:%g' % (label, pow(2, radius) * 50.0)


def _number_from_token(token, index):
    bits = token.split('|')
    if index >= len(bits):
        return float(bits[0])
    else:
        return float(bits[index])


def _create_plots_from_file(in_filename, out_filename, value_index, value_label, plot_see_radii, plot_structures, all_lines):
    with open('../tay/benchmark/%s' % in_filename, 'r') as file:
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
            c, f, l = _format_and_label(label, radius, all_lines)
            plt.plot(x_vals, y_vals, f, color=c, label=l)


def _create_figure(out_filename, in_filenames, value_index, value_label, plot_see_radii, plot_structures, ylim, all_lines):
    fig = plt.figure(figsize=(7, 3.2))
    ax = plt.axes()

    plt.xlabel("Depth correction")
    plt.ylabel(value_label)

    for in_filename in in_filenames:
        _create_plots_from_file(in_filename,
                                out_filename=out_filename,
                                value_index=value_index,
                                value_label=value_label,
                                plot_see_radii=plot_see_radii,
                                plot_structures=plot_structures,
                                all_lines=all_lines)

    if ylim is not None:
        plt.ylim([0, ylim])

    plt.gca().xaxis.set_major_locator(mticker.MultipleLocator(1))
    plt.legend(bbox_to_anchor=(1, 1), loc="upper left");
    plt.tight_layout()
    # plt.show()
    fig.savefig('%s.png' % out_filename)


_create_figure('plot1', ['plot_uniform_runtimes'], 0, 'Milliseconds per step', [0], ['CpuSimple', 'CpuGrid'], None, False)
_create_figure('plot2', ['plot_uniform_runtimes'], 0, 'Milliseconds per step', [2], ['CpuSimple', 'CpuGrid'], None, True)
_create_figure('plot3', ['plot_uniform_runtimes'], 0, 'Milliseconds per step', [0, 1, 2], ['CpuTree'], 300, False)
_create_figure('plot4', ['plot_uniform_runtimes'], 0, 'Milliseconds per step', [0, 1, 2], ['CpuTree', 'CpuGrid'], 100, False)
_create_figure('plot5', ['plot_uniform_runtimes'], 0, 'Milliseconds per step', [0, 1, 2], ['CpuTree', 'CpuGrid', 'GpuSimple (direct)'], 100, False)
_create_figure('plot6', ['plot_uniform_runtimes'], 0, 'Milliseconds per step', [0, 1, 2], ['GpuSimple (direct)', 'GpuSimple (indirect)'], None, False)
_create_figure('plot7', ['plot_uniform_telemetry'], 3, 'Narrow / broad phase ratio (%)', [0, 1, 2], ['CpuSimple', 'CpuTree', 'CpuGrid'], None, False)
_create_figure('plot8', ['plot_uniform_telemetry'], 0, 'Mean relative deviation (%)', [0, 1, 2], ['CpuSimple', 'CpuTree', 'CpuGrid'], None, False)
