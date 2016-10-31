# UCSC Treehouse Pipelines

Makefiles to standardize running Treehouse pipelines at partner sites.

# RNASeq 2.0.8

Requirments: Docker 1.12.1, 40G Memory, 100G Storage per Sample

Install and Test:

    git clone https://github.com/UCSC-Treehouse/pipelines.git
    cd pipelines/rnaseq-cgl-pipeline
    make

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
