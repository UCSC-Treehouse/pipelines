Makefile to run the expression, fusion and variant secondary pipelines used by [Treehouse](https://treehouse.soe.ucsc.edu/) on a single machine from the command line.

## Requirements

    Docker 1.12.x
    16+ cores
    50G+ memory
    100G+ storage for reference files
    100G+ storage per sample

## Getting Started

Clone this repository and then run 'make':

    git clone https://github.com/UCSC-Treehouse/pipelines.git
    make

References will be downloaded, verified via MD5, and then the included TEST paired fastqs will be run through the pipelines and outputs verified. This will take approximately 20-30 minutes on a 16 core machine excluding reference file download time. At the end you should see:

    Verifying md5 of output of TEST file
    tar -xOzvf outputs/expression/TEST_R1merged.tar.gz FAIL.TEST_R1merged/RSEM/rsem_genes.results |
    md5sum -c md5/expression.md5
    FAIL.TEST_R1merged/RSEM/rsem_genes.results
    -: OK
    cut -f 1 outputs/fusions/star-fusion-non-filtered.final | sort | md5sum -c md5/fusions.md5
    -: OK
    tail -n 10 outputs/variants/mini.ann.vcf | md5sum -c md5/variants.md5
    -: OK
    
NOTE: Fail is expected as the test file contains too few reads to pass our qc

Under outputs you should see the following:

    outputs/
    ├── expression
    │   ├── TEST_R1merged.sortedByCoord.md.bam
    │   └── TEST_R1merged.tar.gz
    ├── fusions
    │   ├── Log.final.out
    │   ├── star-fusion-gene-list-filtered.final
    │   └── star-fusion-non-filtered.final
    ├── qc
    │   ├── bam_umend_qc.json
    │   ├── bam_umend_qc.tsv
    │   └── readDist.txt
    └── variants
        └── mini.ann.vcf

Replace the TEST files under samples/ with your own pair of fastq's with _1/_2 or _R1/_R2 in their name and then:

    make expression qc fusions variants

A typical single sample running all three pipelines will take about 18 hours depending on the size/depth. Of this around 8 hours is expression, 1.5 hours is qc, 2 hours is fusion and a few minutes for variants. 

## Expression Outputs

The output is a tar.gz file with a variety of results merged. 

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
    TEST_R1merged/QC/STAR/Log.final.out
    TEST_R1merged/QC/STAR/SJ.out.tab

## Pipeline Sources

For additional information and source code for each pipeline see the following github repos:

[https://github.com/BD2KGenomics/toil-rnaseq]

[https://github.com/UCSC-Treehouse/bam-umend-qc]

[https://github.com/UCSC-Treehouse/fusion]

[https://github.com/UCSC-Treehouse/mini-var-call]
