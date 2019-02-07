"""
Treeshop: The Treehouse Workshop

Experimental fabric based automation to process samples on a docker-machine cluster.

NOTE: This is crafted code primarily used internal to Treehouse and assumes
quite a few things about the layout of primary and secondary files both
on a shared file server and object store. If you are not familiar with
any of these it is recommended to stick with the Makefile for sample by sample
processing on the command line.

Storage Hierarchy:

Samples and outputs are managed on disk or S3 with the following hierarchy:

primary/
    original/
        id/
           *.fastq.gz, *.fq.gz, *.txt.gz or *.bam
           (multiple fastq pairs will be concatenated)
    derived/
        id/
           *.fastq.gz

downstream/
    id/
        secondary/
            pipeline-name-version-hash/
        tertiary/

NOTE: See Makefile for regex that looks from right for 1 or 2 to find pairs

"""
import os
import datetime
import json
import glob
import re
from fabric.api import env, local, run, sudo, runs_once, parallel, warn_only, cd, settings
from fabric.operations import put, get

# To debug communication issues un-comment the following
# import logging
# logging.basicConfig(level=logging.DEBUG)

"""
Setup the fabric hosts environment using docker-machine ip addresses as hostnames are not
resolvable. Also point to all the per machine ssh keys. An alternative would be to use one key but
on openstack the driver deletes it on termination.
"""


def _find_machines():
    """ Fill in host globals from docker-machine """
    env.user = "ubuntu"
    machines = [json.loads(open(m).read())["Driver"]
                for m in glob.glob(os.path.expanduser("~/.docker/machine/machines/*/config.json"))]
    env.hostnames = [m["MachineName"] for m in machines
                     if not env.hosts or m["MachineName"] in env.hosts]
    env.hosts = [m["IPAddress"] for m in machines
                 if not env.hosts or m["MachineName"] in env.hosts]
    # Use single key due to https://github.com/UCSC-Treehouse/pipelines/issues/5
    # env.key_filename = [m["SSHKeyPath"] for m in machines]
    env.key_filename = "~/.ssh/id_rsa"


_find_machines()


def _log_error(message):
    print(message)
    with open("errors.txt", "a") as error_log:
        error_log.write(message + "\n")

@runs_once
def up(count=1):
    """ Spin up 'count' docker machines """
    print("Spinning up {} more cluster machines".format(count))
    for i in range(int(count)):
        hostname = "{}-treeshop-{:%Y%m%d-%H%M%S}".format(
            os.environ["USER"], datetime.datetime.now())
        # Create a new keypair per machine due to https://github.com/docker/machine/issues/3261
        local("""
              docker-machine create --driver openstack \
              --openstack-tenant-id 41e142e18a07427caf61ed29652c8c08 \
              --openstack-auth-url http://controller:5000/v3/ \
              --openstack-domain-id default \
              --openstack-ssh-user ubuntu \
              --openstack-net-name treehouse-net \
              --openstack-floatingip-pool ext-net \
              --openstack-image-name ubuntu-16.04-LTS-x86_64 \
              --openstack-flavor-name m1.large \
              {}
              """.format(hostname))

        # Copy over single key due to https://github.com/UCSC-Treehouse/pipelines/issues/5
        local("cat ~/.ssh/id_rsa.pub" +
              "| docker-machine ssh {} 'cat >> ~/.ssh/authorized_keys'".format(hostname))

    # In case additional commands are called after up
    _find_machines()


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
    """ Get list of docker containers """
    run("docker ps")


@parallel
def configure():
    """ Copy pipeline makefile over, make directories etc... """
    sudo("gpasswd -a ubuntu docker")
    sudo("apt-get -qy install make")

    """ Downgrade docker to version supported by toil """
    run("wget https://packages.docker.com/1.12/apt/repo/pool/main/d/docker-engine/docker-engine_1.12.6~cs8-0~ubuntu-xenial_amd64.deb")  # NOQA
    sudo("apt-get -y remove docker docker-engine docker.io docker-ce containerd.io docker-ce-cli")
    sudo("rm -rf /var/lib/docker")
    sudo("service docker stop") # Service gets upset if we dpkg the new version while it's still running
    sudo("dpkg -i docker-engine_1.12.6~cs8-0~ubuntu-xenial_amd64.deb")
    sudo("service docker start")

    put("{}/Makefile".format(os.path.dirname(env.real_fabfile)), "/mnt")


