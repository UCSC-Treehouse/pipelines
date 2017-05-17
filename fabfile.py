"""
Treeshop: The Treehouse Workshop

Experimental fabric based automation to process
a manifest and run pipelines via docker-machine.

NOTE: This is a bit of a rambling hack and very much
hard coded and idiosyncratic to the current set of
Treehouse pipelines and files they use. YMMV.
"""
import os
import re
import datetime
import csv
import json
import itertools
from fabric.api import env, local, run, sudo, runs_once, parallel, warn_only, cd
from fabric.contrib.files import exists
from fabric.operations import put, get

"""
Setup the fabric hosts environment using docker-machine ip addresses as hostnames are not
resolvable. Also point to all the per machine ssh keys. An alternative would be to use one key but
on openstack the driver deletes it on termination.
"""
def find_machines():
    """ Fill in host globals from docker-machine """
    env.user = "ubuntu"
    env.hostnames = local("docker-machine ls --filter state=Running --format '{{.Name}}'",
                          capture=True).split("\n")
    env.hosts = re.findall(r'[0-9]+(?:\.[0-9]+){3}',
                           local("docker-machine ls --filter state=Running --format '{{.URL}}'",
                                 capture=True))
    env.key_filename = ["~/.docker/machine/machines/{}/id_rsa".format(m) for m in env.hostnames]

find_machines()


@runs_once
def up(count=1):
    """ Spin up 'count' docker machines """
    print("Spinning up {} more cluster machines".format(count))
    for i in range(int(count)):
        hostname = "{}-{:%Y%m%d-%H%M%S}".format(os.environ["USER"],datetime.datetime.now())
        local("""
            docker-machine create --driver openstack \
                --openstack-tenant-name treehouse \
                --openstack-auth-url http://os-con-01.pod:5000/v2.0 \
                --openstack-ssh-user ubuntu \
                --openstack-net-name treehouse-net \
                --openstack-floatingip-pool ext-net \
                --openstack-image-name Ubuntu-16.04-LTS-x86_64 \
                --openstack-flavor-name z1.medium \
                {}
              """.format(hostname))

    # In case additional commands are called after up
    find_machines()


@runs_once
def down():
    """ Terminate ALL docker-machine machines """
    for host in env.hostnames:
        print("Terminating {}".format(host))
        local("docker-machine stop {}".format(host))
        local("docker-machine rm -f {}".format(host))


@runs_once
def machines():
    """ Print hostname, ip, and ssh key location of each machine """
    print("Machines:")
    for machine in zip(env.hostnames, env.hosts):
        print("{}/{}".format(machine[0], machine[1]))


def top():
    """ Get list of docker containers and top 3 processes """
    run("docker ps")
    run("top -b -n 1 | head -n 12  | tail -n 3")


def configure():
    """ Copy pipeline makefile over, make directories etc... """
    run("sudo gpasswd -a ubuntu docker")
    run("sudo apt-get -qy install make")

    # openstack doesn't format /mnt correctly...
    run("sudo umount /mnt")
    run("sudo parted -s /dev/vdb mklabel gpt")
    run("sudo parted -s /dev/vdb mkpart primary 2048s 100%")
    run("sudo mkfs -t ext4 /dev/vdb1")
    run("sudo sed -i 's/auto/ext4/' /etc/fstab")
    run("sudo sed -i 's/vdb/vdb1/' /etc/fstab")
    run("sudo mount /mnt")
    run("sudo chmod 1777 /mnt")

    # run("mkdir -p /mnt/data")
    # run("sudo chown ubuntu:ubuntu /mnt/data")
    # run("mkdir -p /mnt/data/references")
    # run("mkdir -p /mnt/data/samples")
    # run("mkdir -p /mnt/data/outputs")


def push():
    put("Makefile", "/mnt")
    put("references.md5", "/mnt")


@parallel
def download():
    """ Configure each machine with reference files. """
    with cd("/mnt"):
        run("make download")


def run_expression():
    with cd("/mnt"):
        run("make expression")
    return "quay.io/ucsc_cgl/rnaseq-cgl-pipeline:3.2.1-1"


def run_fusion():
    with cd("/mnt"):
        run("make fusion")
    return "jpfeil/star-fusion:0.0.2"


