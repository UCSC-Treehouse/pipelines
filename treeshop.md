# Treeshop Cluster Processing

To process multiple samples through the [Treehouse pipelines Makefile](https://github.com/UCSC-Treehouse/pipelines/blob/master/Makefile) we use [docker-machine](https://docs.docker.com/machine/overview/) to spin up a cluster of machines on Openstack and a simple [Fabric](http://www.fabfile.org/) file to control the compute.

## Requirements

* [docker](https://www.docker.com)
* [docker-machine](https://docs.docker.com/machine/overview/)
* [Fabric](http://www.fabfile.org/)
* Credentials for your Openstack Cluster (OS_USERNAME and OS_PASSWORD environment variables defined)

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

#### Installing docker-machine

From the home directory (type `cd` to get to home directory) type:

    curl -L https://github.com/docker/machine/releases/download/v0.14.0/docker-machine-`uname -s`-`uname -m` > ~/docker-machine
    install ~/docker-machine ~/bin/docker-machine

Congratulations, you are now ready to set up your docker-machine.

### Set Up

Clone this repository:

    git clone https://github.com/UCSC-Treehouse/pipelines.git

Create needed directory  and navigate into the newly cloned repository:

    mkdir ~/.aws
    cd pipelines

Create an SSH keypair in your ~/.ssh folder. This key must be named id_rsa / id_rsa.pub and it must have no passphrase.

### Processing the test sample

Create folders that match the [Treehouse storage layout](https://github.com/UCSC-Treehouse/pipelines/blob/master/fabfile.py#L12):

    mkdir -p treeshop/primary/original/TEST treeshop/downstream

Copy the TEST fastq samples into the storage hierarchy:

    cp samples/*.fastq.gz treeshop/primary/original/TEST/

Spin up a single cluster machine (make sure you have created your SSH key):

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

If you get a different output with an error mesasge, see "Alternate Setup" below.

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

    fab process:manifest=manifest.tsv,base=treeshop 2>&1 | tee log.txt

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
          │   └── RSEM
          │       ├── Hugo
          │       │   ├── rsem_genes.hugo.results
          │       │   └── rsem_isoforms.hugo.results
          │       ├── rsem_genes.results
          │       └── rsem_isoforms.results
          ├── ucsctreehouse-bam-umend-qc-1.1.0-cc481e4
          │   ├── bam_umend_qc.json
          │   ├── bam_umend_qc.tsv
          │   ├── methods.json
          │   └── readDist.txt
          ├── ucsctreehouse-fusion-0.1.0-3faac56
          │   ├── Log.final.out
          │   ├── methods.json
          │   ├── star-fusion-gene-list-filtered.final
          │   └── star-fusion-non-filtered.final
          └── ucsctreehouse-mini-var-call-0.0.1-1976429
              ├── methods.json
              └── mini.ann.vcf

The bam files generated by `qc` and `fusion` will be placed in `primary/derived`. 
Note that the bam file generated by `expression` (`sorted.bam`) is not downloaded at all.

	treeshop/primary/derived
	└── TEST
	  ├── sortedByCoord.md.bam
	  ├── sortedByCoord.md.bam.bai
	  ├── FusionInspector.junction_reads.bam
	  └── FusionInspector.spanning_reads.bam

### Alternate Setup (new 2022)

Sometimes when `fab up` runs, the machine is created but Docker does not sucessfully install.
That is ok because `fab configure` manually installs our preferred version of Docker anyhow.
If `fab up` results in an error message, run the following:

Copy your SSH key to the virtual machine:

    fab unlock

Run an alternative to configure that skips uninstalling the old Docker:

    fab installdocker

Download the reference files:

    fab reference


After this point, you can continue with the `fab process` step of the original flow and
everything should work the same.


### Shut Down

After confirming that you successfully processed your data, you may want to shut down your docker machine.
This will free up resources and space for other users.

To shut down all docker-machines type:

    fab down


## Notes

Error output with respect to finding and copying files will be written to error.log. All of the output for all machines running in parallel will end up in log.txt. As a result if there are internal errors to the pipelines you'll need to sort through log.txt.

Treeshop is a cheap and cheerful option to process 10's to up to 100 samples at a time. Larger scale projects will require a more sophisticated distributed computing approach. If you are not comfortable ssh'ng into various machines, running docker, and scp'ng results around then you may want to find someone that is before trying Treeshop.

To set up multiple machines to process large amounts of samples you can give the `fab up` command a numeric variable input.
For example, to spin up 5 machines type:

    fab up:5

When processing multiple samples you will need to format your manifest.tsv appropriately.
Each sample name will need to be placed on a separate line.
For example:

    1. TEST1
    2. TEST2
    3. TEST3
    etc.

The fabfile will automatically assign the docker-machines samples to run.  

WARNING:  Running `fab process` will automatically stop all currently running docker-machines in order to work on the newly assigned samples.
Make sure your docker-machines have finished processing their samples.
Users comfortable with changing commands may wish to learn how to restrict which machines are used to process samples by using the hosts parameter. [Fabfile hosts](http://docs.fabfile.org/en/1.14/usage/execution.html#globally-via-the-command-line).

While running `fab top` will show you what dockers are running on each machine. After an initial
delay copying the fastqs over you should see the alpine running (calculating md5) and then rnaseq.

The first sample on a fresh machine will cause all the docker's to be pulled, later samples will be
a bit faster.

All the actual processing is achieved by literally calling make after copying the makefile to each
machine - this is so that this tooling and running manually are identical. The fabfile.py then adds
quite a bit of extra provenance by writing methods.json files as well as organizing everything as
per the Treehouse storage layout. That said if you have some custom additional pipelines you want to
run its fairly easy to just add another target to the Makefile and then copy/paste inside of the
fabfile.py process method.

#### Fusion standalone pipeline
To run the fusion pipeline only, run `fab fusion` instead of `fab process` after configuring and downloading references:

    fab fusion:manifest=manifest.tsv,base=treeshop 2>&1 | tee fusion-log.txt

#### Advanced options

Users seeking more information on using multiple fabfiles or using different options should visit the Fabric website. [Fabric options](http://docs.fabfile.org/en/1.14/usage/fab.html).

For more information on selectively shutting down docker-machines review the docker-machine documentation.  [docker-machine](https://docs.docker.com/machine/reference/rm/).

## Troubleshooting

### Fatal error: Needed to prompt...

Do you see this error when you run a `fab` command like `fab top` :
```
Fatal error: Needed to prompt for the target host connection string (host: ), but input would be ambiguous in parallel mode
```

One possible cause: Do you have a machine that docker-machine still remembers, but the actual OpenStack VM is no longer around?
You can check with `docker-machine ls`. It will give you a list of OpenStacks.
Are any of them unexpected or old or something you thought you shut down? Especially if their state is "Error".
Getting rid of this machine from the docker-machine list might help.
You can do this by copying its name (eg YOURNAME-treeshop-DATE) and running:
`docker-machine rm -f YOURNAME-treeshop-DATE`).
