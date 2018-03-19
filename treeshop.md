# Treeshop Cluster Processing

To process multiple samples through the [Treehouse pipelines Makefile](https://github.com/UCSC-Treehouse/pipelines/blob/master/Makefile) we have developed a simple system using [docker-machine](https://docs.docker.com/machine/overview/) to spin up a cluster of machines on an Openstack cluster and a simple [Fabric](http://www.fabfile.org/) file to control the compute. 

## Requirements

  docker
  docker-machine
  Fabric
  Credentials for you Openstack Cluster (OS_USERNAME and OS_PASSWORD defined)

## Getting Started

Clone this repository:

    git clone https://github.com/UCSC-Treehouse/pipelines.git

Create a folders that match the [Treehouse storage layout](https://github.com/UCSC-Treehouse/pipelines/blob/master/fabfile.py#L12):

    mkdir -p treeshop/primary/original/TEST treeshop/downstream

Copy the TEST fastq samples into the storage hierarchy
  
    cp samples/*.fastq.gz treeshop/primary/original/TEST/

Spin up a single cluster machine:

    fab up

Verify that its up and you can see it in docker-machine

    docker-machine

Configure and download references

    fab configure reference

Process the samples in manifest.tsv with source and destination under the treeshop folder:

    fab process:manifest=manifest.txt,base=treeshop 2>&1 | tee log.txt