@parallel
def push():
    """ Update Makefile for use when iterating and debugging """
    # Copy Makefile in case we changed it while developing...
    put("{}/Makefile".format(os.path.dirname(env.real_fabfile)), "/mnt")


@parallel
def reference():
    """ Configure each machine with reference files. """
    put("{}/md5".format(os.path.dirname(env.real_fabfile)), "/mnt")
    with cd("/mnt"):
        run("make reference")


def reset():
    """ Stop any existing processing and delete inputs and outputs """
    print("Resetting {}".format(env.host))
    with warn_only():
        run("docker stop $(docker ps -a -q)")
        run("docker rm $(docker ps -a -q)")
        sudo("rm -rf /mnt/samples/*")
        sudo("rm -rf /mnt/outputs/*")

        # Do we need this? Some pipeline looks like its changing it to root
        sudo("chown -R ubuntu:ubuntu /mnt")


@parallel
def process_ceph(manifest="manifest.tsv", base=".", checksum_only="False"):
    """ Experimental processing from ceph or s3 storage """
    import boto3
    from botocore.config import Config

    boto3.setup_default_session(profile_name="ceph")
    s3 = boto3.resource("s3", endpoint_url="http://ceph-gw-01.pod",
                        config=Config(signature_version='s3'))
    fastqs = sorted([obj.key for obj in s3.Bucket("CCLE").objects.all()
                     if re.search(r"fastq|fq", obj.key)])
    print("Found {} fastq".format(len(fastqs)))
    print(fastqs[0:8])

    pairs = [(fastqs[i], fastqs[i+1]) for i in range(0, len(fastqs), 2)]
    print("Pairs:", pairs[0:4])

    # DEBUG: Skip first big one and the other 2 we already did
    pairs = pairs[3:]

    for pair in pairs[env.hosts.index(env.host)::len(env.hosts)]:
        print("Processing {} on {}".format(pair, env.host))
        reset()

        # Copy files from s3 down to machine
        run("""
            aws --profile ceph --endpoint http://ceph-gw-01.pod/ \
                s3 cp --only-show-errors s3://CCLE/{} /mnt/samples/
            """.format(pair[0]))
        run("""
            aws --profile ceph --endpoint http://ceph-gw-01.pod/ \
                s3 cp --only-show-errors s3://CCLE/{} /mnt/samples/
            """.format(pair[1]))

        # Run checksum as a test
        with settings(warn_only=True):
            result = run("cd /mnt && make expression qc")
            if result.failed:
                _log_error("{} Failed checksums: {}".format(pair, result))
                continue

        # Unpack outputs and normalize names so we don't have sample id in them
        # Delete bam so we don't backhaul it
        with cd("/mnt/outputs/expression"):
            run("tar -xvf *.tar.gz --strip 1")
            run("rm *.tar.gz")
            run("rm -f *.bam")

        # Copy the results back to pstore
        sample_id = pair[0].split(".")[0]
        output = "{}/downstream/{}/secondary".format(base, sample_id)
        local("mkdir -p {}".format(output))

        dest = "{}/ucsc_cgl-rnaseq-cgl-pipeline-3.3.4-785eee9".format(output)
        local("mkdir -p {}".format(dest))
        results = get("/mnt/outputs/expression/*", dest)
        print(results)

        dest = "{}/ucsctreehouse-bam-umend-qc-1.1.0-cc481e4".format(output)
        local("mkdir -p {}".format(dest))
        results = get("/mnt/outputs/qc/*", dest)
        print(results)


