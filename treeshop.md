# Treeshop Cluster Processing

To process multiple samples through the [Treehouse pipelines Makefile](https://github.com/UCSC-Treehouse/pipelines/blob/master/Makefile) we use [docker-machine](https://docs.docker.com/machine/overview/) to spin up a cluster of machines on an Openstack cluster and a simple [Fabric](http://www.fabfile.org/) file to control the compute. 

## Requirements

  [docker](https://www.docker.com)
  [docker-machine](https://docs.docker.com/machine/overview/)
  [Fabric](http://www.fabfile.org/)
  Credentials for your Openstack Cluster (OS_USERNAME and OS_PASSWORD defined)

## Operation Overview

Treeshop automates what you'd do if you spun up a set of machines, copied over the Makefile and
fastq's, ssh'd in, ran, and copied the results back. It does this by using docker-machine to spin up
the machines and Fabric to abstract all the ssh and file copying. The process fabric command performs a
simple round robin allocation splitting up the IDs listed in manifest.txt among all the machines and
then in parallel walking through these lists per machine. As a result if you have a few samples that
are much larger/longer or shorter you'll find your cluster at the end of a run will have mostly
idle machines. While run you can 'fab top' to see what docker's are running on each machine to get a
sense of if things are going smoothly.

## Getting Started

Clone this repository:

    git clone https://github.com/UCSC-Treehouse/pipelines.git

Create a folders that match the [Treehouse storage layout](https://github.com/UCSC-Treehouse/pipelines/blob/master/fabfile.py#L12):

    mkdir -p treeshop/primary/original/TEST treeshop/downstream

Copy the TEST fastq samples into the storage hierarchy
  
    cp samples/*.fastq.gz treeshop/primary/original/TEST/

Spin up a single cluster machine:

    fab up

Output:

    Running pre-create checks...
    Creating machine...
    (username-treeshop-20180319-112512) Creating machine...
    Waiting for machine to be running, this may take a few minutes...
    ...
    Docker is up and running!
    To see how to connect your Docker Client to the Docker Engine running on this virtual machine, run:
    docker-machine env username-treeshop-20180319-112512
    [localhost] local: cat ~/.ssh/id_rsa.pub| docker-machine ssh username-treeshop-20180319-112512 'cat
    >> ~/.ssh/authorized_keys'

Verify that its up and you can see it in docker-machine

    docker-machine ls

Output:

    NAME                               ACTIVE   DRIVER      STATE     URL                        SWARM
    DOCKER        ERRORS
    username-treeshop-20180319-112512   -        openstack   Running   tcp://10.50.102.245:2376
    v18.02.0-ce

Configure and download references

    fab configure reference

Output:

    [10.50.102.245] Executing task 'configure'
    [10.50.102.245] sudo: gpasswd -a ubuntu docker
    [10.50.102.245] out: Adding user ubuntu to group docker
    [10.50.102.245] out:
    ...
    [10.50.102.245] out: STARFusion-GRCh38gencode23/ref_genome.fa.fai
    [10.50.102.245] out: STARFusion-GRCh38gencode23/ref_cdna.fasta
    [10.50.102.245] out:
    Done.

Process the samples in manifest.tsv with source and destination under the treeshop folder sending log output to the console and log.txt:

    fab process:manifest=manifest.txt,base=treeshop 2>&1 | tee log.txt

Output:

  [10.50.102.245] Executing task 'process'
  Warning: run() received nonzero return code 1 while executing 'docker stop $(docker ps -a -q)'!
  Warning: run() received nonzero return code 1 while executing 'docker rm $(docker ps -a -q)'!
  [10.50.102.245] put: /scratch/username/pipelines/Makefile -> /mnt/Makefile
  10.50.102.245 processing TEST
  ...lot and lots of output...
	Done.

After this you should have the following under downstream:

	treeshop/downstream/
	└── TEST
      └── secondary
          ├── md5sum-3.7.0-ccba511
          │   ├── md5
          │   └── methods.json
          ├── ucsc_cgl-rnaseq-cgl-pipeline-3.3.4-785eee9
          │   ├── Kallisto
          │   │   ├── abundance.h5
          │   │   ├── abundance.tsv
          │   │   ├── fusion.txt
          │   │   └── run_info.json
          │   ├── methods.json
          │   ├── QC
          │   │   ├── fastQC
          │   │   │   ├── R1_fastqc.html
          │   │   │   ├── R1_fastqc.zip
          │   │   │   ├── R2_fastqc.html
          │   │   │   └── R2_fastqc.zip
          │   │   └── STAR
          │   │       ├── Log.final.out
          │   │       └── SJ.out.tab
          │   ├── RSEM
          │   │   ├── Hugo
          │   │   │   ├── rsem_genes.hugo.results
          │   │   │   └── rsem_isoforms.hugo.results
          │   │   ├── rsem_genes.results
          │   │   └── rsem_isoforms.results
          │   └── sorted.bam
          ├── ucsctreehouse-bam-umend-qc-1.1.0-cc481e4
          │   ├── bam_umend_qc.json
          │   ├── bam_umend_qc.tsv
          │   ├── methods.json
          │   └── readDist.txt                                                                                                                                                         ├── ucsctreehouse-fusion-0.1.0-3faac56
          │   ├── Log.final.out
          │   ├── methods.json
          │   ├── star-fusion-gene-list-filtered.final
          │   └── star-fusion-non-filtered.final
          └── ucsctreehouse-mini-var-call-0.0.1-1976429
              ├── methods.json
              └── mini.ann.vcf

## Notes

Error output with respect to finding and copying files will be written to error.log. All of the output for all machines running in parallel will end up in log.txt. As a result if there are internal errors to the pipelines you'll need to sort through log.txt.

Treeshop is a cheap and cheerful option to process 10's to up to 100 samples at a time. Larger scale projects will require a more sophisticated distributed computing approach. If you are not comfortable ssh'ng into various machines, running docker, and scp'ng results around then you may want to find someone that is before trying Treeshop.

While running 'fab top' will show you what dockers are running on each machine. After an initial
delay copying the fastqs over you should see the alpine running (calculating md5) and then rnaseq.

The first sample on a fresh machine will cause all the docker's to be pulled, later samples will be
a bit faster.

All the actual processing is achieved by literally calling make after copying the makefile to each
machine - this is so that this tooling and running manually are identical. The fabfile.py then adds
quite a bit of extra provenance by writing methods.json files as well as organizing everything as
per the Treehouse storage layout. That said if you have some custom additional pipelines you want to
run its fairly easy to just add another target to the Makefile and then copy/paste inside of the
fabfile.py process method.
