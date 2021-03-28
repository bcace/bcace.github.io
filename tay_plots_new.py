import matplotlib.ticker as mticker
import matplotlib.pyplot as plt
import numpy as np
import importlib.util

plt.style.use('seaborn-whitegrid')


def _plot(in_filename, out_filename, y_var, see_radii, in_structs, ylim=None):
    spec = importlib.util.spec_from_file_location("tay_data", in_filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    in_data = mod.data

    fig = plt.figure(figsize=(7, 3.2))
    ax = plt.axes()

    plt.xlabel("min partition size")
    plt.ylabel(y_var)

    plots_repo = {}
    for radius in see_radii:
        structs = in_data[radius]
        for struct, runs in structs.items():
            if struct not in in_structs:
                continue
            plot_key = (radius, struct)
            if plot_key not in plots_repo:
                plots_repo[plot_key] = ([], [])
            plot_data = plots_repo[plot_key]
            for run in runs:
                plot_data[0].append(run["part_radii"][0])
                plot_data[1].append(run[y_var])

    for plot_key, plot_data in plots_repo.items():
        if len(plot_data[0]) == 1:
            plt.plot(plot_data[0], plot_data[1], '^', label="%s R:%s" % (plot_key[1], plot_key[0]))
        else:
            plt.plot(plot_data[0], plot_data[1], label="%s R:%s" % (plot_key[1], plot_key[0]))

    if ylim is not None:
        plt.ylim([0, ylim])

    plt.gca().xaxis.set_major_locator(mticker.MultipleLocator(10))
    plt.legend(bbox_to_anchor=(1, 1), loc="upper left");
    plt.tight_layout()
    plt.show()
    # fig.savefig('%s.png' % out_filename)


# _plot("C:/Users/branimir/dev/tay/benchmark/test_nonpoint_runtimes.py", "nonpoint_plot_1",
#       "ms per step", [50], ['CpuSimple', 'CpuTree', 'CpuAabbTree'])
_plot("C:/Users/branimir/dev/tay/benchmark/test_nonpoint_runtimes.py", "nonpoint_plot_2",
      "ms per step", [50, 100, 200], ['CpuAabbTree'])
