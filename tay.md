
## Efficient agent-based system simulation

A number of years ago I was working on [Ochre](https://github.com/bcace/ochre) - agent-based modeling and simulation tool, and I focused mostly on achieving immediate connection between model modification and simulation, and creating a language in which non-programmers could safely write parallel agent interaction code without fear of data races or race conditions. While simulation performance was decent, at a certain scale simulations would slow down enough to break the immediacy of model development, and it was obvious that there isn't a single "best" mechanism to facilitate efficient simulation for all the different models that users might want to develop.

Generally the biggest slowdown in agent-based simulations comes from agent interactions. If it is known in advance which agents will interact (connections between agents exist as separate entities, agents have direct references to other agents, or *all* agents have to interact) then the only thing to do is parallelize execution of those interactions. If the decision whether agents should interact is made based on their proximity ([flocking](https://en.wikipedia.org/wiki/Flocking_(behavior)) is a good example) then there's potential for optimization by using [space partitioning structures](https://en.wikipedia.org/wiki/Space_partitioning). These structures provide rough information on which groups of agents are so far apart that they have no chance of interacting (broad phase). Then we're left with groups of agents which *might* interact, and we have to filter out agent pairs that are too far apart (narrow phase).

> Example: if there are 1000 agents and they all have to interact, that's 999000 interactions at each step. If we now want to limit agents to only interact if they're close enough to each other, and it happens that for a certain range, on average, agents interact with 10 agents at each step, that's 10000 actual interactions. But in order to test whether agents should interact at all we still had to go through all 999000 pairs, which means we just wasted time on 989000 tests. We use pace partitioning structures to reduce this number.

At that point optimizing the chosen structure generally means:

* minimizing the number of agent pairs that pass the broad phase and get rejected in the narrow phase,
* minimizing time required to build/maintain the structure,
* minimizing time required to traverse the structure and find neighboring partitions,
* parallelizing both building and using the structure.

## Tay

[Tay](https://github.com/bcace/tay) is a collection of space partitioning structures created to explore how they perform on different models. The goal is to have multiple different test models and run simulations with different structures, on different numbers of threads and both on CPU and GPU, and compare run-times. Since agent properties, behavior and distribution in space can change during a single simulation run so much that it completely changes which structure is optimal, Tay allows switching between structures during a simulation run (even switching between CPU and GPU), changing the number of threads (on CPU) and adjusting any parameters each structure might have. Since conclusions derived from these experiments should be applicable to a wide variety of agent-based models, the following requirements should be met:

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

Generally with space partitioning structures it seems that there's often an optimal depth to which we partition the space. If we partition the space too little we get too many agents to reject during the narrow phase (distance test), and if we partition too much we get more partitions to build, traverse and test for closeness.

For this reason there are two parameters that can be adjusted for all partitioning structures. First is a set of sizes, one for each dimension, that represent the suggested smallest partition size for each dimension. They are just "suggested" because we can have multiple interactions in a model, each with its own interaction radii, and the smallest partition sizes should be related to those interaction radii. The other is a parameter called `depth_correction` that can then be varied to adjust the smallest partition sizes as `size = suggested_size / 2^depth_correction`.

Also note that unlike most other implementations of grids and trees for this kind of purpose, because we can have multiple interactions with drastically different interaction radii, we cannot assume that to find all agents that are within interaction range we can just consider a partition's immediate neighboring partitions. Generally, as mentioned above, interaction radii are used just as an initial, approximate value for a good partition size.

Currently all partitioning structures are completely rebuilt at the start of each step since profiling shows that it takes very little time compared to actual agent interactions.

### CPU

#### Simple

Simple is a "non-structure" used either when *all* agents have to interact, or just as a reference to measure the effectiveness of other, more elaborate structures. It just distributes agents evenly between threads, and of course we have to test each agent pair for distance and throw away pairs that are too far apart.

#### Tree

Tree structure is a k-d tree; a binary tree where a partition is split in half along a dimension with largest ratio between partition size in that dimension and smallest partition size in the same dimension. Neighboring partitions are found by traversing the tree and testing partitions' bounding boxes for overlap. (Threading)

#### Grid

### GPU

#### Simple

#### Tree

## Tests

(test model, variations, result verification)

All structures are tested and results are compared to make sure there are no race conditions (other than small errors caused by some floating point operations not being commutative) regardless of agent organization, number of execution threads or hardware used. Just to make sure structure implementations are completely independent there is a mode of execution where all structures are used, each one for a single step of the simulation.

(i5-8250U)
