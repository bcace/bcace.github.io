
## Efficient agent-based system simulation

A number of years ago I was working on [Ochre](https://github.com/bcace/ochre) - agent-based modeling and simulation tool, and I focused mostly on achieving immediate connection between model modification and simulation, and creating a language in which non-programmers could safely write parallel agent interaction code without fear of data races or race conditions. While simulation performance was decent, at a certain scale simulations would slow down enough to break the immediacy of model development, and it was obvious that there isn't a single "best" mechanism to facilitate efficient simulation for all the different models that users might want to develop. Even in the simplest case if we assume that all agents are points, and all their interactions depend on distances between them, we can still use completely different optimizations, depending just on whether agent distribution is dense or sparse, and whether agents are static or moving.

Generally the biggest slowdown in agent-based simulations comes from agent interactions. If it is known in advance which agents will interact (connections between agents, direct references to other agents, or when *all* agents have to interact) then the only thing to do is parallelize the execution of those interactions. If the decision whether agents should interact is made based on their proximity ([flocking](https://en.wikipedia.org/wiki/Flocking_(behavior)) is a good example) then there's potential for optimization by using [space partitioning structures](https://en.wikipedia.org/wiki/Space_partitioning). These structures provide rough information on which groups of agents are so far apart that they have no chance of interacting (broad phase). Then we're left with groups of agents which *might* interact, and we have to filter out agent pairs that are too far apart (narrow phase).

> Example: if there are 1000 agents and they all have to interact, that's 999000 interactions at each step. If we now want to limit agents to only interact if they're close enough to each other, and it happens that for a certain range, on average, agents interact with 10 agents at each step, that's 10000 actual interactions. But in order to test whether agents should interact at all we still had to go through all 999000 pairs, which means we just wasted time on 989000 tests. We use pace partitioning structures to reduce this number of agent pairs we have to test.

At that point optimizing the chosen structure generally means:

* minimizing the number of agent pairs that pass the broad phase and get rejected in the narrow phase,
* minimizing time required to build/maintain the structure,
* minimizing time required to traverse the structure and find neighboring partitions,
* parallelizing both building and using the structure.

## Tay

To help explore how different models and optimization methods interact I wrote [Tay](https://github.com/bcace/tay). The goal is to have multiple different test models and simulate them with different space partitioning structures, on different numbers of threads and both on CPU and GPU, and compare run-times. Since during a single simulation agent properties, behavior and distribution in space could change so much that it completely changes which structure is optimal, Tay allows switching between structures during simulation (even between CPU and GPU), changing the number of threads (on CPU) and adjusting any parameters each structure might have.

As mentioned above, results of this work should be applicable to a wide variety of agent-based models, so Tay already accomodates following requirements (at least does not preclude ... from being added):

* communication methods can be combined: communicating with neighbors, through direct references, connection objects or a grid [particle mesh method](https://en.wikipedia.org/wiki/Particle_Mesh),
* space doesn't have fixed boundaries,
* number of space dimensions is flexible (currently 1 - 4),
* there can be multiple agent types with multiple different interactions defined between them, each with its own set of interaction distances,
* agent can have length in any dimension (don't have to be points),
* agent can be removed from or added to a simulation.

## Assigning agent behavior

To avoid race conditions agent behavior code is split into *passes*. There are currently only two types of passes: **act** and **see**. **act** pass describes what each agent does on its own, and **see** pass describes how two agents interact where one agent *sees* the other one. This strict role assignment for the two agents as **seer** and **seen** in **see** passes is what enables lock-free parallelism: knowing which of the two agents can change its state (**seer**) and which one is read-only (**seen**) enables scheduling **see** code execution so that a **seer** agent is never in more than one thread during a **see** pass.

So if we only want to describe a particle system where agents are particles that don't interact, we would only have one **act** pass. ... a C function that would look something like this:

> NOTE: Following simplified examples are written as pseudo code, similar to OpenCL C, in current Tay implementation I write C code with some decorations that a preprocessing script turns into regular C which I pass as function pointers to the simulation for CPU execution, and OpenCL C which I pass to the OpenCl API as string for GPU execution.

```C
void act(MyAgentType *agent, void *pass_context) {
    agent->position.x += 1; /* these agents move along the x axis by 1 each simulation step */
}
```

If we wanted to have a simple interaction where agents bounced off each other:

```C
void see(MyAgentType *seer_agent, MyAgentType *seen_agent, MySeePassSettings *see_settings) {
    float4 d = seer_agent->position - seen_agent->position; /* distance between two agents */
    if (length(d) < see_settings->r) {  /* if the two agents are close enough */
        float4 f = d * see_settings->c; /* calculate force using the spring constant */
        seer_agent->f -= f; /* seer agent gets pushed away from seen agent */
        seen_agent->f += f; /* seen agent gets pushed away from seer agent */
    }
}

void act(MyAgentType *agent, void *pass_context) {
    agent->position += seer_agent->f; /* move agent in the direction of the force */
    seer_agent->f = 0; /* clear the force so in the next simulation step agent can accumulate new resulting force */
}
```

## Space partitioning structures

Space that these structures partition doesn't have to be actual space, the four available dimensions can represent anything; that's why, when e.g. saying that an interaction only works within a certain range, we have to specify the range for each of the used 1, 2, 3 or 4 dimensions.

Generally with space partitioning structures it seems that there's often an optimal depth to which we partition the space. If we partition the space too little we get too many agents to reject during the narrow phase (distance test), and if we partition too much we get more partitions to build, traverse and test for closeness.

For this reason there are two parameters that can be adjusted for all partitioning structures. First is a set of sizes, one for each dimension, that represent the suggested smallest partition size for each dimension. They are just "suggested" because we can have multiple interactions in a model, each with its own interaction radii, and the smallest partition sizes should be related to those interaction radii. Then there is a parameter called "depth_correction" that can then be varied to adjust the smallest partition sizes as follows:

```
size = suggested_size / 2^depth_correction
```

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

All structures are tested and results are compared to make sure there are no race conditions (other than small errors caused by some floating point operations not being commutative) regardless of agent organization, number of execution threads or hardware used. Just to make sure structure implementations are completely independent there is a mode of execution where all structures are used, each one for a single step of the simulation.

(i5-8250U)