def _put_primary(sample_id, base):
    """ Search all fastqs and bams, convert and put to machine as needed """

    # First see if there are ONLY two fastqs in derived
    files = sorted(glob.glob("{}/primary/derived/{}/*.fastq.gz".format(base, sample_id))
                   + glob.glob("{}/primary/derived/{}/*.fq.gz".format(base, sample_id)))
    if len(files) == 2:
        print("Processing two derived fastqs for {}".format(sample_id))
        for fastq in files:
            print("Copying fastq {} to cluster machine....".format(fastq))
            put(fastq, "/mnt/samples/")
        return files

    # Look for fastqs in primary
    files = sorted(glob.glob("{}/primary/original/{}/*.txt.gz".format(base, sample_id))
                   + glob.glob("{}/primary/original/{}/*.fastq.gz".format(base, sample_id))
                   + glob.glob("{}/primary/original/{}/*.fq.gz".format(base, sample_id)))

    # Two primary fastqs
    if len(files) == 2:
        print("Processing two primary fastqs for {}".format(sample_id))
        for fastq in files:
            print("Copying fastq {} to cluster machine....".format(fastq))
            put(fastq, "/mnt/samples/")
        return files

    # More then two original fastqs so concatenate
    if len(files) > 2 and len(files) % 2 == 0:
        print("Converting multiple primary fastqs for {}".format(sample_id))
        for fastq in files:
            print("Copying fastq {} to cluster machine....".format(fastq))
            put(fastq, "/mnt/samples/")
        names = [os.path.basename(f) for f in files]
        print("Names:", names)
        print("Concatenating fastqs...")
        with cd("/mnt/samples"):
            run("zcat {} | gzip > merged.R1.fastq.gz".format(" ".join(names[0::2])))
            run("zcat {} | gzip > merged.R2.fastq.gz".format(" ".join(names[1::2])))
            run("rm {}".format(" ".join(names)))  # Free up space
        return files

    # No fastqs so look for a single bam in original
    files = sorted(glob.glob("{}/primary/original/{}/*.bam".format(base, sample_id)))
    if len(files) == 1:
        print("Converting original bam for {}".format(sample_id))
        bam = os.path.basename(files[0])
        put(files[0], "/mnt/samples/")
        with cd("/mnt/samples"):
            run("docker run --rm"
                " -v /mnt/samples:/data"
                " -e input={}"
                " linhvoyo/btfv9"
                "@sha256:44f5c116f9a4a89e1fc49c6ec5aec86a9808e856f7fd125509dfe7e011f5ef59".format(bam)) # NOQA
            run("rm *.bam")  # Free up space
        local("mkdir -p {}/primary/derived/{}".format(base, sample_id))
        print("Copying fastqs back for archiving")
        get("/mnt/samples/*.log", "{}/primary/derived/{}/".format(base, sample_id))
        fastqs = get("/mnt/samples/*.fastq.gz", "{}/primary/derived/{}/".format(base, sample_id))
        return fastqs

    print("ERROR Unable to find or derive secondary input for {}".format(sample_id))
    return []


