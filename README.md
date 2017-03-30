# UCSC Treehouse Pipelines

Makefile to run pipelines used in Treehouse at partner sites

## Requirements

Docker 1.12.1 or greater
50G Memory
100G Storage per Sample

## Getting Started

Clone this repository and then run 'make':

    git clone https://github.com/UCSC-Treehouse/pipelines.git
    make

References will be downloaded, verified via MD5, and then included test file will be run through the pipelines and outputs verified. This will take approximately X minutes on a 16 core machine.,b

    Verifying output of test file
    OK

At this point you can replace the test file under samples with your own and then:

    make expression

or

    make fusion

Intermediate files will be stores in work/ with the final output named after the input filename with
.gz on the end.  A typical single sample running just expression on a 16 core 120G server will take
about 8 hours to process. Additional samples submitted at the same time will take a bit less. The
Makefile has debugging turned on to facilitate any issues with getting the test files to process.
After you are up and running change to --logInfo. In production these pipelines are run by the UCSC
core via Dockstore (https://dockstore.org/containers/quay.io/ucsc_cgl/rnaseq-cgl-pipeline).

## Expression

The expression pipeline with further calling details can be found here:

    https://github.com/BD2KGenomics/toil-rnaseq

## BAM QC

The makefile by default also runs a quality control pipeline on the aligned bam output of the
expression pipeline. Details on this QC can be found here:

    https://github.com/UCSC-Treehouse/bam_qc

## Fusion

The fusion pipeline with further calling details can be found here:

    https://github.com/UCSC-Treehouse/fusion