def variants(bam):
    run("""
		docker run --rm --name variation \
			-v /mnt/data:/data \
			-v /mnt/data/outputs/rnavar:/data/work \
			-e refgenome=references/GCA_000001405.15_GRCh38_no_alt_analysis_set.fa \
            -v {}:/data/rnaAligned.sortedByCoord.out.bam \
			-e input={} linhvoyo/gatk_rna_variant_v2
        """.format(bam))
    return "linhvoyo/gatk_rna_variant_v2"


def reset_machine():
    # Stop any existing processing and delete inputs and outputs
    with warn_only():
        run("docker stop rnaseq && docker rm rnaseq")
        run("docker stop fusion && docker rm fusion")
        sudo("rm -rf /mnt/samples/*")
        sudo("rm -rf /mnt/outputs/*")


@parallel
def process(manifest="manifest.tsv", outputs=".",
            expression="True", variants="True", fusions="True", limit=None):
    """ Process on all the samples in 'manifest' """

    def log_error(message):
        print(message)
        with open("{}/errors.txt".format(outputs), "a") as error_log:
            error_log.write(message + "\n")

    print("Processing starting on {}".format(env.host))

    # Each machine will process every #hosts samples
    for sample in itertools.islice(csv.DictReader(open(manifest, "rU"), delimiter="\t"),
                                   env.hosts.index(env.host),
                                   int(limit) if limit else None, len(env.hosts)):
        sample_id = sample["Submitter Sample ID"]
        sample_files = map(str.strip, sample["File Path"].split(","))
        print("{} processing {}".format(env.host, sample_id))

        if os.path.exists("{}/{}".format(outputs, sample_id)):
            log_error("{}/{} already exists".format(outputs, sample_id))
            continue

        # See if all the files exist
        for sample in sample_files:
            if not os.path.isfile(sample):
                log_error("{} for {} does not exist".format(sample, sample_id))
                continue

        print("Resetting {}".format(env.host))
        reset_machine()

        methods = {"user": os.environ["USER"],
                   "start": datetime.datetime.utcnow().isoformat(),
                   "treeshop_version": local(
                       "git --work-tree={0} --git-dir {0}/.git describe --always".format(
                           os.path.dirname(__file__)), capture=True),
                   "inputs": sample_files,
                   "pipelines": []}

        with cd("/mnt"):
            # Copy fastqs, fixing r1/r2 for R1/R2 if needed
            if len(sample_files) != 2:
                log_error("Expected 2 samples files {} {}".format(sample_id, sample_files))
                continue

            for fastq in sample_files:
                if not os.path.isfile(fastq):
                    log_error("Unable to find file: {} {}".format(sample_id, fastq))
                    continue
                if not exists("samples/{}".format(os.path.basename(fastq))):
                    print("Copying files....")
                    put(fastq, "samples/{}".format(
                        os.path.basename(fastq).replace("r1.", "R1.").replace("r2.", "R2.")))

        # Create folder on storage for results named after sample id
        # Wait until now in case something above fails so we don't have
        # an empty directory
        results = "{}/{}".format(outputs, sample_id)
        local("mkdir -p {}".format(results))

        # rnaseq
        if expression == "True":
            methods["pipelines"].append(run_expression())

        if fusions == "True":
            methods["pipelines"].append(run_fusion())

        get("outputs", results)

        # Write out methods
        methods["end"] = datetime.datetime.utcnow().isoformat()
        with open("{}/methods.json".format(results), "w") as f:
            f.write(json.dumps(methods, indent=4))


@runs_once
def check(manifest):
    """ Check that each file in manifest exists """
    for sample in csv.DictReader(open(manifest, "rU"), delimiter="\t"):
        sample_id = sample["Submitter Sample ID"]
        sample_files = map(str.strip, sample["File Path"].split(","))

        # See if all the files exist
        for sample in sample_files:
            if not os.path.isfile(sample):
                print("{} for {} does not exist".format(sample, sample_id))
                continue
            else:
                print("{} exists".format(sample))


def verify():
    # Verify md5 of rnaseq output from TEST samples
    with cd("/mnt/data/outputs"):
        put("TEST.md5", "/mnt/data/outputs")
        run("md5sum -c TEST.md5")
