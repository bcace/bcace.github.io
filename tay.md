
## Efficient complex system simulation

A number of years ago I was working on an agent-based modeling and simulation tool ([Ochre](https://github.com/bcace/ochre) is the most recent one of four complete rewrites) and at the time I focused mostly on how to achieve immediate connection between changes in model code and simulation, and creating a language in which non-programmers could write parallel programs without having to worry about writing lock-free and race-condition-free parallel code.

While simulation performance was comparable to or better than similar tools at the time, at certain scale simulations would slow down enough to break the immediacy of model development. And the main worry was that I could never come up with a good [space partitioning](https://en.wikipedia.org/wiki/Space_partitioning) scheme that could be used in a parallel way and would fit all the different models, with their different types of agents, behaviors and interaction mechanisms.

Agent-based (or generally [Complex system](https://en.wikipedia.org/wiki/Complex_system)) simulations are relatively common: academic agent-based simulations, CGI for movies, games and art. Executing all these simulations at large scale is always problematic, and the most significant contribution to simulation run-times comes from the number of interactions between agents.
In simulations where number of interactions is predictable and relatively constant (each agent interacts with all other agents, or they interact with a relatively fixed subset of other agents, identified through references or connections) we only have to parallelize the execution and make sure that workload is balanced between threads.

If agent interaction depends on distance between moving agents then we have an additional job to cull as many "impossible" interactions as quickly as possible. This is usually done by organizing agents into [space partitioning structures](https://en.wikipedia.org/wiki/Space_partitioning) that give us rough information on which groups of agents are so far apart that they have no chance of interacting (broad phase). Then we're left with groups of agents which *might* interact, and we have to filter out agent pairs that are too far apart (narrow phase). At that point optimizing the chosen structure comes down to:

* minimizing the number of agent pairs that pass the broad phase and get rejected in the narrow phase,
* minimizing time required to build/maintain the structure,
* minimizing time required to traverse the structure and find neighboring partitions.

Additionally, we have to be able to use this space partitioning structure from multiple threads in a balanced way.

To explore how different models and optimization methods interact I wrote [Tay](https://github.com/bcace/tay). The goal is to have multiple different test models and simulate them with different space partitioning structures, on different numbers of threads and both on CPU and GPU, and compare run-times. Since during a single simulation agent properties, behavior and distribution in space could change so much that it completely changes which structure is optimal, Tay allows switching between structures during simulation (even between CPU and GPU), changing the number of threads (on CPU) and adjusting any parameters each structure might have.

Results of these tests would not be useful to anyone else if I assumed a certain type of agent-based models, a certain type of agents or a certain method of communication between them; so Tay should already implement or at least not preclude any of the following features from being added.

* Communication methods can be combined: communicating with neighbors, through direct references, connection objects or a grid [particle mesh method](https://en.wikipedia.org/wiki/Particle_Mesh).
* Space doesn't have fixed boundaries.
* Number of space dimensions is flexible (currently 1 - 4).
* There can be multiple agent types with multiple different interactions defined between them, each with its own set of interaction distances.
* Agent can have length in any dimension (don't have to be points).
* Agent can be removed from or added to a simulation.

## Implemented structures

### CPU simple

### CPU tree

### CPU grid

### GPU simple

### GPU tree

## Tests

All structures are tested and results are compared to make sure there are no race conditions (other than small errors caused by some floating point operations not being commutative) regardless of agent organization, number of execution threads or hardware used. Just to make sure structure implementations are completely independent there is a mode of execution where all structures are used, each one for a single step of the simulation.
