
## Efficient agent-based system simulation

A number of years ago I was working on [Ochre](https://github.com/bcace/ochre) - agent-based modeling and simulation tool, and I focused mostly on achieving immediate connection between model modification and simulation, and creating a language in which non-programmers could safely write parallel agent interaction code without fear of data races or race conditions. While simulation performance was decent, at a certain scale simulations would slow down enough to break the immediacy of model development, and it was obvious that there isn't a single most efficient simulation mechanism for all the different models that users might want to develop.

The biggest cause of slowdowns in agent-based simulations is the number of interactions that can occur between agents. If it's known in advance which agents will interact (connections between agents exist as separate entities, agents have direct references to other agents, or *all* agents have to interact) then the only thing to do is parallelize execution of those interactions. If the decision whether agents should interact is made based on their proximity ([flocking](https://en.wikipedia.org/wiki/Flocking_(behavior)) is a good example) then there's potential for optimization by using [space partitioning structures](https://en.wikipedia.org/wiki/Space_partitioning). These structures provide rough information on which agents are so far apart that they have no chance of interacting (broad phase), and which agents *might* interact. Each of the remaining pairs of agents that might interact we have to test for distance explicitly (narrow phase).

As an example of why we need space partitioning let's look at some simple numbers. If there's a 1000 agents in a model and they all have to interact, that's 999000 interactions at each step. If we now want to limit agents to only interact if they're close enough to each other, and it turns out that for the given interaction range agents on average come close enough to 10 other agents at each step, that's 10000 actual interactions. But in order to test whether agents should interact at all we still had to go through all 999000 pairs, which means we just wasted time on 989000 tests. We use pace partitioning structures to reduce this number. At that point optimizing the chosen structure generally means:

* minimizing the number of agent pairs that pass the broad phase and get rejected in the narrow phase,
* minimizing time required to build/maintain the structure,
* minimizing time required to traverse the structure and find neighboring partitions,
* parallelizing both building and using the structure.

## Tay

I wrote [Tay](https://github.com/bcace/tay) as a collection of space partitioning structures to explore how they perform in different conditions. The goal is to have multiple different test models and run simulations with different structures, on different numbers of threads and both on CPU and GPU, and compare run-times. Since agent properties, behavior and distribution in space can change during a single simulation run so much that it completely changes which structure is optimal, Tay allows switching between structures during a simulation run (even switching between CPU and GPU), changing the number of threads (on CPU) and adjusting any parameters each structure might have. Since conclusions derived from these experiments should be applicable to a wide variety of agent-based models, the following requirements should be met:

##### Space dimensions

Currently space can have 1, 2, 3 or 4 dimensions, and those dimensions can be of any type, not just spatial. The fact that dimensions don't have to be of the same type means that space partitioning structures treat each dimension separately. For example, when defining an interaction between agents we cannot just define one range value to which the interaction is limited, we have to specify a separate value for each dimension.

##### Agent size

Agents can have size in any dimension (don't have to be points). This can complicate space partitioning structures somewhat. If it's a tree structure there's a possibility to add agents to non-leaf nodes. If it's a grid structure then the same agent can be added to multiple partitions in which case we have to prevent multiple interactions between same agents, or we can build a "fake" tree from multiple grids of varying partition sizes.

##### Space bounds

Space doesn't have fixed bounds, agents are free to move anywhere, and it's up to the space partitioning structure to update itself correctly.

##### Agent types

Multiple agent types can be defined. This allows having agents with drastically different behaviors in a single model.

##### Behaviors and interactions

To avoid data races and race conditions agent behavior code is split into an arbitrary number of *passes*. There are currently only two types of passes: **act** and **see**.

**act** pass describes what each agent does with its own data, there is no communication with other agents. This pass is defined for a specific agent type and specifies a procedure that is applied to all "live" agents of that type.

**see** pass describes how two agents interact, the **seer** agent and the **seen** agent. This strict role assignment for these two agents is what enables lock-free parallelism: knowing that the **seer** agent can change its state and the **seen** agent is read-only enables scheduling **see** code execution so that a **seer** agent is never in more than one thread during this pass. **see** pass is defined for two agent groups: **seer** agent type and **seen** agent type, and specifies a procedure that is applied to all agent pairs the space partitioning structure decides should interact.

##### Communication methods

Communication methods can be combined: communicating with neighbors within specified range(s), through direct references, connection objects or a [grid](https://en.wikipedia.org/wiki/Particle_Mesh). Currently agents only interact with neighbors, but I took special care to not preclude any of the other mechanisms from being added.

##### Adding/removing agents

Agents can be removed from or added to a running simulation. This requires certain provisions in the space partitioning structures, depending on the model itself and the chosen method for efficiently iterating through agents. The options are roughly:

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

`GpuTree` structure is actually a hybrid: tree update still happens on the CPU, then minimal updates to the structure are copied over to the GPU where the passes get executed. At the end of the simulation step only the new agent positions are copied back to the CPU in order to be able to update the tree again.

### Grid

`CpuGrid` structure is a hash grid. Hash function used to map grid cell indices to bin indices is a simple XOR hash function.

**Update:** Space bounding box and suggested partition sizes are used to convert each agent's position into grid cell indices, which are then hashed to find the appropriate bin for the agent. All non-empty bins are linked into a list for faster access.

**Act:** Each thread iterates through its assigned bins so that each bin's agents get processed by one of the threads.

**See:** Each thread iterates through its set of **seer** bins and finds neighboring **seen** bins through its **seer** agents' positions. Because of hash collisions a single bin can contain agents from multiple grid cells, so in principle we have to find neighboring bins for each **seer** bin agent, but since most bins contain agents of only one cell the algorithm caches found neighboring bins.

To find neighboring **seen** bins, **seer** agent's cell indices are calculated from its position, then cell sizes and **see** radii are used to build the "kernel" of cells neighboring the **seer** cell, and finally indices of each kernel cell are hashed to find the corresponding bins.

Hash collisions also have to be taken into account when looking at kernel **seen** bins. One problem is that kernel **seen** bins can also contain agents from multiple cells, and some of those cells obviously might be outside the kernel. Simplest solution is to ignore the problem and just let those agents get rejected during the narrow phase (then it becomes a problem of reducing the number of collisions, which we have to do anyway). The other problem is that a hash collision could cause the same bin to appear multiple times in the same kernel. The fix for that is to mark bins as already visited and skip them on subsequent encounters.

## Results

So finally we come to the point of the project - comparison of space partitioning structures. Here I run a series of simulations where I apply each structure to a test model (and its variants), and then tweak the structure to see if there's a setting where it performs better than others for the given model.

Since focus is on optimizing spatial agent interactions the model I used is a very abstracted version of flocking. To make agent spatial distribution consistent during simulation runs (and therefore number of interactions), agent movement is predefined (it doesn't depend on agent interactions). To verify that the simulation is running correctly there is a separate `f_buffer` variable that gets updated at each step by the agent's interactions with other agents. I compare values of `f_buffer` variables between simulation runs to make sure that all simulations of the same model run exactly the same, regardless of any differences between how those simulation were run, on which hardware they were run, and which structures were used.

Variables in these experiments can be grouped into model variables and system variables. Model variables are the number of agents in the model, agent distribution in space (density and "clumpiness"), interaction radii, and how demanding the interaction code is. System variables are the number of threads the simulation is running on, the space partitioning structure used (including whether it's a CPU or GPU structure), `depth_correction` (where applicable), and any structure-specific settings like `GpuSimple` structure's `direct` setting or hash table size dictated by the available memory for the `CpuGrid` structure.

So far I only had the chance to run simulations on my ThinkPad T480 with the i5-8250U processor (4 physical and 8 logical processors, base frequency 1.6 Ghz, max. frequency 3.4 GHz (Turbo Boost)) and UHD Graphics 620 (I used Intel's OpenCL SDK for GPU simulations). GPU results are just there to verify that the system works correctly, with consistent simulation results, even when switching between CPU and GPU strucures during simulation runs.

Simulation run-times in milliseconds per step are grouped in tables for each model setting. Columns in tables are for different values of `depth_correction`, where the first three columns are when interaction code is really small so the effects of structures are more noticeable, and the last three columns are when the same code is executed 50 times. For now only the uniform agent distribution is used (no clumps). Interactions number above each table is the average number of interaction each agent has with other agents per simulation step.

**Agents**|10000
**Steps**|1000
**Space size**|1000 * 1000 * 1000
**Threads (CPU)**|8

Distribution: **uniform**, interaction radius: **50**, interactions: **9.259736**

||0|1|2|0|1|2
|---|---|---|---|---|---|---
|`CpuSimple`|241| | |237.811| | |
|`CpuTree`|13.1998|9.1434|21.0415|26.3292|20.9866|31.4384
|`CpuGrid`|12.2572|6.91087|12.0181|23.2136|17.8319|21.9292
|`GpuSimple` (direct)|12.1861| | |13.2801| | |
|`GpuSimple` (indirect)|13.28| | |14.0834| | |
|`GpuTree`|13.5655|13.5737|13.5772|14.3676|14.7656|14.3933

Distribution: **uniform**, interaction radius: **100**, interactions: **68.579978**

||0|1|2|0|1|2
|---|---|---|---|---|---|---
|`CpuSimple`|288.558| | |348.111| | |
|`CpuTree`|67.9695|16.7269|21.9998|165.687|114.562|106.946
|`CpuGrid`|64.9858|14.4933|17.7145|153.531|95.5592|98.3469
|`GpuSimple` (direct)|14.4486| | |22.6436| | |
|`GpuSimple` (indirect)|15.7601| | |23.3795| | |
|`GpuTree`|16.0466|16.0327|16.0371|26.1787|32.8293|32.2879

Distribution: **uniform**, interaction radius: **200**, interactions: **466.408336**

||0|1|2|0|1|2
|---|---|---|---|---|---|---
|`CpuSimple`|371.232| | |876.459| | |
|`CpuTree`|542.854|87.6051|55.7068|1523.16|774.495|710.917
|`CpuGrid`|325.819|79.3073|54.2915|1015.64|661.136|606.212
|`GpuSimple` (direct)|28.2817| | |98.0489| | |
|`GpuSimple` (indirect)|29.4292| | |96.5526| | |
|`GpuTree`|29.7354|29.7095|32.2067|97.2047|96.5641|97.035

Note that these numbers are not the fastest I can get on my machine. I disabled Turbo Boost to make numbers more consistent, but with it enabled (which is the default) I get 1.5 - 2 times faster run-times.
