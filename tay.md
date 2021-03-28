# Tay: comparison of space partitioning structures in agent-based simulations

A number of years ago I was working on [Ochre](https://github.com/bcace/ochre), an agent-based modeling and simulation tool. At the time I focused mostly on creating an immediate connection between modifying the model and seeing the response in the running simulation, and I also wanted to create a language in which non-programmers could safely write parallel agent interaction code without fear of data races or race conditions. While the simulation speed was acceptable for smaller models of a few hundred to a few thousand agents, at a larger scale it would become slow enough to break the immediacy of the modeling-simulation cycle.

Recently I decided to approach the problem from the other side and try to make simulations run efficiently first, before attempting to improve the modeling experience. Because agent-based models are so varied, there's no single best mechanism that will run all possible simulations equally well, so to be able test and compare various data structures in different scenarios and model configurations, I started the [Tay](https://github.com/bcace/tay) project. This post is the first one in a series where I will be writing about major new features and showing benchmark results.

## Space partitioning

Other than *accidental* causes of simulation slowdown (like running the simulation on an interpreter, which I did with Ochre, and won't do again), the main *essential* part of the slowdown is the number of agent interactions that have to be executed. Since agent interactions are local in most agent-based models (N<sub>interactions</sub> << N<sub>agents</sub><sup>2</sup>)) there's a lot that can be done to improve simulation speed by finding agent neighbors efficiently.

Finding agent neighbors is done by dividing the space into smaller partitions, and then efficiently finding neighboring partitions. Normally when agents have to interact we choose a partition and look for its neighboring partitions. We then claim that agents contained in the neighboring partitions are *all* neighbors of *all* agents in the first partition.

This is obviously just a rough estimation (broad phase) that has a lot of false positives, and requires that we additionally test the distance between agents explicitly (narrow phase).

> Example for space partitioning: if there's a 1000 agents in a model and they all have to interact, that's 999000 interactions at each step. If interactions between agents are supposed to be local, and let's say that for a given interaction range agents on average come close enough to 10 other agents at each step, that's 10000 actual interactions. But in order to test whether agents should interact at all we still had to go through all 999000 pairs, which means we just wasted time on 989000 tests.

Regarding partition sizes, if we partition the space too little we get too many agents to reject during the narrow phase, and if we partition too much we get more partitions to build, traverse and test for closeness; and this optimum point is clearly seen in the test results when we vary partition sizes.

## Evaluating space partitioning structures

One way to evaluate a space partitioning structure would be to simply compare it to others on the same model, but that doesn't guarantee that the structure is implemented optimally. To isolate the performance of a structure we can look at the following numbers:

* Number of agent pairs that pass the broad phase and get rejected in the narrow phase
* Time required to update and use the structure to find neighbors
* How well the workload is distributed among threads

## First results

To compare structures I run a series of simulations where I apply each structure to a test model and its variants, and then tweak the structure to see if there's a setting where it performs better than others for the given model.

Since focus is on optimizing spatial agent interactions the model I used is a very abstracted version of flocking. To make agent spatial distribution consistent during simulation runs (and therefore number of interactions), agent movement is predefined (it doesn't depend on agent interactions).

To verify that the simulation is running correctly there is a separate agent variable which accumulates results of interactions with other agents. This value is compared with the same value from a previous simulation run where the model was the same, but a different structure was used. Some small differences are always present because of floating point errors, but this is a kind of interaction result that quickly and drastically diverges if there are any race conditions or errors in neighbor-finding.

Variables in these experiments can be grouped into model variables and system variables. Model variables are the number of agents in the model, agent distribution in space (density and "clumpiness"), interaction radii, and how demanding the interaction code is. System variables are the number of threads the simulation is running on, the space partitioning structure used (including whether it's a CPU or a GPU structure), `depth_correction` (where applicable), and any structure-specific settings like `GpuSimple` structure's `direct` setting or hash table size dictated by the available memory for the `CpuGrid` structure.

So far I only had the chance to run simulations on my ThinkPad T480 with the i5-8250U processor (4 physical and 8 logical processors, base frequency 1.6 Ghz, max. frequency 3.4 GHz (Turbo Boost)) and UHD Graphics 620 (I used Intel's OpenCL SDK for GPU simulations). GPU results are just there to verify that the system works correctly, with consistent simulation results, even when switching between CPU and GPU strucures during simulation runs.

Most results are for uniform distribution of agents moving in random directions inside a fixed cube. Currently the only other distribution is one-clump: 80% of agents uniformly distributed and 20% clumped inside a cube whose side is 5% of the entire space cube's side length.

> Note that the following run-times are not the fastest I can get on my machine. I disabled Turbo Boost to get more consistent results, but with it enabled (which is the default) I get 1.5 - 2 times better run-times.

**Agents**|10000
**Steps**|1000
**Space size**|1000 * 1000 * 1000
**Threads (CPU)**|8

Simulation workload is best measured in number of interactions each agent has during a simulation step, and for the same number of agents, distribution and space size it depends only on the interaction radii. Obviously these numbers are exactly the same regardless of the structure used:

**50**|9.2973
**100**|68.6986
**200**|466.351

#### Simulation run-times

First, to show the benefits of using partitioning structures, here's a comparison of simulation run-times of the brute-force approach (`CpuSimple`) and partitioning structures (`CpuGrid`) for the case when interaction radius is 50:

![plot1](/plot1.png)

and even in the case where interaction radius is much larger at 200 (so the number of interactions is larger) the advantages can still be seen:

![plot2](/plot2.png)

Next, if we look at just one of the space partitioning structures (`CpuTree`) for all three interaction radii (50, 100, 200), we can see the effect of `depth_correction` parameter that balances the overheads of updating and using the structure vs. broad phase being too broad (having to reject too many agent pairs at the narrow phase). For each interaction radius there's an optimal `depth_correction`, but it's a different value for each case:

![plot3](/plot3.png)

Comparing `CpuTree` and `CpuGrid` we can see that grids perform better for all three interaction radii:

![plot4](/plot4.png)

Simulations with uniform distribution (green) perform better than one-clump distribution (blue) because agents in the "clump" are all so close together that they must always interact:

![plot9](/plot9.png)

Finally, when comparing GPU brute-force approach (`GpuSimple`) and a CPU space partitioning structure (`CpuGrid`) we can see that for smaller interaction radii CPU version is still faster:

![plot5](/plot5.png)

Of course, this last comparison is a bit unfair since my GPU is relatively low-performance, and I'm comparing brute-force and space partitioning structures, but as I mentioned before the GPU version is there only to verify that I can integrate GPU simulation execution into the system seamlessly, and obviously there's still work to be done on that front.

Also an interesting thing to see on GPU is what the effect is when iterating through agents using linked lists (indirect) and just assuming they are consecutive in an array (direct):

![plot6](/plot6.png)

#### Simulation efficiency

As mentioned at the beginning, efficiency of a simulation can be measured with three numbers. First number tells us how good our space partitioning is regarding the number of agent pairs that are rejected at the narrow phase test. The following plot shows the ratio between number of agent pairs that should *actually* interact and number of agent pairs that the structure claims *could* interact (higher is better):

![plot7](/plot7.png)

Third number, or thread unbalancing, tells us how well the interaction work is distributed among threads, and is presented in the plot below as a mean relative deviation of the number of interactions executed on each thread vs. what would be the ideal distribution (equal number of interactions on each thread), averaged over all simulation steps (lower is better):

![plot8](/plot8.png)

For the uniform distribution (green) thread unbalancing is small and dropping off because many small cells with few agents each are easier to distribute evenly among threads than few large cells with many agents each. For the one-clump distribution (blue) the same effect is visible at larger depth corrections, but at smaller depth corrections and large interaction radii all partitions have the clump of agents as their neighbor. This means the amount of work will be the same for all of them, which makes the balancing easy:

![plot10](/plot10.png)
