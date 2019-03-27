Commands, Parameters, and Versions run by CGL TOIL RNA-Seq pipeline
================
Holly Beale

Reference version: [Commit f0ab2447 on March, 2019](https://github.com/UCSC-Treehouse/pipelines/tree/f0ab244799d1f0b3f97006750ed580dc719f75a3)

All Docker volume mappings have been removed for brevity from the following commands.

CutAdapt
--------
Docker command:

    docker run \
    --log-driver=none \
    --rm \
    quay.io/ucsc_cgl/cutadapt:1.9--6bd44edd2b8f8f17e25c5a268fedaab65fa851d2 \
    -a AGATCGGAAGAG \
    -m 35 \
    -A AGATCGGAAGAG \
    -o /data/R1_cutadapt.fastq \
    -p /data/R2_cutadapt.fastq /data/R1.fastq /data/R2.fastq

STAR
----
Docker command:

    docker run \
    --rm \
    --log-driver none \
    --name runstar--60HfKPIdEeqJ \
    quay.io/ucsc_cgl/star:2.4.2a--bcbd5122b69ff6ac4ef61958e47bde94001cfe80 \
    --runThreadN 160 \
    --genomeDir /data/starIndex \
    --outFileNamePrefix rna \
    --outSAMunmapped Within \
    --quantMode TranscriptomeSAM \
    --outSAMattributes NH HI AS NM MD \
    --outFilterType BySJout \
    --outFilterMultimapNmax 20 \
    --outFilterMismatchNmax 999 \
    --outFilterMismatchNoverReadLmax 0.04 \
    --alignIntronMin 20 \
    --alignIntronMax 1000000 \
    --alignMatesGapMax 1000000 \
    --alignSJoverhangMin 8 \
    --alignSJDBoverhangMin 1 \
    --sjdbScore 1 \
    --limitBAMsortRAM 49268954168 \
    --outSAMtype BAM Unsorted \
    --readFilesIn /data/R1.fastq /data/R2.fastq

RSEM
----

Docker command:

    docker run \
    --log-driver=none \
    --rm \
    quay.io/ucsc_cgl/rsem:1.2.25--d4275175cc8df36967db460b06337a14f40d2f21 \
    --paired-end \
    --quiet \
    --no-qualities \
    -p 16 \
    --forward-prob 0.5 \
    --seed-length 25 \
    --fragment-length-mean \
    -1.0 \
    --bam /data/transcriptome.bam /data/rsem_ref_hg38/hg38 rsem

Gene symbol conversion
----------------------

Docker command:

    docker run \
    --log-driver=none \
    --rm \
    quay.io/ucsc_cgl/gencode_hugo_mapping:1.0--cb4865d02f9199462e66410f515c4dabbd061e4d \
    -g rsem_genes.results \
    -i rsem_isoforms.results

Commentary
-------------------------------

These dockers generally just wrap the program and pass the arguments directly to the program. For the dockers where the program is ambiguous, you can look to see what program is launched with the instance is started

Command

    docker inspect quay.io/ucsc_cgl/rsem:1.2.25--d4275175cc8df36967db460b06337a14f40d2f21 | grep -A 2 Entrypoint

Result

                "Entrypoint": [
                    "sh",
                    "/opt/rsem/wrapper.sh"

Then I run the docker interactively:

    docker run --rm -ti --entrypoint=/bin/bash quay.io/ucsc_cgl/rsem:1.2.25--d4275175cc8df36967db460b06337a14f40d2f21 

Once it has launched, I run the command

    cat /opt/rsem/wrapper.sh

And I can see that the arguments are passed to "rsem-calculate-expression".

MD5sums for reference files
---------------------------

    6cd4696f598b30605e1708ad0b45188d  GCA_000001405.15_GRCh38_no_alt_analysis_set.dict

    a6da8681616c05eb542f1d91606a7b2f  GCA_000001405.15_GRCh38_no_alt_analysis_set.fa

    5fddbc109c82980f9436aa5c21a57c61  GCA_000001405.15_GRCh38_no_alt_analysis_set.fa.fai

    6b86ffe9530ebbcb0572edd64cb86cd5  rsem_ref_hg38_no_alt.tar.gz

    71331de455188b52f03450cdade807ed  starIndex_hg38_no_alt.tar.gz
