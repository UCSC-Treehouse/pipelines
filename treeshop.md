# Treeshop Cluster Processing

To process multiple samples through the [Treehouse pipelines Makefile](https://github.com/UCSC-Treehouse/pipelines/blob/master/Makefile) we use [docker-machine](https://docs.docker.com/machine/overview/) to spin up a cluster of machines on an Openstack cluster and a simple [Fabric](http://www.fabfile.org/) file to control the compute. 

## Requirements

  docker
  docker-machine
  Fabric
  Credentials for your Openstack Cluster (OS_USERNAME and OS_PASSWORD defined)

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
    docker-machine env rcurrie-treeshop-20180319-112512
    [localhost] local: cat ~/.ssh/id_rsa.pub| docker-machine ssh rcurrie-treeshop-20180319-112512 'cat
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


Process the samples in manifest.tsv with source and destination under the treeshop folder sending log output to the console and log.txt:

    fab process:manifest=manifest.txt,base=treeshop 2>&1 | tee log.txt

## Notes

Error output with respect to finding and copying files will be written to error.log. All of the output for all machines running in parallel will end up in log.txt. As a result if there are internal errors to the pipelines you'll need to sort through log.txt.

Treeshop is a cheap and cheerful option to process 10's to up to 100 samples at a time. Larger scale projects will require a more sophisticated distributed computing approach. If you are not comfortable ssh'ng into various machines, running docker, and scp'ng results around then you may want to find someone that is before trying Treeshop.
