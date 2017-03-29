# UCSC Treehouse Pipelines

Makefiles to run pipelines used in Treehouse at partner sites

# Requirements

Docker 1.12.1 or greater
40G Memory
100G Storage per Sample

# Getting Started

Clone this repository and then run 'make':

    git clone https://github.com/UCSC-Treehouse/pipelines.git
    make

References will be downloaded, verified via MD5, and then included test files will be run through the pipelines and outputs verified. This will take approximately X minutes on a 16 core machine. At the end you should see:

OK

# Expression and QC

    https://github.com/BD2KGenomics/toil-rnaseq

Requirments: Docker 1.12.1, 40G Memory, 100G Storage per Sample


Reference files will be downloaded into inputs/, a test file
processed and the output verified. After about 20 minutes
you should see:

    TEST/RSEM/rsem.genes.norm_counts.tab
    -: OK

To process your own samples place a tar file per sample
in samples/ consisting of two paired read fastq's with
standard R1 R2 naming and then:

    make run

Intermediate files will be stores in outputs/ with the final
output named after the input filename with .gz on the end.
A typical single sample running on a 16 core 120G server will
take about 8 hours to process. Additional samples submitted
at the same time will take a bit less.

See https://github.com/BD2KGenomics/toil-rnaseq for more details.

To run the docker interactively:

    docker run -ti --entrypoint=/bin/bash quay.io/ucsc_cgl/rnaseq-cgl-pipeline:2.0.8 -s

