# UCSC Treehouse Pipelines

Makefile's to standardize running Treehouse pipelines at partner sites.

For each pipeline there is a folder named after the corresponding dockerized Toil pipeline:

https://github.com/BD2KGenomics/cgl-docker-lib

To run a pipeline cd into the pipeline folder and run make. By
default any required reference files will be downloaded into inputs/
and any samples will be processed from samples/. An included test
file will also be processed and one of its output files checked.
