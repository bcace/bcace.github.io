import importlib.util
import matplotlib.pyplot as plt

plt.style.use('seaborn-whitegrid')


def _format_and_label(label, radius, all_lines):
    if label == 'CpuSimple':
        color = '#444444'
    elif label == 'CpuKdTree':
        color = '#008800'
    elif label == 'CpuKdTree (old)':
        color = '#44dd44'
    elif label == 'CpuAabbTree':
        color = '#0022ff'
    elif label == 'CpuAabbTree (old)':
        color = '#44aaff'
    elif label == 'CpuGrid':
        color = '#0022ff'
    elif label == 'CpuGrid (old)':
        color = '#44aaff'
    elif label == 'GpuSimple (direct)':
        color = '#ff9933'
    else:
        color = '#ee0000'
    if label == 'CpuSimple':
        style = '^'
    elif all_lines:
        style = '-'
    elif radius == 50:
        style = '-'
    elif radius == 100:
        style = '--'
    else:
        style = ':'
    return color, style, '%s R:%g' % (label, radius)


def _plot(in_filename, out_filename, y_var, see_radii, in_structs, ylim=None):
    spec = importlib.util.spec_from_file_location("tay_data", in_filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    in_data = mod.data

    fig = plt.figure(figsize=(6, 2.5))
    ax = plt.axes()

    plt.xlabel("min partition size")
    plt.ylabel(y_var)

    plot_data_dict = {}
    for radius in see_radii:
        structs = in_data[radius]
        for struct, runs in structs.items():
            if struct not in in_structs:
                continue
            plot_key = (radius, struct)
            if plot_key not in plot_data_dict:
                plot_data_dict[plot_key] = ([], [])
            plot_data = plot_data_dict[plot_key]
            for run in runs:
                plot_data[0].append(run["part_radii"][0])
                plot_data[1].append(run[y_var])

    for plot_key, plot_data in plot_data_dict.items():
        color, style, label = _format_and_label(plot_key[1], plot_key[0], len(see_radii) == 1)
        plt.plot(plot_data[0], plot_data[1], style, color=color, label=label)

    if ylim is not None:
        plt.ylim([0, ylim])

    plt.legend(bbox_to_anchor=(1, 1), loc="upper left");
    plt.tight_layout()
    plt.show()
    fig.savefig('%s.png' % out_filename)


# _plot("C:/Users/branimir/dev/tay/benchmark/test_nonpoint_telemetry.py", "nonpoint_plot_1",
#       "ms per step", [50], ['CpuSimple', 'CpuTree', 'CpuAabbTree'])

# _plot("C:/Users/branimir/dev/tay/benchmark/test_nonpoint_telemetry.py", "nonpoint_plot_2",
#       "ms per step", [50], ['CpuTree', 'CpuAabbTree'])

# _plot("C:/Users/branimir/dev/tay/benchmark/test_nonpoint_telemetry.py", "nonpoint_plot_3",
#       "ms per step", [100], ['CpuTree', 'CpuAabbTree'])

# _plot("C:/Users/branimir/dev/tay/benchmark/test_nonpoint_telemetry.py", "nonpoint_plot_4",
#       "neighbor-finding efficiency (%)", [50], ['CpuTree', 'CpuAabbTree'])


_plot("C:/Users/User/dev/tay/benchmark/test_basic_runtimes_cached.py", "cached_plot_1",
      "ms per step", [50], ['CpuKdTree (old)', 'CpuKdTree'])

_plot("C:/Users/User/dev/tay/benchmark/test_basic_runtimes_cached.py", "cached_plot_2",
      "ms per step", [50], ['CpuGrid (old)', 'CpuGrid'])

_plot("C:/Users/User/dev/tay/benchmark/test_nonpoint_runtimes_cached.py", "cached_nonpoint_plot_1",
      "ms per step", [50], ['CpuKdTree (old)', 'CpuKdTree'])

_plot("C:/Users/User/dev/tay/benchmark/test_nonpoint_runtimes_cached.py", "cached_nonpoint_plot_2",
      "ms per step", [50], ['CpuAabbTree (old)', 'CpuAabbTree'])