@parallel
def process(manifest="manifest.tsv", base=".", checksum_only="False"):
    """ Process all ids listed in 'manifest' """

    # Copy Makefile in case we changed it while developing...
    put("{}/Makefile".format(os.path.dirname(env.real_fabfile)), "/mnt")

    # Read ids and pick every #hosts to allocate round robin to each machine
    with open(manifest) as f:
        sample_ids = sorted([word.strip() for line in f.readlines() for word in line.split(',')
                             if word.strip()])[env.hosts.index(env.host)::len(env.hosts)]

    for sample_id in sample_ids:
        print("{} processing {}".format(env.host, sample_id))

        # Reset machine clearing all output, samples, and killing dockers
        reset()

        run("mkdir -p /mnt/samples")

        # Put secondary input files from primary storage
        fastqs = _put_primary(sample_id, base)
        print("Original fastq paths", fastqs)
        fastqs = [os.path.relpath(fastq, base) for fastq in fastqs]
        print("Relative fastq paths", fastqs)

        if not fastqs:
            _log_error("Unable find any fastqs or bams associated with {}".format(sample_id))
            continue

        # Create downstream output parent
        output = "{}/downstream/{}/secondary".format(base, sample_id)
        local("mkdir -p {}".format(output))

        # Initialize methods.json
        methods = {"user": os.environ["USER"],
                   "treeshop_version": local(
                      "git --work-tree={0} --git-dir {0}/.git describe --always".format(
                          os.path.dirname(__file__)), capture=True),
                   "sample_id": sample_id}

        # Calculate checksums
        methods["start"] = datetime.datetime.utcnow().isoformat()
        with settings(warn_only=True):
            result = run("cd /mnt && make checksums")
            if result.failed:
                _log_error("{} Failed checksums: {}".format(sample_id, result))
                continue

        # Update methods.json and copy output back
        dest = "{}/md5sum-3.7.0-ccba511".format(output)
        local("mkdir -p {}".format(dest))
        methods["inputs"] = fastqs
        methods["outputs"] = [
            os.path.relpath(p, base) for p in get("/mnt/outputs/checksums/*", dest)]
        methods["end"] = datetime.datetime.utcnow().isoformat()
        methods["pipeline"] = {
            "source": "https://github.com/gliderlabs/docker-alpine",
            "docker": {
                "url": "https://hub.docker.com/alpine",
                "version": "3.7.0",
                "hash": "sha256:ccba511b1d6b5f1d83825a94f9d5b05528db456d9cf14a1ea1db892c939cda64" # NOQA
            }
        }
        with open("{}/methods.json".format(dest), "w") as f:
            f.write(json.dumps(methods, indent=4))

        if checksum_only == "True":
            continue

        # Calculate expression
        methods["start"] = datetime.datetime.utcnow().isoformat()
        with settings(warn_only=True):
            result = run("cd /mnt && make expression")
            if result.failed:
                _log_error("{} Failed expression: {}".format(sample_id, result))
                continue

        # Create output parent - wait till now in case first pipeline halted
        output = "{}/downstream/{}/secondary".format(base, sample_id)
        local("mkdir -p {}".format(output))

        # Unpack outputs and normalize names so we don't have sample id in them
        with cd("/mnt/outputs/expression"):
            run("tar -xvf *.tar.gz --strip 1")
            run("rm *.tar.gz")
            run("mv *.sorted.bam sorted.bam")

        # Temporarily move sorted.bam to parent dir so we don't download it
        # Still pretty hacky but prevents temporary exposure of sequence data to downstream dir
        with cd("/mnt/outputs/expression"):
            run("mv sorted.bam ..")

        # Update methods.json and copy output back
        dest = "{}/ucsc_cgl-rnaseq-cgl-pipeline-3.3.4-785eee9".format(output)
        local("mkdir -p {}".format(dest))
        methods["inputs"] = fastqs
        methods["outputs"] = [
            os.path.relpath(p, base) for p in get("/mnt/outputs/expression/*", dest)]
        methods["end"] = datetime.datetime.utcnow().isoformat()
        methods["pipeline"] = {
            "source": "https://github.com/BD2KGenomics/toil-rnaseq",
            "docker": {
                "url": "https://quay.io/ucsc_cgl/rnaseq-cgl-pipeline",
                "version": "3.3.4-1.12.3",
                "hash": "sha256:785eee9f750ab91078d84d1ee779b6f74717eafc09e49da817af6b87619b0756" # NOQA
            }
        }
        with open("{}/methods.json".format(dest), "w") as f:
            f.write(json.dumps(methods, indent=4))

        # Move sorted.bam back to the expression dir so that QC can find it.
        with cd("/mnt/outputs/expression"):
            run("mv ../sorted.bam .")

        # Calculate qc (bam-umend-qc)
        methods["start"] = datetime.datetime.utcnow().isoformat()
        with settings(warn_only=True):
            result = run("cd /mnt && make qc")
            if result.failed:
                _log_error("{} Failed qc: {}".format(sample_id, result))
                continue

        # Store sortedByCoord.md.bam and .bai in primary/derived
        # First, move it out of the way momentarily so it won't get
        # downloaded into downstream
        bamdest = "{}/primary/derived/{}".format(base, sample_id)
        local("mkdir -p {}".format(bamdest))
        with cd("/mnt/outputs/qc"):
            run("mv sortedByCoord.md.bam* ..")

        # Update methods.json and copy output back
        dest = "{}/ucsctreehouse-bam-umend-qc-1.1.1-5f286d7".format(output)
        local("mkdir -p {}".format(dest))
        methods["inputs"] = ["{}/ucsc_cgl-rnaseq-cgl-pipeline-3.3.4-785eee9/sorted.bam".format(
                os.path.relpath(output, base))]
        methods["outputs"] = [
            os.path.relpath(p, base) for p in get("/mnt/outputs/qc/*", dest)]
        methods["outputs"] += [ 
            os.path.relpath(p, base) for p in get("/mnt/outputs/sortedByCoord.md.bam*", bamdest)]
        methods["end"] = datetime.datetime.utcnow().isoformat()
        methods["pipeline"] = {
            "source": "https://github.com/UCSC-Treehouse/bam-umend-qc",
            "docker": {
                "url": "https://hub.docker.com/r/ucsctreehouse/bam-umend-qc",
                "version": "1.1.1",
                "hash": "sha256:5f286d72395fcc5085a96d463ae3511554acfa4951aef7d691bba2181596c31f" # NOQA
            }
        }
        with open("{}/methods.json".format(dest), "w") as f:
            f.write(json.dumps(methods, indent=4))

        # And move the QC bam back so it's available to the variant caller
        with cd("/mnt/outputs/qc"):
            run("mv ../sortedByCoord.md.bam* .")

        # Calculate fusion
        methods["start"] = datetime.datetime.utcnow().isoformat()
        with settings(warn_only=True):
            result = run("cd /mnt && make fusions")
            if result.failed:
                _log_error("{} Failed fusions: {}".format(sample_id, result))
                continue

        # Update methods.json and copy output back
        dest = "{}/ucsctreehouse-fusion-0.1.0-3faac56".format(output)
        local("mkdir -p {}".format(dest))
        methods["inputs"] = fastqs
        methods["outputs"] = [
            os.path.relpath(p, base) for p in get("/mnt/outputs/fusions/*", dest)]
        methods["end"] = datetime.datetime.utcnow().isoformat()
        methods["pipeline"] = {
            "source": "https://github.com/UCSC-Treehouse/fusion",
            "docker": {
                "url": "https://hub.docker.com/r/ucsctreehouse/fusion",
                "version": "0.1.0",
                "hash": "sha256:3faac562666363fa4a80303943a8f5c14854a5f458676e1248a956c13fb534fd" # NOQA
            }
        }
        with open("{}/methods.json".format(dest), "w") as f:
            f.write(json.dumps(methods, indent=4))

        # Calculate jfkm
        methods["start"] = datetime.datetime.utcnow().isoformat()
        with settings(warn_only=True):
            result = run("cd /mnt && make jfkm")
            if result.failed:
                _log_error("{} Failed jfkm: {}".format(sample_id, result))
                continue

        # Update methods.json and copy output back
        dest = "{}/jpfeil-jfkm-0.1.0-26350e0".format(output)
        local("mkdir -p {}".format(dest))
        methods["inputs"] = fastqs
        methods["outputs"] = [
            os.path.relpath(p, base) for p in get("/mnt/outputs/jfkm/*", dest)]
        methods["end"] = datetime.datetime.utcnow().isoformat()
        methods["pipeline"] = {
            "source": "https://github.com/UCSC-Treehouse/jfkm",
            "docker": {
                "url": "https://cloud.docker.com/repository/docker/jpfeil/jfkm",
                "version": "0.1.0",
                "hash": "sha256:26350e02608115341fe8e735ef6d08216e71d962b176eb53b9a7bc54ef715c10" # NOQA
            }
        }
        with open("{}/methods.json".format(dest), "w") as f:
            f.write(json.dumps(methods, indent=4))

        # Calculate variants
        methods["start"] = datetime.datetime.utcnow().isoformat()
        with settings(warn_only=True):
            result = run("cd /mnt && make variants")
            if result.failed:
                _log_error("{} Failed variants: {}".format(sample_id, result))
                continue

        # Update methods.json and copy output back
        dest = "{}/ucsctreehouse-mini-var-call-0.0.1-1976429".format(output)
        local("mkdir -p {}".format(dest))
        methods["inputs"] = ["{}/sortedByCoord.md.bam".format(bamdest)]
        methods["outputs"] = [
            os.path.relpath(p, base) for p in get("/mnt/outputs/variants/*", dest)]
        methods["end"] = datetime.datetime.utcnow().isoformat()
        methods["pipeline"] = {
            "source": "https://github.com/UCSC-Treehouse/mini-var-call",
            "docker": {
                "url": "https://hub.docker.com/r/ucsctreehouse/mini-var-call",
                "version": "0.0.1",
                "hash": "sha256:197642937956ae73465ad2ef4b42501681ffc3ef07fecb703f58a3487eab37ff" # NOQA
            }
        }
        with open("{}/methods.json".format(dest), "w") as f:
            f.write(json.dumps(methods, indent=4))
