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
import dateutil.parser
import csv
import json
import itertools
import glob
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
        hostname = "{}-treeshop-{:%Y%m%d-%H%M%S}".format(os.environ["USER"],datetime.datetime.now())
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


def push():
    """ Push Makefile convenience while iterating """
    put("{}/Makefile".format(os.path.dirname(env.real_fabfile)), "/mnt")


@parallel
def configure():
    """ Copy pipeline makefile over, make directories etc... """
    sudo("gpasswd -a ubuntu docker")
    sudo("apt-get -qy install make")

    # openstack doesn't format /mnt correctly...
    sudo("umount /mnt")
    sudo("parted -s /dev/vdb mklabel gpt")
    sudo("parted -s /dev/vdb mkpart primary 2048s 100%")
    sudo("mkfs -t ext4 /dev/vdb1")
    sudo("sed -i 's/auto/ext4/' /etc/fstab")
    sudo("sed -i 's/vdb/vdb1/' /etc/fstab")
    sudo("mount /mnt")
    sudo("chmod 1777 /mnt")
    sudo("chown ubuntu:ubuntu /mnt")

    put("{}/Makefile".format(os.path.dirname(env.real_fabfile)), "/mnt")


@parallel
def reference():
    """ Configure each machine with reference files. """
    put("{}/md5".format(os.path.dirname(env.real_fabfile)), "/mnt")
    with cd("/mnt"):
        run("make reference")


def reset():
    # Stop any existing processing and delete inputs and outputs
    print("Resetting {}".format(env.host))
    with warn_only():
        run("docker stop $(docker ps -a -q)")
        run("docker rm $(docker ps -a -q)")
        sudo("rm -rf /mnt/samples/*")
        sudo("rm -rf /mnt/outputs/*")

        # Do we need this? Some pipeline looks like its changing it to root
        sudo("chown -R ubuntu:ubuntu /mnt")


@parallel
def process(manifest="manifest.tsv", outputs=".",
            expression="True", fusion="True", variant="False", limit=None):
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

        # See if all the files exist
        for sample in sample_files:
            if not os.path.isfile(sample):
                log_error("{} for {} does not exist".format(sample, sample_id))
                continue

        # Reset machine clearing all output, samples, and killing dockers
        reset()

        methods = {"user": os.environ["USER"],
                   "start": datetime.datetime.utcnow().isoformat(),
                   "treeshop_version": local(
                       "git --work-tree={0} --git-dir {0}/.git describe --always".format(
                           os.path.dirname(__file__)), capture=True),
                   "inputs": sample_files,
                   "pipelines": []}

        with cd("/mnt"):
            # Copy fastqs over to cluster machine
            if len(sample_files) != 2:
                log_error("Expected 2 samples files {} {}".format(sample_id, sample_files))
                continue

            for fastq in sample_files:
                if not exists("samples/{}".format(os.path.basename(fastq))):
                    print("Copying file {} to cluster machine....".format(fastq))
                    put(fastq, "samples/{}".format(os.path.basename(fastq)))

            # Run the pipelines
            if expression == "True":
                run("make expression")
                methods["pipelines"].append("quay.io/ucsc_cgl/rnaseq-cgl-pipeline:3.3.4-1.12.3")

            if fusion == "True":
                run("make fusion")
                methods["pipelines"].append("jpfeil/star-fusion:0.0.2")

            if variant == "True":
                run("make variant")
                methods["pipelines"].append("linhvoyo/gatk_rna_variant_v2")

        # Create folder on storage for results named after sample id
        # Wait until now in case something above fails so we don't have
        # an empty directory
        results = "{}/{}".format(outputs, sample_id)
        local("mkdir -p {}".format(results))

        # Write out methods
        methods["end"] = datetime.datetime.utcnow().isoformat()
        with open("{}/methods.json".format(results), "w") as f:
            f.write(json.dumps(methods, indent=4))

        # Copy all the output files back
        get("/mnt/outputs/*", results)


@runs_once
def check(manifest="manifest.tsv"):
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


@runs_once
def stats():
    """ Print out stats for all the samples run in the current directory """
    methods = [json.loads(open(m).read()) for m in glob.glob("**/methods.json")]
    durations = [dateutil.parser.parse(m["end"])
                 - dateutil.parser.parse(m["start"]) for m in methods]
    print([d.total_seconds()/(60*60) for d in durations])


def verify():
    # Verify md5 of rnaseq output from TEST samples
    with cd("/mnt/data/outputs"):
        put("TEST.md5", "/mnt/data/outputs")
        run("md5sum -c TEST.md5")
