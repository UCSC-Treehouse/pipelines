# UCSC Treehouse Pipelines

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

References will be downloaded, verified via MD5, and then the included test file will be run through the pipelines and outputs verified. This will take approximately 20-30 minutes on a 16 core machine excluding reference file download time. At the end you should see:

    Verifying md5 of output of TEST file
    tar -xOzvf outputs/expression/TEST_R1merged.tar.gz FAIL.TEST_R1merged/RSEM/rsem_genes.results |
    md5sum -c md5/expression.md5
    FAIL.TEST_R1merged/RSEM/rsem_genes.results
    -: OK
    cut -f 1 outputs/fusions/star-fusion-non-filtered.final | sort | md5sum -c md5/fusions.md5
    -: OK
    tail -n 10 outputs/variants/mini.ann.vcf | md5sum -c md5/variants.md5
    -: OK

You should see the following under outputs:

    outputs/
    ├── expression
    │   ├── TEST_R1merged.sortedByCoord.md.bam
    │   └── TEST_R1merged.tar.gz
    ├── fusions
    │   ├── Log.final.out
    │   ├── star-fusion-gene-list-filtered.final
    │   └── star-fusion-non-filtered.final
    └── variants
        └── mini.ann.vcf

Replace the TEST files under samples/ with your own with 1/2 or R1/R2 in their names and then:

    make expression fusions variants

A typical single sample running all three pipelines will take about 18 hours depending on the size/depth. Of this around 8 hours is expression, 8 hours is bam qc, 2 hours is fusion and a few minutes is variants. 

## Expression and BAM QC Outputs

The output is a tar.gz file with a variety of results merged. If bamqc fails then 'FAIL.' will be
prepended to the folder name:

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

## Pipeline Sources

All of the source to the pipelines are available on github with additional documentation:

[https://github.com/BD2KGenomics/toil-rnaseq]

[https://github.com/UCSC-Treehouse/bam_qc]

[https://github.com/UCSC-Treehouse/fusion]

[https://github.com/UCSC-Treehouse/mini-var-call]

## Options

You can run off bam qc for faster expression run times by removing --bamqc. But note that you will not be able to run the variant pipeline as it requires the sorted bam file that bamqc generates.

Add --logInfo to the rnaseq docker call for additional debugging messages.
