# Tay on GPU

In addition to CPU implementations of space partitioning structures Tay now provides GPU structures that can be used to run the entire simulation or just some of its parts on GPU. The new GPU structures are implemented so they can complement the existing CPU structures: a simulation can be easily moved between CPU and GPU, or it can contain a mix of interacting CPU and GPU structures.

GPU structures are implemented using the OpenCL API, just so I can run them on both my GPUs: Intel UHD 620 and AMD Radeon RX 5500 XT.

Currently there are two GPU structures, `OclSimple` and `OclGrid`. `OclSimple` is the brute-force option where all agent pairs check how close they are to each other (there's not broad phase neighbor search). Althouh this structure is much faster than the corresponding CPU structure (`CpuSimple`) it manages to be as fast as the faster CPU structures such as `CpuGrid` only on smaller agent counts (<100000). With higher agent counts it's not very efficient although it can still be used if we have no other choice - for example if the model requires that all agents interact or we have non-point agents in the model.

`OclGrid` is currently the fastest structure in Tay, and its implementation with regards to how agents interact and act is relatively straightforward, but the agent sorting that happens before any agent interaction is where complications arise.
