
## Comparison of space partitioning structures in agent-based simulations

A number of years ago I was working on [Ochre](https://github.com/bcace/ochre) - agent-based modeling and simulation tool. At the time I focused mostly on achieving immediate connection between modifying the model and running the simulation. Additionally, I wanted to create a language in which non-programmers could safely write parallel agent interaction code without fear of data races or race conditions. While simulation performance was solid, at a certain scale it would slow down enough to break the immediacy of model development, and it was obvious that there isn't a single most efficient simulation mechanism for all the different models that users might want to develop.

A common cause of slowdowns in agent-based simulations is the number of interactions that can occur between agents. If the decision whether agents should interact is made based on their proximity ([flocking](https://en.wikipedia.org/wiki/Flocking_(behavior)) is a good example) then there is potential for optimization by using [space partitioning structures](https://en.wikipedia.org/wiki/Space_partitioning). These structures provide rough information on which agents are so far apart that they have no chance of interacting (**broad phase**), and which agents *might* interact. Each of the remaining pairs of agents that might interact we have to test for distance explicitly (**narrow phase**).

> Example for space partitioning: if there's a 1000 agents in a model and they all have to interact, that's 999000 interactions at each step. If we now want to limit agents to only interact if they're close enough to each other, and let's say that for a given interaction range agents on average come close enough to 10 other agents at each step, that's 10000 actual interactions. But in order to test whether agents should interact at all we still had to go through all 999000 pairs, which means we just wasted time on 989000 tests.

To evaluate a simulation system setup and compare space partitioning structures it's not enough to just look at resulting simulation run-times, since they include various influences such as the hardware we're running simulations on, or how performant the agent behavior code is. To isolate the performance of the system itself we can look at the following numbers:

* number of agent pairs that pass the broad phase and get rejected in the narrow phase,
* time required to update and use the structure to find neighbors,
* how well the workload is distributed among threads.

## Tay library

I wrote [Tay](https://github.com/bcace/tay) as a collection of space partitioning structures to explore how they perform in different conditions. The goal is to have multiple different test models and run simulations with different structures, on different numbers of threads and both on CPU and GPU, and compare run-times. Since agent properties, behavior and distribution in space can change during a single simulation run so much that it completely changes which structure is optimal, Tay allows switching between structures during a simulation run (even switching between CPU and GPU), changing the number of threads (on CPU) and adjusting any parameters each structure might have. Since conclusions derived from these experiments should be applicable to a wide variety of agent-based models, the following requirements should be met:

**Space dimensions:** Currently space can have 1, 2, 3 or 4 dimensions, and those dimensions can be of any type, not just spatial. The fact that dimensions don't have to be of the same type means that space partitioning structures treat each dimension separately. For example, when defining an interaction between agents we cannot just define one range value to which the interaction is limited, we have to specify a separate value for each dimension.

**Agent size:** Agents can have size in any dimension (don't have to be points). This can complicate space partitioning structures somewhat. If it's a tree structure there's a possibility to add agents to non-leaf nodes. If it's a grid structure then the same agent can be added to multiple partitions in which case we have to prevent multiple interactions between same agents, or we can build a "fake" tree from multiple grids of varying partition sizes.

**Space bounds:** Space doesn't have fixed bounds, agents are free to move anywhere, and it's up to the space partitioning structure to update itself correctly.

**Agent types:** Multiple agent types can be defined. This allows having agents with drastically different behaviors in a single model.

**Behaviors and interactions:** To avoid data races and race conditions agent behavior code is split into an arbitrary number of *passes*. There are currently only two types of passes: **act** and **see**.

**act** pass describes what each agent does with its own data, there is no communication with other agents. This pass is defined for a specific agent type and specifies a procedure that is applied to all "live" agents of that type.

**see** pass describes how two agents interact, the **seer** agent and the **seen** agent. This strict role assignment for these two agents is what enables lock-free parallelism: knowing that the **seer** agent can change its state and the **seen** agent is read-only enables scheduling **see** code execution so that a **seer** agent is never in more than one thread during this pass. **see** pass is defined for two agent groups: **seer** agent type and **seen** agent type, and specifies a procedure that is applied to all agent pairs the space partitioning structure decides should interact.

**Communication methods:** Communication methods can be combined: communicating with neighbors within specified range(s), through direct references, connection objects or a [grid](https://en.wikipedia.org/wiki/Particle_Mesh). Currently agents only interact with neighbors, but I took special care to not preclude any of the other mechanisms from being added.

**Adding/removing agents:** Agents can be removed from or added to a running simulation. This requires certain provisions in the space partitioning structures, depending on the model itself and the chosen method for efficiently iterating through agents. The options are roughly:

1. **Connecting agents into linked lists** requires embedding `next` pointers into agents themselves, and the same pointers can be used to group agents into partitions.
2. **Marking "dead" agents** and skipping them, with an occasional "defragmentation" step. The "defragmentation" step where agents would be moved in memory would require that all references to agents from connection objects or other agents are updated as well. This makes this option either more complicated (and potentially lose any performance gains over option 1.) or limited only to use in models where there are no agent references.

## Space partitioning structures

Generally if we partition the space too little we get too many agents to reject during the narrow phase (distance test), and if we partition too much we get more partitions to build, traverse and test for closeness; and this optimum can be clearly seen in the test results, when we vary the partition depth.

For this reason there are two parameters that can be adjusted for all partitioning structures. First is a set of sizes, one for each dimension, that represent the suggested smallest partition size for each dimension. They are only "suggested" because we can have multiple interactions (**see** passes) in a model, each with its own interaction radii, and the smallest partition sizes should be related to those interaction radii. The other is a parameter called `depth_correction` that can then be varied to adjust the smallest partition sizes: `size = suggested_size / 2^depth_correction`.

> Note that because we can have multiple interactions with drastically different interaction radii, we cannot just consider a partition's immediate neighboring partitions to find all agents that are within interaction range. Generally, as mentioned above, interaction radii are used just as an initial, approximate value for a good partition size.

Currently all partitioning structures are completely rebuilt at the start of each step since profiling shows that it takes very little time compared to actual agent interactions.

> GPU structures have an additional difficulty of having to copy data between CPU and GPU and fix any pointers used on both sides (calculating relative addresses and then adding them to the appropriate new base addresses). These data transfers are reduced to essential data needed to continue the simulation run, which is reflected in different scenarios when switching between different structures. For example, when switching from a CPU structure to a GPU structure we have to push the entire simulation state to GPU, but when switching from `GpuSimple` to `GpuTree` only the tree structure data has to be copied and pointer addresses have to be fixed.

### Simple

`CpuSimple` is a "non-structure" structure used either when *all* agents have to interact, or when we need a reference simulation run to measure the effectiveness of other, more elaborate structures. It distributes agents evenly between threads and performs only the narrow phase when deciding which agents should interact.

`GpuSimple` structure works similarly on GPU, only copying data to and from GPU when absolutely necessary. Because of large difference in speed it has the `direct` option that switches iteration through **seen** agents on each thread from using linked list pointers to assuming that all agents are consecutive in a single array. This option can be used when number of agents in a simulation doesn't change.

### Tree

`CpuTree` structure is a k-d tree. Can store agents that have size (are not points) in non-leaf nodes.

**Update:** At the start of each simulation step tree is cleared so that it only contains the root partition, and the root partition's bounding box is updated to enclose all agents. When adding an agent to the tree the the appropriate branch is traversed as far as possible and when further partitioning is needed partitions are split in half along a dimension with largest ratio between partition size in that dimension and smallest partition size in the same dimension.

**Act:** All tree partitions are evenly distributed among threads for processing.

**See:** All tree partitions are evenly distributed among threads as **seer** partitions, or partitions containing **seer** agents. To get **seen** agents for each of those **seer** partitions, the tree is traversed and each of those partitions' bounding boxes is tested for overlap with the **seer** partition's bounding box inflated by the **see** pass radii. Since no two threads ever have the same **seer** partition there is no danger of writing to the same memory location from multiple threads. All threads process the same partitions for **seen** agents, but **seen** agents are read-only.

### Grid

`CpuGrid` structure is a hash grid. Hash function used to map grid cell indices to bin indices is a simple XOR hash function.

**Update:** Space bounding box and suggested partition sizes are used to convert each agent's position into grid cell indices, which are then hashed to find the appropriate bin for each agent. All non-empty bins are linked into a list for faster access.

**Act:** Each thread iterates through its assigned bins so that each bin's agents get processed by one of the threads.

**See:** Each thread iterates through its set of **seer** bins and finds neighboring **seen** bins through its **seer** agents' positions. Because of hash collisions a single bin can contain agents from multiple grid cells, so in principle we have to find neighboring bins for each **seer** bin agent, but since most bins contain agents of only one cell the algorithm caches found neighboring bins.

To find neighboring **seen** bins, **seer** agent's cell indices are calculated from its position, then cell sizes and **see** radii are used to build the "kernel" of cells neighboring the **seer** cell, and finally indices of each kernel cell are hashed to find the corresponding bins.

Hash collisions also have to be taken into account when looking at kernel **seen** bins. One problem is that kernel **seen** bins can also contain agents from multiple cells, and some of those cells obviously might be outside the kernel. Simplest solution is to ignore the problem and just let those agents get rejected during the narrow phase (then it becomes a problem of reducing the number of collisions, which we have to do anyway). The other problem is that a hash collision could cause the same bin to appear multiple times in the same kernel. The fix for that is to mark bins as already visited and skip them on subsequent encounters.

## Results

So finally we come to the point of the project - comparison of space partitioning structures. Here I run a series of simulations where I apply each structure to a test model (and its variants), and then tweak the structure to see if there's a setting where it performs better than others for the given model.

Since focus is on optimizing spatial agent interactions the model I used is a very abstracted version of flocking. To make agent spatial distribution consistent during simulation runs (and therefore number of interactions), agent movement is predefined (it doesn't depend on agent interactions). To verify that the simulation is running correctly there is a separate `f_buffer` variable that gets updated at each step by the agent's interactions with other agents. I compare values of `f_buffer` variables between simulation runs to make sure that all simulations of the same model run exactly the same, regardless of any differences between how those simulation were run, on which hardware they were run, and which structures were used.

Variables in these experiments can be grouped into model variables and system variables. Model variables are the number of agents in the model, agent distribution in space (density and "clumpiness"), interaction radii, and how demanding the interaction code is. System variables are the number of threads the simulation is running on, the space partitioning structure used (including whether it's a CPU or a GPU structure), `depth_correction` (where applicable), and any structure-specific settings like `GpuSimple` structure's `direct` setting or hash table size dictated by the available memory for the `CpuGrid` structure.

So far I only had the chance to run simulations on my ThinkPad T480 with the i5-8250U processor (4 physical and 8 logical processors, base frequency 1.6 Ghz, max. frequency 3.4 GHz (Turbo Boost)) and UHD Graphics 620 (I used Intel's OpenCL SDK for GPU simulations). GPU results are just there to verify that the system works correctly, with consistent simulation results, even when switching between CPU and GPU strucures during simulation runs.

Most results are for uniform distribution of agents moving in random directions inside a fixed cube. Currently the only other distribution is one-clump: 80% of agents uniformly distributed and 20% clumped inside a cube whose side is 5% of the entire space cube's side length.

> Note that the following run-times are not the fastest I can get on my machine. I disabled Turbo Boost to get more consistent results, but with it enabled (which is the default) I get 1.5 - 2 times better run-times.

**Agents**|10000
**Steps**|1000
**Space size**|1000 * 1000 * 1000
**Threads (CPU)**|8

Simulation workload is best measured in number of interactions each agent has during a simulation step, and for the same number of agents, distribution and space size it depends only on the interaction radii. Obviously these numbers are exactly the same regardless of structure used:

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

Simulations with uniform (green) perform better than one-clump (blue) distributions because agents in the "clump" are all so close together that they must always interact:

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

## Application

Currently I'm using Tay only for a flocking simulation which can be seen [here](https://www.youtube.com/watch?v=DD93xIQqz5s). The video shows a simple flocking simulation with 30000 boids, running at around 30 ms per simulation step on the same configuration as the above benchmarks, using the `CpuGrid` structure. I'm hoping to add things like terrain and other, non-point moving agents that would require multiple different structures to be used and updated at different rates, all working together for an efficient simulation.

## Still to do

* Automatic adjustment of `depth_correction`.
* Support for non-point agents in the `CpuTree` structure.
* Combining multiple structures in a single simulation.
* More control over when structures get updated.
* Efficient communication through references or connections.
* Efficient communication through particle grids.
* Implement and benchmark the new `CpuAABBTree` structure.
* Implement thread balancing for the `CpuTree` structure.
* Add a simple samplig profiler to measure time spent updating and using structures.
