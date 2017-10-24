# UCSC Treehouse Pipelines

Makefile to run Treehouse pipelines partner sites on a single machine from the command line.

## Requirements

Docker 1.12.1
50G Memory
100G for reference files
100G Storage per sample

## Getting Started

Clone this repository and then run 'make':

    git clone https://github.com/UCSC-Treehouse/pipelines.git
    make

References will be downloaded, verified via MD5, and then the included test file will be run through the expression pipeline and outputs verified. This will take approximately 20-30 minutes on a 16 core machine excluding reference file download time. At the end you should see:

    -: OK

At this point you can replace the two test files under samples with your own and then:

    make expression

or

    make fusion


Intermediate files will be stored in output/ with the final output named after the input filename with
.gz on the end.  A typical single sample running just expression on a 16 core 120G server will take
about 8 hours to process. Additional samples submitted at the same time will take a bit less. The
Makefile has debugging turned on to facilitate any issues with getting the test files to process.
After you are up and running change to --logInfo. In production these pipelines are run by the UCSC
core via Dockstore (https://dockstore.org/containers/quay.io/ucsc_cgl/rnaseq-cgl-pipeline).

## Expression and BAM QC Outputs

The output is a tar.gz file with a variety of results merged. If bamqc fails then 'FAIL.' will be
prepended to the folder.

    TEST_R1merged/RSEM/rsem_genes.results
    TEST_R1merged/RSEM/rsem_isoforms.results
    TEST_R1merged/RSEM/Hugo/rsem_genes.hugo.results
    TEST_R1merged/RSEM/Hugo/rsem_isoforms.hugo.results
    TEST_R1merged/Kallisto/run_info.json
    TEST_R1merged/Kallisto/abundance.tsv
    TEST_R1merged/Kallisto/abundance.h5
    TEST_R1merged/QC/fastQC/R1_fastqc.html
    TEST_R1merged/QC/fastQC/R1_fastqc.zip
    TEST_R1merged/QC/fastQC/R2_fastqc.html
    TEST_R1merged/QC/fastQC/R2_fastqc.zip
    TEST_R1merged/QC/bamQC/readDist.txt
    TEST_R1merged/QC/bamQC/rnaAligned.out.md.sorted.geneBodyCoverage.curves.pdf
    TEST_R1merged/QC/bamQC/rnaAligned.out.md.sorted.geneBodyCoverage.txt
    TEST_R1merged/QC/bamQC/readDist.txt_FAIL_qc.txt
    TEST_R1merged/QC/STAR/Log.final.out
    TEST_R1merged/QC/STAR/SJ.out.tab

## Expression

The expression pipeline with further calling details can be found here:

    https://github.com/BD2KGenomics/toil-rnaseq

## BAM QC

The expression pipeline runs QC on the aligned bam.Details can be found here:

    https://github.com/UCSC-Treehouse/bam_qc

Remove --bamqc to turn off running bamqc

## Fusion

The fusion pipeline with further calling details can be found here:

    https://github.com/UCSC-Treehouse/fusion

## To run the docker interactively:

    docker run -ti --entrypoint=/bin/bash quay.io/ucsc_cgl/rnaseq-cgl-pipeline:3.2.1-1 -s
